"""Admin runner entry point: python -m scraper.panel_urap."""
from scraper.report_bot import panel_main


if __name__ == '__main__':
    raise SystemExit(panel_main('urap'))
