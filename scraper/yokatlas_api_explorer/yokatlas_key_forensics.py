#!/usr/bin/env python3
"""YOK Atlas complete_data forensic audit. Offline, read-only, standard library only.
Analyzes page coverage, key uniqueness, duplicated net rows and unmatched references.
It does NOT enforce guessed relations or mutate source files.
"""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

SCORING = ('SAY', 'EA', 'SÖZ', 'DİL', 'TYT')
TABLES = ('universities', 'program_groups', 'cities', 'programs', 'net_results')
KEY_TESTS = {
 'universities': [('universiteId',)],
 'program_groups': [('birimGrupId',), ('birimGrupId','puanTuru')],
 'cities': [('ilKodu',)],
 'programs': [('kilavuzKodu',), ('kilavuzKodu','yil'), ('osymKilavuzId','yil')],
 'net_results': [('kilavuzKodu',), ('kilavuzKodu','yil'),
                 ('kilavuzKodu','yil','puanTuru'),
                 ('kilavuzKodu','yil','birimId'),
                 ('kilavuzKodu','yil','puanTuru','birimId'),
                 ('birimId','yil','puanTuru')],
}
REFERENCES = [
 ('net_results','universiteId','universities',('universiteId',)),
 ('net_results','birimGrupId+puanTuru','program_groups',('birimGrupId','puanTuru')),
 ('net_results','kilavuzKodu','programs',('kilavuzKodu',)),
 ('programs','universiteId','universities',('universiteId',)),
 ('programs','birimGrupId+puanTuru','program_groups',('birimGrupId','puanTuru')),
]

def read_json(path):
    with path.open('r',encoding='utf-8-sig') as fh:
        return json.load(fh)

def write_csv(path, items, columns):
    with path.open('w',encoding='utf-8-sig',newline='') as fh:
        writer=csv.DictWriter(fh,fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(items)

def key(record, fields):
    parts=[]
    for field in fields:
        value=record.get(field)
        if value is None or value=='': return None
        if isinstance(value,str): value=value.strip()
        parts.append(value)
    return tuple(parts)

def canonical_hash(record):
    raw=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def collect(root):
    base = root/'complete_data' if (root/'complete_data').is_dir() else root
    if not base.is_dir() or not (base/'net_results').is_dir():
        raise ValueError('Complete data folder not found. --root should point to outputs/yokatlas_full')
    tables={}
    coverage=[]
    for tab in TABLES:
        data=[]
        if tab in ('universities','program_groups','cities'):
            file=base/tab/'all.json'
            if file.exists():
                payload=read_json(file)
                if not isinstance(payload,list): raise ValueError(f'Expected list in {file}')
                data.extend((rec,file.as_posix()) for rec in payload if isinstance(rec,dict))
            else:
                coverage.append({'table':tab,'score_type':'lookup','issue':'missing all.json'})
        else:
            for score in SCORING:
                pages=sorted((base/tab/score).glob('page_*.json'))
                numbers=[]
                expected_pages=set()
                reported=set()
                page_rows=0
                last_seen=False
                bad=[]
                for file in pages:
                    try: number=int(file.stem.removeprefix('page_'))
                    except ValueError: continue
                    numbers.append(number)
                    payload=read_json(file)
                    if not isinstance(payload,dict) or not isinstance(payload.get('content'),list):
                        bad.append(file.name); continue
                    page_rows+=len(payload['content'])
                    data.extend((rec,file.as_posix()) for rec in payload['content'] if isinstance(rec,dict))
                    if isinstance(payload.get('totalPages'),int):
                        expected_pages.add(payload['totalPages'])
                    if isinstance(payload.get('totalElements'),int):
                        reported.add(payload['totalElements'])
                    if payload.get('last') is True: last_seen=True
                expected=next(iter(expected_pages)) if len(expected_pages)==1 else None
                declared=next(iter(reported)) if len(reported)==1 else None
                missing=sorted(set(range(expected))-set(numbers)) if expected is not None else []
                coverage.append({
                    'table':tab,'score_type':score,'files':len(pages), 'loaded_rows':page_rows,
                    'reported_total_pages':expected,'reported_total_elements':declared,
                    'missing_page_count':len(missing),'missing_pages_preview':str(missing[:12]),
                    'saw_last':last_seen,'bad_json_pages':len(bad),
                    'row_total_matches':('yes' if declared==page_rows else 'no' if declared is not None else 'unknown'),
                    'complete_by_page_count':('yes' if expected is not None and not missing and len(numbers)==expected and not bad else 'no' if expected is not None else 'unknown'),
                    'issue':(', '.join(bad[:3]) if bad else ''),
                })
        tables[tab]=data
    return tables,coverage

def audit_keys(tables):
    summary=[]
    for table,specs in KEY_TESTS.items():
        data=tables[table]
        for fields in specs:
            vals=[key(row,fields) for row,_ in data]
            valid=[x for x in vals if x is not None]
            counter={}
            for k in valid: counter[k]=counter.get(k,0)+1
            summary.append({
                'table':table,'candidate_fields':'+'.join(fields), 'rows':len(vals),
                'non_null':len(valid),'null_count':len(vals)-len(valid),
                'distinct':len(counter),'duplicate_rows':len(valid)-len(counter),
                'duplicate_groups':sum(count>1 for count in counter.values()),
                'valid_unique':len(valid)==len(vals) and len(counter)==len(vals) and bool(vals)
            })
    return summary

def audit_duplicates(tables):
    buckets=defaultdict(list)
    for item in tables['net_results']:
        row,source=item
        k=key(row,('kilavuzKodu','yil'))
        if k is not None: buckets[k].append(item)
    groups=[];details=[]
    for (code,year), items in sorted(buckets.items(), key=lambda pair:(str(pair[0][1]),str(pair[0][0]))):
        if len(items)<2: continue
        hashes={canonical_hash(row) for row,_ in items}
        different={field for row,_ in items for field in row if len({json.dumps(r.get(field),sort_keys=True,ensure_ascii=False) for r,_ in items})>1}
        locations={src for _,src in items}
        groups.append({
            'kilavuzKodu':code,'yil':year,'rows':len(items),
            'excess_rows':len(items)-1, 'distinct_payloads':len(hashes),
            'identical_payload':len(hashes)==1,'different_fields':'+'.join(sorted(different)),
            'puan_turleri':'+'.join(sorted({str(r.get('puanTuru')) for r,_ in items})),
            'source_file_count':len(locations),'across_pages':len(locations)>1,
            'source_files':';'.join(sorted(locations))[:600],
        })
        for row,src in items:
            details.append({'kilavuzKodu':code,'yil':year,'source_file':src,
                'payload_sha256':canonical_hash(row),'puanTuru':row.get('puanTuru'),
                'universiteId':row.get('universiteId'), 'birimId':row.get('birimId'),
                'birimGrupId':row.get('birimGrupId'), 'tabanPuan':row.get('tabanPuan'),
                'obp':row.get('obp'), 'katsayi':row.get('katsayi'),
                'birimAdi':row.get('birimAdi')})
    return groups,details

def audit_references(tables):
    summaries=[]; errors=[]
    for child, label, parent, parentfields in REFERENCES:
        childfields=tuple(label.split('+'))
        indexes={key(row,parentfields) for row,_ in tables[parent]}
        indexes.discard(None)
        nulls=matches=unmatched=0
        for row,source in tables[child]:
            val=key(row,childfields)
            if val is None:
                nulls+=1
                continue
            if val in indexes:
                matches+=1
            else:
                unmatched+=1
                errors.append({'child_table':child,'child_fields':label,'parent_table':parent,
                    'value':str(val),'source_file':source,'yil':row.get('yil'),
                    'kilavuzKodu':row.get('kilavuzKodu'),
                    'universiteAdi':row.get('universiteAdi'),
                    'birimAdi':row.get('birimAdi')})
        summaries.append({'child_table':child,'child_fields':label,'parent_table':parent,
            'child_rows':len(tables[child]),'non_null':matches+unmatched,
            'matched':matches,'orphans':unmatched,'nulls':nulls,
            'coverage':round(matches/(matches+unmatched),6) if matches+unmatched else None,
            'caution':'code-only, different years' if child=='net_results' and parent=='programs' else ''})
    return summaries,errors

def main():
    parser=argparse.ArgumentParser(description='Offline YOK Atlas key and completeness forensics')
    parser.add_argument('--root',default='outputs/yokatlas_full',type=Path,
                        help='Directory with complete_data subfolder')
    parser.add_argument('--out',default='outputs/yokatlas_forensics',type=Path)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    tables,coverage=collect(args.root)
    keys=audit_keys(tables)
    duplicates,details=audit_duplicates(tables)
    summary_fks,orphans=audit_references(tables)
    write_csv(args.out/'collection_coverage.csv',coverage,
        ['table','score_type','files','loaded_rows','reported_total_pages','reported_total_elements','missing_page_count','missing_pages_preview','saw_last','bad_json_pages','row_total_matches','complete_by_page_count','issue'])
    write_csv(args.out/'key_candidate_matrix.csv',keys,
        ['table','candidate_fields','rows','non_null','null_count','distinct','duplicate_rows','duplicate_groups','valid_unique'])
    write_csv(args.out/'net_duplicate_groups.csv',duplicates,
        ['kilavuzKodu','yil','rows','excess_rows','distinct_payloads','identical_payload','different_fields','puan_turleri','source_file_count','across_pages','source_files'])
    write_csv(args.out/'net_duplicate_details.csv',details,
        ['kilavuzKodu','yil','source_file','payload_sha256','puanTuru','universiteId','birimId','birimGrupId','tabanPuan','obp','katsayi','birimAdi'])
    write_csv(args.out/'reference_summary.csv',summary_fks,
        ['child_table','child_fields','parent_table','child_rows','non_null','matched','orphans','nulls','coverage','caution'])
    write_csv(args.out/'reference_exceptions.csv',orphans,
        ['child_table','child_fields','parent_table','value','source_file','yil','kilavuzKodu','universiteAdi','birimAdi'])
    summary={
        'data_row_counts':{k:len(v) for k,v in tables.items()},
        'duplicate_program_year_groups':len(duplicates),
        'duplicate_program_year_excess_rows':sum(row['excess_rows'] for row in duplicates),
        'identical_groups':sum(row['identical_payload'] for row in duplicates),
        'different_payload_groups':sum(not row['identical_payload'] for row in duplicates),
        'cross_page_groups':sum(row['across_pages'] for row in duplicates),
        'unique_candidate_keys':[{'table':r['table'],'fields':r['candidate_fields']} for r in keys if r['valid_unique']],
        'collection_complete_for_search':all(r.get('complete_by_page_count')=='yes' for r in coverage if r['table'] in ('programs','net_results')),
        'warnings':['Identical payloads may be safely considered for de-duplication after manual review; do not delete automatically.',
                    'Net to current program join is code-only and crosses years; do not enforce it as a foreign key.',
                    'Missing keys in 2026 lookups may represent historical entries, not source corruption.']
    }
    with (args.out/'forensics_summary.json').open('w',encoding='utf-8') as f:
        json.dump(summary,f,ensure_ascii=False,indent=2)
    print('AUDIT:',args.out.resolve())
    print('ROWS:',summary['data_row_counts'])
    print('NET DUPLICATES:',len(duplicates),'key groups /',summary['duplicate_program_year_excess_rows'],'excess rows')
    print('IDENTICAL GROUPS:',summary['identical_groups'],'CHANGED GROUPS:',summary['different_payload_groups'])
    print('CROSS PAGE:',summary['cross_page_groups'])
    print('COLLECTION COVERAGE VERIFIED:',summary['collection_complete_for_search'])

if __name__=='__main__':
    main()
