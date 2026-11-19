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
        return json.load(open(CHANNELS_CACHE))
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


def main():
    now = datetime.now(timezone.utc)
    os.makedirs("scheduled", exist_ok=True)

    # 1) i post gia' in Buffer con orario passato sono stati pubblicati
    in_buffer = 0
    for f in sorted(glob.glob("scheduled/*.json")):
        p = json.load(open(f))
        if datetime.fromisoformat(p["publish_at"]) <= now:
            shutil.move(f, os.path.join("published", os.path.basename(f)))
        else:
            in_buffer += 1

    # 2) riempi i posti liberi con i prossimi post della coda
    todo = sorted(glob.glob("queue/*.json"),
                  key=lambda f: json.load(open(f))["publish_at"])
    free = MAX_IN_BUFFER - in_buffer
    print(f"In Buffer: {in_buffer} | posti liberi: {free} | in coda: {len(todo)}")
    if free <= 0 or not todo:
        return
    chans = channels()
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
            dest = "published" if post.get("draft") else "scheduled"
            shutil.move(f, os.path.join(dest, os.path.basename(f)))
            print(f"OK {f} -> Buffer {bid} ({'bozza' if post.get('draft') else post['publish_at']})")
        except Exception as e:
            errors += 1
            print(f"ERRORE {f}: {e}", file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
