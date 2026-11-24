# imt-reels
Reel di IMT

## Come funziona
- `specs/*.json`: testo e grafico di ogni Reel → `python3 scripts/make_reel.py specs/X.json reels/X.mp4`
- `queue/*.json`: post da pubblicare (ora, video, didascalia)
- GitHub Actions ogni 30 min carica in Buffer i prossimi post (max 9 alla volta, limite piano gratuito) → `scheduled/` → `published/`
- Orari: 08:00, 15:30, 21:00 (Europe/Rome)
- Ogni Reel esce anche come YouTube Short su @imetatrading (stesso orario, titolo = prima riga della didascalia, categoria Education). YouTube via Buffer accetta max 2 Short al giorno: passano i primi 2 Reel della giornata; la domenica e il mercoledì passano il reel del LIBRO + il primo reel tecnico (08:00). Gli altri restano solo su Instagram. Per escluderne uno: `"no_youtube": true`
- YouTube Shorts (da 2026-11-24): SOLO 2 Shorts al giorno, alle 18:00 e alle 21:00 (ora di Roma). Nei file di coda dei Reel scelti si mette `"youtube_at": "AAAA-MM-GGTHH:MM:00+01:00"` (orario dello Short, può essere diverso dall'orario Instagram); gli altri Reel del giorno hanno `"no_youtube": true`. `scripts/buffer_sync.py`: se nella giornata almeno un Reel ha `youtube_at`, su YouTube vanno solo i Reel con `youtube_at`, ciascuno al suo orario; i file senza `youtube_at` seguono la regola vecchia (retrocompatibile).
  - 21:00 = il Reel delle 21:00; 18:00 = il migliore tra i Reel delle 08:00 e 15:30 (preferibilmente order flow); nei giorni del libro lo slot delle 18:00 va al Reel del libro (`youtube_at` alle 18:00 sul file del libro).

## Limite YouTube: 2 Shorts in 24 ore MOBILI (dal 24/11/2026)
- Buffer gratuito blocca il 3° Short pubblicato in un qualunque intervallo di 24 ore (non per giorno di calendario): il 23/11 *DOM pulling* è fallito per questo.
- `scripts/buffer_sync.py` prima di mandare uno Short controlla gli orari degli Shorts già mandati (`youtube_scheduled_at`) e, se serve, lo sposta di qualche minuto (margine 4 min) finché in ogni finestra di 24 h ce ne sono al massimo 2. Gli orari quindi slittano di ~4 min al giorno (18:04, 18:08…); quando lo spostamento supererebbe 45 min lo Short di quel giorno resta solo su Instagram e gli orari tornano a 18:00/21:00 (circa una volta ogni 12 giorni).
- DOMENICA: niente Short delle 18 (scelta dell'utente del 24/11/2026), solo quello delle 21:00; nei giorni del libro la domenica lo Short delle 21:00 è il Reel del libro. Questo azzera ogni settimana lo slittamento degli orari (max ~25 min), quindi non si salta più nessun altro Short.
- Campi: `youtube_scheduled_at` = orario effettivo dello Short; `youtube_failed: true` = Short fallito in Buffer (non conta nel limite).
- I video lunghi caricati a mano da YouTube Studio NON passano da Buffer e non contano in questo limite.

## Stile dei Reel v2 (dal 24/11/2026)
- `make_reel.py` usa di default lo stile v2: gancio leggibile già dal primo fotogramma (sopra il grafico), grafico in movimento da subito, regola 1-2-3 veloce, durata ~9-10 s. Per il vecchio stile da 16,5 s: `"version": 1` nella spec.
- Motivo: nella settimana 17-23/11 circa l'81% degli spettatori lasciava il Reel nei primi 3 secondi.
- Test dei ganci: ogni Reel ha `"hook_type"` (question / number / mistake / contrarian) nella spec e nel file di coda; nei 3 Reel di un giorno si usano 3 tipi diversi. Alla verifica del martedì si confrontano i tipi.

## Reel del LIBRO (2 a settimana, domenica e mercoledì alle 19:00)
- Libro: "Smart Money Concepts" di Glauco Giovinazzi – https://www.amazon.it/dp/B0C9S5R573
- Copertina: `assets/book_cover.jpg` (scaricata dal workflow "Scarica asset" da `assets/urls.txt`)
- `specs/libro/*.json` → `python3 scripts/make_book_reel.py specs/libro/X.json reels/X.mp4`
- Reel in italiano (il libro è in italiano), chiusura "LINK IN BIO": il link Amazon sta nella bio di Instagram

## Bot Telegram del canale IMT (`scripts/telegram_bot.py`, workflow "Bot Telegram IMT")
- Ogni 15 min legge il feed RSS di YouTube @imetatrading (ID UC5FAGTJzGsvW2z8_cWMwn6g) e per ogni video nuovo pubblica sul canale Telegram: titolo, breve sintesi (prime frasi della descrizione, senza link/hashtag) e link con anteprima. Al primo avvio i video già esistenti vengono solo segnati come visti (`telegram/youtube_seen.json`).
- Shorts: su Telegram va SOLO lo Short delle 18:00 (fascia `"shorts_window"` in `telegram/config.json`, ora di Roma); gli altri Shorts vengono saltati, i video lunghi escono sempre. `"include_shorts": false` li esclude tutti.
- Didascalia dello Short delle 18: `telegram/teasers/AAAA-MM-GG.json` → `{"teaser": "HTML Telegram, in italiano"}` scritto ogni giorno dall'attività "Reel IMT del giorno dopo"; se manca, il bot usa la sintesi della descrizione.
- Coda messaggi: `telegram/queue/*.json` → `{"send_at": "...+01:00", "kind": "briefing", "text": "HTML Telegram"}`; inviati quando arriva l'ora, poi spostati in `telegram/sent/`. Il briefing viene limitato a 10 righe. Messaggi più vecchi di 10 ore non vengono inviati.
- Secret: `TELEGRAM_BOT_TOKEN` (da @BotFather). L'ID del canale viene trovato da solo (il bot deve essere amministratore del canale) e salvato in `telegram/config.json`; in alternativa secret `TELEGRAM_CHAT_ID`.
