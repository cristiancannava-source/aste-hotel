"""Storage SQLite. Tiene lo stato tra una scansione e l'altra.

Responsabilita':
  - decidere cosa e' NUOVO (mai visto prima, per uid)
  - deduplicare CROSS-FONTE (stesso bene fisico da fonti diverse -> notifica una volta)
  - conservare lo storico per una eventuale dashboard
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from .models import Listing


SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    uid          TEXT PRIMARY KEY,
    dedup_key    TEXT NOT NULL,
    source       TEXT NOT NULL,
    source_id    TEXT NOT NULL,
    url          TEXT,
    title        TEXT,
    price        REAL,
    city         TEXT,
    province     TEXT,
    region       TEXT,
    tribunale    TEXT,
    procedura    TEXT,
    sale_date    TEXT,
    pub_date     TEXT,
    description  TEXT,
    first_seen   TEXT DEFAULT (datetime('now')),
    last_seen    TEXT DEFAULT (datetime('now')),
    notified     INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_dedup ON listings(dedup_key);
CREATE INDEX IF NOT EXISTS idx_notified ON listings(notified);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def process(self, listings: Iterable[Listing]) -> list[Listing]:
        """Inserisce/aggiorna i listing e restituisce SOLO quelli da notificare:
        nuovi (uid mai visto) E il cui bene fisico (dedup_key) non e' gia' stato
        notificato da un'altra fonte. Aggiorna last_seen per quelli gia' noti."""
        to_notify: list[Listing] = []
        # dedup_key gia' accettati per la notifica IN QUESTO STESSO giro:
        # evita che lo stesso bene, arrivato da due fonti nella stessa scansione,
        # venga notificato due volte.
        accepted_keys: set[str] = set()
        with self._conn() as c:
            for lst in listings:
                row = c.execute(
                    "SELECT uid FROM listings WHERE uid = ?", (lst.uid,)
                ).fetchone()
                if row:
                    c.execute(
                        "UPDATE listings SET last_seen = datetime('now'), "
                        "price = ?, sale_date = ? WHERE uid = ?",
                        (lst.price, lst.sale_date, lst.uid),
                    )
                    continue

                # uid nuovo: e' gia' stato notificato lo stesso bene da altra fonte
                # (in un giro precedente) oppure gia' accettato in questo giro?
                dup = c.execute(
                    "SELECT 1 FROM listings WHERE dedup_key = ? AND notified = 1 LIMIT 1",
                    (lst.dedup_key,),
                ).fetchone() or (lst.dedup_key in accepted_keys)

                d = lst.to_row()
                c.execute(
                    """INSERT INTO listings
                       (uid, dedup_key, source, source_id, url, title, price,
                        city, province, region, tribunale, procedura, sale_date,
                        pub_date, description, notified)
                       VALUES
                       (:uid, :dedup_key, :source, :source_id, :url, :title, :price,
                        :city, :province, :region, :tribunale, :procedura, :sale_date,
                        :pub_date, :description, 0)""",
                    d,
                )
                if not dup:
                    to_notify.append(lst)
                    accepted_keys.add(lst.dedup_key)
        return to_notify

    def mark_notified(self, uids: Iterable[str]) -> None:
        with self._conn() as c:
            c.executemany(
                "UPDATE listings SET notified = 1 WHERE uid = ?",
                [(u,) for u in uids],
            )

    def all_active(self) -> list[sqlite3.Row]:
        """Per una futura dashboard: tutti i lotti, piu' recenti prima."""
        with self._conn() as c:
            return c.execute(
                "SELECT * FROM listings ORDER BY first_seen DESC"
            ).fetchall()
