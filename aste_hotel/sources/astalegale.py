"""Adapter Astalegale.net - app Nuxt. Lista filtrata alberghi + prezzo dal dettaglio."""
from __future__ import annotations
import re, logging
from .base import Source
from ..core.models import Listing
log = logging.getLogger(__name__)

SITE = "https://www.astalegale.net"
SUBCATS = ["alberghi-e-pensioni", "albergo-e-pensione"]
_LINK_RE = re.compile(r"/Aste/Detail/(B\d+)-([A-Za-z0-9\-]+)")
_PRICE_RE = re.compile(r'(\d+),"€\s*([\d.]+,\d{2})"')

class AstalegaleSource(Source):
    name = "astalegale"
    delay = 1.5

    def fetch(self) -> list[Listing]:
        listings, visti = [], set()
        for sub in SUBCATS:
            page = 1
            while page <= 15:
                url = f"{SITE}/Immobili?categories=altro%2C{sub}&page={page}"
                resp = self.get(url)
                if not resp:
                    break
                links = list(dict.fromkeys(re.findall(r"/Aste/Detail/B\d+-[A-Za-z0-9\-]+", resp.text)))
                links = [l for l in links if sub in l.lower()]
                nuovi = [l for l in links if l not in visti]
                if not nuovi:
                    break
                for href in nuovi:
                    visti.add(href)
                    lst = self._build(href)
                    if lst:
                        listings.append(lst)
                page += 1
        log.info("[astalegale] raccolti %d lotti", len(listings))
        return listings

    def _build(self, href):
        m = _LINK_RE.search(href)
        if not m:
            return None
        bid, slug = m.group(1), m.group(2)
        url = SITE + href
        parti = slug.split("-")
        citta = parti[-1] if parti else ""
        price, sale_date = None, ""
        det = self.get(url)
        if det:
            pm = _PRICE_RE.search(det.text)
            if pm:
                price = _to_float(pm.group(2))
            dm = re.search(r'(\d{2}/\d{2}/\d{4})', det.text)
            if dm:
                d, mo, y = dm.group(1).split("/")
                sale_date = f"{y}-{mo}-{d}"
        return Listing(
            source=self.name, source_id=bid, url=url,
            title=slug.replace("-", " "), price=price, city=citta,
            sale_date=sale_date, description="Alberghi e pensioni")

def _to_float(s):
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None
