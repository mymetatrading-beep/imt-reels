#!/usr/bin/env python3
"""IMT Reel generator parametrico: python3 make_reel.py spec.json out.mp4
Stile modello: Reel #1 (sfondo scuro, glow magenta, header IMT, gancio con rimbalzo,
grafico a candele con colpo/lampo/vibrazione, regola 1-2-3, FOLLOW)."""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 16.5
SPEC = json.load(open(sys.argv[1]))
# v2 (default dal 24/11/2026): gancio leggibile dal PRIMO fotogramma, grafico in
# movimento subito sotto il gancio, durata ~10 s. "version": 1 = vecchio stile 16,5 s.
# v3 (default dal 28/11/2026): stile IMT Liquid Glass rosa/bianco con logo originale
# (scripts/imt_glass.py). "version": 2 = stile v2, "version": 1 = vecchio stile.
VER = SPEC.get("version", 3)
V2 = VER >= 2
V3 = VER >= 3
OUT = sys.argv[2] if len(sys.argv) > 2 else "reel.mp4"
WORK = os.path.dirname(os.path.abspath(OUT))
FD = "/usr/share/fonts/truetype/google-fonts/"
def F(name, size): return ImageFont.truetype(FD + name, size)
BOLD, MED, REG = "Poppins-Bold.ttf", "Poppins-Medium.ttf", "Poppins-Regular.ttf"

PINK = (255, 60, 172); MAG = (214, 0, 160); WHITE = (245, 245, 250)
GREY = (150, 150, 170); RED = (255, 70, 90); GREEN = (40, 220, 150)
BG = (8, 6, 16)

def ease_out_back(t):
    t = min(max(t, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def ease_out(t):
    t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def clamp(t): return min(max(t, 0), 1)

# ---------- background (static, precomputed) ----------
yy, xx = np.mgrid[0:H, 0:W]
def glow(cx, cy, r, col, k):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    g = np.exp(-d ** 2) * k
    return g[..., None] * np.array(col)[None, None, :]
bg = np.ones((H, W, 3)) * np.array(BG)
bg += glow(W * 0.85, H * 0.12, 700, MAG, 0.55)
bg += glow(W * 0.1, H * 0.85, 800, (120, 0, 200), 0.45)
# subtle grid
grid = ((xx % 90 == 0) | (yy % 90 == 0)).astype(float)[..., None] * 10
bg = np.clip(bg + grid, 0, 255).astype(np.uint8)
BG_IMG = Image.fromarray(bg)

def text_center(d, y, txt, font, fill, x=W // 2):
    w = d.textlength(txt, font=font)
    d.text((x - w / 2, y), txt, font=font, fill=fill)

def header(d, t):
    a = clamp(t / 0.4)
    f = F(BOLD, 44)
    txt = "IMT · ORDER FLOW SMC"
    w = d.textlength(txt, font=f)
    x0 = (W - w) / 2 - 34; y0 = 120
    d.rounded_rectangle((x0, y0, x0 + w + 68, y0 + 84), radius=42, outline=PINK, width=4)
    text_center(d, y0 + 14, txt, f, PINK)

def bounce_words(layer, words, t0, t, y, size, colors, gap=0.18):
    """Words pop in one by one with a bounce; returns nothing."""
    f = F(BOLD, size)
    d = ImageDraw.Draw(layer)
    widths = [d.textlength(w_, font=f) for w_ in words]
    space = size * 0.28
    total = sum(widths) + space * (len(words) - 1)
    x = (W - total) / 2
    pos = []
    for i, (wd, ww) in enumerate(zip(words, widths)):
        lt = (t - t0 - i * gap) / 0.35
        if lt > 0:
            s = ease_out_back(lt)
            # render word to its own image, scale it
            im = Image.new("RGBA", (int(ww + 40), int(size * 1.5)), (0, 0, 0, 0))
            di = ImageDraw.Draw(im)
            di.text((20, 0), wd, font=f, fill=colors[i])
            sw, sh = max(1, int(im.width * s)), max(1, int(im.height * s))
            im = im.resize((sw, sh), Image.LANCZOS)
            cx = x + ww / 2; cy = y + size * 0.75 - (1 - clamp(lt)) * 60
            layer.alpha_composite(im, (int(cx - sw / 2), int(cy - sh / 2)))
        pos.append((x, ww))
        x += ww + space
    return pos

# ---------- candle scene (from spec) ----------
CH = SPEC["chart"]
CH_T0, CH_T1 = (0.0, None) if V2 else (3.6, 9.4)
OHLC = [tuple(x) for x in CH["ohlc"]]
C0 = None
STEP = min(0.2, 2.8 / len(OHLC)) if V2 else min(0.25, 4.2 / len(OHLC))
# v2: le prime 3 candele sono gia' disegnate al fotogramma 0 (niente riquadro vuoto)
C0 = -2 * STEP if V2 else 0.4
MARK = CH.get("marker", {}).get("candle")
REV = CH["hit_candle"]
SPIKE = CH.get("spike", False)
HIT = C0 + REV * STEP + 0.17
YMIN, YMAX = CH["yrange"]
LEVEL = CH.get("level")
# tempi delle scene
if V2:
    T_RULES = round(CH_T0 + HIT + 2.2, 2)   # impatto + frase finale ben leggibili
    T_OUTRO = T_RULES + 3.0
    DUR = T_OUTRO + 1.7
else:
    T_RULES, T_OUTRO = 9.5, 14.0

def chart(layer, t):
    d = ImageDraw.Draw(layer)
    lt = t - CH_T0
    box = (90, 560, W - 90, 1380)
    d.rounded_rectangle(box, radius=30, fill=(14, 10, 28, 230), outline=(70, 40, 110), width=3)
    if not V2:
        text_center(d, 430, CH["title"], F(BOLD, 64 if len(CH["title"]) < 24 else 54), WHITE)
    text_center(d, 600, CH["subtitle"], F(BOLD, 46), PINK)
    gx0, gx1, gy0, gy1 = 150, W - 150, 690, 1340
    def py(v): return gy1 - (v - YMIN) / (YMAX - YMIN) * (gy1 - gy0)
    cw = (gx1 - gx0) / len(OHLC)
    hit = lt > HIT
    if LEVEL:
        ly = py(LEVEL["value"])
        lc = (120, 90, 160) if not hit else (90, 60, 120)
        x = gx0
        while x < gx1:
            d.line((x, ly, min(x + 22, gx1), ly), fill=lc, width=4); x += 38
    for i, (o, h, l, c) in enumerate(OHLC):
        ct = lt - (C0 + i * STEP)
        if ct < 0: break
        k = clamp(ct / STEP)
        if i == REV and SPIKE:
            up = h - o > o - l
            ext = h if up else l
            if k < 0.6:
                q = k / 0.6; cc = o + (ext - o) * ease_out(q)
                hh, ll = max(o, cc), min(o, cc)
            else:
                q = (k - 0.6) / 0.4; cc = ext + (c - ext) * ease_out(q)
                hh, ll = (h, min(o, cc)) if up else (max(o, cc), l)
        else:
            cc = o + (c - o) * ease_out(k)
            hh = max(o, cc) + (h - max(o, cc)) * k
            ll = min(o, cc) + (l - min(o, cc)) * k
        col = GREEN if cc >= o else RED
        cx = gx0 + cw * (i + 0.5)
        d.line((cx, py(hh), cx, py(ll)), fill=col, width=4)
        top, bot = py(max(o, cc)), py(min(o, cc))
        if bot - top < 4: bot = top + 4
        d.rectangle((cx - cw * 0.32, top, cx + cw * 0.32, bot), fill=col)
    if LEVEL:
        lab = LEVEL["label"] if not hit else LEVEL.get("label_after", LEVEL["label"])
        fl = F(BOLD, 32); tw = d.textlength(lab, font=fl)
        lx = gx1 - tw - 10 if LEVEL.get("right") else gx0
        lyl = ly + (60 if LEVEL.get("below") else 0)
        d.rounded_rectangle((lx - 12, lyl - 52, lx + tw + 12, lyl - 8), radius=12, fill=(14, 10, 28, 235), outline=(90, 60, 130), width=2)
        d.text((lx, lyl - 48), lab, font=fl, fill=(200, 190, 220) if not hit else RED)
    if MARK is not None:
        M = CH["marker"]
        bt = lt - (C0 + (MARK + 1) * STEP)
        if bt > 0:
            bx = gx0 + cw * (MARK + 0.5); by = py(M["y"])
            p = ease_out_back(bt / 0.3)
            pc = (GREEN if M.get("good", True) else RED) if not hit else RED
            fb = F(BOLD, 34)
            lab = M["label"] if not hit else M.get("label_after", M["label"])
            tw = d.textlength(lab, font=fb)
            x1 = bx - 30; x0 = x1 - (tw + 36) * p
            d.rounded_rectangle((x0, by - 28, x1, by + 28), radius=16, fill=pc)
            if p > 0.8: d.text((x1 - 18 - tw, by - 24), lab, font=fb, fill=WHITE)
            d.polygon([(x1 - 6, by + 8), (x1 + 12, by - 10), (bx - 8, py(OHLC[MARK][3]) - 10)], fill=pc)
    if hit:
        txt = CH["impact"]
        f = F(BOLD, 100 if len(txt) <= 12 else 80)
        p = ease_out_back((lt - HIT) / 0.35)
        im = Image.new("RGBA", (1000, 150), (0, 0, 0, 0))
        di = ImageDraw.Draw(im)
        di.text((500 - di.textlength(txt, font=f) / 2, 5), txt, font=f, fill=RED if CH.get("impact_bad", True) else GREEN)
        sw, sh = int(1000 * p), max(1, int(150 * p))
        if sw > 0:
            im = im.resize((sw, sh), Image.LANCZOS)
            layer.alpha_composite(im, (int(W / 2 - sw / 2), int(1450 - sh / 2 + 40)))
        if lt > HIT + 0.6:
            fa = F(BOLD, 54)
            s1, s2 = CH["punch"]
            w1, w2 = d.textlength(s1, font=fa), d.textlength(s2, font=fa)
            if w1 + w2 > W - 80:
                fa = F(BOLD, 46); w1, w2 = d.textlength(s1, font=fa), d.textlength(s2, font=fa)
            xs = (W - w1 - w2) / 2
            d.text((xs, 1590), s1, font=fa, fill=WHITE)
            d.text((xs + w1, 1590), s2, font=fa, fill=PINK)

def rules(layer, t):
    d = ImageDraw.Draw(layer)
    lt = t - T_RULES
    text_center(d, 470, SPEC.get("rules_title", "THE RULE"), F(BOLD, 96), PINK)
    items = [tuple(x) for x in SPEC["rules"]]
    f = F(BOLD, 46); fn = F(BOLD, 60)
    for i, (a, b, c) in enumerate(items):
        it = ((lt - 0.2 - i * 0.55) / 0.3) if V2 else ((lt - 0.5 - i * 0.9) / 0.4)
        if it <= 0: continue
        off = (1 - ease_out(it)) * 300
        alpha = int(255 * clamp(it))
        y = 700 + i * 230
        x0 = 80 + off
        d.ellipse((x0, y, x0 + 110, y + 110), fill=MAG + (alpha,))
        num = str(i + 1)
        d.text((x0 + 55 - d.textlength(num, font=fn) / 2, y + 8), num, font=fn, fill=(255, 255, 255, alpha))
        x = x0 + 135
        for seg, colr in ((a, WHITE), (b, PINK), (c, WHITE)):
            if seg:
                ff = f if d.textlength(a + b + c, font=f) < W - x0 - 160 else F(BOLD, 38)
                d.text((x, y + 22 + (4 if ff is not f else 0)), seg, font=ff, fill=colr + (alpha,))
                x += d.textlength(seg, font=ff); continue
                x += d.textlength(seg, font=f)

def outro(layer, t):
    d = ImageDraw.Draw(layer)
    lt = t - T_OUTRO
    p = ease_out_back(lt / 0.4)
    f = F(BOLD, 110)
    im = Image.new("RGBA", (1000, 160), (0, 0, 0, 0))
    di = ImageDraw.Draw(im)
    di.text((500 - di.textlength("FOLLOW", font=f) / 2, 0), "FOLLOW", font=f, fill=PINK)
    sw, sh = max(1, int(1000 * p)), max(1, int(160 * p))
    layer.alpha_composite(im.resize((sw, sh), Image.LANCZOS), (int(W / 2 - sw / 2), int(780 - sh / 2)))
    if lt > (0.15 if V2 else 0.3):
        text_center(d, 880, SPEC.get("cta", "for tomorrow's rule"), F(BOLD, 64), WHITE)
    if lt > (0.3 if V2 else 0.6):
        bob = math.sin(lt * 8) * 18
        ax, ay = W / 2, 1080 + bob
        d.line((ax, ay, ax, ay + 150), fill=PINK, width=14)
        d.polygon([(ax - 50, ay + 120), (ax + 50, ay + 120), (ax, ay + 190)], fill=PINK)
    text_center(d, 1700, "Educational content. Not financial advice.", F(REG, 34), GREY)

def hook_static(layer, d, t):
    """Gancio v2: tutto leggibile dal fotogramma 0, piccolo 'punch' iniziale, parole
    rosa e sottolineatura gia' presenti. Sta sopra il grafico (y 240-540)."""
    rows = SPEC["hook"]
    sizes = []
    for row in rows:
        sz = min(row.get("size", 96), 96 if len(rows) < 3 else 74)
        while sz > 52:
            ff = F(BOLD, sz)
            tot = sum(d.textlength(w_, font=ff) for w_ in row["words"]) + sz * 0.28 * (len(row["words"]) - 1)
            if tot <= W - 110: break
            sz -= 4
        sizes.append(sz)
    total_h = sum(int(sz * 1.3) for sz in sizes)
    y = 230 + max(0, (300 - total_h) // 2)
    s = 1 + 0.08 * (1 - ease_out(t / 0.35))          # punch-in iniziale
    im = Image.new("RGBA", (W, 330), (0, 0, 0, 0)); di = ImageDraw.Draw(im)
    yy0 = y - 240
    for row, sz in zip(rows, sizes):
        ff = F(BOLD, sz); sp = sz * 0.28
        ws = [di.textlength(w_, font=ff) for w_ in row["words"]]
        x = (W - sum(ws) - sp * (len(ws) - 1)) / 2
        for j, (w_, ww) in enumerate(zip(row["words"], ws)):
            pink = j in row.get("pink", [])
            di.text((x, yy0), w_, font=ff, fill=PINK if pink else WHITE)
            if row.get("underline") == j:
                di.rounded_rectangle((x, yy0 + sz * 1.18, x + ww, yy0 + sz * 1.18 + 12), radius=6, fill=PINK)
            x += ww + sp
        yy0 += int(sz * 1.3)
    if s != 1:
        im = im.resize((int(W * s), int(330 * s)), Image.LANCZOS)
    layer.alpha_composite(im, (int(W / 2 - im.width / 2), int(240 + 165 - im.height / 2)))


def frame(t):
    img = BG_IMG.copy().convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    header(d, t)
    shake = (0, 0)
    if V2 and t < T_RULES:
        hook_static(layer, d, t)
        chart(layer, t)
        lt = t - CH_T0
        if HIT < lt < HIT + 0.5:
            k = (HIT + 0.5 - lt) / 0.5
            shake = (int(math.sin(lt * 90) * 22 * k), int(math.cos(lt * 70) * 16 * k))
    elif V2 and t < T_OUTRO:
        rules(layer, t)
    elif V2:
        outro(layer, t)
    elif t < 3.5:
        t0 = 0.15
        for row in SPEC["hook"]:
            cols = [PINK if j in row.get("pink", []) else WHITE for j in range(len(row["words"]))]
            sz = row.get("size", 110)
            while sz > 60:
                ff = F(BOLD, sz)
                tot = sum(d.textlength(w_, font=ff) for w_ in row["words"]) + sz * 0.28 * (len(row["words"]) - 1)
                if tot <= W - 110: break
                sz -= 4
            pos = bounce_words(layer, row["words"], t0, t, row["y"], sz, cols,
                               gap=row.get("gap", 0.18))
            u = row.get("underline")
            if u is not None and t > t0 + 0.7:
                p = ease_out((t - t0 - 0.7) / 0.4)
                mx, mw = pos[u]
                uy = row["y"] + sz * 1.42
                d.rounded_rectangle((mx, uy, mx + mw * p, uy + 18), radius=9, fill=PINK)
            t0 += 0.25 + 0.18 * len(row["words"])
    elif t < 9.5:
        chart(layer, t)
        lt = t - CH_T0
        if HIT < lt < HIT + 0.5:
            k = (HIT + 0.5 - lt) / 0.5
            shake = (int(math.sin(lt * 90) * 22 * k), int(math.cos(lt * 70) * 16 * k))
    elif t < 14.0:
        rules(layer, t)
    else:
        outro(layer, t)
    # glow pass for text
    g = layer.filter(ImageFilter.GaussianBlur(18))
    img.alpha_composite(g); img.alpha_composite(layer)
    if shake != (0, 0):
        img = img.transform(img.size, Image.AFFINE, (1, 0, -shake[0], 0, 1, -shake[1]))
    # flash on hit
    lt = t - CH_T0
    if HIT < lt < HIT + 0.3:
        a = int(170 * (1 - (lt - HIT) / 0.3))
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 40, 80, a)))
    # scene fade-in
    for st in ((T_RULES, T_OUTRO) if V2 else (3.5, 9.5, 14.0)):
        if st <= t < st + 0.2:
            a = int(255 * (1 - (t - st) / 0.2))
            img.alpha_composite(Image.new("RGBA", (W, H), BG + (a,)))
    return img.convert("RGB")

if V3:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from reel_v3 import install
    frame = install(globals())

# ---------- music ----------
SR = 44100
def music():
    n = int(SR * DUR); out = np.zeros(n)
    t_all = np.arange(n) / SR
    bpm = 120; beat = 60 / bpm; bar = beat * 4
    def nf(m): return 440 * 2 ** ((m - 69) / 12)
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    bass = [45, 41, 36, 43]
    start = 0.0 if V2 else 0.15
    # pads
    for b in range(int(DUR / bar) + 1):
        ch = chords[b % 4]; t0 = start + b * bar
        i0, i1 = int(t0 * SR), min(n, int((t0 + bar) * SR))
        if i0 >= n: break
        tt = np.arange(i1 - i0) / SR
        env = np.minimum(1, tt / 0.05) * np.exp(-tt * 0.4)
        for m in ch:
            for det in (-0.08, 0.08):
                f = nf(m + 12) * (1 + det / 100)
                out[i0:i1] += 0.05 * env * (2 * ((tt * f) % 1) - 1)
        # arpeggio 16ths
        for s in range(16):
            ts = t0 + s * beat / 4
            j0 = int(ts * SR); j1 = min(n, j0 + int(0.12 * SR))
            if j0 >= n: break
            m = ch[s % 3] + 24 + (12 if s % 8 == 7 else 0)
            tq = np.arange(j1 - j0) / SR
            out[j0:j1] += 0.06 * np.exp(-tq * 25) * np.sign(np.sin(2 * np.pi * nf(m) * tq))
        # bass 8ths
        for s in range(8):
            ts = t0 + s * beat / 2
            j0 = int(ts * SR); j1 = min(n, j0 + int(0.22 * SR))
            if j0 >= n: break
            tq = np.arange(j1 - j0) / SR
            out[j0:j1] += 0.22 * np.exp(-tq * 8) * np.sin(2 * np.pi * nf(bass[b % 4]) * tq)
    # drums
    k = 0
    while True:
        ts = start + k * beat / 2
        if ts >= DUR: break
        j0 = int(ts * SR)
        if k % 2 == 0:  # kick each beat
            j1 = min(n, j0 + int(0.3 * SR)); tq = np.arange(j1 - j0) / SR
            f = 50 + 120 * np.exp(-tq * 30)
            out[j0:j1] += 0.6 * np.exp(-tq * 9) * np.sin(2 * np.pi * np.cumsum(f) / SR)
        if k % 4 == 2:  # clap
            j1 = min(n, j0 + int(0.2 * SR)); tq = np.arange(j1 - j0) / SR
            out[j0:j1] += 0.25 * np.exp(-tq * 18) * np.random.default_rng(k).normal(0, 1, j1 - j0)
        j1 = min(n, j0 + int(0.04 * SR)); tq = np.arange(j1 - j0) / SR  # hat
        out[j0:j1] += 0.07 * np.exp(-tq * 90) * np.random.default_rng(k + 99).normal(0, 1, j1 - j0)
        k += 1
    # thud on each loss
    for x in [C0 + i * STEP for i in CH.get("thuds", [])]:
        j0 = int((CH_T0 + x) * SR); j1 = min(n, j0 + int(0.25 * SR)); tq = np.arange(j1 - j0) / SR
        out[j0:j1] += 0.35 * np.exp(-tq * 14) * np.sin(2 * np.pi * (90 + 120 * np.exp(-tq * 25)) * tq)
    # impact on the big hit
    hit = CH_T0 + HIT; j0 = int(hit * SR); j1 = min(n, j0 + int(1.2 * SR)); tq = np.arange(j1 - j0) / SR
    out[j0:j1] += 0.7 * np.exp(-tq * 4) * np.sin(2 * np.pi * (40 + 60 * np.exp(-tq * 8)) * tq)
    out[j0:j1] += 0.3 * np.exp(-tq * 6) * np.random.default_rng(1).normal(0, 1, j1 - j0)
    # fade out
    fo = int(0.8 * SR); out[-fo:] *= np.linspace(1, 0, fo)
    out = np.tanh(out * 1.3) * 0.85
    pcm = (out * 32767).astype(np.int16)
    with wave.open(os.path.join(WORK, "music.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

if V2 and SPEC.get("music") != "classic":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import music_v2
    style = SPEC.get("music") or "dark_trap"   # scelto dall'utente il 24/11/2026
    music_v2.render(os.path.join(WORK, "music.wav"), DUR, CH_T0 + HIT,
                    [CH_T0 + C0 + i * STEP for i in CH.get("thuds", [])], T_RULES, T_OUTRO,
                    style=style, seed=sum(map(ord, os.path.basename(OUT))))
else:
    music()
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                      "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", os.path.join(WORK, "music.wav"),
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                      "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
                     stdin=subprocess.PIPE)
for i in range(int(DUR * FPS)):
    p.stdin.write(frame(i / FPS).tobytes())
p.stdin.close(); p.wait()
if os.environ.get("PREVIEW"):
    for ts in ((0.0, CH_T0 + HIT + 0.3, T_RULES + 2.5, T_OUTRO + 1.0) if V2 else (3.2, 9.0, 13.5)):
        frame(ts).resize((360, 640)).save(OUT.replace(".mp4", f"_p{ts}.png"))
print("done")
