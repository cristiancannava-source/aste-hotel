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
    def __init__(self, nome, comuni, poligono, parole_chiave, centro=None,
                 raggio_km=5, parole_escluse=()):
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


# ---- ZONE DI ROMA (centro comune, smistate per poligono) ----
# centro di Roma per la ricerca ampia via API (raggio abbondante che copre tutte le zone)
CENTRO_ROMA = "41.9150,12.4750"
RAGGIO_ROMA = 8

def _z(nome, poly, kw):
    return Zona(nome=nome, comuni=["Roma"], poligono=poly, parole_chiave=kw,
                centro=CENTRO_ROMA, raggio_km=RAGGIO_ROMA)

CENTRO_STORICO = _z("Centro Storico",
    [(41.9110,12.4720),(41.9080,12.4830),(41.9020,12.4950),(41.8950,12.4980),
     (41.8880,12.4920),(41.8890,12.4780),(41.8950,12.4680),(41.9030,12.4670)],
    ["centro storico","pantheon","piazza navona","campo de fiori","via del corso",
     "fontana di trevi","piazza di spagna","via dei coronari","largo argentina"])

PRATI = _z("Prati",
    [(41.9130,12.4560),(41.9160,12.4680),(41.9110,12.4740),(41.9060,12.4720),
     (41.9055,12.4600),(41.9085,12.4530)],
    ["prati","cola di rienzo","piazza cavour","via crescenzio","via ottaviano",
     "via boezio","piazza dei quiriti","via germanico","viale giulio cesare"])

BORGO = _z("Borgo",
    [(41.9060,12.4500),(41.9055,12.4690),(41.9010,12.4700),(41.8975,12.4610),
     (41.8990,12.4510),(41.9025,12.4465)],
    ["borgo","san pietro","castel sant angelo","via della conciliazione",
     "borgo pio","via di porta angelica","borgo vittorio"])

MAZZINI = _z("Mazzini",
    [(41.9180,12.4530),(41.9200,12.4620),(41.9150,12.4650),(41.9110,12.4580),
     (41.9130,12.4500)],
    ["piazza mazzini","viale mazzini","via oslavia","via monte zebio","via col di lana"])

DELLA_VITTORIA = _z("Della Vittoria",
    [(41.9230,12.4560),(41.9250,12.4650),(41.9200,12.4680),(41.9160,12.4620),
     (41.9180,12.4540)],
    ["della vittoria","piazza della vittoria","viale angelico","via caccini nord",
     "piazzale maresciallo giardino","via tacito nord"])

DEGLI_EROI = _z("Degli Eroi",
    [(41.9110,12.4440),(41.9130,12.4530),(41.9080,12.4560),(41.9040,12.4490),
     (41.9060,12.4420)],
    ["degli eroi","piazzale degli eroi","via candia","via baldo degli ubaldi bassa",
     "via anastasio","via santamaura"])

PARIOLI = _z("Parioli",
    [(41.9345,12.4665),(41.9350,12.4830),(41.9310,12.4930),(41.9255,12.4975),
     (41.9195,12.4950),(41.9155,12.4870),(41.9145,12.4760),(41.9200,12.4715),
     (41.9270,12.4690)],
    ["parioli","viale parioli","piazza euclide","viale bruno buozzi","via panama",
     "via archimede","piazza ungheria","via bertoloni","via g. paisiello"])

FLAMINIO = _z("Flaminio",
    [(41.9330,12.4640),(41.9300,12.4700),(41.9220,12.4695),(41.9160,12.4710),
     (41.9160,12.4630),(41.9250,12.4595)],
    ["flaminio","via flaminia","piazza del popolo","viale tiziano","auditorium",
     "via guido reni","ponte del risorgimento","villa glori"])

TRASTEVERE = _z("Trastevere",
    [(41.8920,12.4630),(41.8900,12.4720),(41.8830,12.4740),(41.8770,12.4680),
     (41.8820,12.4580),(41.8880,12.4570)],
    ["trastevere","santa maria in trastevere","viale trastevere","via della lungaretta",
     "piazza trilussa","via garibaldi","vicolo del cinque"])

CORSO_FRANCIA = _z("Corso Francia",
    [(41.9380,12.4650),(41.9400,12.4760),(41.9340,12.4790),(41.9300,12.4700),
     (41.9330,12.4620)],
    ["corso francia","via flaminia nuova bassa","piazza dei giochi delfici"])

VIGNA_CLARA = _z("Vigna Clara",
    [(41.9450,12.4600),(41.9480,12.4720),(41.9410,12.4750),(41.9370,12.4650),
     (41.9400,12.4560)],
    ["vigna clara","piazza dei giochi delfici alta","via ugo ojetti bassa",
     "largo maresciallo diaz","via cortina d ampezzo bassa"])

FLEMING = _z("Fleming",
    [(41.9520,12.4680),(41.9550,12.4800),(41.9480,12.4830),(41.9440,12.4730),
     (41.9470,12.4640)],
    ["fleming","via alexander fleming","via due ponti bassa","piazza walter rossi",
     "via riano","lungotevere flaminio"])

PONTE_MILVIO = _z("Ponte Milvio",
    [(41.9400,12.4740),(41.9420,12.4840),(41.9350,12.4870),(41.9310,12.4790),
     (41.9350,12.4720)],
    ["ponte milvio","piazzale ponte milvio","via capoprati","foro italico",
     "lungotevere maresciallo cadorna"])

TRIESTE = _z("Trieste",
    [(41.9280,12.5010),(41.9310,12.5150),(41.9240,12.5220),(41.9160,12.5180),
     (41.9150,12.5040),(41.9210,12.4990)],
    ["corso trieste","piazza istria","viale libia","viale eritrea","viale somalia",
     "piazza crati","quartiere africano","via nomentana media"])

SALARIO = _z("Salario",
    [(41.9180,12.4960),(41.9200,12.5050),(41.9140,12.5080),(41.9080,12.5020),
     (41.9100,12.4930),(41.9150,12.4920)],
    ["salario","piazza fiume","via salaria","corso d italia","villa albani",
     "via po","piazza buenos aires","via bergamo"])

BOLOGNA = _z("Bologna",
    [(41.9150,12.5140),(41.9180,12.5280),(41.9100,12.5330),(41.9030,12.5250),
     (41.9050,12.5130),(41.9110,12.5100)],
    ["piazza bologna","viale delle province","via tiburtina","la sapienza",
     "via lorenzo il magnifico","via catania","via ravenna","via michele di lando"])

# ---- PORTO CERVO (invariata) ----
PORTO_CERVO = Zona(
    nome="Porto Cervo", comuni=["Arzachena"], centro="41.1300,9.5350", raggio_km=5,
    poligono=[(41.1550,9.5150),(41.1560,9.5480),(41.1400,9.5560),(41.1250,9.5580),
              (41.1100,9.5500),(41.1020,9.5320),(41.1050,9.5150),(41.1250,9.5080),
              (41.1400,9.5050)],
    parole_chiave=["porto cervo","portocervo","cala di volpe","capriccioli","pevero",
        "golfo pevero","pantogia","liscia di vacca","capo ferro","romazzino",
        "piccolo pevero","abbiadori","cala granu","poltu quatu","li nibani"])

# chiavi interne (per il dedup e le etichette) -> Zona
ZONE = {
    "centro_storico": CENTRO_STORICO, "prati": PRATI, "borgo": BORGO,
    "mazzini": MAZZINI, "della_vittoria": DELLA_VITTORIA, "degli_eroi": DEGLI_EROI,
    "parioli": PARIOLI, "flaminio": FLAMINIO, "trastevere": TRASTEVERE,
    "corso_francia": CORSO_FRANCIA, "vigna_clara": VIGNA_CLARA, "fleming": FLEMING,
    "ponte_milvio": PONTE_MILVIO,
    "trieste": TRIESTE, "salario": SALARIO, "bologna": BOLOGNA,
    "porto_cervo": PORTO_CERVO,
}

# zone che condividono la stessa ricerca API (stesso centro Roma)
ZONE_ROMA = [k for k, z in ZONE.items() if z.centro == CENTRO_ROMA]
