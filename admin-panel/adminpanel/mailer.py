"""E-posta gönderimi (SMTP)."""
import smtplib
import ssl
from email.message import EmailMessage
from html import escape

from . import config


def configured() -> bool:
    return bool(config.SMTP_HOST)


def send(recipients: list[str], subject: str, body: str) -> None:
    """Hata olursa istisna fırlatır; çağıran kaydeder."""
    if not configured():
        raise RuntimeError("SMTP ayarlı değil (ADMIN_SMTP_HOST boş)")
    if not recipients:
        raise RuntimeError("Bildirim alacak e-posta adresi yok")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.SMTP_FROM
    msg["To"] = ", ".join(recipients)
    msg.set_content(body + f"\n\nPanel: {config.PANEL_URL}\n")
    msg.add_alternative(
        "<div style=\"font-family:Arial,sans-serif;color:#1D1A3A\">"
        "<p style=\"font-weight:700;color:#3448D8;margin:0 0 12px\">ÜniRota admin paneli</p>"
        f"<pre style=\"font-family:inherit;white-space:pre-wrap;font-size:15px\">{escape(body)}</pre>"
        f"<p><a href=\"{escape(config.PANEL_URL)}\" style=\"color:#3448D8\">Paneli aç</a></p></div>",
        subtype="html",
    )
    ctx = ssl.create_default_context()
    if config.SMTP_SSL:
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=ctx, timeout=20) as s:
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
    else:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
            if config.SMTP_STARTTLS:
                s.starttls(context=ctx)
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
