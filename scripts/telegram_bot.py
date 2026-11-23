#!/usr/bin/env python3
"""Robottino Telegram del canale IMT.

Fa due cose a ogni giro (GitHub Actions ogni 15 min):
1. YouTube: legge il feed RSS del canale @imetatrading e, per ogni video NUOVO,
   pubblica sul canale Telegram titolo + breve sintesi + link (con anteprima).
   Al primo avvio segna come "gia' visti" i video esistenti, cosi' non inonda il canale.
2. Coda: invia i messaggi in telegram/queue/*.json con "send_at" arrivato
   (es. la sintesi del briefing mattutino), poi li sposta in telegram/sent/.
   Formato: {"send_at": "2026-11-24T07:30:00+01:00", "text": "<b>...</b>"}  (HTML Telegram)

Variabili d'ambiente: TELEGRAM_BOT_TOKEN (secret), TELEGRAM_CHAT_ID (facoltativo).
Se TELEGRAM_CHAT_ID manca, lo script trova da solo l'ID del canale in cui il bot
e' amministratore (getUpdates) e lo salva in telegram/config.json.
Impostazioni in telegram/config.json: include_shorts (true/false).
"""
import glob, html, json, os, re, shutil, sys, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CFG_PATH = "telegram/config.json"
SEEN_PATH = "telegram/youtube_seen.json"
QUEUE, SENT = "telegram/queue", "telegram/sent"
MAX_LINES_BRIEFING = 10
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}
UA = {"User-Agent": "Mozilla/5.0 (IMT telegram bot)"}


def tg(method, payload=None):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}",
                                 data=json.dumps(payload or {}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["result"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Telegram {method}: HTTP {e.code} {e.read().decode()}")


def load(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def save(path, data):
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=2)


def chat_id(cfg):
    cid = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or cfg.get("chat_id")
    if cid:
        return cid
    found = {}
    for u in tg("getUpdates", {"allowed_updates": ["my_chat_member", "channel_post"]}):
        for key in ("my_chat_member", "channel_post"):
            chat = (u.get(key) or {}).get("chat") or {}
            if chat.get("type") == "channel":
                found[chat["id"]] = chat.get("title", "")
    if not found:
        raise RuntimeError("Non trovo il canale: aggiungi il bot come amministratore del canale "
                           "Telegram IMT e scrivi un messaggio qualsiasi nel canale, poi rilancia.")
    cid = next((i for i, t in found.items() if "IMT" in t.upper()), next(iter(found)))
    print(f"Canale trovato: {found[cid]} ({cid})")
    cfg["chat_id"] = cid
    save(CFG_PATH, cfg)
    return cid


def send(cid, text, preview_url=None):
    p = {"chat_id": cid, "text": text, "parse_mode": "HTML"}
    p["link_preview_options"] = ({"url": preview_url, "prefer_large_media": True}
                                 if preview_url else {"is_disabled": True})
    tg("sendMessage", p)


# ---------------------------------------------------------------- YouTube
SKIP = re.compile(r"(https?://|www\.|^#|educational content|not financial advice|follow|"
                  r"subscribe|iscriviti|seguimi|link in bio|^\d\ufe0f?\u20e3|^\d+[.)]\s|^[\W\d_]+$)", re.I)


def summary(desc, limit=320):
    """Breve sintesi dalla descrizione: prime frasi utili, senza link/hashtag/CTA."""
    lines = [l.strip() for l in (desc or "").splitlines()]
    keep = [l for l in lines if l and not SKIP.search(l)]
    text = " ".join(keep)
    text = re.sub(r"#\w+", "", text).strip()
    if len(text) > limit:
        cut = text[:limit]
        end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        text = cut[:end + 1] if end > 80 else cut.rsplit(" ", 1)[0] + "…"
    return text


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def is_short(vid, link):
    if "/shorts/" in link:
        return True
    try:
        op = urllib.request.build_opener(NoRedirect)
        r = op.open(urllib.request.Request(f"https://www.youtube.com/shorts/{vid}", headers=UA), timeout=20)
        return r.status == 200
    except urllib.error.HTTPError:
        return False          # 30x = video normale
    except Exception:
        return False


def youtube(cfg, cid):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cfg['youtube_channel_id']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        root = ET.fromstring(r.read())
    entries = []
    for e in root.findall("a:entry", NS):
        g = e.find("media:group", NS)
        entries.append({
            "id": e.findtext("yt:videoId", namespaces=NS),
            "title": e.findtext("a:title", namespaces=NS) or "",
            "link": (e.find("a:link", NS).get("href") if e.find("a:link", NS) is not None else ""),
            "published": e.findtext("a:published", namespaces=NS) or "",
            "desc": g.findtext("media:description", namespaces=NS) if g is not None else "",
        })
    seen = load(SEEN_PATH, None)
    if seen is None:                       # primo avvio: niente raffica di vecchi video
        save(SEEN_PATH, [x["id"] for x in entries])
        print(f"Primo avvio: segnati {len(entries)} video esistenti come gia' visti.")
        return
    new = [x for x in reversed(entries) if x["id"] not in seen][:3]
    for v in new:
        short = is_short(v["id"], v["link"])
        seen.append(v["id"])
        if short and not cfg.get("include_shorts", True):
            print(f"Short saltato: {v['title']}")
            continue
        watch = f"https://youtu.be/{v['id']}" if not short else f"https://youtube.com/shorts/{v['id']}"
        head = "⚡ <b>Nuovo Short su YouTube</b>" if short else "🎬 <b>Nuovo video su YouTube</b>"
        s = summary(v["desc"])
        text = f"{head}\n\n<b>{html.escape(v['title'])}</b>\n"
        if s:
            text += f"\n{html.escape(s)}\n"
        text += f"\n▶️ <a href=\"{watch}\">Guardalo qui</a>"
        send(cid, text, preview_url=watch)
        print(f"Pubblicato: {v['title']}")
    save(SEEN_PATH, seen[-200:])


# ---------------------------------------------------------------- coda messaggi
def queue(cid):
    now = datetime.now(timezone.utc)
    for path in sorted(glob.glob(f"{QUEUE}/*.json")):
        msg = json.load(open(path))
        when = datetime.fromisoformat(msg["send_at"])
        if when > now:
            continue
        name = os.path.basename(path)
        if now - when > timedelta(hours=10):
            print(f"Scaduto, non inviato: {name}")
        else:
            lines = [l for l in msg["text"].strip().splitlines()]
            if msg.get("kind") == "briefing" and len([l for l in lines if l.strip()]) > MAX_LINES_BRIEFING:
                body = [l for l in lines if l.strip()]
                lines = body[:MAX_LINES_BRIEFING - 1] + body[-1:]
                print("Briefing oltre 10 righe: accorciato.")
            send(cid, "\n".join(lines))
            print(f"Inviato: {name}")
        shutil.move(path, f"{SENT}/{name}")


def main():
    if not TOKEN:
        sys.exit("Manca il secret TELEGRAM_BOT_TOKEN.")
    cfg = load(CFG_PATH, {})
    cid = chat_id(cfg)
    errors = []
    for step in (lambda: youtube(cfg, cid), lambda: queue(cid)):
        try:
            step()
        except Exception as e:
            errors.append(str(e))
            print("ERRORE:", e)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
