#!/usr/bin/env python3
"""Pubblica su Instagram (API con login Instagram) i post in coda la cui ora e' arrivata.

Coda: queue/*.json, un file per post:
{
  "publish_at": "2026-11-23T08:00:00+01:00",
  "type": "REELS",                       # REELS | IMAGE | CAROUSEL | STORIES
  "media": ["reels/2026-11-23-tema.mp4"], # percorsi nel repo o URL completi
  "caption": "testo..."
}
Dopo la pubblicazione il file viene spostato in published/ con l'ID del post.
Variabili d'ambiente: IG_TOKEN, IG_USER_ID, GITHUB_REPOSITORY.
"""
import glob, json, os, shutil, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

API = "https://graph.instagram.com/v23.0"
TOKEN = os.environ["IG_TOKEN"]
USER = os.environ["IG_USER_ID"]
REPO = os.environ.get("GITHUB_REPOSITORY", "mymetatrading-beep/imt-reels")
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"


def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode()}")


def url_of(m):
    return m if m.startswith("http") else RAW + m


def wait_ready(cid):
    for _ in range(60):  # max ~10 minuti
        st = call("GET", cid, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid}: {st}")
        time.sleep(10)
    raise RuntimeError(f"container {cid}: timeout")


def container(kind, media, caption=None, child=False):
    p = {}
    is_video = media.lower().endswith((".mp4", ".mov"))
    if kind == "STORIES":
        p["media_type"] = "STORIES"
    elif is_video:
        p["media_type"] = "REELS" if not child else "VIDEO"
        if not child:
            p["share_to_feed"] = "true"
    if is_video:
        p["video_url"] = url_of(media)
    else:
        p["image_url"] = url_of(media)
    if child:
        p["is_carousel_item"] = "true"
    if caption and kind != "STORIES":
        p["caption"] = caption
    cid = call("POST", f"{USER}/media", **p)["id"]
    wait_ready(cid)
    return cid


def publish(post):
    kind = post.get("type", "REELS").upper()
    media, caption = post["media"], post.get("caption", "")
    if kind == "CAROUSEL":
        kids = [container(kind, m, child=True) for m in media]
        cid = call("POST", f"{USER}/media", media_type="CAROUSEL",
                   children=",".join(kids), caption=caption)["id"]
        wait_ready(cid)
    else:
        cid = container(kind, media[0], caption)
    return call("POST", f"{USER}/media_publish", creation_id=cid)["id"]


def main():
    now = datetime.now(timezone.utc)
    errors = 0
    for f in sorted(glob.glob("queue/*.json")):
        post = json.load(open(f))
        when = datetime.fromisoformat(post["publish_at"])
        if when > now:
            continue
        try:
            pid = publish(post)
            post["published_id"] = pid
            post["published_at"] = now.isoformat()
            json.dump(post, open(f, "w"), indent=2, ensure_ascii=False)
            shutil.move(f, os.path.join("published", os.path.basename(f)))
            print(f"OK {f} -> post {pid}")
        except Exception as e:
            errors += 1
            print(f"ERRORE {f}: {e}", file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
