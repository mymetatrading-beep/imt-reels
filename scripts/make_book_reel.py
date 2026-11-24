#!/usr/bin/env python3
"""IMT Reel LIBRO: python3 make_book_reel.py spec.json out.mp4
Stesso stile dei Reel IMT (sfondo scuro, glow magenta, header, gancio con rimbalzo),
poi copertina del libro, 3 punti chiave e chiusura "LINK IN BIO" con freccia in su."""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
SPEC = json.load(open(sys.argv[1]))
REVIEWS = SPEC.get("reviews", True)   # dal 24/11/2026: scena recensioni Amazon vere (assets/recensioni.json)
DUR = 19.5 if REVIEWS else 16.5
OUT = sys.argv[2] if len(sys.argv) > 2 else "reel.mp4"
WORK = os.path.dirname(os.path.abspath(OUT))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = "/usr/share/fonts/truetype/google-fonts/"
def F(name, size): return ImageFont.truetype(FD + name, size)
BOLD, REG = "Poppins-Bold.ttf", "Poppins-Regular.ttf"

PINK = (255, 60, 172); MAG = (214, 0, 160); WHITE = (245, 245, 250)
GREY = (150, 150, 170); ORANGE = (255, 165, 40); BG = (8, 6, 16)

def ease_out_back(t):
    t = min(max(t, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def ease_out(t):
    t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def clamp(t): return min(max(t, 0), 1)

yy, xx = np.mgrid[0:H, 0:W]
def glow(cx, cy, r, col, k):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    return (np.exp(-d ** 2) * k)[..., None] * np.array(col)[None, None, :]
bg = np.ones((H, W, 3)) * np.array(BG)
bg += glow(W * 0.85, H * 0.12, 700, MAG, 0.55)
bg += glow(W * 0.1, H * 0.85, 800, (120, 0, 200), 0.45)
bg += ((xx % 90 == 0) | (yy % 90 == 0)).astype(float)[..., None] * 10
BG_IMG = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))

COVER = Image.open(os.path.join(ROOT, SPEC.get("cover", "assets/book_cover.jpg"))).convert("RGBA")
def cover_at(width):
    h = int(COVER.height * width / COVER.width)
    return COVER.resize((width, h), Image.LANCZOS)
COV_BIG = cover_at(600)
COV_SMALL = cover_at(380)

def text_center(d, y, txt, font, fill, x=W // 2):
    d.text((x - d.textlength(txt, font=font) / 2, y), txt, font=font, fill=fill)

def fit_font(d, txt, size, maxw):
    while size > 30 and d.textlength(txt, font=F(BOLD, size)) > maxw: size -= 2
    return F(BOLD, size)

def header(d):
    f = F(BOLD, 44); txt = SPEC.get("header", "IMT · ORDER FLOW SMC")
    w = d.textlength(txt, font=f); x0 = (W - w) / 2 - 34; y0 = 120
    d.rounded_rectangle((x0, y0, x0 + w + 68, y0 + 84), radius=42, outline=PINK, width=4)
    text_center(d, y0 + 14, txt, f, PINK)

def bounce_words(layer, words, t0, t, y, size, colors, gap=0.18):
    f = F(BOLD, size); d = ImageDraw.Draw(layer)
    widths = [d.textlength(w_, font=f) for w_ in words]
    space = size * 0.28; x = (W - sum(widths) - space * (len(words) - 1)) / 2
    pos = []
    for i, (wd, ww) in enumerate(zip(words, widths)):
        lt = (t - t0 - i * gap) / 0.35
        if lt > 0:
            s = ease_out_back(lt)
            im = Image.new("RGBA", (int(ww + 40), int(size * 1.5)), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((20, 0), wd, font=f, fill=colors[i])
            sw, sh = max(1, int(im.width * s)), max(1, int(im.height * s))
            im = im.resize((sw, sh), Image.LANCZOS)
            cx = x + ww / 2; cy = y + size * 0.75 - (1 - clamp(lt)) * 60
            layer.alpha_composite(im, (int(cx - sw / 2), int(cy - sh / 2)))
        pos.append((x, ww)); x += ww + space
    return pos

def paste_cover(img, cov, cx, cy, scale, tilt=0.0):
    if scale <= 0.01: return
    c = cov.resize((max(1, int(cov.width * scale)), max(1, int(cov.height * scale))), Image.LANCZOS)
    if tilt: c = c.rotate(tilt, resample=Image.BICUBIC, expand=True)
    # glow rosa dietro la copertina
    halo = Image.new("RGBA", (c.width + 160, c.height + 160), (0, 0, 0, 0))
    ImageDraw.Draw(halo).rounded_rectangle((60, 60, c.width + 100, c.height + 100), radius=30, fill=PINK + (150,))
    halo = halo.filter(ImageFilter.GaussianBlur(40))
    img.alpha_composite(halo, (int(cx - halo.width / 2), int(cy - halo.height / 2)))
    img.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))

# ---------- scene ----------
T_BOOK, T_LIST = 3.5, 8.3
T_REV = 12.0 if REVIEWS else 99
T_CTA = 15.6 if REVIEWS else 12.6
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reviews_card import draw_reviews

def scene_hook(layer, d, t):
    t0 = 0.15
    for row in SPEC["hook"]:
        cols = [PINK if j in row.get("pink", []) else WHITE for j in range(len(row["words"]))]
        sz = row.get("size", 110)
        while sz > 60:
            ff = F(BOLD, sz)
            if sum(d.textlength(w_, font=ff) for w_ in row["words"]) + sz * 0.28 * (len(row["words"]) - 1) <= W - 110: break
            sz -= 4
        pos = bounce_words(layer, row["words"], t0, t, row["y"], sz, cols)
        u = row.get("underline")
        if u is not None and t > t0 + 0.7:
            p = ease_out((t - t0 - 0.7) / 0.4); mx, mw = pos[u]; uy = row["y"] + sz * 1.42
            d.rounded_rectangle((mx, uy, mx + mw * p, uy + 18), radius=9, fill=PINK)
        t0 += 0.25 + 0.18 * len(row["words"])

def scene_book(img, d, t):
    lt = t - T_BOOK
    a = clamp(lt / 0.4)
    f = fit_font(d, SPEC["book_line"], 76, W - 120)
    text_center(d, 280, SPEC["book_line"], f, WHITE + (int(255 * a),))
    p = ease_out_back((lt - 0.3) / 0.6)
    bob = math.sin(lt * 2.2) * 12
    paste_cover(img, COV_BIG, W / 2, 1030 + bob, p, tilt=(1 - clamp(p)) * 12)
    if lt > 1.4:
        q = ease_out((lt - 1.4) / 0.4)
        lab = SPEC.get("badge", "DISPONIBILE SU AMAZON")
        fb = F(BOLD, 44); tw = d.textlength(lab, font=fb)
        x0 = W / 2 - (tw / 2 + 40) * q; x1 = W / 2 + (tw / 2 + 40) * q
        d.rounded_rectangle((x0, 1530, x1, 1620), radius=45, fill=ORANGE)
        if q > 0.8: text_center(d, 1546, lab, fb, (20, 12, 0))

def scene_list(d, t):
    lt = t - T_LIST
    text_center(d, 420, SPEC.get("list_title", "DENTRO TROVI"), fit_font(d, SPEC.get("list_title", "DENTRO TROVI"), 96, W - 100), PINK)
    for i, (a, b, c) in enumerate([tuple(x) for x in SPEC["bullets"]]):
        it = (lt - 0.4 - i * 0.8) / 0.4
        if it <= 0: continue
        off = (1 - ease_out(it)) * 300; alpha = int(255 * clamp(it))
        y = 680 + i * 250; x0 = 70 + off
        d.ellipse((x0, y, x0 + 110, y + 110), fill=MAG + (alpha,))
        fn = F(BOLD, 60); num = str(i + 1)
        d.text((x0 + 55 - d.textlength(num, font=fn) / 2, y + 8), num, font=fn, fill=(255, 255, 255, alpha))
        x = x0 + 135; ff = fit_font(d, a + b + c, 46, W - x - 40)
        for seg, colr in ((a, WHITE), (b, PINK), (c, WHITE)):
            if seg:
                d.text((x, y + 24), seg, font=ff, fill=colr + (alpha,)); x += d.textlength(seg, font=ff)

def scene_cta(img, d, t):
    lt = t - T_CTA
    # freccia che punta in alto (verso la bio)
    bob = math.sin(lt * 8) * 18
    ax, ay = W / 2, 300 + bob
    if lt > 0.2:
        d.polygon([(ax - 55, ay + 70), (ax + 55, ay + 70), (ax, ay)], fill=PINK)
        d.line((ax, ay + 60, ax, ay + 200), fill=PINK, width=16)
    p = ease_out_back(lt / 0.4)
    f = F(BOLD, 124); txt = SPEC.get("cta", "LINK IN BIO")
    im = Image.new("RGBA", (1060, 180), (0, 0, 0, 0)); di = ImageDraw.Draw(im)
    f = fit_font(di, txt, 124, 1020)
    di.text((530 - di.textlength(txt, font=f) / 2, 0), txt, font=f, fill=PINK)
    sw, sh = max(1, int(1060 * p)), max(1, int(180 * p))
    img.alpha_composite(im.resize((sw, sh), Image.LANCZOS), (int(W / 2 - sw / 2), int(620 - sh / 2)))
    if lt > 0.3:
        text_center(d, 720, SPEC.get("cta_sub", "e lo ordini con un tocco"), fit_font(d, SPEC.get("cta_sub", "e lo ordini con un tocco"), 56, W - 100), WHITE)
    paste_cover(img, COV_SMALL, W / 2, 1180, ease_out_back((lt - 0.4) / 0.5))
    text_center(d, 1700, SPEC.get("footer", "Contenuto educativo. Non è consulenza finanziaria."), F(REG, 32), GREY)

def frame(t):
    img = BG_IMG.copy().convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    header(d)
    if t < T_BOOK: scene_hook(layer, d, t)
    elif t < T_LIST: scene_book(img, d, t)
    elif t < min(T_REV, T_CTA): scene_list(d, t)
    elif t < T_CTA: draw_reviews(layer, t - T_REV, y0=330)
    else: scene_cta(img, d, t)
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(18))); img.alpha_composite(layer)
    for st in (T_BOOK, T_LIST, T_REV, T_CTA):
        if st <= t < st + 0.2:
            img.alpha_composite(Image.new("RGBA", (W, H), BG + (int(255 * (1 - (t - st) / 0.2)),)))
    return img.convert("RGB")

# ---------- musica (stessa base energica Am-F-C-G) ----------
SR = 44100
def music():
    n = int(SR * DUR); out = np.zeros(n)
    beat = 0.5; bar = 2.0
    def nf(m): return 440 * 2 ** ((m - 69) / 12)
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]; bass = [45, 41, 36, 43]
    start = 0.15
    for b in range(int(DUR / bar) + 1):
        ch = chords[b % 4]; t0 = start + b * bar
        i0, i1 = int(t0 * SR), min(n, int((t0 + bar) * SR))
        if i0 >= n: break
        tt = np.arange(i1 - i0) / SR; env = np.minimum(1, tt / 0.05) * np.exp(-tt * 0.4)
        for m in ch:
            for det in (-0.08, 0.08):
                out[i0:i1] += 0.05 * env * (2 * ((tt * nf(m + 12) * (1 + det / 100)) % 1) - 1)
        for s in range(16):
            j0 = int((t0 + s * beat / 4) * SR); j1 = min(n, j0 + int(0.12 * SR))
            if j0 >= n: break
            tq = np.arange(j1 - j0) / SR; m = ch[s % 3] + 24 + (12 if s % 8 == 7 else 0)
            out[j0:j1] += 0.06 * np.exp(-tq * 25) * np.sign(np.sin(2 * np.pi * nf(m) * tq))
        for s in range(8):
            j0 = int((t0 + s * beat / 2) * SR); j1 = min(n, j0 + int(0.22 * SR))
            if j0 >= n: break
            tq = np.arange(j1 - j0) / SR
            out[j0:j1] += 0.22 * np.exp(-tq * 8) * np.sin(2 * np.pi * nf(bass[b % 4]) * tq)
    k = 0
    while start + k * beat / 2 < DUR:
        j0 = int((start + k * beat / 2) * SR)
        if k % 2 == 0:
            j1 = min(n, j0 + int(0.3 * SR)); tq = np.arange(j1 - j0) / SR
            out[j0:j1] += 0.6 * np.exp(-tq * 9) * np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-tq * 30)) / SR)
        if k % 4 == 2:
            j1 = min(n, j0 + int(0.2 * SR)); tq = np.arange(j1 - j0) / SR
            out[j0:j1] += 0.25 * np.exp(-tq * 18) * np.random.default_rng(k).normal(0, 1, j1 - j0)
        j1 = min(n, j0 + int(0.04 * SR)); tq = np.arange(j1 - j0) / SR
        out[j0:j1] += 0.07 * np.exp(-tq * 90) * np.random.default_rng(k + 99).normal(0, 1, j1 - j0)
        k += 1
    # colpo quando entra la copertina
    j0 = int((T_BOOK + 0.35) * SR); j1 = min(n, j0 + int(1.0 * SR)); tq = np.arange(j1 - j0) / SR
    out[j0:j1] += 0.6 * np.exp(-tq * 4) * np.sin(2 * np.pi * (40 + 60 * np.exp(-tq * 8)) * tq)
    fo = int(0.8 * SR); out[-fo:] *= np.linspace(1, 0, fo)
    out = np.tanh(out * 1.3) * 0.85
    with wave.open(os.path.join(WORK, "music_book.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())

if os.environ.get("PREVIEW_ONLY"):
    for ts in (2.6, 6.0, 11.5, 14.8, DUR - 1):
        frame(ts).resize((360, 640)).save(OUT.replace(".mp4", f"_p{ts}.png"))
    sys.exit()
music()
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                      "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", os.path.join(WORK, "music_book.wav"),
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                      "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
                     stdin=subprocess.PIPE)
for i in range(int(DUR * FPS)):
    p.stdin.write(frame(i / FPS).tobytes())
p.stdin.close(); p.wait()
print("done")
