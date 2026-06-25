"""Adapter PVP via API JSON (single-page Angular: niente scraping)."""
from __future__ import annotations
import logging, time
from .base import Source
from ..core.models import Listing
log = logging.getLogger(__name__)

API_URL = "https://pvp.giustizia.it/ric-496b258c-986a1b71/ric-ms/ricerca/vendite"
# Due codici storici per gli alberghi: cercarli entrambi per non perdere annunci.
SEARCH_BODY = {
    "tipoLotto": "IMMOBILI",
    "categoriaBene": ["ALBERGO_E_PENSIONE", "ALBERGHI_E_PENSIONI"],
    "flagRicerca": 0, "coordIndirizzo": "", "raggioIndirizzo": "",
}
PAGE_SIZE = 50

class PvpSource(Source):
    name = "pvp"
    delay = 3.0

    def fetch(self) -> list[Listing]:
        listings, page, total_pages = [], 0, 1
        while page < total_pages:
            params = {"language": "it", "page": page, "size": PAGE_SIZE, "sort": "dataOraVendita,asc"}
            resp = self._post(API_URL, params, SEARCH_BODY)
            if not resp:
                break
            try:
                data = resp.json()
            except ValueError:
                log.error("[pvp] risposta non JSON (pagina %d)", page); break
            body = data.get("body") or {}
            content = body.get("content") or []
            if page == 0:
                total_pages = body.get("totalPages", 1) or 1
                log.info("[pvp] %s lotti totali, %d pagine", body.get("totalElements", "?"), total_pages)
            for item in content:
                lst = self._parse_item(item)
                if lst:
                    listings.append(lst)
            page += 1
            if page > 50:
                break
        log.info("[pvp] raccolti %d lotti", len(listings))
        return listings

    def _post(self, url, params, json):
        elapsed = time.time() - self._last_req
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        try:
            r = self.session.post(url, params=params, json=json, timeout=20,
                headers={"Origin": "https://pvp.giustizia.it", "Accept": "application/json"})
            self._last_req = time.time()
            r.raise_for_status()
            return r
        except Exception as e:
            log.warning("[pvp] POST fallita %s: %s", url, e); return None

    def _parse_item(self, item: dict) -> Listing | None:
        lot_id = item.get("id")
        if lot_id is None:
            return None
        indirizzo = item.get("indirizzo") or {}
        cat = item.get("categoriaBene")
        if isinstance(cat, list):
            cat = ", ".join(cat)
        url = f"https://pvp.giustizia.it/pvp/it/detail_annuncio.page?idAnnuncio={lot_id}"
        return Listing(
            source=self.name, source_id=str(lot_id), url=url,
            title=item.get("descLotto") or cat or f"Lotto {lot_id}",
            price=_to_float(item.get("prezzoBaseAsta")),
            city=indirizzo.get("citta") or "", province=indirizzo.get("provincia") or "",
            tribunale=item.get("tribunale") or "",
            procedura=str(item.get("procedura") or ""),
            sale_date=str(item.get("dataOraVendita") or ""),
            pub_date=str(item.get("dataPubblicazione") or ""),
            description=" ".join(x for x in [indirizzo.get("via") or "", cat or ""] if x))

def _to_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
