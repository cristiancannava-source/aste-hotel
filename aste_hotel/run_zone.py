"""Monitor ricerche mirate: residenziali in zone precise (Parioli, Porto Cervo).
Notifiche etichettate per zona, cosi' si capisce subito di cosa si tratta."""
from __future__ import annotations
import logging, tomllib
from datetime import date
from pathlib import Path
from .core.store import Store
from .core.models import Listing
from .sinks.notify import TelegramSink, ConsoleSink, EmailSink, MultiSink
from .zone import ZONE
from .metratura import estrai_mq
from .sources import pvp_zone

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aste_zone")

DB = Path(__file__).parent.parent / "data_zone.sqlite"
CFG = Path(__file__).parent.parent / "config" / "settings_zone.toml"

# etichette per le notifiche, una per zona
ETICHETTE = {
    "parioli": ("nuovi immobili — Parioli (Roma)", "🏛"),
    "porto_cervo": ("nuovi immobili — Porto Cervo", "🌊"),
}

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

def to_listing(item, zona_nome, mq, metodo):
    lid = item.get("id")
    ind = item.get("indirizzo") or {}
    cat = item.get("categoriaBene")
    if isinstance(cat, list):
        cat = ", ".join(cat)
    mq_txt = f"{mq:.0f} mq" if mq else "mq non indicati"
    return Listing(
        source=f"pvp_{zona_nome}", source_id=str(lid),
        url=f"https://pvp.giustizia.it/pvp/it/detail_annuncio.page?idAnnuncio={lid}",
        title=(item.get("descLotto") or cat or f"Lotto {lid}")[:200],
        price=_f(item.get("prezzoBaseAsta")),
        city=ind.get("citta") or "", province=ind.get("provincia") or "",
        tribunale=item.get("tribunale") or "",
        procedura=str(item.get("procedura") or ""),
        sale_date=str(item.get("dataOraVendita") or ""),
        pub_date=str(item.get("dataPubblicazione") or ""),
        description=f"{ind.get('via','')} · {cat} · {mq_txt} · [{metodo}]")

def main():
    cfg = load_config()
    store = Store(DB)
    oggi = date.today().isoformat()

    for chiave, zona in ZONE.items():
        log.info("=== Zona: %s ===", zona.nome)
        grezzi = pvp_zone.cerca_intorno(zona.centro, zona.raggio_km)
        log.info("Scaricati %d lotti nel raggio", len(grezzi))
        trovati = []
        for item in grezzi:
            ind = item.get("indirizzo") or {}
            citta = ind.get("citta") or ""
            coord = ind.get("coordinate") or {}
            lat, lon = coord.get("latitudine"), coord.get("longitudine")
            testo = f"{ind.get('via','')} {citta} {item.get('descLotto','')}"
            if not zona.comune_pertinente(citta):
                continue
            dentro, metodo = zona.contiene(lat, lon, testo)
            if not dentro:
                continue
            mq = estrai_mq(item.get("descLotto") or "")
            if chiave == "parioli":
                min_mq = cfg.get("filtri", {}).get("parioli_min_mq", 150)
                if mq is not None and mq < min_mq:
                    continue
            sd = str(item.get("dataOraVendita") or "")[:10]
            if sd and sd < oggi:
                continue
            trovati.append(to_listing(item, chiave, mq, metodo))
        log.info("Dentro i confini e con asta aperta: %d", len(trovati))
        for l in trovati:
            log.info("   %s | base %s | %s", l.city, l.price, l.title[:55])

        nuovi = store.process(trovati)
        log.info("Novita' da notificare per %s: %d", zona.nome, len(nuovi))
        if nuovi:
            etich, emoji = ETICHETTE.get(chiave, ("nuovi immobili", "🏠"))
            sink = build_sink(cfg, etich, emoji)
            sink.send(nuovi)
            store.mark_notified([l.uid for l in nuovi])
    log.info("fatto.")

if __name__ == "__main__":
    main()
