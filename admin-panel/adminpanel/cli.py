"""Komut satırı yardımcıları.

  python -m adminpanel.cli migrate                    # ops şemasını kurar / günceller
  python -m adminpanel.cli create-user merve "Merve Gündoğdu" --email merve@ornek.com
  python -m adminpanel.cli set-password merve
  python -m adminpanel.cli add-example-bot            # panelin denemesi için örnek bot
"""
import argparse
import getpass
import sys

from psycopg.types.json import Jsonb

from . import db, security


def _ask_password() -> str:
    while True:
        p1 = getpass.getpass("Parola (en az 10 karakter): ")
        if len(p1) < 10:
            print("Parola çok kısa.")
            continue
        if p1 != getpass.getpass("Parola (tekrar): "):
            print("Parolalar aynı değil.")
            continue
        return p1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="adminpanel.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    cu = sub.add_parser("create-user")
    cu.add_argument("username")
    cu.add_argument("full_name")
    cu.add_argument("--email")
    sp = sub.add_parser("set-password")
    sp.add_argument("username")
    sub.add_parser("add-example-bot")
    a = ap.parse_args(argv)

    if a.cmd == "migrate":
        print("Uygulandı:", ", ".join(db.migrate()))
    elif a.cmd == "create-user":
        pw = _ask_password()
        db.run("INSERT INTO ops.users(username, full_name, email, password_hash) VALUES (%s,%s,%s,%s)",
               (a.username, a.full_name, a.email, security.hash_password(pw)))
        print(f"{a.username} oluşturuldu.")
    elif a.cmd == "set-password":
        pw = _ask_password()
        if not db.run("UPDATE ops.users SET password_hash=%s WHERE username=%s",
                      (security.hash_password(pw), a.username)):
            sys.exit(f"{a.username} bulunamadı")
        db.run("DELETE FROM ops.sessions WHERE user_id=(SELECT user_id FROM ops.users WHERE username=%s)",
               (a.username,))
        print("Parola değişti.")
    elif a.cmd == "add-example-bot":
        db.run("INSERT INTO ops.bots(slug, name, description, command, working_dir, schedule_cron, settings, "
               "expected_min_records, timeout_minutes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
               "ON CONFLICT (slug) DO NOTHING",
               ("ornek-bot", "Örnek bot",
                "Panelin denemesi için: sayfa indiriyormuş gibi yapar, gerçek siteye gitmez.",
                "python -m bots.ornek_bot", ".", None,
                Jsonb({"sayfa_sayisi": 40, "bekleme_saniye": 0.5, "hata_orani": 0.05}), 30, 30))
        print("ornek-bot eklendi (zaten varsa dokunulmadı).")


if __name__ == "__main__":
    main()
