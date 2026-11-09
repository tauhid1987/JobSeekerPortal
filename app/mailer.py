"""Sends the 'your access is approved' email over SMTP. Nothing is sent unless the server has SMTP settings.

Free Render servers block the SMTP ports (25, 465, 587), so the preferred way is Brevo's web API (port 443):
  BREVO_API_KEY (a Brevo API key, not the SMTP key) and MAIL_FROM (a sender verified in Brevo)
SMTP still works where the ports are open (paid plan, your own PC). Set these on the host, never in the repo:
  SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD, MAIL_FROM (defaults to SMTP_USER), SITE_URL
For Gmail use smtp.gmail.com / 587 and an App Password (needs 2-step verification), not the normal password.
"""
import os
import re
import smtplib
import socket
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

import requests

# same rule as docs/js/email.js: name@domain.tld, no spaces, no double dots
EMAIL_RE = re.compile(r"^(?!.*\.\.)[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$")
DEFAULT_SITE = "https://tauhid1987.github.io/JobSeekerPortal/"


class MailNotConfigured(Exception):
    pass


def valid_email(addr):
    return isinstance(addr, str) and len(addr) <= 120 and EMAIL_RE.match(addr) is not None


def _env(name, default=""):
    """Setting from the environment with stray spaces / new lines (easy to paste by mistake) removed."""
    return (os.getenv(name) or default).strip()


class MailApiError(Exception):
    def __init__(self, status, detail):
        super().__init__(f"{status} {detail}")
        self.status, self.detail = status, detail


def configured():
    return bool(_env("BREVO_API_KEY") and _env("MAIL_FROM")) or bool(_env("SMTP_HOST") and _env("SMTP_USER") and _env("SMTP_PASSWORD"))


def _clean(text, limit):
    """One line, no control characters: stops header injection through a person's name."""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(text or "")).strip()[:limit]


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_approval(to_addr, name):
    if not valid_email(to_addr):
        raise ValueError("invalid email address")
    site = _env("SITE_URL", DEFAULT_SITE)
    sender = _env("MAIL_FROM") or _env("SMTP_USER")
    who = _clean(name, 60) or "there"
    msg = EmailMessage()
    msg["Subject"] = "Your JobMatch access is approved"
    msg["From"] = formataddr(("JobMatch", sender))
    msg["To"] = to_addr
    msg.set_content(
        f"Hello {who},\n\nGood news: an admin approved your JobMatch account.\n\n"
        f"Confirm and start here (sign in with this email address):\n{site}\n\n"
        "Upload your CV, choose your country and get a ranked list of jobs you can apply for.\n\n"
        "If you did not ask for access, you can ignore this email.\n")
    msg.add_alternative(
        f"<p>Hello {_esc(who)},</p><p>Good news: an admin approved your <b>JobMatch</b> account.</p>"
        f'<p><a href="{_esc(site)}" style="background:#2563eb;color:#fff;padding:10px 18px;border-radius:6px;'
        f'text-decoration:none;display:inline-block">Confirm and open JobMatch</a></p>'
        "<p>Sign in with this email address. Then upload your CV, choose your country and get a ranked list of jobs you can apply for.</p>"
        '<p style="color:#666;font-size:12px">If you did not ask for access, you can ignore this email.</p>', subtype="html")
    return msg


def explain(exc):
    """A short, safe reason for the admin. Never contains a password or key."""
    host = _env("SMTP_HOST", "the SMTP host")
    if isinstance(exc, MailApiError):
        if exc.status in (401, 403):
            return "Brevo rejected the API key. On Render check BREVO_API_KEY (an API key from Brevo > SMTP & API > API Keys, not the SMTP key). If it is right, Brevo may need your account activated."
        return f"Brevo refused this message: {exc.status} {_clean(exc.detail, 160)} (check MAIL_FROM is a verified sender in Brevo)."
    if isinstance(exc, requests.exceptions.RequestException):
        return "Could not reach the Brevo email service. Try again in a minute."
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "The email service rejected the login. On Render check SMTP_USER (the Login shown on the Brevo SMTP page, not the key name) and SMTP_PASSWORD (the SMTP key)."
    if isinstance(exc, (smtplib.SMTPSenderRefused, smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError)):
        return "The email service refused this message: " + _reply(exc) + " (check MAIL_FROM is a verified sender, and that the Brevo account is activated)."
    if isinstance(exc, (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, socket.gaierror, ConnectionError, TimeoutError)):
        return f"Could not connect to {host}. Check SMTP_HOST and SMTP_PORT on Render."
    return f"The email could not be sent ({type(exc).__name__}). See the Render logs for details."


def _reply(exc):
    text = getattr(exc, "smtp_error", None) or getattr(exc, "recipients", None) or str(exc)
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    code = getattr(exc, "smtp_code", "")
    return re.sub(r"[\x00-\x1f\x7f]+", " ", f"{code} {text}").strip()[:200]


def _api_send(msg):
    sender, to = parseaddr(str(msg["From"]))[1], parseaddr(str(msg["To"]))[1]
    body = {"sender": {"name": "JobMatch", "email": sender}, "to": [{"email": to}], "subject": str(msg["Subject"]),
            "textContent": msg.get_body(("plain",)).get_content(), "htmlContent": msg.get_body(("html",)).get_content()}
    r = requests.post("https://api.brevo.com/v3/smtp/email", json=body, timeout=20,
                      headers={"api-key": _env("BREVO_API_KEY"), "accept": "application/json"})
    if r.status_code >= 300:
        raise MailApiError(r.status_code, r.text)


def send(msg):
    if not configured():
        raise MailNotConfigured("Email is not set up on the server (BREVO_API_KEY or SMTP settings missing).")
    if _env("BREVO_API_KEY") and _env("MAIL_FROM"):
        return _api_send(msg)
    host, port = _env("SMTP_HOST"), int(_env("SMTP_PORT", "587"))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20, context=ctx) as s:
            s.login(_env("SMTP_USER"), _env("SMTP_PASSWORD"))
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(_env("SMTP_USER"), _env("SMTP_PASSWORD"))
            s.send_message(msg)
