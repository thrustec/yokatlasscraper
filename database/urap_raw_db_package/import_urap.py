"""Strict, transactional URAP PDF-derived CSV -> source-oriented RAW importer.
Usage: python import_urap.py --csv ... --pdf ... --database-url "$DATABASE_URL"
Defaults to validation-only. Supply --write explicitly to commit.
"""
import argparse
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

METRICS = ["article_score", "citation_score", "scientific_document_score", "doctoral_score", "faculty_student_score", "international_collaboration_score", "domestic_collaboration_score", "tubitak_project_score"]
FIELDS = ["edition", "source_page", "rank", "university_name", "city", *METRICS, "total_score", "score_delta"]
EXPECTED_EDITION = '2025-2026'
EXPECTED_PDF_SHA256 = '8d7847e3d62c995b1e9e6156cddb4ee61f67eedfe6c17832a6b19477e5dc5095'
PDF_URL = 'https://newtr.urapcenter.org/cdn/storage/PDFs/tQbaMj9JihCHaaNuE/original/tQbaMj9JihCHaaNuE.pdf'
PARSER_VERSION = 'urap_pdf_tab10_pilot_v1'

def check_csv(path):
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ValueError(f'CSV columns differ: {reader.fieldnames}')
        rows = list(reader)
    if len(rows) != 198:
        raise ValueError(f'Expected 198 rows, got {len(rows)}')
    ranks = set()
    for r in rows:
        if r['edition'] != EXPECTED_EDITION:
            raise ValueError('Unexpected edition')
        rank = int(r['rank'])
        page = int(r['source_page'])
        if not (18 <= page <= 26) or rank in ranks or not r['university_name'].strip() or not r['city'].strip():
            raise ValueError(f'Bad row rank={rank}')
        ranks.add(rank)
        parts = [Decimal(r[m]) for m in METRICS]
        total = Decimal(r['total_score'])
        delta = Decimal(r['score_delta'])
        if min(parts + [total]) < 0 or abs(sum(parts) - total) > Decimal('0.06'):
            raise ValueError(f'Score mismatch at rank {rank}')
        if abs(delta - (sum(parts) - total)) > Decimal('0.011'):
            raise ValueError(f'Delta mismatch at rank {rank}')
    if ranks != set(range(1, 199)):
        raise ValueError('Ranks not 1..198')
    return rows

def check_pdf(path):
    payload = path.read_bytes()
    sha = hashlib.sha256(payload).hexdigest()
    if sha != EXPECTED_PDF_SHA256:
        raise ValueError(f'PDF SHA256 differs from reviewed artifact: {sha}')
    return sha, len(payload)

def insert(cur, rows, sha, size, pdf_path):
    cur.execute("""INSERT INTO raw.urap_artifacts
      (sha256,source_url,storage_uri,content_type,byte_size,parser_version,published_on)
      VALUES (%s,%s,%s,%s,%s,%s,%s)
      ON CONFLICT (sha256) DO NOTHING""", (sha,PDF_URL,pdf_path.resolve().as_uri(),'application/pdf',size,PARSER_VERSION,'2025-10-19'))
    cur.execute('SELECT id FROM raw.urap_artifacts WHERE sha256=%s', (sha,))
    artifact_id = cur.fetchone()[0]
    cur.execute("""INSERT INTO raw.urap_editions (edition,publication_date,source_artifact_id)
       VALUES (%s,%s,%s) ON CONFLICT (edition) DO NOTHING""", (EXPECTED_EDITION,'2025-10-19',artifact_id))
    cur.execute('SELECT id,source_artifact_id FROM raw.urap_editions WHERE edition=%s', (EXPECTED_EDITION,))
    edition_id, existing_artifact = cur.fetchone()
    if existing_artifact != artifact_id:
        raise ValueError('Existing edition refers to another PDF; manual version review required')
    cur.execute('SELECT id FROM raw.urap_ranking_groups WHERE code=%s', ('GENERAL',))
    group_id = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM raw.urap_ranking_rows WHERE edition_id=%s AND group_id=%s',(edition_id,group_id))
    existing_count = cur.fetchone()[0]
    if existing_count:
        if existing_count != 198:
            raise ValueError(f'Incomplete existing import: {existing_count} rows; manual review required')
        for row in rows:
            cur.execute('''SELECT r.id,r.source_artifact_id,r.source_page,r.university_name,r.city,r.total_score
              FROM raw.urap_ranking_rows r WHERE r.edition_id=%s AND r.group_id=%s AND r.source_rank=%s''', (edition_id,group_id,int(row['rank'])))
            old = cur.fetchone()
            if not old or (old[1],old[2],old[3],old[4],old[5]) != (artifact_id,int(row['source_page']),row['university_name'],row['city'],Decimal(row['total_score'])):
                raise ValueError(f'Existing data differs at rank {row["rank"]}; no silent overwrite')
            cur.execute('SELECT metric_code,score FROM raw.urap_metric_scores WHERE ranking_row_id=%s',(old[0],))
            scores = dict(cur.fetchall())
            if len(scores) != 8 or any(scores.get(m) != Decimal(row[m]) for m in METRICS):
                raise ValueError(f'Existing metric differs at rank {row["rank"]}')
        return 'already_loaded_and_identical'
    for row in rows:
        cur.execute('''INSERT INTO raw.urap_ranking_rows
          (edition_id,group_id,source_artifact_id,source_page,source_rank,university_name,city,total_score,extraction_score_delta)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id''',
          (edition_id,group_id,artifact_id,int(row['source_page']),int(row['rank']),row['university_name'],row['city'],Decimal(row['total_score']),Decimal(row['score_delta'])))
        row_id = cur.fetchone()[0]
        for m in METRICS:
            cur.execute('INSERT INTO raw.urap_metric_scores (ranking_row_id,metric_code,score) VALUES (%s,%s,%s)',(row_id,m,Decimal(row[m])))
    return 'inserted_198'

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv',type=Path,required=True)
    p.add_argument('--pdf',type=Path,required=True)
    p.add_argument('--database-url',help='PostgreSQL DSN, required only for --write')
    p.add_argument('--write',action='store_true',help='Commit import to database')
    a=p.parse_args()
    rows=check_csv(a.csv)
    sha,size=check_pdf(a.pdf)
    result={'validated_rows':len(rows),'artifact_sha256':sha,'artifact_bytes':size,'mode':'validation_only'}
    if a.write:
        if not a.database_url:
            p.error('Provide --database-url when using --write')
        import psycopg
        with psycopg.connect(a.database_url) as conn:
            with conn.cursor() as cur:
                result['result']=insert(cur,rows,sha,size,a.pdf)
            conn.commit()
        result['mode']='database_write'
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
