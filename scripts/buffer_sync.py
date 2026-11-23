#!/usr/bin/env python3
"""Riempie in automatico la coda di Buffer con i post di queue/.

Buffer gratuito tiene al massimo 10 post programmati per canale: questo script
ne carica fino a MAX_IN_BUFFER alla volta (i piu' vicini nel tempo) e, appena
Buffer ne pubblica uno, al giro successivo carica il prossimo.
Buffer poi pubblica ogni post all'ora esatta indicata in "publish_at".

Coda: queue/*.json, un file per post:
{
  "publish_at": "2026-11-23T08:00:00+01:00",
  "type": "REELS",                        # REELS | IMAGE | CAROUSEL | STORIES
  "media": ["reels/2026-11-23-tema.mp4"],  # percorsi nel repo o URL completi
  "caption": "testo...",
  "channel": "instagram",                 # facoltativo (default instagram)
  "no_youtube": false,                     # true = NON pubblicarlo anche come Short
  "youtube_at": "2026-11-24T18:00:00+01:00", # facoltativo: orario dello Short su YouTube
  # (se nella giornata almeno un Reel ha "youtube_at", su YouTube vanno SOLO
  #  i Reel con "youtube_at", ciascuno al proprio orario; altrimenti regola vecchia)
  # ogni REELS su Instagram parte in automatico anche come YouTube Short
  # (se il canale YouTube e' collegato in Buffer)
  "draft": false                           # true = solo bozza in Buffer (test)
}
Flusso dei file: queue/ -> scheduled/ (caricato in Buffer) -> published/.
Variabili d'ambiente: BUFFER_API_KEY, GITHUB_REPOSITORY.
"""
import glob, json, os, shutil, sys, urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.buffer.com"
KEY = os.environ["BUFFER_API_KEY"]
REPO = os.environ.get("GITHUB_REPOSITORY", "mymetatrading-beep/imt-reels")
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"
MAX_IN_BUFFER = 9          # piano gratuito: 10 per canale, teniamo 1 di margine
CHANNELS_CACHE = "buffer_channels.json"


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}")
    if out.get("errors"):
        raise RuntimeError(json.dumps(out["errors"], ensure_ascii=False))
    return out["data"]


def channels():
    if os.path.exists(CHANNELS_CACHE):
        cached = json.load(open(CHANNELS_CACHE))
        if "youtube" in cached:
            return cached
    orgs = gql("query { account { organizations { id name } } }")["account"]["organizations"]
    found = {}
    for o in orgs:
        q = """query($org: OrganizationId!) {
                 channels(input: {organizationId: $org}) { id name service } }"""
        for c in gql(q, {"org": o["id"]})["channels"]:
            found.setdefault(c["service"].lower(), c["id"])
            print(f"Canale trovato: {c['service']} '{c['name']}' -> {c['id']}")
    json.dump(found, open(CHANNELS_CACHE, "w"), indent=2)
    return found


def url_of(m):
    return m if m.startswith("http") else RAW + m


def is_video(m):
    return m.lower().endswith((".mp4", ".mov"))


CREATE = """mutation($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id dueAt } }
    ... on MutationError { message }
  }
}"""


def build_input(post, channel_id, asset_style):
    kind = post.get("type", "REELS").upper()
    ig_type = {"REELS": "reel", "STORIES": "story"}.get(kind, "post")
    media = post["media"]
    if asset_style == "list":     # formato attuale della documentazione Buffer
        assets = [{"video": {"url": url_of(m)}} if is_video(m)
                  else {"image": {"url": url_of(m)}} for m in media]
    else:                         # formato precedente, usato come ripiego
        vids = [{"url": url_of(m)} for m in media if is_video(m)]
        imgs = [{"url": url_of(m)} for m in media if not is_video(m)]
        assets = {k: v for k, v in (("videos", vids), ("images", imgs)) if v}
    inp = {
        "channelId": channel_id,
        "text": post.get("caption", ""),
        "schedulingType": "automatic",
        "mode": "customScheduled",
        "dueAt": datetime.fromisoformat(post["publish_at"]).astimezone(timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "assets": assets,
    }
    if post.get("channel", "instagram") == "instagram":
        inp["metadata"] = {"instagram": {"type": ig_type, "shouldShareToFeed": kind != "STORIES"}}
    elif post.get("channel") == "youtube":
        inp["metadata"] = {"youtube": {"title": post["yt_title"], "categoryId": "27",
                                       "madeForKids": False, "notifySubscribers": True}}
    if post.get("draft"):
        inp["saveToDraft"] = True
    return inp


def push(post, chans):
    service = post.get("channel", "instagram")
    if service not in chans:
        raise RuntimeError(f"nessun canale '{service}' collegato in Buffer: {list(chans)}")
    last = None
    for style in ("list", "object"):
        try:
            res = gql(CREATE, {"input": build_input(post, chans[service], style)})["createPost"]
        except RuntimeError as e:
            last = e
            continue
        if res.get("message"):
            raise RuntimeError(f"Buffer ha rifiutato il post: {res['message']}")
        return res["post"]["id"]
    raise last


AMAZON = "https://amzn.eu/d/0fsxwSEH"

LINKS = [  # (emoji, testo EN, testo IT, link) - footer fisso sotto ogni Short
    ("📖", 'My book "Smart Money Concepts" on Amazon', 'Il mio libro "Smart Money Concepts" su Amazon', AMAZON),
    ("🎁", '2 FREE gifts: trading guide + free book chapter on Liquidity (Italian)', '2 regali GRATIS: guida "La bussola del trading" + capitolo del libro sulla Liquidità', "https://subscribepage.io/KiSZN8"),
    ("📢", "Free Telegram analysis channel", "Canale Telegram gratuito di analisi", "https://t.me/+EkcsHUUEjig3YTY0"),
    ("🎓", "Free beginner course (playlist)", "Corso base gratuito per principianti", "https://youtube.com/playlist?list=PL_oGz3uWRGI2C2UsExwjXxXpX_tBQrVCr"),
    ("🚀", "My trading program", "Il mio percorso di trading", "https://mymetatrader.gumroad.com/l/ghllv"),
    ("📸", "Instagram", "Instagram", "https://www.instagram.com/institutionalmetatrading/"),
    ("✉️", "Info", "Info", "mymetatrading@gmail.com"),
]


def footer(italian, skip_book):
    rows = [f"{e} {it if italian else en}: {url}" for e, en, it, url in LINKS
            if not (skip_book and url == AMAZON)]
    return "\n\n━━━━━━━━━━━━━━━\n" + "\n".join(rows)


def youtube_twin(post):
    """Stesso Reel adattato a YouTube Shorts (titolo + descrizione)."""
    cap = post.get("caption", "")
    first = cap.strip().split("\n")[0].strip() or "Order flow rule"
    title = (first[:88].rstrip() + " #shorts")[:100]
    desc = cap.replace("Follow @institutionalmetatrading", "Subscribe to @imetatrading")
    desc = desc.replace("Il link per acquistarlo è nella BIO: un tocco e sei su Amazon.",
                        "Acquistalo su Amazon: " + AMAZON)
    book = is_book(post)
    if book and AMAZON not in desc:
        desc = desc.replace("\n\n#", f"\n\n📖 Amazon: {AMAZON}\n\n#", 1)
    # hashtag in fondo (YouTube ne usa max 15), footer con i link prima degli hashtag
    body, sep, tags = desc.rpartition("\n\n#")
    if not sep:
        body, tags = desc, ""
    desc = body + footer(italian=book, skip_book=book) + (("\n\n#" + tags) if tags else "")
    when = post.get("youtube_at") or post["publish_at"]
    soon = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=5)
    if datetime.fromisoformat(when) < soon:
        when = soon.isoformat()
    return {**post, "channel": "youtube", "yt_title": title, "caption": desc,
            "publish_at": when}


BOOK_DAYS = (6, 2)   # domenica e mercoledi': giorni dei reel del libro


def is_book(post):
    return "libro" in post["media"][0]


def wants_youtube(post):
    """YouTube via Buffer: max 2 Short al giorno.
    Se il Reel ha "youtube_at" -> si' (a quell'orario); se un altro Reel dello stesso
    giorno ha "youtube_at" -> no. Altrimenti (vecchi file) regola precedente:
    giorni del libro -> reel del libro + primo reel tecnico; altri giorni -> primi 2."""
    if not (post.get("type", "REELS").upper() == "REELS"
            and post.get("channel", "instagram") == "instagram"
            and not post.get("draft") and not post.get("no_youtube")):
        return False
    if post.get("youtube_at"):
        return True
    day = datetime.fromisoformat(post["publish_at"])
    for f in glob.glob("queue/*.json") + glob.glob("scheduled/*.json") + glob.glob("published/*.json"):
        q = json.load(open(f))
        if q.get("youtube_at") and datetime.fromisoformat(q["publish_at"]).date() == day.date():
            return False   # giornata con orari YouTube espliciti: solo i Reel con "youtube_at"
    if is_book(post):
        return True
    if day.weekday() not in BOOK_DAYS:
        return True
    tech = []
    for f in glob.glob("queue/*.json") + glob.glob("scheduled/*.json") + glob.glob("published/*.json"):
        q = json.load(open(f))
        d = datetime.fromisoformat(q["publish_at"])
        if (q.get("type", "REELS").upper() == "REELS" and not is_book(q)
                and q.get("channel", "instagram") == "instagram" and d.date() == day.date()):
            tech.append(q["publish_at"])
    return not tech or post["publish_at"] == min(tech)


def add_youtube(f, post, chans):
    """Carica lo Short gemello; in caso di errore non blocca Instagram."""
    if "youtube" not in chans or post.get("buffer_id_youtube") or not wants_youtube(post):
        return False
    try:
        post["buffer_id_youtube"] = push(youtube_twin(post), chans)
        json.dump(post, open(f, "w"), indent=2, ensure_ascii=False)
        print(f"OK YouTube {f} -> Buffer {post['buffer_id_youtube']}")
        return True
    except Exception as e:
        if "maximum number of posts YouTube allows" in str(e):
            # YouTube via Buffer: max 2 Short al giorno -> questo Reel resta solo su Instagram
            post["no_youtube"] = True
            json.dump(post, open(f, "w"), indent=2, ensure_ascii=False)
            print(f"YouTube: limite 2/giorno raggiunto, {f} solo su Instagram")
        else:
            print(f"ERRORE YouTube {f}: {e}", file=sys.stderr)
        return False


def main():
    now = datetime.now(timezone.utc)
    os.makedirs("scheduled", exist_ok=True)

    # 1) i post gia' in Buffer con orario passato sono stati pubblicati
    in_buffer = 0
    chans = channels()
    for f in sorted(glob.glob("scheduled/*.json")):
        p = json.load(open(f))
        if datetime.fromisoformat(p["publish_at"]) <= now:
            shutil.move(f, os.path.join("published", os.path.basename(f)))
        else:
            in_buffer += 1
            add_youtube(f, p, chans)

    # 2) riempi i posti liberi con i prossimi post della coda
    todo = sorted(glob.glob("queue/*.json"),
                  key=lambda f: json.load(open(f))["publish_at"])
    free = MAX_IN_BUFFER - in_buffer
    print(f"In Buffer: {in_buffer} | posti liberi: {free} | in coda: {len(todo)}")
    if free <= 0 or not todo:
        return
    errors = 0
    for f in todo[:free]:
        post = json.load(open(f))
        if datetime.fromisoformat(post["publish_at"]) < now and not post.get("draft"):
            # orario gia' passato: lo pubblichiamo tra 5 minuti
            post["publish_at"] = (now.replace(microsecond=0) + timedelta(minutes=5)).isoformat()
        try:
            bid = push(post, chans)
            post["buffer_id"] = bid
            json.dump(post, open(f, "w"), indent=2, ensure_ascii=False)
            add_youtube(f, post, chans)
            dest = "published" if post.get("draft") else "scheduled"
            shutil.move(f, os.path.join(dest, os.path.basename(f)))
            print(f"OK {f} -> Buffer {bid} ({'bozza' if post.get('draft') else post['publish_at']})")
        except Exception as e:
            errors += 1
            print(f"ERRORE {f}: {e}", file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
