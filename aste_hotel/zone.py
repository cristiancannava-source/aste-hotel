"""Filtri geografici a poligono per le ricerche mirate."""
from __future__ import annotations
import re, unicodedata

def _norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()

def punto_in_poligono(lat, lon, poly) -> bool:
    if lat is None or lon is None:
        return False
    dentro = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        yi, xi = poly[i]
        yj, xj = poly[j]
        if ((xi > lon) != (xj > lon)) and (lat < (yj - yi) * (lon - xi) / (xj - xi) + yi):
            dentro = not dentro
        j = i
    return dentro

class Zona:
    def __init__(self, nome, comuni, poligono, parole_chiave, centro=None, raggio_km=5, parole_escluse=()):
        self.nome = nome
        self.centro = centro
        self.raggio_km = raggio_km
        self.comuni = [_norm(c) for c in comuni]
        self.poligono = poligono
        self.parole_chiave = [_norm(k) for k in parole_chiave]
        self.parole_escluse = [_norm(k) for k in parole_escluse]

    def comune_pertinente(self, citta) -> bool:
        c = _norm(citta)
        return any(com in c or c in com for com in self.comuni if com)

    def contiene(self, lat, lon, testo):
        if lat is not None and lon is not None:
            return (punto_in_poligono(lat, lon, self.poligono), "gps")
        t = _norm(testo)
        if any(x in t for x in self.parole_escluse):
            return (False, "testo")
        if any(k in t for k in self.parole_chiave):
            return (True, "testo")
        return (False, "testo")

PARIOLI = Zona(
    nome="Parioli (Roma)", comuni=["Roma"], centro="41.9250,12.4820", raggio_km=2,
    poligono=[(41.9345, 12.4665), (41.9350, 12.4830), (41.9310, 12.4930),
              (41.9255, 12.4975), (41.9195, 12.4950), (41.9155, 12.4870),
              (41.9145, 12.4760), (41.9200, 12.4680), (41.9270, 12.4650)],
    parole_chiave=["parioli", "viale parioli", "piazza euclide", "viale bruno buozzi",
        "via ruggero fauro", "viale romania", "viale liegi", "via lima", "villa glori",
        "via archimede", "piazza ungheria", "via panama", "viale maresciallo pilsudski",
        "via antonelli", "via mangili", "via bertoloni", "via denza", "via paisiello",
        "via sacchetti", "villa balestra", "via ammannati", "via nemea"],
)

PORTO_CERVO = Zona(
    nome="Porto Cervo (Arzachena)", comuni=["Arzachena"], centro="41.1300,9.5350", raggio_km=5,
    poligono=[(41.1550, 9.5150), (41.1560, 9.5480), (41.1400, 9.5560),
              (41.1250, 9.5580), (41.1100, 9.5500), (41.1020, 9.5320),
              (41.1050, 9.5150), (41.1250, 9.5080), (41.1400, 9.5050)],
    parole_chiave=["porto cervo", "portocervo", "cala di volpe", "capriccioli",
        "pevero", "golfo pevero", "pantogia", "liscia di vacca", "capo ferro",
        "romazzino", "piccolo pevero", "abbiadori", "cala granu", "poltu quatu",
        "li nibani"],
)

ZONE = {"parioli": PARIOLI, "porto_cervo": PORTO_CERVO}
