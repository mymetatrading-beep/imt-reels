#!/usr/bin/env python3
"""IMT Reel - '70% win rate... and still LOSING?' (risk:reward)"""
import math, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 16.5
OUT = sys.argv[1] if len(sys.argv) > 1 else "reel01.mp4"
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

# ---------- numeric scene: 70% win rate, negative P&L ----------
CH_T0, CH_T1 = 3.6, 9.4
TRADES = [100, 100, -300, 100, 100, 100, -300, 100, 100, -300]
C0, STEP = 0.4, 0.42
LOSSES = [i for i, v in enumerate(TRADES) if v < 0]
HIT = C0 + 9 * STEP + 0.2       # impact: last loss pushes the account red

def chart(layer, t):
    d = ImageDraw.Draw(layer)
    lt = t - CH_T0
    box = (90, 560, W - 90, 1380)
    d.rounded_rectangle(box, radius=30, fill=(14, 10, 28, 230), outline=(70, 40, 110), width=3)
    text_center(d, 430, "7 wins. 3 losses.", F(BOLD, 70), WHITE)
    text_center(d, 600, "But every win is tiny\u2026", F(BOLD, 46), PINK)
    gx0, gx1, gy0, gy1 = 150, W - 150, 760, 1330
    def py(v): return 980 - v * 1.1
    cw = (gx1 - gx0) / len(TRADES)
    zy = py(0)
    x = gx0
    while x < gx1:
        d.line((x, zy, min(x + 22, gx1), zy), fill=(120, 90, 160), width=3); x += 38
    eq = [0.0]; wins = losses = 0; cur = 0.0
    pts = [(gx0, zy)]
    for i, v in enumerate(TRADES):
        ct = lt - (C0 + i * STEP)
        if ct < 0: break
        k = ease_out(clamp(ct / 0.3))
        val = v * k
        col = GREEN if v > 0 else RED
        cx = gx0 + cw * (i + 0.5)
        y1 = py(val)
        d.rectangle((cx - cw * 0.3, min(zy, y1), cx + cw * 0.3, max(zy, y1) + (0 if v > 0 else 0)), fill=col)
        fl = F(BOLD, 25)
        if k > 0.9:
            lab = ("+" if v > 0 else "\u2212") + str(abs(v))
            tw = d.textlength(lab, font=fl)
            d.text((cx - tw / 2, (y1 - 40) if v > 0 else (y1 + 6)), lab, font=fl, fill=col)
        cur += val
        if k > 0.5:
            if v > 0: wins += 1
            else: losses += 1
        pts.append((cx, py(cur)))
    if len(pts) > 1:
        d.line(pts, fill=WHITE, width=5, joint="curve")
        ex, ey = pts[-1]
        d.ellipse((ex - 11, ey - 11, ex + 11, ey + 11), fill=PINK)
    fc = F(BOLD, 40)
    d.text((gx0 - 20, 670), f"W {wins} \u00b7 L {losses}", font=fc, fill=GREY)
    pl = int(round(cur))
    lab = ("P&L +$" if pl >= 0 else "P&L \u2212$") + str(abs(pl))
    d.text((gx1 + 20 - d.textlength(lab, font=fc), 670), lab, font=fc, fill=GREEN if pl >= 0 else RED)
    if lt > HIT:
        f = F(BOLD, 110)
        p = ease_out_back((lt - HIT) / 0.35)
        im = Image.new("RGBA", (980, 160), (0, 0, 0, 0))
        di = ImageDraw.Draw(im)
        txt = "NET: \u2212$200"
        di.text((490 - di.textlength(txt, font=f) / 2, 5), txt, font=f, fill=RED)
        sw, sh = int(980 * p), max(1, int(160 * p))
        if sw > 0:
            im = im.resize((sw, sh), Image.LANCZOS)
            layer.alpha_composite(im, (int(W / 2 - sw / 2), int(1450 - sh / 2 + 40)))
        if lt > HIT + 0.6:
            fa = F(BOLD, 54)
            s1, s2 = "Small wins. ", "BIG losses."
            w1, w2 = d.textlength(s1, font=fa), d.textlength(s2, font=fa)
            xs = (W - w1 - w2) / 2
            d.text((xs, 1590), s1, font=fa, fill=WHITE)
            d.text((xs + w1, 1590), s2, font=fa, fill=PINK)

def rules(layer, t):
    d = ImageDraw.Draw(layer)
    lt = t - 9.5
    text_center(d, 470, "THE RULE", F(BOLD, 96), PINK)
    items = [("Set your ", "TARGET", " first"),
             ("Only take ", "1:2+", " setups"),
             ("Let ", "WINNERS", " run")]
    f = F(BOLD, 46); fn = F(BOLD, 60)
    for i, (a, b, c) in enumerate(items):
        it = (lt - 0.5 - i * 0.9) / 0.4
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
                d.text((x, y + 22), seg, font=f, fill=colr + (alpha,))
                x += d.textlength(seg, font=f)

def outro(layer, t):
    d = ImageDraw.Draw(layer)
    lt = t - 14.0
    p = ease_out_back(lt / 0.4)
    f = F(BOLD, 110)
    im = Image.new("RGBA", (1000, 160), (0, 0, 0, 0))
    di = ImageDraw.Draw(im)
    di.text((500 - di.textlength("FOLLOW", font=f) / 2, 0), "FOLLOW", font=f, fill=PINK)
    sw, sh = max(1, int(1000 * p)), max(1, int(160 * p))
    layer.alpha_composite(im.resize((sw, sh), Image.LANCZOS), (int(W / 2 - sw / 2), int(780 - sh / 2)))
    if lt > 0.3:
        text_center(d, 880, "for tomorrow's rule", F(BOLD, 64), WHITE)
    if lt > 0.6:
        bob = math.sin(lt * 8) * 18
        ax, ay = W / 2, 1080 + bob
        d.line((ax, ay, ax, ay + 150), fill=PINK, width=14)
        d.polygon([(ax - 50, ay + 120), (ax + 50, ay + 120), (ax, ay + 190)], fill=PINK)
    text_center(d, 1700, "Educational content. Not financial advice.", F(REG, 34), GREY)

def frame(t):
    img = BG_IMG.copy().convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    header(d, t)
    shake = (0, 0)
    if t < 3.5:
        bounce_words(layer, ["70%", "win", "rate\u2026"], 0.15, t, 640, 120, [WHITE, WHITE, WHITE])
        bounce_words(layer, ["and", "still"], 0.7, t, 810, 100, [WHITE] * 2)
        pos = bounce_words(layer, ["LOSING?"], 1.5, t, 1020, 160, [PINK], gap=0.24)
        if t > 2.2:
            p = ease_out((t - 2.2) / 0.4)
            mx, mw = pos[0]
            d.rounded_rectangle((mx, 1250, mx + mw * p, 1268), radius=9, fill=PINK)
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
    for st in (3.5, 9.5, 14.0):
        if st <= t < st + 0.2:
            a = int(255 * (1 - (t - st) / 0.2))
            img.alpha_composite(Image.new("RGBA", (W, H), BG + (a,)))
    return img.convert("RGB")

# ---------- music ----------
SR = 44100
def music():
    n = int(SR * DUR); out = np.zeros(n)
    t_all = np.arange(n) / SR
    bpm = 120; beat = 60 / bpm; bar = beat * 4
    def nf(m): return 440 * 2 ** ((m - 69) / 12)
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    bass = [45, 41, 36, 43]
    start = 0.15
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
    for x in [C0 + i * STEP for i in LOSSES[:-1]]:
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
    with wave.open("music.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

music()
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                      "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", "music.wav",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                      "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
                     stdin=subprocess.PIPE)
for i in range(int(DUR * FPS)):
    p.stdin.write(frame(i / FPS).tobytes())
p.stdin.close(); p.wait()
for ts in (1.0, 3.2, 6.5, 8.2, 9.0, 12.5, 15.5):
    frame(ts).resize((360, 640)).save(f"preview_{ts}.png")
print("done")
