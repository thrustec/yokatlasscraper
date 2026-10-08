#!/usr/bin/env python3
"""YOK Atlas full public-API collector and evidence-based schema analyzer.
Python 3.10+, pip install requests. Only known, read-only public endpoints.
Collect: --mode collect (resumable); re-analyze: --mode analyze (no network).
Never claims access to the source's physical database schema.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

LOOKUPS = {'universities':'/api/tercih-kilavuz/universiteler',
           'program_groups':'/api/tercih-kilavuz/universite-programlar',
           'cities':'/api/tercih-kilavuz/universite-iller'}
SEARCH = {'programs':'/api/tercih-kilavuz/search',
          'net_results':'/api/netler/search'}
SCORES = ('SAY','EA','SÖZ','DİL','TYT')
KEYS = {'universities':('universiteId',),'program_groups':('birimGrupId',),
        'cities':('ilKodu',),'programs':('kilavuzKodu','yil'),
        'net_results':('kilavuzKodu','yil')}
CANDIDATES = [
    ('programs',('universiteId',),'universities',('universiteId',)),
    ('programs',('birimGrupId',),'program_groups',('birimGrupId',)),
    ('programs',('birimGrupId','puanTuru'),'program_groups',('birimGrupId','puanTuru')),
    ('programs',('ilKodu',),'cities',('ilKodu',)),
    ('programs',('uniIlKodu',),'cities',('ilKodu',)),
    ('programs',('fymkIlKodu',),'cities',('ilKodu',)),
    ('net_results',('universiteId',),'universities',('universiteId',)),
    ('net_results',('birimGrupId',),'program_groups',('birimGrupId',)),
    ('net_results',('birimGrupId','puanTuru'),'program_groups',('birimGrupId','puanTuru')),
    ('net_results',('kilavuzKodu',),'programs',('kilavuzKodu',)),
    ('net_results',('kilavuzKodu','yil'),'programs',('kilavuzKodu','yil')),
    ('net_results',('birimId',),'programs',('birimId',)),
]
SCORE_DATE_NOTE = 'Yil alanini resmi yayin bilgileriyle dogrulayin; current/1/2/3 eslemesi varsayimdir.'

def now(): return datetime.now(timezone.utc).isoformat()
def dump(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    temp.replace(path)
def read_json(path, default=None):
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError,json.JSONDecodeError): return default

def write_csv(path, rows, columns=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    columns=columns or list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore')
        w.writeheader(); w.writerows(rows)

def snake(s):
    return re.sub(r'[^a-zA-Z0-9_]+','_',re.sub(r'([a-z0-9])([A-Z])',r'\1_\2',s)).strip('_').lower()
def q(s): return '"'+s.replace('"','""')+'"'
def normalize(v):
    if v is None: return None
    if isinstance(v,str): return v.strip()
    if isinstance(v,(dict,list)): return json.dumps(v,sort_keys=True,ensure_ascii=False)
    return v

def key_of(row, fields):
    vals=tuple(normalize(row.get(x)) for x in fields)
    return vals if all(v is not None and v != '' for v in vals) else None

def shape(v):
    if v is None: return 'null'
    if isinstance(v,bool): return 'boolean'
    if isinstance(v,int): return 'integer'
    if isinstance(v,float): return 'number'
    if isinstance(v,str): return 'string'
    if isinstance(v,list): return 'array'
    return 'object'

def content(v):
    if isinstance(v,list): return v
    return v.get('content',[]) if isinstance(v,dict) else []

def pages_of(v):
    if not isinstance(v,dict): return None
    n=v.get('totalPages')
    if isinstance(n,int) and n>=0: return n
    return None

class Collector:
    def __init__(self,args):
        import requests
        self.requests=requests
        self.args=args; self.calls=0; self.previous=0.0
        self.session=requests.Session()
        self.session.headers.update({'Accept':'application/json','User-Agent':'YOKAtlasIntelligenceResearch/1.0 (read-only)'})
        self.events=[]

    def get(self,entity,method,path,payload=None):
        if self.calls>=self.args.max_requests: raise StopIteration('Maximum request budget reached')
        wait=max(0,self.args.delay-(time.monotonic()-self.previous))
        if wait: time.sleep(wait)
        self.calls+=1; self.previous=time.monotonic()
        try:
            r=self.session.request(method,self.args.base_url.rstrip('/')+path,
                json=payload if method=='POST' else None,timeout=self.args.timeout)
        except self.requests.RequestException as e:
            self.events.append({'entity':entity,'status':'network_error','error':str(e),'time':now()})
            raise RuntimeError(f'Network error: {e}') from e
        event={'entity':entity,'status':r.status_code,'time':now(),
               'payload':payload,'bytes':len(r.content)}
        self.events.append(event)
        if r.status_code in (403,418,429): raise RuntimeError(f'HTTP {r.status_code}: stopped (no retry)')
        if r.status_code>=400: raise RuntimeError(f'HTTP {r.status_code}: {r.text[:200]}')
        if 'json' not in r.headers.get('content-type','').lower():
            raise RuntimeError('Non-JSON response; stopped')
        try: return r.json()
        except ValueError as e: raise RuntimeError('Malformed JSON response') from e

    def collect(self,root):
        target=root/'complete_data'; target.mkdir(parents=True,exist_ok=True)
        try:
            for name,path in LOOKUPS.items():
                dest=target/name/'all.json'
                if dest.exists() and not self.args.refresh:
                    print('SKIP',dest); continue
                data=self.get(name,'GET',path)
                if not isinstance(data,list): raise RuntimeError(f'{name}: expected JSON list; got {type(data).__name__}')
                dump(dest,data); print(name,len(data),'records')
            for name,path in SEARCH.items():
                for score in SCORES:
                    page=0
                    while page<self.args.max_pages_per_score:
                        dest=target/name/score/f'page_{page:06d}.json'
                        if dest.exists() and not self.args.refresh:
                            data=read_json(dest)
                            if data is None: raise RuntimeError(f'Corrupted cached JSON: {dest}')
                        else:
                            payload={'filters':{'puanTuru':score},'page':page,'size':self.args.size}
                            if name=='programs': payload.update({'sortBy':'basariSirasi','direction':'ASC'})
                            data=self.get(name,'POST',path,payload)
                            if not isinstance(data,dict) or not isinstance(data.get('content'),list):
                                raise RuntimeError(f'{name}/{score}/{page}: unexpected search response')
                            dump(dest,data)
                        records=content(data)
                        total=pages_of(data)
                        print(f'{name:12} {score:3} page={page:5} rows={len(records):4} pages={total}')
                        page+=1
                        if not records or data.get('last') is True or (total is not None and page>=total): break
        except (RuntimeError,StopIteration) as e:
            print(f'Collection paused: {e}',file=sys.stderr)
        finally:
            self.session.close()
            dump(root/'collection_log.json',{'time':now(),'new_requests':self.calls,'events':self.events,
                                              'resumable':True})

def load_data(root):
    base=root/'complete_data'; rows={}
    for entity in [*LOOKUPS,*SEARCH]:
        if entity in LOOKUPS:
            raw=read_json(base/entity/'all.json',[])
            rows[entity]=[r for r in raw if isinstance(r,dict)] if isinstance(raw,list) else []
        else:
            rows[entity]=[]
            for file in sorted((base/entity).glob('*/page_*.json')):
                data=read_json(file,{})
                if isinstance(data,dict): rows[entity].extend(r for r in content(data) if isinstance(r,dict))
    return rows

def pk_test(rows,table,fields):
    values=[key_of(r,fields) for r in rows]
    good=[x for x in values if x is not None]
    distinct=len(set(good)); repeated=len(good)-distinct
    return {'table':table,'key_fields':'+'.join(fields),'rows':len(rows),
            'non_null':len(good),'null_or_missing':len(rows)-len(good),
            'distinct':distinct,'duplicate_rows':repeated,
            'uniqueness':round(distinct/len(good),6) if good else None,
            'valid_primary_key':bool(rows) and len(good)==len(rows) and not repeated}

def key_tests(rows):
    specs={'universities':[('universiteId',)],'cities':[('ilKodu',)],
           'program_groups':[('birimGrupId',),('birimGrupId','puanTuru')],
           'programs':[('kilavuzKodu',),('kilavuzKodu','yil'),('osymKilavuzId','yil'),('birimId','yil')],
           'net_results':[('kilavuzKodu',),('kilavuzKodu','yil'),('birimId','yil'),('osymKilavuzId','yil')]}
    return [pk_test(rows[t],t,f) for t,fields in specs.items() for f in fields]

def fk_tests(rows):
    output=[]
    for child,cfields,parent,pfields in CANDIDATES:
        target=[key_of(x,pfields) for x in rows[parent]]
        clean=[x for x in target if x is not None]; lookup=set(clean)
        keys=[key_of(x,cfields) for x in rows[child]]
        observed=[k for k in keys if k is not None]
        matched=sum(k in lookup for k in observed)
        distinct=set(observed); overlap=len(distinct&lookup)
        target_unique=len(clean)==len(lookup) and len(clean)==len(rows[parent])
        years=sorted({r.get('yil') for r in rows[child] if isinstance(r.get('yil'),int)})
        parent_years=sorted({r.get('yil') for r in rows[parent] if isinstance(r.get('yil'),int)})
        output.append({'child_table':child,'child_fields':'+'.join(cfields),
          'parent_table':parent,'parent_fields':'+'.join(pfields),
          'child_rows':len(keys),'non_null_child_rows':len(observed),
          'null_child_rows':len(keys)-len(observed),'parent_rows':len(target),
          'parent_distinct_keys':len(lookup),'parent_key_unique':target_unique,
          'matched_child_rows':matched,'orphan_child_rows':len(observed)-matched,
          'join_coverage':round(matched/len(observed),6) if observed else None,
          'distinct_child_keys':len(distinct),'matched_distinct_child_keys':overlap,
          'distinct_key_coverage':round(overlap/len(distinct),6) if distinct else None,
          'child_years':str(years),'parent_years':str(parent_years),
          'status':('no_data' if not clean or not observed else
                    'candidate_complete' if matched==len(observed) and target_unique else
                    'parent_not_unique' if not target_unique else 'partial_or_year_mismatch'),
          'enforce_fk':False})
    return output

def year_tests(rows):
    cols=set().union(*(r.keys() for r in rows['programs'])) if rows['programs'] else set()
    pattern=re.compile(r'^(.*?)([123])$')
    output=[]
    # suffixes only if a counterpart base or common historical family exists
    families={'minPuan','basariSirasi','gk','kontenjan','yerlesen','obk','sgy'}
    for field in sorted(cols):
        m=pattern.fullmatch(field)
        if not m or m.group(1) not in families: continue
        base,suffix=m.group(1),int(m.group(2))
        values=[r.get(field) for r in rows['programs']]
        years=sorted({r.get('yil') for r in rows['programs'] if isinstance(r.get('yil'),int)})
        output.append({'source_table':'programs','historical_field':field,'base_field':base,
             'suffix':suffix,'observed_current_years':','.join(map(str,years)),
             'proposed_year_offset':-suffix,'mapping_status':'UNVERIFIED',
             'nonnull_values':sum(v is not None for v in values),
             'zero_like_values':sum(v in (0,'0','0.0') for v in values),
             'note':SCORE_DATE_NOTE})
    for table in ('programs','net_results'):
        values=Counter(str(x.get('yil','MISSING')) for x in rows[table])
        for year,n in sorted(values.items()):
            output.append({'source_table':table,'historical_field':'yil','base_field':'yil',
                'observed_current_years':year,'nonnull_values':n,
                'mapping_status':'OBSERVED','note':'Year provided directly by API'})
    return output

def catalog(rows):
    output=[]
    for table,items in rows.items():
        fields=defaultdict(Counter)
        for r in items:
            for k,v in r.items(): fields[k][shape(v)]+=1
        for field,counts in sorted(fields.items()):
            present=sum(counts.values())
            output.append({'table':table,'api_field':field,'sql_column':snake(field),
                 'observed_types':dict(counts),'rows':len(items),
                 'present':present,'missing':len(items)-present,
                 'nonnull':present-counts.get('null',0),
                 'sql_type':('JSONB' if set(counts)&{'array','object'} else
                      'BOOLEAN' if set(counts)-{'null'}=={'boolean'} else
                      'BIGINT' if set(counts)-{'null'}=={'integer'} else
                      'DOUBLE PRECISION' if set(counts)-{'null'}<={'integer','number'} else 'TEXT')})
    return output

def build_schema(rows,pk,fk,fields,years):
    valid={(r['table'],r['key_fields']):r['valid_primary_key'] for r in pk}
    schema={'schema_version':'draft-1','generated_at':now(),
            'notice':'Logical schema inferred from publicly returned JSON, NOT source physical schema. FK relationships are advisory only.',
            'source_entities':{},'candidate_relationships':fk,'historical_year_mappings':years,
            'derived_tables':[{'name':'raw_api_snapshots','reason':'immutable raw source provenance'},
                              {'name':'ingestion_runs','reason':'audit and restart tracking'},
                              {'name':'program_conditions','reason':'normalized kosulList bridge; requires verification'}]}
    for table in rows:
        cols=[x for x in fields if x['table']==table]
        keys=[r for r in pk if r['table']==table and r['valid_primary_key']]
        chosen=next((k for k in keys if k['key_fields']=='+'.join(KEYS[table])),keys[0] if keys else None)
        schema['source_entities'][table]={'rows_observed':len(rows[table]),'fields':cols,
            'suggested_unique_key':chosen['key_fields'].split('+') if chosen else None,
            'key_is_sample_validated':bool(chosen),
            'risk':'API schemas can change; samples do not prove future-year uniqueness'}
    return schema

def ddl(schema):
    lines=['-- Generated DRAFT PostgreSQL DDL. No inferred foreign keys enforced.',
           '-- Preserve raw input and verify year alignment / key uniqueness before production.',
           'CREATE TABLE IF NOT EXISTS ingestion_runs (run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, started_at TIMESTAMPTZ DEFAULT now(), status TEXT NOT NULL, notes TEXT);',
           'CREATE TABLE IF NOT EXISTS raw_api_snapshots (snapshot_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id BIGINT REFERENCES ingestion_runs(run_id), endpoint TEXT NOT NULL, score_type TEXT, page_number INTEGER, fetched_at TIMESTAMPTZ DEFAULT now(), sha256 TEXT NOT NULL, payload JSONB NOT NULL);']
    for table,spec in schema['source_entities'].items():
        cols=['    _row_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY',
              '    _source_year INTEGER','    _fetched_at TIMESTAMPTZ',
              '    _payload JSONB NOT NULL DEFAULT \'{}\'::jsonb']
        names={'_row_id','_source_year','_fetched_at','_payload'}
        for field in spec['fields']:
            name=field['sql_column']
            if name in names: raise ValueError('Name collision: '+name)
            names.add(name)
            cols.append(f'    {q(name)} {field["sql_type"]}')
        lines.append(f'CREATE TABLE IF NOT EXISTS {q(table)} (\n'+',\n'.join(cols)+'\n);')
        key=spec['suggested_unique_key']
        if key:
            sql_cols=[snake(k) for k in key]
            lines.append(f'-- Observed unique in sample; validate on full data and across years before enforcing.')
            lines.append(f'CREATE INDEX IF NOT EXISTS {q("idx_"+table+"_natural")} ON {q(table)} ('+', '.join(q(k) for k in sql_cols)+');')
    lines.append('-- Future normalization candidates: program_year_statistics, conditions, program_conditions.')
    return '\n\n'.join(lines)+'\n'

def mermaid(schema):
    out=['erDiagram']
    for table,entity in schema['source_entities'].items():
        out.append(f'    {table} {{')
        out.append('        bigint _row_id PK')
        for f in entity['fields']:
            typ={'BIGINT':'bigint','TEXT':'string','BOOLEAN':'boolean','DOUBLE PRECISION':'float','JSONB':'json'}.get(f['sql_type'],'string')
            out.append(f'        {typ} {f["sql_column"]}')
        out.append('    }')
    for r in schema['candidate_relationships']:
        if r['status']=='candidate_complete' and len(r['child_fields'].split('+'))==1:
            out.append(f'    {r["parent_table"]} ||..o{{ {r["child_table"]} : "candidate {r["child_fields"]}"')
    return '\n'.join(out)+'\n'

def analyze(root):
    rows=load_data(root)
    if not any(rows.values()):
        raise SystemExit(f'No raw records in {root / "complete_data"}. Run --mode collect first.')
    pk=key_tests(rows); fk=fk_tests(rows); years=year_tests(rows); fields=catalog(rows)
    schema=build_schema(rows,pk,fk,fields,years)
    report=root/'schema_analysis'; report.mkdir(exist_ok=True,parents=True)
    write_csv(report/'primary_key_analysis.csv',pk)
    write_csv(report/'foreign_key_analysis.csv',fk)
    write_csv(report/'year_mapping.csv',years)
    write_csv(report/'all_fields.csv',[{**f,'observed_types':json.dumps(f['observed_types'],ensure_ascii=False)} for f in fields])
    dump(report/'normalized_schema.json',schema)
    (report/'schema.postgresql.sql').write_text(ddl(schema),encoding='utf-8')
    (report/'schema.mmd').write_text(mermaid(schema),encoding='utf-8')
    summary={'counts':{k:len(v) for k,v in rows.items()},'discovered_fields':len(fields),
             'relationship_candidates':len(fk),'fully_matched_candidates':sum(r['status']=='candidate_complete' for r in fk),
             'note':'All inferred relations require human review; normalized_schema.json is a draft.'}
    dump(report/'analysis_summary.json',summary)
    print('REPORT:',report.resolve())
    print(json.dumps(summary,ensure_ascii=False,indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['collect','analyze','all'],default='all')
    p.add_argument('--out',default='outputs/yokatlas_full')
    p.add_argument('--base-url',default='https://yokatlas.yok.gov.tr')
    p.add_argument('--size',type=int,default=100)
    p.add_argument('--delay',type=float,default=2.0)
    p.add_argument('--timeout',type=float,default=25)
    p.add_argument('--max-requests',type=int,default=5000)
    p.add_argument('--max-pages-per-score',type=int,default=10000)
    p.add_argument('--refresh',action='store_true',help='Re-fetch existing cache files (normally avoid)')
    a=p.parse_args()
    if a.delay<1 or not 1<=a.size<=100 or a.max_requests<1 or a.max_pages_per_score<1:
        p.error('Requires delay>=1, size=1..100 and positive request/page caps')
    root=Path(a.out)
    if a.mode in ('collect','all'):
        Collector(a).collect(root)
    if a.mode in ('analyze','all'):
        analyze(root)
if __name__=='__main__': main()
