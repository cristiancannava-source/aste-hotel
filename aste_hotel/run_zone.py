"""Monitor ricerche mirate: residenziali in zone precise di Roma + Porto Cervo.
Ottimizzato: una sola ricerca API ampia per Roma, poi smistamento per poligono.
Notifiche etichettate per zona."""
from __future__ import annotations
import logging, tomllib
from datetime import date
from pathlib import Path
from .core.store import Store
from .core.models import Listing
from .sinks.notify import TelegramSink, ConsoleSink, EmailSink, MultiSink
from .zone import ZONE, ZONE_ROMA, CENTRO_ROMA, RAGGIO_ROMA
from .metratura import estrai_mq
from .sources import pvp_zone

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aste_zone")

DB = Path(__file__).parent.parent / "data_zone.sqlite"
CFG = Path(__file__).parent.parent / "config" / "settings_zone.toml"

# emoji per le notifiche: Roma -> 🏛, mare -> 🌊
def _emoji(chiave):
    return "🌊" if chiave == "porto_cervo" else "🏛"

def load_config():
    if not CFG.exists():
        log.warning("config zone mancante, uso ConsoleSink")
        return {}
    with open(CFG, "rb") as f:
        return tomllib.load(f)

def build_sink(cfg, etichetta, emoji):
    sinks = []
    tg = cfg.get("telegram", {})
    if tg.get("token") and tg.get("chat_id"):
        sinks.append(TelegramSink(tg["token"], tg["chat_id"], etichetta, emoji))
    em = cfg.get("email", {})
    if em.get("user") and em.get("password") and em.get("to"):
        sinks.append(EmailSink(host=em.get("host", "smtp.gmail.com"),
            port=em.get("port", 587), user=em["user"], password=em["password"],
            to=em["to"], cc=em.get("cc", []), etichetta=etichetta, emoji=emoji))
    if not sinks:
        return ConsoleSink()
    return sinks[0] if len(sinks) == 1 else MultiSink(sinks)

def _f(v):
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None

def to_listing(item, zona_chiave, mq, metodo):
    lid = item.get("id")
    ind = item.get("indirizzo") or {}
    cat = item.get("categoriaBene")
    if isinstance(cat, list):
        cat = ", ".join(cat)
    mq_txt = f"{mq:.0f} mq" if mq else "mq non indicati"
    return Listing(
        source=f"pvp_{zona_chiave}", source_id=str(lid),
        url=f"https://pvp.giustizia.it/pvp/it/detail_annuncio.page?idAnnuncio={lid}",
        title=(item.get("descLotto") or cat or f"Lotto {lid}")[:200],
        price=_f(item.get("prezzoBaseAsta")),
        city=ind.get("citta") or "", province=ind.get("provincia") or "",
        tribunale=item.get("tribunale") or "",
        procedura=str(item.get("procedura") or ""),
        sale_date=str(item.get("dataOraVendita") or ""),
        pub_date=str(item.get("dataPubblicazione") or ""),
        description=f"{ind.get('via','')} · {cat} · {mq_txt} · [{metodo}]")

def processa_gruppo(cfg, store, chiave_zone, grezzi):
    """Smista i lotti grezzi nelle zone indicate e notifica per zona."""
    oggi = date.today().isoformat()
    per_zona = {k: [] for k in chiave_zone}
    for item in grezzi:
        ind = item.get("indirizzo") or {}
        citta = ind.get("citta") or ""
        coord = ind.get("coordinate") or {}
        lat, lon = coord.get("latitudine"), coord.get("longitudine")
        testo = f"{ind.get('via','')} {citta} {item.get('descLotto','')}"
        sd = str(item.get("dataOraVendita") or "")[:10]
        if sd and sd < oggi:
            continue
        for chiave in chiave_zone:
            zona = ZONE[chiave]
            if not zona.comune_pertinente(citta):
                continue
            dentro, metodo = zona.contiene(lat, lon, testo)
            if not dentro:
                continue
            mq = estrai_mq(item.get("descLotto") or "")
            per_zona[chiave].append(to_listing(item, chiave, mq, metodo))
            break  # un lotto in una sola zona
    for chiave, trovati in per_zona.items():
        zona = ZONE[chiave]
        log.info("%s: %d lotti attivi in zona", zona.nome, len(trovati))
        nuovi = store.process(trovati)
        if nuovi:
            log.info("  -> %d novita' da notificare", len(nuovi))
            etich = f"nuovi immobili — {zona.nome}"
            sink = build_sink(cfg, etich, _emoji(chiave))
            sink.send(nuovi)
            store.mark_notified([l.uid for l in nuovi])

def main():
    cfg = load_config()
    store = Store(DB)

    # Gruppo 1: tutte le zone di Roma con una sola ricerca ampia
    log.info("=== Ricerca ampia su Roma (raggio %s km) ===", RAGGIO_ROMA)
    grezzi_roma = pvp_zone.cerca_intorno(CENTRO_ROMA, RAGGIO_ROMA, max_pagine=60)
    log.info("Scaricati %d lotti residenziali nell'area di Roma", len(grezzi_roma))
    processa_gruppo(cfg, store, ZONE_ROMA, grezzi_roma)

    # Gruppo 2: Porto Cervo (ricerca separata)
    pc = ZONE["porto_cervo"]
    log.info("=== Ricerca Porto Cervo ===")
    grezzi_pc = pvp_zone.cerca_intorno(pc.centro, pc.raggio_km)
    log.info("Scaricati %d lotti nell'area di Porto Cervo", len(grezzi_pc))
    processa_gruppo(cfg, store, ["porto_cervo"], grezzi_pc)

    log.info("fatto.")

if __name__ == "__main__":
    main()
