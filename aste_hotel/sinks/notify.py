"""Canali di notifica (sink). Interfaccia comune cosi' aggiungere un canale
(email, webhook, Discord...) non tocca la logica del resto del sistema.

Telegram e' il default consigliato: gratis, push immediato sul telefono, niente
problemi di spam/deliverability come l'email, link cliccabili.

Setup Telegram (una volta):
  1. Su Telegram cerca @BotFather -> /newbot -> ottieni il TOKEN.
  2. Scrivi un messaggio al tuo bot, poi apri
     https://api.telegram.org/bot<TOKEN>/getUpdates per leggere il tuo chat_id.
  3. Metti token e chat_id in config/settings.toml (vedi esempio).
"""

from __future__ import annotations

import logging
from typing import Iterable

import requests

from ..core.models import Listing

log = logging.getLogger(__name__)


class Sink:
    def send(self, listings: list[Listing]) -> None:
        raise NotImplementedError


def _fmt(lst: Listing) -> str:
    price = f"{lst.price:,.0f} €".replace(",", ".") if lst.price else "n/d"
    bits = [f"🏨 <b>{_esc(lst.title)}</b>"]
    loc = " · ".join(p for p in [lst.city, lst.province, lst.region] if p)
    if loc:
        bits.append(_esc(loc))
    bits.append(f"💰 Base: {price}")
    if lst.tribunale:
        bits.append(f"⚖️ {_esc(lst.tribunale)} {_esc(lst.procedura)}")
    if lst.sale_date:
        bits.append(f"📅 Vendita: {_esc(lst.sale_date)}")
    bits.append(f"🔗 {lst.url}")
    bits.append(f"<i>fonte: {lst.source}</i>")
    return "\n".join(bits)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class TelegramSink(Sink):
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def send(self, listings: list[Listing]) -> None:
        for lst in listings:
            self._send_one(_fmt(lst))

    def _send_one(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            r = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=15,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            log.error("invio Telegram fallito: %s", e)


class ConsoleSink(Sink):
    """Utile in sviluppo: stampa a schermo invece di inviare."""

    def send(self, listings: list[Listing]) -> None:
        for lst in listings:
            print("-" * 60)
            print(_fmt(lst).replace("<b>", "").replace("</b>", "")
                  .replace("<i>", "").replace("</i>", ""))


# --- Email (SMTP Gmail) ---
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

DASHBOARD_URL = "https://cristiancannava-source.github.io/aste-hotel/"


def _email_html(listings):
    righe = []
    for lst in listings:
        price = f"{lst.price:,.0f} €".replace(",", ".") if lst.price else "n/d"
        loc = " · ".join(p for p in [lst.city, lst.province, lst.region] if p)
        trib = f"{lst.tribunale} {lst.procedura}".strip()
        data = lst.sale_date[:10] if lst.sale_date else ""
        if data and "-" in data:
            data = "/".join(reversed(data.split("-")))
        righe.append(f'<tr><td style="padding:12px;border-bottom:1px solid #eee;"><a href="{_esc(lst.url)}" style="color:#1558d6;text-decoration:none;font-weight:600;">{_esc(lst.title[:140])}</a><br><span style="color:#555;font-size:13px;">{_esc(loc)}</span></td><td style="padding:12px;border-bottom:1px solid #eee;white-space:nowrap;font-weight:600;color:#0a7d4b;">{_esc(price)}</td><td style="padding:12px;border-bottom:1px solid #eee;font-size:13px;color:#555;">{_esc(trib)}</td><td style="padding:12px;border-bottom:1px solid #eee;font-size:13px;color:#555;white-space:nowrap;">{_esc(data)}</td><td style="padding:12px;border-bottom:1px solid #eee;font-size:12px;color:#888;">{_esc(lst.source)}</td></tr>')
    return f'''<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:760px;margin:auto;">
<h2 style="color:#222;">🏨 Nuove aste alberghiere ({len(listings)})</h2>
<table style="width:100%;border-collapse:collapse;font-size:14px;">
<tr style="text-align:left;color:#888;font-size:12px;"><th style="padding:8px 12px;">Lotto</th><th style="padding:8px 12px;">Base</th><th style="padding:8px 12px;">Tribunale</th><th style="padding:8px 12px;">Vendita</th><th style="padding:8px 12px;">Fonte</th></tr>
{"".join(righe)}
</table>
<div style="margin:24px 0;text-align:center;">
<a href="{DASHBOARD_URL}" style="display:inline-block;background:#1558d6;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:600;font-size:14px;">📊 Apri la dashboard completa</a>
</div>
<p style="color:#aaa;font-size:12px;margin-top:8px;text-align:center;">Monitoraggio automatico aste hotel · <a href="{DASHBOARD_URL}" style="color:#999;">{DASHBOARD_URL}</a></p>
</div>'''


class EmailSink(Sink):
    def __init__(self, host, port, user, password, to, cc=None):
        self.host, self.port = host, port
        self.user, self.password = user, password
        self.to = to
        self.cc = cc or []

    def send(self, listings):
        if not listings:
            return
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🏨 {len(listings)} nuove aste alberghiere"
        msg["From"] = self.user
        msg["To"] = ", ".join(self.to)
        if self.cc:
            msg["Cc"] = ", ".join(self.cc)
        msg.attach(MIMEText(_email_html(listings), "html", "utf-8"))
        destinatari = self.to + self.cc
        try:
            with smtplib.SMTP(self.host, self.port, timeout=30) as s:
                s.starttls()
                s.login(self.user, self.password)
                s.sendmail(self.user, destinatari, msg.as_string())
            log.info("email inviata a %d destinatari", len(destinatari))
        except Exception as e:
            log.error("invio email fallito: %s", e)


class MultiSink(Sink):
    def __init__(self, sinks):
        self.sinks = sinks

    def send(self, listings):
        for s in self.sinks:
            try:
                s.send(listings)
            except Exception as e:
                log.error("sink %s fallito: %s", type(s).__name__, e)
