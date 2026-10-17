"""Veritabanı gerektirmeyen hızlı testler:  python -m pytest tests"""
from adminpanel import security
from adminpanel.runner import LEVEL_RE
from adminpanel.web import BotIn


def test_password_roundtrip():
    h = security.hash_password("uzun-bir-parola")
    assert security.verify_password("uzun-bir-parola", h)
    assert not security.verify_password("yanlis-parola", h)


def test_log_levels():
    assert LEVEL_RE.match("WARNING: dikkat").group(1) == "WARNING"
    assert LEVEL_RE.match("ERROR - hata").group(1) == "ERROR"
    assert LEVEL_RE.match("normal satır") is None


def test_cron_validation():
    assert BotIn(schedule_cron="0 3 * * *").schedule_cron == "0 3 * * *"
    assert BotIn(schedule_cron="").schedule_cron == ""
    try:
        BotIn(schedule_cron="her gece")
        assert False
    except ValueError:
        pass


def test_working_dir_stays_in_repo():
    for bad in ("/etc", "../disari", "scraper/../../x"):
        try:
            BotIn(working_dir=bad)
            assert False, bad
        except ValueError:
            pass
    assert BotIn(working_dir="scraper").working_dir == "scraper"
