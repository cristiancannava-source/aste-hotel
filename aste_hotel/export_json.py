"""Esporta il contenuto di un database in un file JSON per la dashboard."""
import json, sqlite3
from pathlib import Path

def esporta(db_path, json_path):
    db = Path(db_path)
    if not db.exists():
        Path(json_path).write_text("[]", encoding="utf-8")
        return 0
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT source, title, price, city, province, tribunale, "
        "sale_date, url FROM listings ORDER BY first_seen DESC"
    ).fetchall()
    conn.close()
    dati = [dict(r) for r in rows]
    Path(json_path).write_text(json.dumps(dati, ensure_ascii=False), encoding="utf-8")
    return len(dati)
