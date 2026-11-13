#!/usr/bin/env python3
"""Offline, resumable archived-JSON -> raw, staging, core loader for Data Contract v1.

No network requests. One atomic transaction per source JSON file. Reruns
reuse RAW pages; new snapshots refresh CORE even for known content. Identical net entries
are deduped only in core and conflicting natural keys enter quarantine.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
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
            if len(v)>=2 and v[0]==v[-1] and v[0] in ('"',"'"): v=v[1:-1]
            out[k.strip()]=v
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
    if isinstance(value,bool) or not isinstance(value,(str,int,float)):
        raise ValueError(f'{key}: expected integer')
    if isinstance(value,float) and (not math.isfinite(value) or not value.is_integer() or abs(value)>2**53):
        raise ValueError(f'{key}: expected whole number')
    number=int(value)
    if not -(2**63) <= number < 2**63: raise ValueError(f'{key}: outside BIGINT range')
    return number

def parse_float(obj,key):
    value=obj.get(key)
    if value is None or value=='': return None
    if isinstance(value,bool): raise ValueError(f'{key}: unexpected bool')
    number=float(value)
    if not math.isfinite(number): raise ValueError(f'{key}: non-finite number')
    return number

def field_values(row,fields,Jsonb):
    result=[]
    for f in fields:
        value=row.get(f['api_field'])
        if value is not None:
            typ=f['sql_type']
            if typ=='JSONB':
                if f['api_field']=='kosulList' and (not isinstance(value,list) or
                        not all(isinstance(entry,dict) and all(code.strip() and
                            (description is None or isinstance(description,str))
                            for code,description in entry.items()) for entry in value)):
                    raise ValueError('kosulList: expected condition code/description objects')
                value=Jsonb(value)
            elif typ=='BIGINT': value=parse_int(row,f['api_field'])
            elif typ=='DOUBLE PRECISION': value=parse_float(row,f['api_field'])
            elif typ=='TEXT':
                if isinstance(value,(bool,dict,list)): raise ValueError(f"{f['api_field']}: expected text/scalar")
                value=str(value)
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
            parse_int(row,'fymkId'),parse_float(row,'minPuan'),parse_int(row,'basariSirasi'),
            parse_int(row,'kontenjan'),srid,Jsonb(row)))
        pvid=cur.fetchone()[0]
        conditions=row.get('kosulList')
        if isinstance(conditions,list):
            if not all(isinstance(entry,dict) for entry in conditions):
                raise ValueError('kosulList: expected a list of objects')
            cur.execute('DELETE FROM core.program_conditions WHERE program_version_id=%s',(pvid,))
            for entry in conditions:
                for condition_code,description in entry.items():
                    cur.execute('''INSERT INTO core.conditions AS c (condition_code,description,raw_details)
                        VALUES (%s,%s,%s) ON CONFLICT (condition_code) DO UPDATE SET
                        description=CASE WHEN coalesce((c.raw_details->>'description_year')::int,0)
                            <=(EXCLUDED.raw_details->>'description_year')::int
                            THEN EXCLUDED.description ELSE c.description END,
                        raw_details=c.raw_details || jsonb_build_object(
                            'description_year',greatest(coalesce((c.raw_details->>'description_year')::int,0),
                                (EXCLUDED.raw_details->>'description_year')::int),
                            'descriptions_by_year',coalesce(c.raw_details->'descriptions_by_year','{}'::jsonb)
                                || (EXCLUDED.raw_details->'descriptions_by_year'))''',
                        (str(condition_code),str(description) if description is not None else None,
                         Jsonb({'description_year':year,'descriptions_by_year':{str(year):description}})))
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
           parse_float(row,'tabanPuan'),parse_float(row,'katsayi'),parse_float(row,'obp'),
           parse_float(row,'tytTrkNet'),parse_float(row,'tytSosNet'),parse_float(row,'tytMatNet'),parse_float(row,'tytFenNet'),
           parse_float(row,'aytMatNet'),parse_float(row,'aytFizNet'),parse_float(row,'aytKimNet'),parse_float(row,'aytBioNet'),
           parse_float(row,'aytTdeNet'),parse_float(row,'aytTrh1Net'),parse_float(row,'aytCog1Net'),parse_float(row,'aytTrh2Net'),
           parse_float(row,'aytCog2Net'),parse_float(row,'aytFelNet'),parse_float(row,'aytDinNet'),parse_float(row,'ydtYdilNet'),
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
        cur.execute('''UPDATE core.net_results n SET program_version_id=(
            SELECT p.program_version_id FROM core.program_versions p
            WHERE p.kilavuz_kodu=n.kilavuz_kodu AND p.yil=n.yil AND p.puan_turu=n.puan_turu)
            WHERE n.kilavuz_kodu=%s AND n.yil=%s AND n.puan_turu=%s''',(code,year,score))

def import_archive(root, env_file=None, max_files=0, dry_run=False, on_progress=None):
    """Import each page atomically; committed pages are safe to replay after a crash."""
    root=Path(root).resolve()
    inputs=list(source_files(root))
    if not inputs: raise ValueError(f'No JSON files under {root}/complete_data')
    total_inputs=len(inputs)
    if max_files>0: inputs=inputs[:max_files]
    if dry_run:
        counts=Counter()
        for entity,score,page,path in inputs:
            _,rows=parse_file(path,entity)
            counts[entity]+=len(rows)
        return dict(counts)
    import psycopg
    from psycopg import sql
    from psycopg.types.json import Jsonb
    pkgroot=Path(__file__).resolve().parents[2]
    if env_file and not Path(env_file).is_file(): raise ValueError('Database env file does not exist')
    env={**read_env(Path(env_file) if env_file else pkgroot/'.env'),**os.environ}
    password=env.get('PGPASSWORD') or env.get('ATLAS_INGEST_PASSWORD')
    if not password: raise ValueError('Set PGPASSWORD or ATLAS_INGEST_PASSWORD in the environment or env file')
    fields=json.loads((pkgroot/'docs/database/data_contract_v1.json').read_text())['observed_field_metadata']
    manifest_path=root/'manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if manifest and manifest.get('phase') not in ('collected','importing','completed','archived'):
        raise ValueError('Snapshot collection is incomplete; resume collection before importing')
    if manifest and total_inputs!=sum(part['pages'] for part in manifest['partitions'].values()):
        raise ValueError('Snapshot is missing archived pages or contains unexpected pages')
    stats=Counter()
    observations=[]
    params=dict(host=env.get('PGHOST','127.0.0.1'),
        port=int(env.get('PGPORT',env.get('POSTGRES_PORT','5433'))),
        dbname=env.get('PGDATABASE','yokatlas_intelligence'),
        user=env.get('PGUSER','atlas_ingest'),password=password,
        connect_timeout=10,autocommit=True,
        options='-c statement_timeout=60000 -c lock_timeout=10000')
    for name,param in [('PGSSLMODE','sslmode'),('PGSSLROOTCERT','sslrootcert')]:
        if env.get(name): params[param]=env[name]
    with psycopg.connect(**params) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(hashtext('yokatlas_archive_loader'))")
            if not cur.fetchone()[0]: raise RuntimeError('Another YOK Atlas importer is running')
            cur.execute("""SELECT details->'observed_response_ids' FROM raw.ingestion_runs
                WHERE scraper_version='yokatlas-archive-2' AND details->>'archive_root'=%s""",(str(root),))
            completed_responses={response_id for row in cur.fetchall() for response_id in (row[0] or [])}
            cur.execute("""UPDATE raw.ingestion_runs SET status='interrupted',completed_at=now()
                WHERE status='running' AND scraper_version='yokatlas-archive-2'
                  AND details->>'archive_root'=%s""",(str(root),))
            cur.execute("""INSERT INTO raw.ingestion_runs (source_system,scraper_version,details)
                VALUES ('yokatlas','yokatlas-archive-2',%s) RETURNING ingestion_run_id""",
                (Jsonb({'archive_root':str(root),'source_files':len(inputs)}),))
            run_id=cur.fetchone()[0]
        try:
            for index,(entity,score,page,path) in enumerate(inputs,1):
                if on_progress: on_progress(entity,score,page,index-1,len(inputs),dict(stats))
                obj,rows=parse_file(path,entity)
                relative=path.relative_to(root).as_posix()
                meta_path=path.with_suffix('.meta.json')
                meta=json.loads(meta_path.read_text()) if manifest and meta_path.exists() else None
                if manifest and not meta: raise ValueError(f'Missing archive receipt: {relative}')
                # Bot archives retain exact response bytes; legacy archives keep their original identity convention.
                payload_hash=hashlib.sha256(path.read_bytes()).hexdigest() if meta else digest(obj)
                if meta and payload_hash!=meta['sha256']: raise ValueError(f'Archive checksum mismatch: {relative}')
                method,endpoint=PATHS[entity]
                delta=Counter()
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute("""INSERT INTO raw.api_responses
                            (ingestion_run_id,endpoint,method,score_type,page_number,captured_at,
                             source_hash_sha256,http_status,payload,source_path)
                             VALUES (%s,%s,%s,%s,%s,coalesce(%s::timestamptz,now()),%s,200,%s,%s)
                             ON CONFLICT DO NOTHING RETURNING api_response_id""",
                            (run_id,endpoint,method,score,page,meta['captured_at'] if meta else None,
                             payload_hash,Jsonb(obj),str(path)))
                        found=cur.fetchone()
                        if found is None:
                            cur.execute("""SELECT r.api_response_id,ir.details->>'archive_root'
                                FROM raw.api_responses r JOIN raw.ingestion_runs ir USING (ingestion_run_id)
                                WHERE endpoint=%s AND coalesce(score_type,'')=coalesce(%s,'')
                                  AND coalesce(page_number,-1)=coalesce(%s,-1) AND source_hash_sha256=%s""",
                                (endpoint,score,page,payload_hash))
                            response_id,original_root=cur.fetchone()
                            cur.execute('SELECT count(*) FROM raw.source_records WHERE api_response_id=%s',(response_id,))
                            if cur.fetchone()[0]!=len(rows):
                                raise ValueError(f'Existing RAW page is incomplete: {relative}')
                            # A RAW-only writer must not make us skip ETL for an existing response.
                            cur.execute(sql.SQL("""SELECT count(*) FROM raw.source_records r
                                LEFT JOIN staging.{} s USING (source_record_id)
                                WHERE r.api_response_id=%s AND s.source_record_id IS NULL
                                  AND NOT EXISTS (SELECT 1 FROM quality.quarantined_records q
                                      WHERE q.source_record_ids @> jsonb_build_array(r.source_record_id))""").format(sql.Identifier(entity)),(response_id,))
                            if cur.fetchone()[0]: raise ValueError(f'Existing RAW page has unfinished ETL: {relative}')
                            if original_root==str(root) or response_id in completed_responses:
                                delta['unchanged_files_skipped']+=1
                            else:
                                # A later snapshot may revert to previously seen values; RAW dedup must not leave CORE stale.
                                cur.execute(sql.SQL('''SELECT r.record,r.source_record_id
                                    FROM raw.source_records r JOIN staging.{} s USING (source_record_id)
                                    WHERE r.api_response_id=%s ORDER BY r.source_array_index''').format(sql.Identifier(entity)),(response_id,))
                                for record,srid in cur.fetchall():
                                    canonical_upsert(cur,entity,record,srid,run_id,Jsonb,delta)
                                delta['files_reapplied']+=1
                        else:
                            response_id=found[0]
                            api_fields=fields[entity]
                            query=sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
                                sql.Identifier('staging',entity),
                                sql.SQL(',').join(map(sql.Identifier,['source_record_id',*[f['sql_column'] for f in api_fields],'source_payload'])),
                                sql.SQL(',').join(sql.Placeholder() for _ in range(len(api_fields)+2)))
                            for row_index,row in enumerate(rows):
                                cur.execute("""INSERT INTO raw.source_records
                                    (api_response_id,source_entity,source_array_index,record,record_hash_sha256)
                                    VALUES (%s,%s,%s,%s,%s) RETURNING source_record_id""",
                                    (response_id,entity,row_index,Jsonb(row),digest(row)))
                                srid=cur.fetchone()[0]
                                try: values=field_values(row,api_fields,Jsonb)
                                except (ValueError,TypeError,OverflowError):
                                    quarantine(cur,run_id,entity,'invalid_field_type',
                                        {'source_array_index':row_index},srid,row,Jsonb)
                                    continue
                                cur.execute(query,(srid,*values,Jsonb(row)))
                                canonical_upsert(cur,entity,row,srid,run_id,Jsonb,delta)
                                delta[entity]+=1
                            delta['files_imported']+=1
                        cur.execute("""SELECT count(*) FROM quality.quarantined_records q
                            WHERE EXISTS (SELECT 1 FROM raw.source_records r
                                WHERE r.api_response_id=%s AND q.source_record_ids @> jsonb_build_array(r.source_record_id))""",(response_id,))
                        delta['quarantined_records']+=cur.fetchone()[0]
                stats.update(delta)
                observations.append(response_id)
                details={'archive_root':str(root),'source_files':len(inputs),'processed_files':index,
                    'observed_response_ids':observations,'source_parameters':manifest.get('parameters',{}) if manifest else {},
                    'stats':dict(stats)}
                with conn.cursor() as cur:
                    cur.execute('UPDATE raw.ingestion_runs SET details=%s WHERE ingestion_run_id=%s',(Jsonb(details),run_id))
                if on_progress: on_progress(entity,score,page,index,len(inputs),dict(stats))
            issues=any(stats[key] for key in ('quarantined_records','unresolved_program_group','unresolved_city'))
            status=('partial' if len(inputs)<total_inputs else 'completed_with_issues' if issues else 'completed')
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO quality.data_quality_checks
                    (ingestion_run_id,check_name,status,observed_value) VALUES (%s,%s,%s,%s)""",
                    (run_id,'archive_import','passed' if status=='completed' else 'warning',Jsonb(dict(stats))))
                cur.execute("""UPDATE raw.ingestion_runs SET status=%s,completed_at=now(),details=%s
                    WHERE ingestion_run_id=%s""",(status,Jsonb(details),run_id))
            return {'run_id':run_id,'status':status,**stats}
        except BaseException as exc:
            # Avoid logging credentials/connection strings carried by driver exceptions.
            if not conn.closed:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""UPDATE raw.ingestion_runs SET status='failed',completed_at=now(),details=%s
                            WHERE ingestion_run_id=%s""",(Jsonb({'archive_root':str(root),
                            'error_type':type(exc).__name__,'observed_response_ids':observations,'stats':dict(stats)}),run_id))
                except psycopg.Error: pass
            raise


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',default='outputs/yokatlas_full',help='folder containing complete_data')
    ap.add_argument('--env-file',default=None,help='database env file (environment variables take precedence)')
    ap.add_argument('--max-files',type=int,default=0,help='0=all, otherwise import only first N files')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args(argv)
    try:
        result=import_archive(args.root,args.env_file,args.max_files,args.dry_run)
    except ImportError as exc:
        raise SystemExit('Install requirements: python -m pip install -r database/requirements.txt') from exc
    print('Finished:',json.dumps(result,ensure_ascii=False))


if __name__=='__main__': main()
