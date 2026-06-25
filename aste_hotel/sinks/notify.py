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
