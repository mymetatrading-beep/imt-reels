#!/usr/bin/env python3
"""IMT grafiche statiche: caroselli (1080x1350) e storie (1080x1920).

  python3 make_static.py specs/X.json out_dir/

spec:
{
  "format": "carousel" | "story",
  "slides": [ ...vedi tipi sotto... ],
  "caption": "..."            # solo carosello
}
Tipi di slide:
  cover   {"kicker", "title": [righe], "pink": [indici righe rosa], "sub"}
  point   {"num", "title", "body", "footprint"?: {...}, "tip"?}
  rule    {"title", "items": [[a, KEY, c], ...]}
  cta     {"title", "sub"}
  quiz    {"kicker", "question", "options": [...], "footer"}
  answer  {"kicker", "correct": "B", "answer", "explain", "footer"}
footprint: {"rows": [[prezzo, bid, ask], ...] dall'alto in basso,
            "buy_imb": [indici righe con ask in evidenza],
            "sell_imb": [indici righe con bid in evidenza],
            "poc": indice, "label": "testo sotto"}
Solo caratteri presenti in Poppins (niente emoji / frecce speciali).
"""
import json, os, sys, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FD = "/usr/share/fonts/truetype/google-fonts/"
def F(name, size): return ImageFont.truetype(FD + name, size)
BOLD, MED, REG = "Poppins-Bold.ttf", "Poppins-Medium.ttf", "Poppins-Regular.ttf"
PINK = (255, 60, 172); MAG = (214, 0, 160); WHITE = (245, 245, 250)
GREY = (150, 150, 170); RED = (255, 70, 90); GREEN = (40, 220, 150)
BG = (8, 6, 16); PANEL = (14, 10, 28)


def background(W, H, seed=0):
    yy, xx = np.mgrid[0:H, 0:W]
    def glow(cx, cy, r, col, k):
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        return (np.exp(-d ** 2) * k)[..., None] * np.array(col)[None, None, :]
    bg = np.ones((H, W, 3)) * np.array(BG)
    pts = [(0.85, 0.12), (0.15, 0.2), (0.8, 0.8)][seed % 3]
    bg += glow(W * pts[0], H * pts[1], 650, MAG, 0.55)
    bg += glow(W * (1 - pts[0]), H * (1 - pts[1] * 0.3), 750, (120, 0, 200), 0.45)
    grid = ((xx % 90 == 0) | (yy % 90 == 0)).astype(float)[..., None] * 10
    return Image.fromarray(np.clip(bg + grid, 0, 255).astype(np.uint8)).convert("RGBA")


def center(d, W, y, txt, font, fill):
    d.text(((W - d.textlength(txt, font=font)) / 2, y), txt, font=font, fill=fill)


def wrap(d, txt, font, maxw):
    words, lines, cur = txt.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def header(d, W, y=70):
    f = F(BOLD, 36); txt = "IMT · ORDER FLOW SMC"
    w = d.textlength(txt, font=f); x0 = (W - w) / 2 - 28
    d.rounded_rectangle((x0, y, x0 + w + 56, y + 70), radius=35, outline=PINK, width=3)
    center(d, W, y + 12, txt, f, PINK)


def footer(d, W, H, page, total):
    f = F(MED, 28)
    d.text((70, H - 80), "@institutionalmetatrading", font=f, fill=GREY)
    if total:
        t = f"{page}/{total}"
        d.text((W - 70 - d.textlength(t, font=f), H - 80), t, font=f, fill=GREY)


def fit_lines(d, lines, maxw, size, min_size=60):
    while size > min_size and max(d.textlength(l, font=F(BOLD, size)) for l in lines) > maxw:
        size -= 4
    return size


def draw_footprint(d, box, fp):
    x0, y0, x1, y1 = box
    rows = fp["rows"]; n = len(rows)
    d.rounded_rectangle(box, radius=24, fill=PANEL + (235,), outline=(70, 40, 110), width=3)
    rh = (y1 - y0 - 60) / n
    fpx, fn = F(MED, 30), F(BOLD, 34)
    cx = (x0 + x1) / 2
    d.text((x0 + 30, y0 + 18), "PRICE", font=F(MED, 22), fill=GREY)
    d.text((cx - 150, y0 + 18), "BID", font=F(MED, 22), fill=GREY)
    d.text((cx + 90, y0 + 18), "ASK", font=F(MED, 22), fill=GREY)
    for i, (p, b, a) in enumerate(rows):
        y = y0 + 50 + i * rh
        if i == fp.get("poc"):
            d.rectangle((x0 + 20, y + 2, x1 - 20, y + rh - 2), outline=PINK, width=3)
        d.text((x0 + 30, y + rh / 2 - 18), str(p), font=fpx, fill=GREY)
        bcol, acol = WHITE, WHITE
        if i in fp.get("sell_imb", []):
            d.rectangle((cx - 190, y + 6, cx - 10, y + rh - 6), fill=(120, 20, 45))
            bcol = RED
        if i in fp.get("buy_imb", []):
            d.rectangle((cx + 10, y + 6, cx + 190, y + rh - 6), fill=(10, 90, 65))
            acol = GREEN
        bt, at = str(b), str(a)
        d.text((cx - 30 - d.textlength(bt, font=fn), y + rh / 2 - 20), bt, font=fn, fill=bcol)
        d.text((cx - 4, y + rh / 2 - 20), "x", font=F(REG, 28), fill=GREY)
        d.text((cx + 30, y + rh / 2 - 20), at, font=fn, fill=acol)
    if fp.get("label"):
        f = F(BOLD, 30)
        d.text(((x0 + x1 - d.textlength(fp["label"], font=f)) / 2, y1 + 18), fp["label"], font=f, fill=PINK)


def render(slide, W, H, page, total, seed):
    img = background(W, H, seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    header(d, W)
    k = slide["kind"]
    story = H > 1500
    top = 330 if story else 230
    if k == "cover":
        f = F(BOLD, 40); center(d, W, top, slide.get("kicker", ""), f, GREY)
        lines = slide["title"]
        size = fit_lines(d, lines, W - 140, 120)
        y = top + 110
        for i, l in enumerate(lines):
            center(d, W, y, l, F(BOLD, size), PINK if i in slide.get("pink", []) else WHITE)
            y += size * 1.2
        if slide.get("sub"):
            y += 30
            for l in wrap(d, slide["sub"], F(MED, 44), W - 200):
                center(d, W, y, l, F(MED, 44), GREY); y += 60
        if not story:
            t = "SWIPE  >>>"; ft = F(BOLD, 40)
            center(d, W, H - 200, t, ft, PINK)
    elif k == "point":
        r = 70
        d.ellipse((80, top, 80 + 2 * r, top + 2 * r), fill=MAG)
        n = str(slide["num"]); fn = F(BOLD, 80)
        d.text((80 + r - d.textlength(n, font=fn) / 2, top + 18), n, font=fn, fill=WHITE)
        ft = F(BOLD, 64)
        tl = wrap(d, slide["title"], ft, W - 330)
        ty = top + r - len(tl) * 38
        for l in tl:
            d.text((250, ty), l, font=ft, fill=WHITE); ty += 76
        y = top + 2 * r + 50
        fb = F(MED, 42)
        for l in wrap(d, slide["body"], fb, W - 160):
            d.text((80, y), l, font=fb, fill=(220, 215, 235)); y += 60
        if slide.get("footprint"):
            hgt = min(H - 200 - (y + 40), 90 * len(slide["footprint"]["rows"]) + 60)
            draw_footprint(d, (140, y + 40, W - 140, y + 40 + hgt), slide["footprint"])
            y += 40 + hgt + 70
        if slide.get("tip"):
            ft2 = F(BOLD, 40)
            tl2 = wrap(d, slide["tip"], ft2, W - 220)
            hh = 50 + 56 * len(tl2)
            yb = max(y + 20, H - 200 - hh) if not slide.get("footprint") else y
            d.rounded_rectangle((80, yb, W - 80, yb + hh), radius=24, fill=(60, 10, 60, 230), outline=PINK, width=3)
            yy = yb + 25
            for l in tl2:
                center(d, W, yy, l, ft2, WHITE); yy += 56
    elif k == "rule":
        center(d, W, top, slide.get("title", "THE RULE"), F(BOLD, 96), PINK)
        f = F(BOLD, 46)
        for i, (a, b, c) in enumerate(slide["items"]):
            y = top + 220 + i * 210
            d.ellipse((80, y, 190, y + 110), fill=MAG)
            n = str(i + 1); fn = F(BOLD, 60)
            d.text((135 - d.textlength(n, font=fn) / 2, y + 8), n, font=fn, fill=WHITE)
            ff = f if d.textlength(a + b + c, font=f) < W - 300 else F(BOLD, 38)
            x = 215
            for seg, col in ((a, WHITE), (b, PINK), (c, WHITE)):
                if seg:
                    d.text((x, y + 28), seg, font=ff, fill=col); x += d.textlength(seg, font=ff)
    elif k == "cta":
        center(d, W, H / 2 - 260, slide.get("title", "FOLLOW"), F(BOLD, 120), PINK)
        y = H / 2 - 90
        for l in wrap(d, slide.get("sub", ""), F(BOLD, 52), W - 200):
            center(d, W, y, l, F(BOLD, 52), WHITE); y += 70
        center(d, W, y + 60, "SAVE  ·  SHARE  ·  FOLLOW", F(BOLD, 40), GREY)
        center(d, W, H - 170, "Educational content. Not financial advice.", F(REG, 30), GREY)
    elif k in ("quiz", "answer"):
        center(d, W, top, slide.get("kicker", "QUIZ"), F(BOLD, 56), PINK)
        y = top + 130
        if k == "quiz":
            fq = F(BOLD, 64)
            for l in wrap(d, slide["question"], fq, W - 160):
                center(d, W, y, l, fq, WHITE); y += 84
            y += 60
            fo = F(BOLD, 46)
            for i, o in enumerate(slide["options"]):
                lab = "ABCD"[i]
                ol = wrap(d, o, fo, W - 330)
                hh = 60 + 58 * len(ol)
                d.rounded_rectangle((90, y, W - 90, y + hh), radius=30, fill=PANEL + (235,), outline=(110, 60, 160), width=3)
                d.ellipse((120, y + hh / 2 - 45, 210, y + hh / 2 + 45), fill=MAG)
                d.text((165 - d.textlength(lab, font=F(BOLD, 52)) / 2, y + hh / 2 - 36), lab, font=F(BOLD, 52), fill=WHITE)
                yy = y + 30
                for l in ol:
                    d.text((245, yy), l, font=fo, fill=WHITE); yy += 58
                y += hh + 34
        else:
            center(d, W, y, f"Answer: {slide['correct']}", F(BOLD, 110), GREEN); y += 170
            fa = F(BOLD, 58)
            for l in wrap(d, slide["answer"], fa, W - 160):
                center(d, W, y, l, fa, WHITE); y += 78
            y += 50
            fe = F(MED, 44)
            for l in wrap(d, slide["explain"], fe, W - 180):
                center(d, W, y, l, fe, (220, 215, 235)); y += 62
        if slide.get("footer"):
            ff = F(BOLD, 44)
            fl = wrap(d, slide["footer"], ff, W - 240)
            yb = H - 330 - 60 * len(fl)
            d.rounded_rectangle((100, yb, W - 100, yb + 50 + 60 * len(fl)), radius=30, fill=(60, 10, 60, 230), outline=PINK, width=3)
            yy = yb + 25
            for l in fl:
                center(d, W, yy, l, ff, WHITE); yy += 60
    if not story:
        footer(d, W, H, page, total)
    g = layer.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(g); img.alpha_composite(layer)
    return img.convert("RGB")


def main():
    spec = json.load(open(sys.argv[1]))
    out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    W, H = (1080, 1350) if spec["format"] == "carousel" else (1080, 1920)
    n = len(spec["slides"]); paths = []
    for i, s in enumerate(spec["slides"]):
        p = os.path.join(out, f"{name}-{i + 1:02d}.jpg")
        render(s, W, H, i + 1, n if spec["format"] == "carousel" else 0, i).save(p, quality=92)
        paths.append(p)
    print("\n".join(paths))


if __name__ == "__main__":
    main()
