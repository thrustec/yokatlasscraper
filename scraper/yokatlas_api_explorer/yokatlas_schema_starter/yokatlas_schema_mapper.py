#!/usr/bin/env python3
"""Infer an auditable relational schema from YOK Atlas explorer outputs.

Usage (PowerShell): python yokatlas_schema_mapper.py --input outputs/yokatlas_discovery --out outputs/schema
No HTTP calls are made. Does not assume that unobserved endpoints/tables do not exist.
Python 3.10+, standard library only.
"""
import argparse
import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ENTITY_SPEC = {
 'universities': ('universiteler','[].', 'universiteId'),
 'program_groups': ('program_gruplari','[].','birimGrupId'),
 'cities': ('iller','[].','ilKodu'),
 'programs': ('program_arama','content[].','kilavuzKodu'),
 'net_results': ('net_arama','content[].',None),
}
LOOKUP = {'universiteler':'universities','program_gruplari':'program_groups','iller':'cities','program_arama':'programs','net_arama':'net_results'}
# Explicit *candidates* based on field names, never claim proven by name alone.
LINKS = [
 ('programs','universiteId','universities','universiteId'),
 ('programs','birimGrupId','program_groups','birimGrupId'),
 ('programs','ilKodu','cities','ilKodu'),
 ('net_results','universiteId','universities','universiteId'),
 ('net_results','birimGrupId','program_groups','birimGrupId'),
 ('net_results','kilavuzKodu','programs','kilavuzKodu'),
 ('net_results','birimId','programs','birimId'),
 ('net_results','kilavuzKodu+yil','programs','kilavuzKodu+yil'),
]
YEAR_SUFFIX_RE = re.compile(r'^(minPuan|basariSirasi|kontenjan|yerlesen|gk|obk|sgy)([123])$')

def jload(p, default=None):
    try: return json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError): return default

def dump(p,obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def csvout(p,rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows: return
    cols=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)

def sql_name(s):
    s=re.sub('([a-z0-9])([A-Z])',r'\1_\2',s)
    return re.sub('[^a-zA-Z0-9_]','_',s).lower()

def normalize(v):
    if v is None: return None
    if isinstance(v,str): return v.strip()
    return v

def infer_type(observed):
    kinds={k.split(':')[0] for k in (observed or '').split('|') if ':' in k}
    kinds.discard('null')
    if not kinds: return 'TEXT'
    if kinds <= {'integer'}: return 'INTEGER'
    if kinds <= {'integer','number'}: return 'REAL'
    if kinds <= {'boolean'}: return 'INTEGER'
    return 'TEXT'  # use TEXT for mixed-type and nested JSON

def extract_samples(root):
    out=defaultdict(list)
    for name,path in [('universities',root/'lookups'/'universiteler.json'),('program_groups',root/'lookups'/'program_gruplari.json'),('cities',root/'lookups'/'iller.json')]:
        records=jload(path,[])
        if isinstance(records,list): out[name].extend(x for x in records if isinstance(x,dict))
    for path in sorted((root/'samples').glob('*.json')) if (root/'samples').exists() else []:
        if path.name.startswith('program_arama_'): dest='programs'
        elif path.name.startswith('net_arama_'): dest='net_results'
        else: continue
        page=jload(path,{})
        if isinstance(page,dict) and isinstance(page.get('content'),list):
            out[dest].extend(x for x in page['content'] if isinstance(x,dict))
    return out

def uniqueness(rows,cols):
    if not rows: return {'observed':0,'non_null':0,'distinct':0,'uniqueness':None,'duplicates':None}
    vals=[]
    for r in rows:
        v=tuple(normalize(r.get(col)) for col in cols)
        if all(x is not None and x!='' for x in v): vals.append(v)
    n=len(vals); unique=len(set(vals))
    return {'observed':len(rows),'non_null':n,'distinct':unique,'uniqueness':round(unique/n,5) if n else None,'duplicates':n-unique}

def overlap(src,scols,dst,dcols):
    a={tuple(normalize(r.get(c)) for c in scols) for r in src}
    b={tuple(normalize(r.get(c)) for c in dcols) for r in dst}
    a={x for x in a if all(v is not None and v!='' for v in x)}
    b={x for x in b if all(v is not None and v!='' for v in x)}
    return {'source_distinct':len(a),'target_distinct':len(b), 'matched':len(a&b),
            'coverage':round(len(a&b)/len(a),5) if a else None}

def main():
    p=argparse.ArgumentParser(description='Build schema, relation evidence, DDL and ERD from YOK Atlas discovery artifacts')
    p.add_argument('--input', default='outputs/yokatlas_discovery',help='Explorer output directory')
    p.add_argument('--out', default='outputs/schema',help='Schema export directory')
    a=p.parse_args(); root=Path(a.input); target=Path(a.out); target.mkdir(parents=True,exist_ok=True)
    inv=jload(root/'field_inventory.json')
    if not isinstance(inv,list): p.error(f'Missing {root / "field_inventory.json"}')
    samples=extract_samples(root)
    tables=[]; fields=[]; fieldset={}
    for table,(endpoint,prefix,pk) in ENTITY_SPEC.items():
        rows=[]
        for r in inv:
            path=r.get('json_path','')
            if r.get('endpoint') != endpoint or not path.startswith(prefix): continue
            key=path[len(prefix):]
            if not key or '.' in key or '[]' in key: continue
            rows.append({'table':table,'source_endpoint':endpoint,'source_json_path':path,
                         'api_field':key,'sql_column':sql_name(key),'sql_type':infer_type(r.get('types','')),
                         'observed_types':r.get('types',''),'occurrences':r.get('occurrences',0),
                         'sample_values':r.get('examples',''), 'key_candidate':key==pk,
                         'comment':'Historical suffix requires year validation' if YEAR_SUFFIX_RE.match(key) else ''})
        rows.sort(key=lambda r:r['api_field'])
        fields.extend(rows); fieldset[table]={r['api_field'] for r in rows}
        key_metrics=uniqueness(samples[table],[pk]) if pk else None
        tables.append({'table':table,'source_endpoint':endpoint,'observed_columns':len(rows),
                       'loaded_sample_rows':len(samples[table]),'primary_key_candidate':pk,
                       'key_evidence':key_metrics,'status':'observed_endpoint_entity'})
    # Preserve dynamic special conditions as separate normalized dimension and junction.
    conditions={}
    for rec in samples['programs']:
        for entry in rec.get('kosulList') or []:
            if isinstance(entry,dict):
                for k,v in entry.items(): conditions[str(k)]=v
    logical=[
      {'table':'program_conditions','columns':['kilavuz_kodu','condition_code','source_year','condition_text'], 'source':'programs.kosulList[]','status':'derived_normalization'},
      {'table':'conditions','columns':['condition_code','condition_text'], 'source':'programs.kosulList[]','status':'derived_normalization'},
      {'table':'raw_api_snapshots','columns':['snapshot_id','endpoint','request_json','response_json','fetched_at','sha256'], 'source':'all HTTP responses','status':'recommended_ingestion_audit'},
      {'table':'etl_runs','columns':['run_id','started_at','finished_at','status','source_version'], 'source':'pipeline metadata','status':'recommended_pipeline'},
      {'table':'historical_program_statistics','columns':['kilavuz_kodu','base_year','year_offset','source_field','value_raw'], 'source':'programs.*1,*2,*3','status':'derived_pending_year_offset_verification'},
    ]
    relations=[]
    for child,col,parent,pcol in LINKS:
        s=col.split('+'); d=pcol.split('+')
        e=overlap(samples[child],s,samples[parent],d)
        child_presence=all(k in fieldset[child] for k in s)
        parent_presence=all(k in fieldset[parent] for k in d)
        parent_unique=uniqueness(samples[parent],d)
        observed=bool(samples[child] and samples[parent])
        # When year data are different, explicitly keep as temporal relation, no FK.
        temporal=('yil' in s or 'yil' in d)
        conf=('strong_candidate' if child_presence and parent_presence and observed and e['coverage']==1 and parent_unique['duplicates']==0
              else 'partial_evidence' if child_presence and parent_presence and observed and e['matched']>0
              else 'unverified')
        if temporal: conf='year_sensitive_'+conf
        relations.append({'child_table':child,'child_fields':col,'parent_table':parent,'parent_fields':pcol,
                          'confidence':conf,'source_field_exists':child_presence,'target_field_exists':parent_presence,
                          'parent_key_unique_in_sample':parent_unique['duplicates']==0 if parent_unique else None,
                          'observed_child_rows':len(samples[child]),'observed_parent_rows':len(samples[parent]),
                          **e,'sql_foreign_key_created':False,
                          'reason':'Name-based candidate; sampled cross-table overlap, not an official DB foreign key'})
    relations.extend([
      {'child_table':'program_conditions','child_fields':'kilavuz_kodu','parent_table':'programs','parent_fields':'kilavuzKodu','confidence':'derived_model','sql_foreign_key_created':True},
      {'child_table':'program_conditions','child_fields':'condition_code','parent_table':'conditions','parent_fields':'condition_code','confidence':'derived_model','sql_foreign_key_created':True},
    ])
    # Declare PK only if it was actually unique in the loaded samples, except no rows -> unverified.
    ddl=['-- YOK Atlas inferred schema. API-derived columns are preserved; unverified FKs are NOT enforced.',
         '-- Raw program rows may refer to a current year while net rows refer to a different year.',
         'PRAGMA foreign_keys=ON;','']
    for t in tables:
        name=t['table']; cols=[f for f in fields if f['table']==name]; pk=t['primary_key_candidate']
        lines=['  '+('"'+f['sql_column']+'"')+' '+f['sql_type'] for f in cols]
        is_unique=bool(pk and t['key_evidence'] and t['key_evidence']['non_null'] and t['key_evidence']['duplicates']==0)
        if name=='net_results':
            lines.insert(0,'  "_id" INTEGER PRIMARY KEY AUTOINCREMENT')
        elif is_unique: pass  # Add table-level PRIMARY KEY after all columns
        else:
            lines.insert(0,'  "_id" INTEGER PRIMARY KEY AUTOINCREMENT')
        lines.extend(['  "_source_year" INTEGER','  "_fetched_at" TEXT','  "_raw_json" TEXT'])
        if name != 'net_results' and is_unique:
            lines.append('  PRIMARY KEY ("'+sql_name(pk)+'")')
        ddl.append('CREATE TABLE IF NOT EXISTS "'+name+'" (\n'+',\n'.join(lines)+'\n);\n')
    ddl.extend([
      'CREATE TABLE IF NOT EXISTS "conditions" (condition_code TEXT PRIMARY KEY, condition_text TEXT);',
      'CREATE TABLE IF NOT EXISTS "program_conditions" (kilavuz_kodu INTEGER NOT NULL, condition_code TEXT NOT NULL, source_year INTEGER, condition_text TEXT, PRIMARY KEY(kilavuz_kodu,condition_code,source_year));',
      'CREATE TABLE IF NOT EXISTS "historical_program_statistics" (kilavuz_kodu INTEGER, base_year INTEGER, year_offset INTEGER, source_field TEXT, value_raw TEXT, PRIMARY KEY(kilavuz_kodu,base_year,year_offset,source_field));',
      'CREATE TABLE IF NOT EXISTS "raw_api_snapshots" (snapshot_id TEXT PRIMARY KEY, endpoint TEXT, request_json TEXT, response_json TEXT, fetched_at TEXT, sha256 TEXT);',
      'CREATE TABLE IF NOT EXISTS "etl_runs" (run_id TEXT PRIMARY KEY, started_at TEXT, finished_at TEXT, status TEXT, source_version TEXT);',
      'CREATE INDEX IF NOT EXISTS idx_program_university ON programs(universite_id);',
      'CREATE INDEX IF NOT EXISTS idx_net_program_year ON net_results(kilavuz_kodu, yil);',
      'CREATE INDEX IF NOT EXISTS idx_program_condition_code ON program_conditions(condition_code);',
      ''] )
    (target/'schema.sqlite.sql').write_text('\n'.join(ddl),encoding='utf-8')
    # Diagram differentiates inferred conceptual relations from asserted physical FKs.
    diagram=['erDiagram']
    for t in tables:
        diagram.append('    '+t['table'].upper()+' {')
        for f in fields:
            if f['table']==t['table']:
                typ={'INTEGER':'int','REAL':'float','TEXT':'string'}[f['sql_type']]
                diagram.append('        '+typ+' '+f['sql_column']+(' PK' if f['api_field']==t['primary_key_candidate'] else ''))
        diagram.append('    }')
    for x in logical:
        diagram.append('    '+x['table'].upper()+' {')
        for c in x['columns']: diagram.append('        string '+c)
        diagram.append('    }')
    for r in relations:
        diagram.append('    '+r['parent_table'].upper()+' ||--o{ '+r['child_table'].upper()+ ' : "'+r['child_fields']+' candidate"')
    (target/'schema.mmd').write_text('\n'.join(diagram)+'\n',encoding='utf-8')
    dump(target/'schema.json',{'generated_at':datetime.now(timezone.utc).isoformat(),'tables':tables,'fields':fields,'normalized_tables':logical,'relations':relations,'observed_special_conditions':conditions,'warnings':[
      'An API exposes resources, not underlying database tables; physical internal tables cannot be exhaustively identified from these five endpoints.',
      'Relationships are inferred candidates, not verified server foreign keys; not enforced in SQL.',
      'Missing joined rows can result from only sampling first pages; use full downloads to verify overlap.',
      'Historical suffixes 1/2/3 must be mapped to exact year using official documentation or controlled data.',
      'Program and net years can differ; joining on kilavuzKodu alone does not guarantee same-year equivalence.',
      'Fields with mixed numeric/string types are stored as TEXT pending cleaning.'
    ]})
    csvout(target/'all_fields.csv',fields)
    csvout(target/'relationships.csv',relations)
    csvout(target/'tables.csv',tables)
    csvout(target/'conditions_sample.csv',[{'code':k,'text':v} for k,v in sorted(conditions.items())])
    report=['# YÖK Atlas Schema Discovery','',f'Observed endpoint entities: {len(tables)}',f'Direct scalar/JSON columns: {len(fields)}',f'Candidate relationships: {len(relations)}',f'Available sample rows: '+str(sum(len(s) for s in samples.values())),'',
    '## Important distinction','The result reconstructs a **logical model of exposed API resources**, not the server\'s hidden physical DB schema.',
    'All name-derived relations are candidates. Review overlap and cardinality before enforcing foreign keys.','','## Tables']
    for t in tables: report.append(f"- {t['table']}: {t['observed_columns']} columns, {t['loaded_sample_rows']} sample records, PK candidate {t['primary_key_candidate']}")
    report+=['','## Candidate relationships']
    for r in relations: report.append(f"- {r['child_table']}.{r['child_fields']} -> {r['parent_table']}.{r['parent_fields']}: {r['confidence']}, overlap={r.get('coverage','not applicable')}")
    report+=['','## Next steps','1. Download complete pages in a separately rate-limited collector and retain original response JSON.',
            '2. Compare candidate keys with full-set cardinalities and orphan rates.','3. Verify historical year offsets and net data year independently.',
            '4. Review ERD and approve constraints before production migrations.','5. Implement incremental yearly ingestion, validation, versioning and insight jobs.']
    (target/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    # DDL syntactic validation without claiming discovered FKs are valid.
    con=sqlite3.connect(':memory:')
    try: con.executescript('\n'.join(ddl)); con.execute('PRAGMA integrity_check').fetchone()
    finally: con.close()
    print('Schema built:',target.resolve())
    print('Observed tables:',len(tables),' | fields:',len(fields),' | relationships:',len(relations))
    print('Sample availability:',{k:len(v) for k,v in samples.items()})
    print('SQL validation: passed')

if __name__=='__main__': main()
