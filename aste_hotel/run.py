"""Orchestratore: raccoglie dalle fonti, filtra, deduplica, notifica."""
from __future__ import annotations
import logging, tomllib
from datetime import date
from pathlib import Path
from .core.store import Store
from .core.models import Listing
from .sources.pvp import PvpSource
from .sources.fallcoaste import FallcoasteSource
from .sources.astegiudiziarie import AstegiudiziarieSource
from .sources.astalegale import AstalegaleSource
from .sources.portali import (FallimentiSource, FallimentieasteSource)
from .sinks.notify import TelegramSink, ConsoleSink, EmailSink, MultiSink

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aste_hotel")

ALL_SOURCES = {
    "pvp": PvpSource, "fallcoaste": FallcoasteSource,
    "astegiudiziarie": AstegiudiziarieSource, "astalegale": AstalegaleSource,
    "fallimenti": FallimentiSource, "fallimentieaste": FallimentieasteSource,
}

def load_config() -> dict:
    p = Path(__file__).parent.parent / "config" / "settings.toml"
    if not p.exists():
        log.warning("config mancante, uso default")
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)

def passes_filters(lst: Listing, flt: dict) -> bool:
    min_price = flt.get("min_price")
    if min_price and (lst.price is None or lst.price < min_price):
        return False
    regions = flt.get("regions")
    if regions:
        want = {r.lower() for r in regions}
        if lst.region and lst.region.lower() not in want:
            return False
    if flt.get("only_future", True) and lst.sale_date:
        if str(lst.sale_date)[:10] < date.today().isoformat():
            return False
    return True

def build_sink(cfg: dict):
    sinks = []
    tg = cfg.get("telegram", {})
    if tg.get("token") and tg.get("chat_id"):
        sinks.append(TelegramSink(tg["token"], tg["chat_id"]))
    em = cfg.get("email", {})
    if em.get("user") and em.get("password") and em.get("to"):
        sinks.append(EmailSink(
            host=em.get("host", "smtp.gmail.com"),
            port=em.get("port", 587),
            user=em["user"], password=em["password"],
            to=em["to"], cc=em.get("cc", []),
        ))
    if not sinks:
        log.info("nessun canale configurato -> uso ConsoleSink")
        return ConsoleSink()
    if len(sinks) == 1:
        return sinks[0]
    return MultiSink(sinks)

def main():
    cfg = load_config()
    enabled = cfg.get("sources", list(ALL_SOURCES.keys()))
    flt = cfg.get("filters", {})
    db_path = Path(__file__).parent.parent / "data.sqlite"
    store = Store(db_path)
    sink = build_sink(cfg)
    collected: list[Listing] = []
    for name in enabled:
        cls = ALL_SOURCES.get(name)
        if not cls:
            log.warning("fonte sconosciuta: %s", name); continue
        try:
            collected.extend(cls().fetch())
        except Exception as e:
            log.error("[%s] errore durante fetch: %s", name, e)
    collected = [l for l in collected if passes_filters(l, flt)]
    log.info("totale lotti dopo filtri: %d", len(collected))
    new = store.process(collected)
    log.info("novita' da notificare: %d", len(new))
    if new:
        sink.send(new)
        store.mark_notified([l.uid for l in new])
    log.info("fatto.")

if __name__ == "__main__":
    main()
