# Monitor Aste Hotel

Sistema unificato che monitora le aste giudiziarie/fallimentari di alberghi su più
portali, deduplica i lotti che compaiono su più fonti, e ti avvisa solo delle
**novità** su un unico canale (Telegram).

## Architettura

```
sources/   un adapter per fonte  -> restituisce Listing normalizzati
core/      models (dedup) + store (SQLite: stato, storico, novità)
sinks/     canali di notifica (Telegram, console, ...)
run.py     orchestratore: raccoglie -> filtra -> dedup -> notifica
```

Il disegno è **modulare di proposito**: quando un sito cambia HTML, riscrivi un
solo adapter senza toccare il resto. Il dedup riconosce lo stesso hotel anche se
ripubblicato da fonti diverse, confrontando `tribunale + procedura`.

## Fonti incluse

| adapter          | stato        | tipo                         |
|------------------|--------------|------------------------------|
| pvp              | riferimento  | portale ufficiale Ministero  |
| astegiudiziarie  | stub         | privato, categoria alberghi  |
| astalegale       | stub         | privato, categoria alberghi  |
| fallcoaste       | stub         | fallimentare                 |
| fallimenti       | stub         | fallimentare                 |
| fallimentieaste  | stub         | privato, strutture ricettive |

«stub» = struttura pronta, **selettori CSS da completare** guardando il DOM reale
(vedi sotto). Il dedup, lo storage, i filtri e la notifica funzionano già.

## Setup

```bash
pip install -r requirements.txt
cp config/settings.example.toml config/settings.toml
# compila token Telegram e filtri in settings.toml
python -m aste_hotel.run
```

Senza credenziali Telegram, il sistema stampa le novità a schermo (ConsoleSink):
utile per provare in locale.

### Telegram (5 min)
1. `@BotFather` su Telegram → `/newbot` → ottieni il **token**.
2. Manda un messaggio al tuo bot, poi apri
   `https://api.telegram.org/bot<TOKEN>/getUpdates` → leggi il tuo **chat_id**.
3. Mettili in `config/settings.toml`.

## Tarare gli adapter «stub» (il vero lavoro)

Per ogni sito, una volta sola, ~5 minuti:
1. Apri l'URL di categoria (già scritto in `sources/portali.py`).
2. Tasto destro su una card di risultato → **Ispeziona**.
3. Individua le classi CSS di: contenitore card, titolo, prezzo, città, data,
   tribunale/procedura.
4. Riempi i campi `sel_*` nella sottoclasse corrispondente.

Per il **PVP** (`sources/pvp.py`): lancia la ricerca avanzata filtrata su
"Alberghi e pensioni", copia l'URL risultante in `RESULTS_URL` (contiene i codici
categoria giusti), poi aggiorna i selettori sul DOM reale.

Suggerimento: attiva un adapter per volta in `settings.toml`, verifica che i
lotti escano corretti nel ConsoleSink, poi passa al successivo.

## Schedulazione

- **GitHub Actions (gratis, senza server):** copia `config/github-actions.yml`
  in `.github/workflows/monitor.yml`, imposta i Secret `TG_TOKEN` e `TG_CHAT_ID`.
  Gira ogni 8 ore e conserva lo stato via cache.
- **VPS/PC con cron:** `0 */8 * * * cd /path && python -m aste_hotel.run`

## Buona condotta (importante)

- Gli adapter rispettano già: User-Agent identificabile, ritardo tra richieste,
  timeout. **Metti un tuo contatto reale** in `sources/base.py` (USER_AGENT).
- Prima di attivare lo scraping su un sito, controlla `robots.txt` e i Termini
  d'uso. Diverse di queste fonti offrono un **"salva ricerca con avviso email"**
  nativo: dove c'è, valuta di usarlo al posto dello scraping — più stabile e più
  rispettoso. Il PVP ha anche una "Iscrizione Newsletter" ufficiale.

## Estendere

- **Nuovo sito:** crea una sottoclasse di `_HtmlListSource` in `portali.py` (o un
  nuovo file se la struttura è molto diversa) e aggiungila a `ALL_SOURCES` in
  `run.py`.
- **Nuovo canale (email/Discord):** crea una sottoclasse di `Sink` in
  `sinks/notify.py` con un metodo `send()`.
- **Dashboard:** `Store.all_active()` restituisce già tutto lo storico; bastano
  poche righe di Flask/FastAPI per servirlo.
```
