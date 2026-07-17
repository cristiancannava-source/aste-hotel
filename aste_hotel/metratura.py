"""Estrae la superficie in mq dal testo di un annuncio.
Le fonti non espongono la metratura come dato strutturato: va cercata nella
descrizione. Se non la trova ritorna None (metratura non nota)."""
import re

_PATTERNS = [
    r"(?:superficie|sup\.?|estensione)[^\d]{0,20}(\d{2,5}(?:[.,]\d+)?)\s*(?:mq|m2|m²|metri)",
    r"\bmq\.?\s*(\d{2,5}(?:[.,]\d+)?)",
    r"(\d{2,5}(?:[.,]\d+)?)\s*(?:mq|m2|m²)\b",
    r"(\d{2,5}(?:[.,]\d+)?)\s*metri\s*quadr",
]

def estrai_mq(testo):
    if not testo:
        return None
    t = testo.lower()
    trovate = []
    for p in _PATTERNS:
        for m in re.finditer(p, t):
            val = m.group(1).replace(".", "").replace(",", ".")
            try:
                v = float(val)
                if 10 <= v <= 20000:
                    trovate.append(v)
            except ValueError:
                pass
    return max(trovate) if trovate else None
