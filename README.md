# imt-reels
Reel di IMT

## Come funziona
- `specs/*.json`: testo e grafico di ogni Reel → `python3 scripts/make_reel.py specs/X.json reels/X.mp4`
- `queue/*.json`: post da pubblicare (ora, video, didascalia)
- GitHub Actions ogni 30 min carica in Buffer i prossimi post (max 9 alla volta, limite piano gratuito) → `scheduled/` → `published/`
- Orari: 08:00, 15:30, 21:00 (Europe/Rome)
- Ogni Reel esce anche come YouTube Short su @imetatrading (stesso orario, titolo = prima riga della didascalia, categoria Education). YouTube via Buffer accetta max 2 Short al giorno: passano i primi 2 Reel della giornata; la domenica e il mercoledì passano il reel del LIBRO + il primo reel tecnico (08:00). Gli altri restano solo su Instagram. Per escluderne uno: `"no_youtube": true`

## Reel del LIBRO (2 a settimana, domenica e mercoledì alle 19:00)
- Libro: "Smart Money Concepts" di Glauco Giovinazzi – https://www.amazon.it/dp/B0C9S5R573
- Copertina: `assets/book_cover.jpg` (scaricata dal workflow "Scarica asset" da `assets/urls.txt`)
- `specs/libro/*.json` → `python3 scripts/make_book_reel.py specs/libro/X.json reels/X.mp4`
- Reel in italiano (il libro è in italiano), chiusura "LINK IN BIO": il link Amazon sta nella bio di Instagram

## Bot Telegram del canale IMT (`scripts/telegram_bot.py`, workflow "Bot Telegram IMT")
- Ogni 15 min legge il feed RSS di YouTube @imetatrading (ID UC5FAGTJzGsvW2z8_cWMwn6g) e per ogni video nuovo pubblica sul canale Telegram: titolo, breve sintesi (prime frasi della descrizione, senza link/hashtag) e link con anteprima. Al primo avvio i video già esistenti vengono solo segnati come visti (`telegram/youtube_seen.json`).
- Shorts inclusi: per escluderli `"include_shorts": false` in `telegram/config.json`.
- Coda messaggi: `telegram/queue/*.json` → `{"send_at": "...+01:00", "kind": "briefing", "text": "HTML Telegram"}`; inviati quando arriva l'ora, poi spostati in `telegram/sent/`. Il briefing viene limitato a 10 righe. Messaggi più vecchi di 10 ore non vengono inviati.
- Secret: `TELEGRAM_BOT_TOKEN` (da @BotFather). L'ID del canale viene trovato da solo (il bot deve essere amministratore del canale) e salvato in `telegram/config.json`; in alternativa secret `TELEGRAM_CHAT_ID`.
