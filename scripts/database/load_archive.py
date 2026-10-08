#!/usr/bin/env python3
"""Offline, resumable archived-JSON -> raw, staging, core loader for Data Contract v1.

No network requests. One atomic transaction per source JSON file. Reruns
skip unchanged pages. All raw duplicates are preserved; identical net entries
are deduped only in core and conflicting natural keys enter quarantine.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ENTITIES = ('universities', 'program_groups', 'cities', 'programs', 'net_results')
PATHS = {
    'universities': ('GET','/api/tercih-kilavuz/universiteler'),
    'program_groups': ('GET','/api/tercih-kilavuz/universite-programlar'),
    'cities': ('GET','/api/tercih-kilavuz/universite-iller'),
    'programs': ('POST','/api/tercih-kilavuz/search'),
    'net_results': ('POST','/api/netler/search'),
}

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def digest(obj):
    return hashlib.sha256(canonical(obj).encode('utf-8')).hexdigest()

def read_env(path):
    out={}
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k,v=line.split('=',1)
            out[k]=v
    return out

def source_files(root):
    base=root / 'complete_data'
    if not base.is_dir():
        raise FileNotFoundError(f'Archive missing: {base}')
    for entity in ENTITIES:
        if entity in ENTITIES[:3]:
            path=base/entity/'all.json'
            if path.exists(): yield entity,None,None,path
        else:
            for path in sorted((base/entity).glob('*/page_*.json')):
                score=path.parent.name
                if score not in ('SAY','EA','SÖZ','DİL','TYT'): continue
                m=re.fullmatch(r'page_(\d+)\.json',path.name)
                if m: yield entity,score,int(m.group(1)),path

def parse_file(path,entity):
    obj=json.loads(path.read_text(encoding='utf-8-sig'))
    if entity in ENTITIES[:3]:
        if not isinstance(obj,list): raise ValueError(f'{path}: expected list')
        content=obj
    else:
        if not isinstance(obj,dict) or not isinstance(obj.get('content'),list):
            raise ValueError(f'{path}: expected search JSON with content[]')
        content=obj['content']
    if not all(isinstance(x,dict) for x in content):
        raise ValueError(f'{path}: non-object in content')
    return obj,content

def parse_int(obj,key):
    value=obj.get(key)
    if value is None or value == '': return None
    if isinstance(value,bool): raise ValueError(f'{key}: unexpected bool')
    return int(value)

def field_values(row,fields,Jsonb):
    result=[]
    for f in fields:
        value=row.get(f['api_field'])
        if value is not None and f['sql_type']=='JSONB':
            value=Jsonb(value)
        result.append(value)
    return result

def quarantine(cur,run_id,entity,reason,natural_key,srid,candidate,Jsonb):
    cur.execute('''INSERT INTO quality.quarantined_records
      (ingestion_run_id,entity,reason,natural_key,source_record_ids,candidate_payloads)
      VALUES (%s,%s,%s,%s,%s,%s)''',
      (run_id,entity,reason,Jsonb(natural_key),Jsonb([srid]),Jsonb([candidate])))

def canonical_upsert(cur,entity,row,srid,run_id,Jsonb,stats):
    if entity=='universities':
        id_=parse_int(row,'universiteId')
        if id_ is None or not row.get('universiteAdi'):
            return quarantine(cur,run_id,entity,'missing_university_key',row,srid,row,Jsonb)
        cur.execute('''INSERT INTO core.universities (universite_id,universite_adi,source_record_id)
           VALUES (%s,%s,%s) ON CONFLICT (universite_id) DO UPDATE SET
           universite_adi=EXCLUDED.universite_adi,source_record_id=EXCLUDED.source_record_id,
           updated_at=now()''',(id_,row['universiteAdi'],srid))
    elif entity=='cities':
        id_=parse_int(row,'ilKodu')
        if id_ is None or not row.get('ilAdi'):
            return quarantine(cur,run_id,entity,'missing_city_key',row,srid,row,Jsonb)
        cur.execute('''INSERT INTO core.cities (il_kodu,il_adi,source_record_id)
           VALUES (%s,%s,%s) ON CONFLICT (il_kodu) DO UPDATE SET
           il_adi=EXCLUDED.il_adi,source_record_id=EXCLUDED.source_record_id,updated_at=now()''',
           (id_,row['ilAdi'],srid))
    elif entity=='program_groups':
        gid=parse_int(row,'birimGrupId'); score=row.get('puanTuru')
        if gid is None or not score or not row.get('birimGrupAdi'):
            return quarantine(cur,run_id,entity,'missing_program_group_key',row,srid,row,Jsonb)
        cur.execute('''INSERT INTO core.program_groups (birim_grup_id,puan_turu,birim_grup_adi,source_record_id)
           VALUES (%s,%s,%s,%s) ON CONFLICT (birim_grup_id,puan_turu) DO UPDATE SET
           birim_grup_adi=EXCLUDED.birim_grup_adi,source_record_id=EXCLUDED.source_record_id''',
           (gid,score,row['birimGrupAdi'],srid))
    elif entity=='programs':
        code=parse_int(row,'kilavuzKodu'); year=parse_int(row,'yil'); uni=parse_int(row,'universiteId')
        if not code or not year or not uni or not row.get('birimAdi') or not row.get('puanTuru'):
            return quarantine(cur,run_id,entity,'missing_program_key',{'kilavuzKodu':code,'yil':year},srid,row,Jsonb)
        g=parse_int(row,'birimGrupId')
        # Avoid breaking the batch if future datasets reference missing lookups.
        if g is not None:
            cur.execute('SELECT 1 FROM core.program_groups WHERE birim_grup_id=%s AND puan_turu=%s',(g,row['puanTuru']))
            if cur.fetchone() is None: g=None; stats['unresolved_program_group']+=1
        cur.execute('SELECT 1 FROM core.universities WHERE universite_id=%s',(uni,))
        if cur.fetchone() is None:
            stats['unresolved_university']+=1
            return quarantine(cur,run_id,entity,'missing_parent_university',{'universiteId':uni},srid,row,Jsonb)
        city=parse_int(row,'ilKodu')
        if city is not None:
            cur.execute('SELECT 1 FROM core.cities WHERE il_kodu=%s',(city,))
            if cur.fetchone() is None: city=None; stats['unresolved_city']+=1
        cur.execute('''INSERT INTO core.program_versions
          (kilavuz_kodu,yil,universite_id,il_kodu,birim_grup_id,puan_turu,
           birim_id,birim_adi,fymk_id,min_puan,basari_sirasi,kontenjan,source_record_id,remaining_fields)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (kilavuz_kodu,yil) DO UPDATE SET
             universite_id=EXCLUDED.universite_id,il_kodu=EXCLUDED.il_kodu,
             birim_grup_id=EXCLUDED.birim_grup_id,puan_turu=EXCLUDED.puan_turu,
             birim_id=EXCLUDED.birim_id,birim_adi=EXCLUDED.birim_adi,
             fymk_id=EXCLUDED.fymk_id,min_puan=EXCLUDED.min_puan,
             basari_sirasi=EXCLUDED.basari_sirasi,kontenjan=EXCLUDED.kontenjan,
             source_record_id=EXCLUDED.source_record_id,
             remaining_fields=EXCLUDED.remaining_fields,ingested_at=now()
           RETURNING program_version_id''',(
            code,year,uni,city,g,row['puanTuru'],parse_int(row,'birimId'),row['birimAdi'],
            parse_int(row,'fymkId'),row.get('minPuan'),parse_int(row,'basariSirasi'),
            parse_int(row,'kontenjan'),srid,Jsonb(row)))
        pvid=cur.fetchone()[0]
        conditions=row.get('kosulList')
        if isinstance(conditions,list):
            for entry in conditions:
                if not isinstance(entry,dict): continue
                for condition_code,description in entry.items():
                    cur.execute('''INSERT INTO core.conditions (condition_code,description)
                        VALUES (%s,%s) ON CONFLICT (condition_code) DO NOTHING''',
                        (str(condition_code),str(description) if description is not None else None))
                    cur.execute('''INSERT INTO core.program_conditions (program_version_id,condition_code)
                        VALUES (%s,%s) ON CONFLICT DO NOTHING''',(pvid,str(condition_code)))
    elif entity=='net_results':
        code=parse_int(row,'kilavuzKodu'); year=parse_int(row,'yil'); score=row.get('puanTuru')
        if not code or not year or not score:
            return quarantine(cur,run_id,entity,'missing_net_key',{'kilavuzKodu':code,'yil':year,'puanTuru':score},srid,row,Jsonb)
        cur.execute('''INSERT INTO core.net_results (
          kilavuz_kodu,yil,puan_turu,universite_id,birim_grup_id,taban_puan,katsayi,obp,
          tyt_trk_net,tyt_sos_net,tyt_mat_net,tyt_fen_net,
          ayt_mat_net,ayt_fiz_net,ayt_kim_net,ayt_bio_net,ayt_tde_net,ayt_trh1_net,
          ayt_cog1_net,ayt_trh2_net,ayt_cog2_net,ayt_fel_net,ayt_din_net,ydt_ydil_net,
          source_record_id,remaining_fields)
          VALUES ('''+','.join(['%s']*26)+''') ON CONFLICT (kilavuz_kodu,yil,puan_turu) DO NOTHING
          RETURNING net_result_id''',(
           code,year,score,parse_int(row,'universiteId'),parse_int(row,'birimGrupId'),
           row.get('tabanPuan'),row.get('katsayi'),row.get('obp'),
           row.get('tytTrkNet'),row.get('tytSosNet'),row.get('tytMatNet'),row.get('tytFenNet'),
           row.get('aytMatNet'),row.get('aytFizNet'),row.get('aytKimNet'),row.get('aytBioNet'),
           row.get('aytTdeNet'),row.get('aytTrh1Net'),row.get('aytCog1Net'),row.get('aytTrh2Net'),
           row.get('aytCog2Net'),row.get('aytFelNet'),row.get('aytDinNet'),row.get('ydtYdilNet'),
           srid,Jsonb(row)))
        if cur.fetchone() is None:
            cur.execute('''SELECT sr.record FROM core.net_results n
                LEFT JOIN raw.source_records sr ON sr.source_record_id=n.source_record_id
                WHERE n.kilavuz_kodu=%s AND n.yil=%s AND n.puan_turu=%s''',(code,year,score))
            old=cur.fetchone()
            if old and old[0]==row:
                stats['identical_net_duplicate']+=1
            else:
                stats['conflicting_net_duplicate']+=1
                quarantine(cur,run_id,entity,'conflicting_net_natural_key',
                   {'kilavuzKodu':code,'yil':year,'puanTuru':score},srid,row,Jsonb)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',default='outputs/yokatlas_full',help='folder containing complete_data')
    ap.add_argument('--env-file',default=None,help='path to DB .env (default: next to this package compose.yaml)')
    ap.add_argument('--max-files',type=int,default=0,help='0=all, otherwise import only first N files')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    root=Path(args.root)
    inputs=list(source_files(root))
    if not inputs: ap.error(f'No JSON files under {root}/complete_data')
    if args.max_files>0: inputs=inputs[:args.max_files]
    print(f'Files found: {len(inputs)}; archive root: {root}')
    if args.dry_run:
        counts=Counter()
        for entity,score,page,path in inputs:
            _,rows=parse_file(path,entity)
            counts[entity]+=len(rows)
        print('Dry run row counts:',dict(counts)); return
    try:
        import psycopg
        from psycopg import sql
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit('Install requirements: python -m pip install -r requirements.txt') from exc
    pkgroot=Path(__file__).resolve().parents[2]
    env=read_env(Path(args.env_file) if args.env_file else pkgroot/'.env')
    if not env.get('ATLAS_INGEST_PASSWORD'):
        raise SystemExit('ATLAS_INGEST_PASSWORD missing; run scripts/setup.ps1')
    contract=json.loads((pkgroot/'docs/database/data_contract_v1.json').read_text(encoding='utf-8'))
    fields=contract['observed_field_metadata']
    stats=Counter()
    with psycopg.connect(host='127.0.0.1',port=int(env.get('POSTGRES_PORT',5433)),
        dbname='yokatlas_intelligence',user='atlas_ingest',password=env['ATLAS_INGEST_PASSWORD'],
        autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute('''INSERT INTO raw.ingestion_runs (source_system,scraper_version,details)
                VALUES ('yokatlas','offline-archive-bootstrap-1',%s) RETURNING ingestion_run_id''',
                (Jsonb({'archive_root':str(root),'source_files':len(inputs)}),))
            run_id=cur.fetchone()[0]
        try:
            for fileidx,(entity,score,page,path) in enumerate(inputs,1):
                obj,rows=parse_file(path,entity)
                payload_hash=digest(obj)
                method,endpoint=PATHS[entity]
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute('''INSERT INTO raw.api_responses
                            (ingestion_run_id,endpoint,method,score_type,page_number,
                             source_hash_sha256,http_status,payload,source_path)
                             VALUES (%s,%s,%s,%s,%s,%s,200,%s,%s)
                             ON CONFLICT DO NOTHING RETURNING api_response_id''',
                            (run_id,endpoint,method,score,page,payload_hash,Jsonb(obj),str(path)))
                        r=cur.fetchone()
                        if r is None:
                            stats['unchanged_files_skipped']+=1
                            continue
                        response_id=r[0]
                        api_fields=fields[entity]
                        for index,row in enumerate(rows):
                            cur.execute('''INSERT INTO raw.source_records
                                (api_response_id,source_entity,source_array_index,record,record_hash_sha256)
                                VALUES (%s,%s,%s,%s,%s) RETURNING source_record_id''',
                                (response_id,entity,index,Jsonb(row),digest(row)))
                            srid=cur.fetchone()[0]
                            colnames=[f['sql_column'] for f in api_fields]
                            # Identifiers are derived from the checked-in contract, never API payload text.
                            query=sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
                                sql.Identifier('staging',entity),
                                sql.SQL(',').join(map(sql.Identifier,['source_record_id',*colnames,'source_payload'])),
                                sql.SQL(',').join(sql.Placeholder() for _ in range(len(colnames)+2)))
                            cur.execute(query,(srid,*field_values(row,api_fields,Jsonb),Jsonb(row)))
                            canonical_upsert(cur,entity,row,srid,run_id,Jsonb,stats)
                            stats[entity]+=1
                stats['files_imported']+=1
                if fileidx%20==0 or fileidx==len(inputs):
                    print(f'{fileidx}/{len(inputs)} files, {sum(stats[k] for k in ENTITIES)} rows staged',flush=True)
            with conn.cursor() as cur:
                cur.execute('''UPDATE raw.ingestion_runs SET status='completed',completed_at=now(),
                    details=%s WHERE ingestion_run_id=%s''',(Jsonb(dict(stats)),run_id))
        except Exception as e:
            with conn.cursor() as cur:
                cur.execute('''UPDATE raw.ingestion_runs SET status='failed',completed_at=now(),
                    details=%s WHERE ingestion_run_id=%s''',(Jsonb({'error':str(e),**stats}),run_id))
            raise
    print('Finished:',json.dumps(dict(stats),ensure_ascii=False))

if __name__=='__main__': main()
