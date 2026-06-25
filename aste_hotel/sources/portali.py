"""Adapter per i portali privati con una categoria 'alberghi' gia' filtrabile via URL.

Tutti questi siti hanno una pagina-listino dedicata alle strutture ricettive
raggiungibile direttamente. Strutturalmente si comportano allo stesso modo
(lista di card -> dettaglio), quindi condividono una base comune: cambia solo
la CATEGORY_URL e i SELETTORI. Riempi i selettori guardando il DOM reale di
ciascun sito (DevTools -> Ispeziona su una card di risultato).

URL di categoria gia' individuati (giugno 2026) — verifica che siano ancora validi:
  astegiudiziarie : https://www.astegiudiziarie.it/Immobili/altra-categoria/alberghi-e-pensioni
  astalegale      : https://www.astalegale.net/Immobili?categories=altro%2Calberghi-e-pensioni
  fallcoaste      : https://www.fallcoaste.it/categoria/alberghi-e-pensioni-567.html
  fallimenti      : https://www.fallimenti.it/aste-complesso-alberghiero
  fallimentieaste : https://fallimentieaste.it/c/immobili/albergo-struttura-ricettiva-immobili/

NOTA LEGALE/OPERATIVA: prima di attivare lo scraping su ciascun sito, controlla
robots.txt e i Termini d'uso. Dove il sito offre un 'salva ricerca con avviso
email', valuta se usarlo invece dello scraping: e' piu' rispettoso e piu' stabile.
"""

from __future__ import annotations

import re
import logging

from bs4 import BeautifulSoup

from .base import Source
from ..core.models import Listing

log = logging.getLogger(__name__)


class _HtmlListSource(Source):
    """Base per portali a lista. Le sottoclassi impostano name, base_url,
    category_url e i selettori."""

    base_url: str = ""
    category_url: str = ""

    # --- SELETTORI DA TARARE SUL DOM REALE DI OGNI SITO ---
    sel_card = ""          # contenitore di un singolo risultato
    sel_link = "a[href]"   # link al dettaglio dentro la card
    sel_title = ""
    sel_price = ""
    sel_city = ""
    sel_tribunale = ""
    sel_procedura = ""
    sel_date = ""
    id_url_regex = r"/(\d{4,})"   # come estrarre un id stabile dall'URL dettaglio

    def fetch(self) -> list[Listing]:
        out: list[Listing] = []
        resp = self.get(self.category_url)
        if not resp:
            return out
        soup = BeautifulSoup(resp.text, "html.parser")

        if not self.sel_card:
            log.warning("[%s] selettori non ancora configurati - skip", self.name)
            return out

        for card in soup.select(self.sel_card):
            lst = self._parse(card)
            if lst:
                out.append(lst)
        log.info("[%s] raccolti %d lotti", self.name, len(out))
        return out

    def _parse(self, card) -> Listing | None:
        def txt(sel):
            if not sel:
                return ""
            el = card.select_one(sel)
            return el.get_text(strip=True) if el else ""

        link = card.select_one(self.sel_link)
        if not link or not link.get("href"):
            return None
        href = link["href"]
        if href.startswith("/"):
            href = self.base_url + href

        m = re.search(self.id_url_regex, href)
        source_id = m.group(1) if m else href

        return Listing(
            source=self.name,
            source_id=source_id,
            url=href,
            title=txt(self.sel_title) or "Lotto",
            price=_parse_price(txt(self.sel_price)),
            city=txt(self.sel_city),
            tribunale=txt(self.sel_tribunale),
            procedura=txt(self.sel_procedura),
            sale_date=txt(self.sel_date),
        )


# --------- un sottotipo per sito: basta riempire URL e selettori ---------

class AstegiudiziarieSource(_HtmlListSource):
    name = "astegiudiziarie"
    base_url = "https://www.astegiudiziarie.it"
    category_url = "https://www.astegiudiziarie.it/Immobili/altra-categoria/alberghi-e-pensioni"
    # sel_card = "..."  <-- da DevTools


class AstalegaleSource(_HtmlListSource):
    name = "astalegale"
    base_url = "https://www.astalegale.net"
    category_url = "https://www.astalegale.net/Immobili?categories=altro%2Calberghi-e-pensioni"
    # sel_card = "..."


class FallcoasteSource(_HtmlListSource):
    name = "fallcoaste"
    base_url = "https://www.fallcoaste.it"
    category_url = "https://www.fallcoaste.it/categoria/alberghi-e-pensioni-567.html"
    # sel_card = "..."


class FallimentiSource(_HtmlListSource):
    name = "fallimenti"
    base_url = "https://www.fallimenti.it"
    category_url = "https://www.fallimenti.it/aste-complesso-alberghiero"
    # sel_card = "..."


class FallimentieasteSource(_HtmlListSource):
    name = "fallimentieaste"
    base_url = "https://fallimentieaste.it"
    category_url = "https://fallimentieaste.it/c/immobili/albergo-struttura-ricettiva-immobili/"
    # sel_card = "..."


def _parse_price(s: str) -> float | None:
    if not s:
        return None
    s = re.sub(r"[^\d,]", "", s).replace(".", "").replace(",", ".")
    try:
        return float(s) if s else None
    except ValueError:
        return None
