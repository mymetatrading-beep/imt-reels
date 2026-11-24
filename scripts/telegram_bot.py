#!/usr/bin/env python3
"""Robottino Telegram del canale IMT.

Fa due cose a ogni giro (GitHub Actions ogni 15 min):
1. YouTube: legge il feed RSS del canale @imetatrading e, per ogni video NUOVO,
   pubblica sul canale Telegram titolo + breve sintesi + link (con anteprima).
   Al primo avvio segna come "gia' visti" i video esistenti, cosi' non inonda il canale.
2. Coda: invia i messaggi in telegram/queue/*.json con "send_at" arrivato
   (es. la sintesi del briefing mattutino), poi li sposta in telegram/sent/.
   Formato: {"send_at": "2026-11-24T07:30:00+01:00", "text": "<b>...</b>"}  (HTML Telegram)
   Con media (facoltativo, percorsi nel repo o URL https):
     "photo": "posts/x.jpg"   -> foto con il testo come didascalia
     "video": "reels/x.mp4"   -> video con il testo come didascalia (max 50 MB)
     "media": ["a.jpg", "b.mp4", ...] -> album (2-10 foto/video), didascalia sul primo
   Se il testo supera 1024 caratteri, il media esce senza didascalia e subito dopo il testo.

Variabili d'ambiente: TELEGRAM_BOT_TOKEN (secret), TELEGRAM_CHAT_ID (facoltativo).
Se TELEGRAM_CHAT_ID manca, lo script trova da solo l'ID del canale in cui il bot
e' amministratore (getUpdates) e lo salva in telegram/config.json.
Impostazioni in telegram/config.json: include_shorts (true/false).
"""
import glob, html, json, mimetypes, os, re, shutil, sys, uuid, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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


def tg_upload(method, fields, files):
    """Chiamata multipart (invio di file dal repo). files: {nome_campo: percorso}."""
    b = uuid.uuid4().hex
    body = bytearray()
    for k, v in fields.items():
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n".encode()
        body += (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)).encode() + b"\r\n"
    for k, path in files.items():
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        body += (f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; "
                 f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
        body += open(path, "rb").read() + b"\r\n"
    body += f"--{b}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", data=bytes(body),
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)["result"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Telegram {method}: HTTP {e.code} {e.read().decode()}")


def _kind(path):
    return "video" if path.lower().endswith((".mp4", ".mov", ".m4v", ".webm")) else "photo"


def send_media(cid, text, photo=None, video=None, media=None):
    """Foto, video o album con didascalia HTML. I percorsi locali vengono caricati, gli URL passati cosi'."""
    caption = text if text and len(text) <= 1024 else ""
    if media:
        items, files = [], {}
        for i, m in enumerate(media[:10]):
            ref = m if m.startswith("http") else f"attach://f{i}"
            if not m.startswith("http"):
                files[f"f{i}"] = m
            it = {"type": _kind(m), "media": ref}
            if i == 0 and caption:
                it.update(caption=caption, parse_mode="HTML")
            items.append(it)
        if len(items) == 1:
            return send_media(cid, text, **{items[0]["type"]: media[0]})
        tg_upload("sendMediaGroup", {"chat_id": str(cid), "media": items}, files)
    else:
        kind, path = ("photo", photo) if photo else ("video", video)
        fields = {"chat_id": str(cid)}
        if caption:
            fields.update(caption=caption, parse_mode="HTML")
        if kind == "video":
            fields["supports_streaming"] = "true"
        if path.startswith("http"):
            fields[kind] = path
            tg_upload("send" + kind.capitalize(), fields, {})
        else:
            tg_upload("send" + kind.capitalize(), fields, {kind: path})
    if text and not caption:
        send(cid, text)


def load(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def save(path, data):
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=2)


def chat_id(cfg):
    cid = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or cfg.get("chat_id")
    if cid:
        return cid
    me = tg("getMe")
    print(f"Bot collegato: @{me.get('username')} ({me.get('first_name')})")
    found, seen_chats = {}, {}
    for u in tg("getUpdates", {"allowed_updates": []}):
        for key, val in u.items():
            if not isinstance(val, dict):
                continue
            chat = val.get("chat") or {}
            if chat:
                seen_chats[chat["id"]] = (chat.get("type"), chat.get("title") or chat.get("first_name"))
            if chat.get("type") == "channel":
                found[chat["id"]] = chat.get("title", "")
    print("Chat viste dal bot:", seen_chats or "nessuna")
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


ROME = ZoneInfo("Europe/Rome")


def rome_time(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ROME)


def short_allowed(cfg, published):
    """Su Telegram va solo lo Short delle 18 (fascia in config "shorts_window")."""
    if not cfg.get("include_shorts", True):
        return False
    win = cfg.get("shorts_window")
    if not win:
        return True
    hm = rome_time(published).strftime("%H:%M")
    return win[0] <= hm <= win[1]


def load_teaser(published):
    """Didascalia scritta apposta per Telegram: telegram/teasers/AAAA-MM-GG.json {"teaser": "..."}."""
    path = f"telegram/teasers/{rome_time(published):%Y-%m-%d}.json"
    if os.path.exists(path):
        return (json.load(open(path)).get("teaser") or "").strip() or None
    return None


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
        if short and not short_allowed(cfg, v["published"]):
            print(f"Short saltato (fuori dalla fascia delle 18): {v['title']}")
            continue
        watch = f"https://youtu.be/{v['id']}" if not short else f"https://youtube.com/shorts/{v['id']}"
        head = "⚡ <b>Nuovo Short su YouTube</b>" if short else "🎬 <b>Nuovo video su YouTube</b>"
        teaser = load_teaser(v["published"]) if short else None
        s = teaser or html.escape(summary(v["desc"]))
        title = re.sub(r"\s*#shorts\b", "", v["title"], flags=re.I).strip()
        text = f"{head}\n\n<b>{html.escape(title)}</b>\n"
        if s:
            text += f"\n{s}\n"
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
            text = "\n".join(lines).strip()
            if msg.get("photo") or msg.get("video") or msg.get("media"):
                send_media(cid, text, photo=msg.get("photo"), video=msg.get("video"), media=msg.get("media"))
            else:
                send(cid, text)
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
