"""Adapter Astegiudiziarie.it - SPA Vue, API JSON a due fasi (map -> Data)."""
from __future__ import annotations
import time, logging
from .base import Source
from ..core.models import Listing
log = logging.getLogger(__name__)

API = "https://webapi.astegiudiziarie.it/api/search"
SITE = "https://www.astegiudiziarie.it"
SEARCH_BODY = {
    "tipoRicerca": 1, "indirizzo": None, "latitudine": None, "longitudine": None,
    "latitudineNW": None, "longitudineNW": None, "latitudineSE": None,
    "longitudineSE": None, "noGeo": False, "idEsperimentoVendita": None,
    "idTipologie": [], "tipologia": None, "idCategorie": [43, 35],
    "categoria": None, "descrizione": None, "comune": None, "provincia": None,
    "regione": None, "cap": None, "ricercaCap": None, "prezzoDa": None,
    "prezzoA": None, "priceMax": 0, "priceSteps": None, "tipologie": None,
    "idTribunale": None, "tribunale": None, "numeroProcedura": None,
    "annoProcedura": None, "ruolo": None, "idTipologiaProcedura": None,
    "giudice": None, "professionista": None, "idTipologiaVendita": None,
    "idModalitaVendita": None, "idPubblicazione": None, "dataVenditaDa": None,
    "dataVenditaA": None, "codiceAsta": None, "hasFoto": None,
    "hasPlanimetrie": None, "hasVirtualTour": None, "hasVideo": None,
    "bandita": None, "telematica": None, "inScadenza": None, "lottoUnico": None,
    "venditeAGI": None, "storica": False, "vetrina": False, "sezione": None,
    "searchOnMap": False, "tribunali": None, "tipologieProcedura": None,
    "tipologieVendita": None, "modalitaVendita": None, "numeroPubblicazioni": None,
    "listaIdLotto": None, "idProcedura": None, "orderBy": 6,
}
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": SITE, "Referer": SITE + "/", "X-Referer": SITE + "/",
}

class AstegiudiziarieSource(Source):
    name = "astegiudiziarie"
    delay = 2.0

    def fetch(self) -> list[Listing]:
        r = self._post(f"{API}/map", SEARCH_BODY)
        if not r:
            return []
        try:
            punti = r.json()
        except ValueError:
            log.error("[astegiudiziarie] map: risposta non JSON"); return []
        ids = [p["idLotto"] for p in punti if isinstance(p, dict) and p.get("idLotto")]
        log.info("[astegiudiziarie] %d lotti alberghi trovati", len(ids))
        if not ids:
            return []
        listings = []
        for i in range(0, len(ids), 50):
            rd = self._post(f"{API}/Data", ids[i:i+50])
            if not rd:
                continue
            try:
                items = rd.json()
            except ValueError:
                continue
            for it in items:
                lst = self._parse(it)
                if lst:
                    listings.append(lst)
        log.info("[astegiudiziarie] raccolti %d lotti", len(listings))
        return listings

    def _post(self, url, payload):
        elapsed = time.time() - self._last_req
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        try:
            r = self.session.post(url, json=payload, timeout=20, headers=HEADERS)
            self._last_req = time.time()
            r.raise_for_status()
            return r
        except Exception as e:
            log.warning("[astegiudiziarie] POST %s fallita: %s", url, e); return None

    def _parse(self, it):
        lid = it.get("idLotto")
        if not lid:
            return None
        url = it.get("urlSchedaDettagliata") or ""
        if url.startswith("/"):
            url = SITE + url
        proc, anno = it.get("numeroProcedura"), it.get("annoProcedura")
        procedura = f"{proc}/{anno}" if proc and anno else (str(proc) if proc else "")
        data = it.get("dataUdienza") or it.get("dataVendita") or it.get("dataFinePubblicazione") or ""
        return Listing(
            source=self.name, source_id=str(lid), url=url,
            title=(it.get("descrizione") or "")[:200] or f"Lotto {lid}",
            price=_to_float(it.get("prezzoBase")),
            city=it.get("comune") or "", province=it.get("provincia") or "",
            tribunale=it.get("tribunale") or "", procedura=procedura,
            sale_date=str(data), description=it.get("categoria") or "")

def _to_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
