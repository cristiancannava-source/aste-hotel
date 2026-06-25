"""Modello dati normalizzato. Ogni adapter di sito DEVE restituire una lista di Listing.

Il campo `uid` e' la chiave di deduplica STABILE: deve restare identico tra una
scansione e l'altra per lo stesso lotto, altrimenti riceverai notifiche doppie.
La chiave di dedup CROSS-FONTE (`dedup_key`) e' invece calcolata sui dati fisici
del lotto (tribunale + procedura + comune), cosi' lo stesso hotel ripubblicato da
PVP e da un portale privato viene riconosciuto come un unico bene.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Optional


def _norm(s: Optional[str]) -> str:
    """Normalizza una stringa per confronti robusti: minuscolo, senza accenti,
    senza punteggiatura, spazi compressi."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class Listing:
    # --- identificazione ---
    source: str                      # nome dell'adapter, es. "pvp"
    source_id: str                   # id del lotto COSI' COM'E' sul sito di origine
    url: str

    # --- contenuto ---
    title: str = ""
    price: Optional[float] = None    # base d'asta in euro
    city: str = ""
    province: str = ""
    region: str = ""
    tribunale: str = ""
    procedura: str = ""              # es. "E.I. 123/2024" o "Fall. 45/2023"
    sale_date: str = ""              # data udienza/vendita, stringa ISO se possibile
    pub_date: str = ""               # data pubblicazione
    description: str = ""

    # --- calcolati ---
    uid: str = field(default="", init=False)
    dedup_key: str = field(default="", init=False)

    def __post_init__(self):
        # uid: stabile per (fonte, id-sul-sito). Identifica univocamente l'annuncio.
        self.uid = f"{self.source}:{self.source_id}"

        # dedup_key: identifica il BENE FISICO a prescindere dalla fonte.
        # Se tribunale+procedura ci sono, sono il segnale piu' affidabile.
        # Altrimenti ripieghiamo su comune+un troncone di titolo.
        trib = _norm(self.tribunale)
        proc = _norm(self.procedura)
        if trib and proc:
            basis = f"{trib}|{proc}"
        else:
            basis = f"{_norm(self.city)}|{_norm(self.title)[:60]}"
        self.dedup_key = hashlib.sha1(basis.encode()).hexdigest()[:16]

    def to_row(self) -> dict:
        d = asdict(self)
        d["uid"] = self.uid
        d["dedup_key"] = self.dedup_key
        return d
