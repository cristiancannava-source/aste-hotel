"""Classe base per ogni adapter di sito.

Regole di buona condotta verso i siti (incorporate qui, non opzionali):
  - User-Agent onesto e identificabile
  - ritardo tra le richieste (gentle crawling)
  - timeout e niente retry aggressivi

Ogni sito concreto eredita da Source e implementa fetch() -> list[Listing].
"""

from __future__ import annotations

import time
import logging
from typing import Optional

import requests

from ..core.models import Listing

log = logging.getLogger(__name__)

# Identificati onestamente. Metti un contatto reale: e' cortesia e ti evita ban.
USER_AGENT = "AsteHotelMonitor/1.0 (+monitoraggio personale; contatto: tua@email.it)"


class Source:
    name: str = "base"
    # secondi di pausa tra una richiesta HTTP e la successiva verso lo stesso sito
    delay: float = 2.0

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._last_req = 0.0

    def get(self, url: str, **kw) -> Optional[requests.Response]:
        # rispetta il delay tra richieste
        elapsed = time.time() - self._last_req
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        try:
            r = self.session.get(url, timeout=20, **kw)
            self._last_req = time.time()
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            log.warning("[%s] richiesta fallita %s: %s", self.name, url, e)
            return None

    def fetch(self) -> list[Listing]:
        """Da implementare in ogni adapter concreto."""
        raise NotImplementedError
