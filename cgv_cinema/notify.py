# -*- coding: utf-8 -*-
"""Notification sinks: console (always) + optional SMTP email."""

from __future__ import annotations

import datetime as dt
import smtplib
import sys
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

from . import config

# UTF-8 console (Windows cp949 안전장치)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


class ConsoleNotifier:
    """Loud terminal output with a BEL beep. Always available."""

    def send(self, subject: str, body: str) -> bool:
        bar = "═" * 64
        # \a rings the terminal bell.
        print(f"\a\n{bar}\n🔔  {subject}\n{bar}\n{body}\n{bar}\n", flush=True)
        return True


class EmailNotifier:
    """Sends alerts over SMTP (STARTTLS by default).

    Configured entirely from environment variables; see
    :func:`cgv_cinema.config.email_config`.
    """

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or config.email_config()

    @property
    def enabled(self) -> bool:
        c = self.cfg
        return bool(c["host"] and c["user"] and c["password"] and c["to_addrs"])

    def send(self, subject: str, body: str) -> bool:
        if not self.enabled:
            return False
        c = self.cfg
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = formataddr(("CGV 알리미", c["from_addr"]))
        msg["To"] = ", ".join(c["to_addrs"])
        msg["Date"] = formatdate(localtime=True)
        try:
            if c.get("use_ssl"):
                srv = smtplib.SMTP_SSL(c["host"], c["port"], timeout=20)
            else:
                srv = smtplib.SMTP(c["host"], c["port"], timeout=20)
            with srv:
                srv.ehlo()
                if c["use_tls"] and not c.get("use_ssl"):
                    srv.starttls()
                    srv.ehlo()
                srv.login(c["user"], c["password"])
                srv.sendmail(c["from_addr"], c["to_addrs"], msg.as_string())
            print(f"   ✉️  이메일 발송 → {', '.join(c['to_addrs'])}", flush=True)
            return True
        except Exception as e:   # noqa: BLE001 - never let alerting crash the loop
            print(f"   ⚠️  이메일 발송 실패: {e}", flush=True)
            return False


class NotifierGroup:
    """Fan-out to several notifiers; one failure never blocks the others."""

    def __init__(self, *notifiers):
        self.notifiers = [n for n in notifiers if n is not None]

    def send(self, subject: str, body: str) -> None:
        for n in self.notifiers:
            try:
                n.send(subject, body)
            except Exception as e:   # noqa: BLE001
                print(f"   ⚠️  notifier {n.__class__.__name__} 실패: {e}",
                      flush=True)


def build_default_notifier() -> NotifierGroup:
    """Console always; email only when SMTP env vars are present."""
    email = EmailNotifier()
    if email.enabled:
        return NotifierGroup(ConsoleNotifier(), email)
    return NotifierGroup(ConsoleNotifier())


def format_alert(kind: str, shows, date: str, site_name: str) -> tuple[str, str]:
    """Compose (subject, body) for an alert about a list of showtimes."""
    d = dt.datetime.strptime(date, "%Y%m%d").date()
    wd = "월화수목금토일"[d.weekday()]
    subject = f"[CGV 알림] {site_name} 토이스토리5 2D — {kind} ({d:%m/%d} {wd})"
    lines = [
        f"{site_name}  |  {d:%Y-%m-%d}({wd})  |  토이 스토리 5 · 일반관 2D",
        f"사유: {kind}",
        "",
    ]
    for s in shows:
        lines.append(
            f"  {s.start_hhmm}~{s.end_hhmm} | {s.hall} | {s.format} | "
            f"잔여 {s.free_seats}/{s.total_seats}석 | {s.seq}회"
        )
    lines += ["", "예매: https://cgv.co.kr/cnm/movieBook/cinema"]
    return subject, "\n".join(lines)
