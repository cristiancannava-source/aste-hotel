"""Adapter Fallcoaste.it - sito classico, annunci come <article data-*>.
Categoria base 'tutti gli immobili' + filtro parole chiave ricettive lato codice
(la categoria alberghi precisa non e' filtrabile via URL su questo sito)."""
from __future__ import annotations
import re, logging
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base import Source
from ..core.models import Listing
log = logging.getLogger(__name__)

_FILTER = "macro|527^ubicazione_dst|50^stato|1"
BASE = "https://www.fallcoaste.it/ricerca.html"

_KW = ["albergo","alberghi","alberghiero","alberghiera","hotel","pensione",
       "pensioni","ricettiv","residence","resort","ostello","agriturismo",
       "b&b","bed and breakfast","motel","locanda","villaggio turistico"]
_PAT = re.compile("(" + "|".join(re.escape(k) for k in _KW) + ")", re.I)

class FallcoasteSource(Source):
    name = "fallcoaste"
    delay = 2.0

    def fetch(self) -> list[Listing]:
        listings, page = [], 1
        while True:
            url = f"{BASE}?filter={quote(_FILTER)}&page={page}"
            resp = self.get(url)
            if not resp:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            arts = soup.select("article[data-auction-id]")
            if not arts:
                break
            for art in arts:
                lst = self._parse(art)
                if lst:
                    listings.append(lst)
            page += 1
            if page > 30:
                break
        log.info("[fallcoaste] raccolti %d lotti ricettivi", len(listings))
        return listings

    def _parse(self, art) -> Listing | None:
        aid = art.get("data-auction-id")
        if not aid:
            return None
        photo = art.select_one("a.single-photo")
        titolo = (photo.get("title") if photo else "") or ""
        # FILTRO: tieni solo se il titolo contiene una parola chiave ricettiva
        if not _PAT.search(titolo):
            return None
        url = art.get("data-auction-url") or ""
        pb = art.select_one("span.price-block")
        prezzo_raw = (pb.get("title") if pb else "") or ""
        m = re.search(r"([\d.]+,\d{2})", prezzo_raw)
        price = _to_float(m.group(1)) if m else None
        ente = art.select_one(".ribbon a.colored-link")
        ente = ente.get_text(strip=True) if ente else ""
        termine = art.get("data-auction-data-termine") or ""
        citta = ""
        mc = re.match(r"([A-ZÀ-Ù'\.\s]+)\(", titolo)
        if mc:
            citta = mc.group(1).strip().title()
        return Listing(
            source=self.name, source_id=str(aid), url=url,
            title=titolo or f"Lotto {aid}", price=price, city=citta,
            tribunale=ente, sale_date=_to_iso(termine), description=titolo)

def _to_float(s):
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def _to_iso(s):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{2}:\d{2})", s or "")
    if not m:
        return s or ""
    d, mo, y, hm = m.groups()
    return f"{y}-{mo}-{d}T{hm}"
