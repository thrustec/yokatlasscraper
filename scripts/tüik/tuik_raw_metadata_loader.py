#!/usr/bin/env python3
"""Load vetted TUIK SDMX structure metadata into PostgreSQL. No observation fetching.
Dependencies: pip install 'psycopg[binary]'
Usage: python tuik_raw_metadata_loader.py --data-dir data/tuik_discovery/all_dsd --catalog data/tuik_discovery/tuik_full_catalog.csv --dsn '...' --check-only
Remove --check-only to write. Apply tuik_raw_metadata_compatible.sql first.
Connection can also be PG* env vars (do not place passwords in arguments/history).
"""
import argparse,csv,collections,json,os,pathlib,sys

def load(path):
    with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def num(s):return int(s) if s else None
def nul(s):return s if s not in ('',None) else None

def main():
 p=argparse.ArgumentParser();p.add_argument('--data-dir',type=pathlib.Path,default=pathlib.Path('data/tuik_discovery/all_dsd'));p.add_argument('--catalog',type=pathlib.Path,default=pathlib.Path('data/tuik_discovery/tuik_full_catalog.csv'));p.add_argument('--dsn',default='');p.add_argument('--check-only',action='store_true');a=p.parse_args()
 needed=['dataflow_dsd_map.csv','dsd_dimensions.csv','dsd_attributes.csv','dsd_codelist_codes.csv','dsd_key_templates.csv','manifest.json']
 for fn in needed:
  if not (a.data_dir/fn).exists():p.error(f'Missing {a.data_dir/fn}')
 if not a.catalog.exists():p.error(f'Missing {a.catalog}')
 data={k:load(a.data_dir/k) for k in needed if k.endswith('.csv')};catalog=load(a.catalog)
 manifest=json.loads((a.data_dir/'manifest.json').read_text(encoding='utf-8-sig'))
 success=[r for r in manifest['results'] if r['status']=='ok'];dsds={(r['dsd_key'].split('|')[0],r['dsd_key'].split('|')[1],r['dsd_key'].split('|')[2]):r for r in success}
 if len(success)!=len(manifest['results']) or len(dsds)!=65:raise ValueError('Incomplete/nonunique DSD manifest')
 flows=data['dataflow_dsd_map.csv']; cat={(r['agency_id'],r['flow_id'],r['version']):r for r in catalog}
 if len(cat)!=len(catalog) or len(flows)!=508:raise ValueError('Unexpected flow count / duplicate catalog')
 for r in flows:
  if (r['dsd_agency'],r['dsd_id'],r['dsd_version']) not in dsds:raise ValueError('Flow references missing DSD: '+str(r))
  if ('TR',r['dataflow_id'],r['dataflow_version']) not in cat:raise ValueError('Unmapped flow: '+str(r))
 codes={};links=set()
 for r in data['dsd_codelist_codes.csv']:
  k=tuple(r[x] for x in ('codelist_agency','codelist_id','codelist_version','code'))
  v=tuple(nul(r[x]) for x in ('parent_code','label_tr','label_en'))
  if k in codes and codes[k]!=v:raise ValueError(f'Conflicting code {k}')
  codes[k]=v
  links.add(tuple(r[x] for x in ('dsd_agency','dsd_id','dsd_version','codelist_agency','codelist_id','codelist_version')))
 dims=data['dsd_dimensions.csv']; attrs=data['dsd_attributes.csv'];templates=data['dsd_key_templates.csv']
 cls={(k[0],k[1],k[2]) for k in codes}
 for r in dims+attrs:
  if r['codelist_id']: cls.add((r['codelist_agency'],r['codelist_id'],r['codelist_version']))
 for link in links:cls.add(link[3:])
 print(f'Checked: {len(cat)} flows; {len(dsds)} DSD versions; {len(dims)} dimensions; {len(attrs)} attributes; {len(cls)} codelists; {len(codes)} unique codes; {len(links)} DSD-codelist links; {len(templates)} templates')
 if a.check_only:print('CHECK ONLY: database not accessed.');return
 try:import psycopg
 except ImportError:sys.exit('Missing psycopg: pip install "psycopg[binary]"')
 from psycopg import sql
 with psycopg.connect(a.dsn or '',connect_timeout=15) as con:
  with con.cursor() as cur:
   cur.execute('SET LOCAL statement_timeout = %s',('180s',))
   cur.execute('SELECT pg_advisory_xact_lock(917620261018)')
   for k,r in sorted(dsds.items()):
    cur.execute('INSERT INTO raw.tuik_dsd (agency_id,dsd_id,dsd_version,metadata_status,source_sha256,discovered_at) VALUES (%s,%s,%s,%s,%s,now()) ON CONFLICT (agency_id,dsd_id,dsd_version) DO UPDATE SET metadata_status=EXCLUDED.metadata_status,source_sha256=EXCLUDED.source_sha256',(*k,r['status'],r['sha256']))
   for r in flows:
    c=cat[('TR',r['dataflow_id'],r['dataflow_version'])]
    cur.execute('''INSERT INTO raw.tuik_dataflow (agency_id,flow_id,flow_version,name_tr,name_en,description_tr,dsd_agency_id,dsd_id,dsd_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (agency_id,flow_id,flow_version) DO UPDATE SET name_tr=EXCLUDED.name_tr,name_en=EXCLUDED.name_en,description_tr=EXCLUDED.description_tr,dsd_agency_id=EXCLUDED.dsd_agency_id,dsd_id=EXCLUDED.dsd_id,dsd_version=EXCLUDED.dsd_version''', ('TR',r['dataflow_id'],r['dataflow_version'],nul(c['name_tr']),nul(c['name_en']),nul(c['description_tr']),r['dsd_agency'],r['dsd_id'],r['dsd_version']))
   cur.executemany('INSERT INTO raw.tuik_codelist (agency_id,codelist_id,codelist_version) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',sorted(cls))
   cur.executemany('''INSERT INTO raw.tuik_codelist_code (agency_id,codelist_id,codelist_version,code,parent_code,label_tr,label_en) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (agency_id,codelist_id,codelist_version,code) DO UPDATE SET parent_code=EXCLUDED.parent_code,label_tr=EXCLUDED.label_tr,label_en=EXCLUDED.label_en''', [(*k,*v) for k,v in sorted(codes.items())])
   for r in dims:
    cur.execute('''INSERT INTO raw.tuik_dsd_dimension (dsd_agency,dsd_id,dsd_version,dimension_id,dimension_kind,source_position,key_position,concept_id,codelist_agency,codelist_id,codelist_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (dsd_agency,dsd_id,dsd_version,dimension_id) DO UPDATE SET dimension_kind=EXCLUDED.dimension_kind,source_position=EXCLUDED.source_position,key_position=EXCLUDED.key_position,concept_id=EXCLUDED.concept_id,codelist_agency=EXCLUDED.codelist_agency,codelist_id=EXCLUDED.codelist_id,codelist_version=EXCLUDED.codelist_version''',(r['dsd_agency'],r['dsd_id'],r['dsd_version'],r['id'],r['kind'],num(r['position']),num(r['key_position']),nul(r['concept_id']),nul(r['codelist_agency']),nul(r['codelist_id']),nul(r['codelist_version'])))
   for r in attrs:
    cur.execute('''INSERT INTO raw.tuik_dsd_attribute (dsd_agency,dsd_id,dsd_version,attribute_id,attribute_kind,concept_id,codelist_agency,codelist_id,codelist_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (dsd_agency,dsd_id,dsd_version,attribute_id) DO UPDATE SET attribute_kind=EXCLUDED.attribute_kind,concept_id=EXCLUDED.concept_id,codelist_agency=EXCLUDED.codelist_agency,codelist_id=EXCLUDED.codelist_id,codelist_version=EXCLUDED.codelist_version''',(r['dsd_agency'],r['dsd_id'],r['dsd_version'],r['id'],nul(r['kind']),nul(r['concept_id']),nul(r['codelist_agency']),nul(r['codelist_id']),nul(r['codelist_version'])))
   cur.executemany('''INSERT INTO raw.tuik_dsd_codelist (dsd_agency,dsd_id,dsd_version,codelist_agency,codelist_id,codelist_version) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',sorted(links))
   for r in templates:
    cur.execute('''INSERT INTO raw.tuik_key_template (dsd_agency,dsd_id,dsd_version,dimension_order,query_key_template,template_kind,notes) VALUES (%s,%s,%s,%s,%s,'structural_only',%s) ON CONFLICT (dsd_agency,dsd_id,dsd_version) DO UPDATE SET dimension_order=EXCLUDED.dimension_order,query_key_template=EXCLUDED.query_key_template,notes=EXCLUDED.notes''',(r['dsd_agency'],r['dsd_id'],r['dsd_version'],r['dimension_order'],r['query_key_template'],nul(r['note'])))
  print('Committed all metadata successfully.')
if __name__=='__main__':main()
