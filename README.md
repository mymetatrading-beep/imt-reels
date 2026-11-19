# imt-reels
Reel di IMT

## Come funziona
- `specs/*.json`: testo e grafico di ogni Reel → `python3 scripts/make_reel.py specs/X.json reels/X.mp4`
- `queue/*.json`: post da pubblicare (ora, video, didascalia)
- GitHub Actions ogni 30 min carica in Buffer i prossimi post (max 9 alla volta, limite piano gratuito) → `scheduled/` → `published/`
- Orari: 08:00, 15:30, 21:00 (Europe/Rome)

## Reel del LIBRO (2 a settimana, domenica e mercoledì alle 19:00)
- Libro: "Smart Money Concepts" di Glauco Giovinazzi – https://www.amazon.it/dp/B0C9S5R573
- Copertina: `assets/book_cover.jpg` (scaricata dal workflow "Scarica asset" da `assets/urls.txt`)
- `specs/libro/*.json` → `python3 scripts/make_book_reel.py specs/libro/X.json reels/X.mp4`
- Reel in italiano (il libro è in italiano), chiusura "LINK IN BIO": il link Amazon sta nella bio di Instagram
