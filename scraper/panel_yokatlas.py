"""Admin runner entry point: python -m scraper.panel_yokatlas."""
from __future__ import annotations

import logging
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from scraper.bot import AccessBlocked, Paused, SnapshotChanged, cycle, process_lock


def run(bot):
    settings = bot.settings
    root = Path(settings.get('arsiv_dizini', 'outputs/yokatlas_bot'))
    if root.is_absolute() or '..' in root.parts:
        raise ValueError('Arşiv dizini proje klasörünün içinde olmalı.')
    args = SimpleNamespace(bot=bot, archive_only=settings.get('sadece_arsiv', False),
        page_size=int(settings.get('sayfa_boyutu', 100)),
        delay=float(settings.get('bekleme_saniye', 2)),
        timeout=20, retries=3, max_requests=int(settings.get('azami_istek', 10000)),
        interval=86400, env_file=Path('.env'))
    if (not isinstance(args.archive_only, bool) or not 1 <= args.page_size <= 100
            or not math.isfinite(args.delay) or args.delay < 1 or args.max_requests < 1):
        raise ValueError('Geçersiz bot ayarları: sayfa 1–100, bekleme en az 1 saniye olmalı.')
    # Data writes always use the ingestion role; ADMIN_DATABASE_URL is only for botkit.
    os.environ.update(PGHOST='postgres', PGPORT='5432', PGDATABASE='yokatlas_intelligence', PGUSER='atlas_ingest')
    os.environ.pop('PGPASSWORD', None)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stdout)
    with process_lock(root.resolve()):
        result = cycle(root.resolve(), args)
    bot.summary(snapshot=result['snapshot_id'], database_result=result.get('database_result', {}))
    if result.get('database_result', {}).get('status') == 'completed_with_issues':
        raise ValueError('Aktarım bitti; karantina/kalite kayıtlarının incelenmesi gerekiyor.')
    bot.progress(1, 1, 'Tamamlandı')


def main():
    from botkit import Bot
    try:
        with Bot.from_env() as bot:
            try:
                run(bot)
            except (KeyboardInterrupt, Paused, SnapshotChanged, AccessBlocked, ValueError):
                raise
            except Exception as exc:
                # Driver exceptions can contain credentials; do not send their text to panel logs.
                raise RuntimeError(f'İşlem durdu ({type(exc).__name__}); bağlantıyı ve arşivi kontrol edin.') from None
    except KeyboardInterrupt:
        print('WARNING: Durduruldu; arşiv ve kontrol noktası korundu.', flush=True)
        return 130
    except (Paused, SnapshotChanged) as exc:
        print(f'WARNING: {exc}', flush=True)
        return 2
    except Exception as exc:
        print(f'ERROR: {exc}', flush=True)
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
