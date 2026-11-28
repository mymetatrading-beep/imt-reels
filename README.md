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

## Stile v3 Liquid Glass (default dal 28/11/2026)
- Deciso da Glauco il 28/11/2026: Reel/Shorts, caroselli e storie usano lo stile IMT Liquid Glass con i colori e il logo ORIGINALI di IMT. Default `"version": 3` in `make_reel.py` e `make_static.py`; `"version": 2` = stile v2 (Poppins, bordi magenta), `"version": 1` = vecchio Reel da 16,5 s. Formati, durate, campi delle spec e musica invariati.
- Codice: `scripts/imt_glass.py` (palette, font, fondo con bagliori, lastre di vetro, sfere, pillole, logo vettoriale, candele cilindriche), `scripts/reel_v3.py` (scene dei Reel), `scripts/static_v3.py` (caroselli e storie).
- Colori: rosa #FF66C4 (chiaro #FFB8E2, scuro #A8287A), bianco #FFFFFF / argento #E4EAF2 > #8C96A6, fondo #05070D, testo secondario #9AA6B8, oro #FFC24B solo per POC e livelli chiave (linea del livello e pillola dell'etichetta prima dell'impatto). Niente azzurro, arancione, verde o rosso.
- Fondo: bagliore rosa rgba(255,102,196,0.22) in alto a sinistra, freddo rgba(170,180,230,0.10) in basso a destra.
- Lastre di vetro: bianco ~6%, angoli 22-30 px, filo di luce sul bordo alto, riflesso diagonale, ombra morbida. Pillole per etichette (rosa = buy/accento, argento = sell/neutro, oro = livello chiave). Numeri e lettere in sfere rosa con riflesso in alto a sinistra.
- Candele: rialziste bianco-argento, ribassiste rosa, angoli arrotondati e gradiente laterale chiaro > pieno > scuro (effetto cilindro). Bolle opzionali nel grafico: `"bubbles": [{"candle": 8, "y": 61, "r": 26, "buy": true}]` (sfera rosa = buy, argento = sell).
- Logo: marchio originale IMT in vettoriale (box 472x470: anello rosa centro (236,230) r 218/168 aperto in basso tra x 132-340 per y > 300, barre rosa ai lati, barra centrale bianca piu' alta), vetro con gradiente diagonale, riflesso, bordo chiaro, alone rosa e ombra. Header: pillola di vetro con logo + "IMT · SMC ORDER FLOW" in Montserrat SemiBold spaziato, puntino rosa. Mai una sfera con scritto IMT.
- Font: Montserrat per il marchio, Inter per i testi, DejaVu Sans Mono per prezzi e footprint (JetBrains Mono non installato). Niente emoji nelle grafiche.
- Reel: gancio leggibile dal fotogramma 0 sopra la lastra del grafico (parola chiave rosa sottolineata), grafico in movimento da subito, riflesso che scorre sulla lastra nei primi secondi, impatto in una lastra di vetro, regole in lastre che entrano con scala + dissolvenza, finale con logo e FOLLOW.
- Footprint (caroselli): ask in pillola rosa = buy imbalance, bid in pillola argento = sell imbalance, POC con contorno oro.

## Stile dei Reel v2 (dal 24/11/2026)
- `make_reel.py` usa di default lo stile v2: gancio leggibile già dal primo fotogramma (sopra il grafico), grafico in movimento da subito, regola 1-2-3 veloce, durata ~9-10 s. Per il vecchio stile da 16,5 s: `"version": 1` nella spec.
- Motivo: nella settimana 17-23/11 circa l'81% degli spettatori lasciava il Reel nei primi 3 secondi.
- Musica v2 (`scripts/music_v2.py`, dal 24/11/2026): stereo con riverbero, sidechain sui pad, filtro che si apre nell'intro, riser + mezzo secondo di silenzio prima del colpo, impatto, outro che si chiude. 3 stili: `dark_trap`, `cinematic`, `synthwave`; stile scelto dall'utente: `dark_trap` (default; tonalità diversa per ogni Reel). Altri stili solo con `"music"` nella spec; `"music": "classic"` = vecchia musica.
- Test dei ganci: ogni Reel ha `"hook_type"` (question / number / mistake / contrarian) nella spec e nel file di coda; nei 3 Reel di un giorno si usano 3 tipi diversi. Alla verifica del martedì si confrontano i tipi.

## Slot già occupati e gancio contrarian (dal 27/11/2026)
- Prima di creare i Reel del giorno dopo controlla queue/, scheduled/ e published/: se per uno slot (08:00, 15:30, 21:00) esiste già un Reel (es. creato a mano in chat), NON crearne un altro per quello slot e non toccare i suoi campi youtube_at / no_youtube; se esiste già telegram/teasers/<data>.json non sovrascriverlo. Carosello e storie si creano comunque.
- Il gancio "contrarian" nella forma "[convinzione comune] isn't [verità] ⚠️" è quello che rende di più ("Tight stop isn't less RISK." = 111,8% di visualizzazione media): ogni giorno almeno 1 Reel usa questo formato, gli altri continuano il test degli altri ganci.
- Già creati in chat il 27/11: 29/11 08:00, 15:30, 21:00 e 30/11 08:00 (con Short YouTube del 30/11 alle 18:00 e teaser Telegram).

## Reel del LIBRO (2 a settimana, domenica e mercoledì alle 19:00)
- Libro: "Smart Money Concepts" di Glauco Giovinazzi – https://www.amazon.it/dp/B0C9S5R573
- Copertina: `assets/book_cover.jpg` (scaricata dal workflow "Scarica asset" da `assets/urls.txt`)
- `specs/libro/*.json` → `python3 scripts/make_book_reel.py specs/libro/X.json reels/X.mp4`
- Reel in italiano (il libro è in italiano), chiusura "LINK IN BIO": il link Amazon sta nella bio di Instagram
- RECENSIONI (dal 24/11/2026, richiesta dell'utente): ogni Reel e ogni storia del libro mostra le recensioni Amazon VERE in `assets/recensioni.json` (scena `scripts/reviews_card.py`, tra i punti chiave e il LINK IN BIO; Reel da 19,5 s). Mai inventare o modificare recensioni: se ne aggiungono altre solo se le fornisce l'utente. Per escluderle da un Reel: `"reviews": false` nella spec.

## Bot Telegram del canale IMT (`scripts/telegram_bot.py`, workflow "Bot Telegram IMT")
- Ogni 15 min legge il feed RSS di YouTube @imetatrading (ID UC5FAGTJzGsvW2z8_cWMwn6g) e per ogni video nuovo pubblica sul canale Telegram: titolo, breve sintesi (prime frasi della descrizione, senza link/hashtag) e link con anteprima. Al primo avvio i video già esistenti vengono solo segnati come visti (`telegram/youtube_seen.json`).
- Shorts: su Telegram va SOLO lo Short delle 18:00 (fascia `"shorts_window"` in `telegram/config.json`, ora di Roma); gli altri Shorts vengono saltati, i video lunghi escono sempre. `"include_shorts": false` li esclude tutti.
- Didascalia dello Short delle 18: `telegram/teasers/AAAA-MM-GG.json` → `{"teaser": "HTML Telegram, in italiano"}` scritto ogni giorno dall'attività "Reel IMT del giorno dopo"; se manca, il bot usa la sintesi della descrizione.
- Coda messaggi: `telegram/queue/*.json` → `{"send_at": "...+01:00", "kind": "briefing", "text": "HTML Telegram"}`; inviati quando arriva l'ora, poi spostati in `telegram/sent/`. Il briefing viene limitato a 10 righe. Messaggi più vecchi di 10 ore non vengono inviati.
- Secret: `TELEGRAM_BOT_TOKEN` (da @BotFather). L'ID del canale viene trovato da solo (il bot deve essere amministratore del canale) e salvato in `telegram/config.json`; in alternativa secret `TELEGRAM_CHAT_ID`.

## Telegram: post con foto, video e album
Oltre al testo, i file in `telegram/queue/*.json` possono avere:
- `"photo": "posts/x.jpg"` → foto con il testo come didascalia
- `"video": "reels/x.mp4"` → video (max 50 MB) con il testo come didascalia
- `"media": ["a.jpg", "b.mp4", ...]` → album di 2-10 elementi, didascalia sul primo

Percorsi nel repo oppure URL https. Se il testo supera 1024 caratteri il media esce senza didascalia e il testo subito dopo.
Esempio: `{"send_at": "2026-11-25T12:30:00+01:00", "text": "<b>Titolo</b>\nTesto", "video": "reels/2026-11-25-0800-x.mp4"}`
