"""Admin runner entry point: python -m scraper.panel_tuik."""
from __future__ import annotations

import os
import re
from urllib.parse import parse_qs, urlsplit


def targets(settings, retries):
    selected = {(settings.get('dataflow_id', 'DF_ADNKS_T16'),
                 str(settings.get('version', '1.0')), int(settings.get('yil', 2025)))}
    retry_targets = set()
    for request in retries:
        url = urlsplit(request.get('url') or request['request_key'])
        match = re.fullmatch(r'/rest/data/TR,([A-Z0-9_]+),(\d+(?:\.\d+){1,2})', url.path)
        if match:
            query = parse_qs(url.query)
            year = int(query['startPeriod'][0])
            retry_targets.add((*match.groups(), year))
    result = sorted(retry_targets or selected)
    for dataflow, version, year in result:
        if (not isinstance(dataflow, str) or not re.fullmatch(r'[A-Z0-9_]{1,100}', dataflow)
                or not re.fullmatch(r'\d+(?:\.\d+){1,2}', version) or not 1900 <= year <= 2100):
            raise ValueError('Veri akışı, sürüm veya yıl ayarı geçersiz.')
    return result


def run(bot):
    from backend import tuik_jobs as jobs
    os.environ.update(PGHOST='postgres', PGPORT='5432', PGDATABASE='yokatlas_intelligence')
    chosen = targets(bot.settings, bot.retry_requests)
    bot.progress(0, len(chosen), 'TÜİK: katalog doğrulaması')
    catalog = jobs.list_datasets(monitor=bot)
    if bot.settings.get('sadece_katalog', False):
        bot.summary(dataset_count=len(catalog), dataflows=catalog)
        bot.progress(1, 1, 'TÜİK: katalog hazır')
        bot.log(f'TÜİK kataloğunda {len(catalog)} veri akışı var.')
        return
    for dataflow, version, year in chosen:
        if bot.should_stop():
            raise KeyboardInterrupt
        dataset = next((d for d in catalog if d['id'] == dataflow and d['version'] == version), None)
        if dataset is None:
            raise ValueError('Seçilen veri akışı/sürüm TÜİK kataloğunda bulunamadı.')
        bot.log(f"TÜİK: {dataset['title']} ({dataflow}, {version}), yıl {year}")
        run_id = jobs.create_run(dataset, year)
        jobs.run_ingestion(run_id, dataset, year, monitor=bot)
        result = jobs.get_run(run_id)
        if not result or result['status'] not in ('completed', 'completed_with_issues'):
            raise RuntimeError((result or {}).get('message') or 'TÜİK aktarımı tamamlanamadı.')
        if result['status'] == 'completed_with_issues':
            raise ValueError('Aktarım bitti; kalite/il eşleme uyarılarını inceleyin.')
        bot.log(f"TÜİK tamamlandı: {result['records']} gözlem, {result['staged_records']} il kaydı.")


def main():
    from botkit import Bot
    try:
        with Bot.from_env() as bot:
            try:
                run(bot)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                from backend.tuik_jobs import TuikError
                message = str(exc) if isinstance(exc, (TuikError, ValueError, RuntimeError)) else f'TÜİK işlemi durdu ({type(exc).__name__}).'
                raise RuntimeError(message) from None
    except KeyboardInterrupt:
        print('WARNING: TÜİK durduruldu; tamamlanmamış transaction geri alındı.', flush=True)
        return 130
    except Exception as exc:
        print(f'ERROR: {exc}', flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
