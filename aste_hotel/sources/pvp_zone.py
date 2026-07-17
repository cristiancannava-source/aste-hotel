"""Adapter PVP per ricerche mirate: usa il filtro per RAGGIO dell'API.
Molto piu' efficiente che scaricare tutti i residenziali d'Italia:
l'API restituisce solo i lotti entro N km dal punto indicato.
Il poligono (in zone.py) affina poi il confine con precisione."""
import time, logging, requests

log = logging.getLogger(__name__)
API_URL = "https://pvp.giustizia.it/ric-496b258c-986a1b71/ric-ms/ricerca/vendite"

CAT_RESIDENZIALI = [
    "VILLA", "VILLINO", "ABITAZIONE_TIPO_CIV", "ABITAZIONE_TIPO_ECO",
    "ABITAZIONE_TIPO_POP", "ABITAZIONE_TIPO_SIGNORILE", "ABITAZIONE_IN_VILLE",
    "ABITAZIONE_TIPO_RUR", "ABITAZIONE_TIPO_ULTRAPOP", "APPARTAMENTO",
]
HEADERS = {"Origin": "https://pvp.giustizia.it", "Accept": "application/json"}

def cerca_intorno(coord, raggio_km, page_size=50, max_pagine=20):
    """coord: 'lat,lon' come stringa. raggio_km: stringa o numero."""
    out = []
    page, total_pages = 0, 1
    body = {"tipoLotto": "IMMOBILI", "categoriaBene": CAT_RESIDENZIALI,
            "flagRicerca": 0, "coordIndirizzo": str(coord),
            "raggioIndirizzo": str(raggio_km)}
    sess = requests.Session()
    while page < total_pages and page < max_pagine:
        params = {"language": "it", "page": page, "size": page_size,
                  "sort": "dataOraVendita,asc"}
        try:
            r = sess.post(API_URL, params=params, json=body, timeout=25, headers=HEADERS)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning("[pvp_zone] pagina %d fallita: %s", page, e)
            break
        b = data.get("body") or {}
        content = b.get("content") or []
        if page == 0:
            total_pages = b.get("totalPages", 1) or 1
            log.info("[pvp_zone] raggio %s km da %s: %s lotti",
                     raggio_km, coord, b.get("totalElements", "?"))
        out.extend(content)
        page += 1
        if page < total_pages:
            time.sleep(2)
    return out
