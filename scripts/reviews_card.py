"""Scena "recensioni" riusabile (Reel e storie del libro).
draw_reviews(layer, lt, y0=..., title=True): disegna titolo + stelle + 3 card che entrano una alla volta.
lt = secondi dall'inizio della scena. Le recensioni stanno in assets/recensioni.json (solo recensioni vere)."""
import json, math, os
from PIL import ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = "/usr/share/fonts/truetype/google-fonts/Poppins-%s.ttf"
def F(s, n): return ImageFont.truetype(FD % s, n)
PINK = (255, 60, 172); WHITE = (245, 245, 250); GREY = (185, 178, 204); GOLD = (255, 200, 50)
W = 1080
DATA = json.load(open(os.path.join(ROOT, "assets", "recensioni.json")))
def _e(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def _back(x):
    x = min(max(x, 0), 1); c = 1.70158; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def star(d, cx, cy, r, col):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=col)
def wrap(d, txt, font, maxw):
    out, line = [], ""
    for w in txt.split():
        t = (line + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: line = t
        else: out.append(line); line = w
    out.append(line); return out
def draw_reviews(layer, lt, y0=330, title=True, n=3):
    d = ImageDraw.Draw(layer)
    if title:
        a = _e(lt / 0.4)
        f = F("Bold", 76); txt = "COSA DICONO"
        d.text((W / 2, y0), txt, font=f, fill=WHITE + (int(255 * a),), anchor="mm")
        d.text((W / 2, y0 + 92), "I LETTORI", font=f, fill=PINK + (int(255 * a),), anchor="mm")
        for i in range(5):
            s = _back((lt - 0.3 - i * 0.08) / 0.35) * 30
            if s > 0: star(d, W / 2 - 160 + i * 80, y0 + 200, s, GOLD)
        d.text((W / 2, y0 + 262), DATA.get("rating_label", ""), font=F("Medium", 36), fill=GREY + (int(255 * _e((lt - 0.7) / 0.4)),), anchor="mm")
        y = y0 + 340
    else:
        y = y0
    for k, r in enumerate(DATA["reviews"][:n]):
        t0 = 0.9 + k * 0.75; a = _e((lt - t0) / 0.45)
        if a <= 0: continue
        fq = F("Medium", 40); lines = wrap(d, "“" + r["text"] + "”", fq, 860)
        h = 70 + len(lines) * 52 + 50
        x = 70 + (1 - a) * 260
        d.rounded_rectangle((x, y, x + 940, y + h), radius=30, fill=(255, 255, 255, int(26 * a)), outline=GOLD + (int(170 * a),), width=3)
        for i in range(r.get("stars", 5)): star(d, x + 50 + i * 40, y + 40, 15, GOLD + (int(255 * a),))
        d.text((x + 260, y + 40), "Acquisto verificato", font=F("Medium", 28), fill=GREY + (int(255 * a),), anchor="lm")
        for i, ln in enumerate(lines):
            d.text((x + 40, y + 80 + i * 52), ln, font=fq, fill=WHITE + (int(255 * a),))
        d.text((x + 900, y + h - 30), "— " + r["name"], font=F("Bold", 32), fill=PINK + (int(255 * a),), anchor="rm")
        y += h + 28
    return y
