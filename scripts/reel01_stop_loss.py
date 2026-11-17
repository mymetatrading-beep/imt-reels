#!/usr/bin/env python3
"""IMT Reel #1 - 'Your stop loss isn't the problem. You moving it is.'"""
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

# ---------- candle chart data ----------
rng = np.random.default_rng(7)
N = 34
key = [(0, 99.6), (5, 100.0), (16, 98.4), (25, 96.4), (33, 93.6)]
closes = list(np.interp(range(N), [k for k, _ in key], [v for _, v in key]) + rng.normal(0, 0.18, N))
closes[5] = 100.0
candles = []
for i in range(N):
    o = closes[i - 1] if i else closes[0] - 0.3
    c = closes[i]
    hi = max(o, c) + abs(rng.normal(0, 0.15)); lo = min(o, c) - abs(rng.normal(0, 0.15))
    candles.append((o, hi, lo, c))
ENTRY = 100.0
STOP0 = 98.0; STOP1 = 96.0; STOP2 = 94.0
CH_T0, CH_T1 = 3.6, 9.4  # chart scene

def chart(layer, t):
    d = ImageDraw.Draw(layer)
    lt = t - CH_T0
    box = (90, 560, W - 90, 1380)
    d.rounded_rectangle(box, radius=30, fill=(14, 10, 28, 230), outline=(70, 40, 110), width=3)
    title_f = F(BOLD, 52)
    text_center(d, 430, "Watch what happens…", title_f, WHITE)
    lo_p, hi_p = min(c[2] for c in candles) - 1, max(c[1] for c in candles) + 1
    def py(p): return box[3] - 40 - (p - lo_p) / (hi_p - lo_p) * (box[3] - box[1] - 80)
    n_vis = int(clamp(lt / 4.2) * N) + 1
    cw = (box[2] - box[0] - 80) / N
    # stop level over time
    stop = STOP0; moved = 0
    if lt > 2.0: stop, moved = STOP1, 1
    if lt > 3.1: stop, moved = STOP2, 2
    hit = lt > 4.3
    # entry line
    ey = py(ENTRY)
    d.line((box[0] + 30, ey, box[2] - 30, ey), fill=(120, 160, 255), width=3)
    d.text((box[2] - 210, ey - 46), "ENTRY", font=F(BOLD, 34), fill=(120, 160, 255))
    # ghost old stops
    for k, sp in enumerate([STOP0, STOP1][:moved]):
        gy = py(sp)
        for xd in range(int(box[0] + 30), int(box[2] - 30), 30):
            d.line((xd, gy, xd + 14, gy), fill=(255, 70, 90, 110), width=3)
    sy = py(stop)
    d.line((box[0] + 30, sy, box[2] - 30, sy), fill=RED, width=5)
    lab = "STOP" if moved == 0 else ("STOP  moved ✗" if moved == 1 else "STOP  moved again ✗✗")
    d.text((box[0] + 40, sy + 10), lab.replace("✗", "x"), font=F(BOLD, 34), fill=RED)
    # move arrows
    for k, (a, b, tt) in enumerate([(STOP0, STOP1, 2.0), (STOP1, STOP2, 3.1)]):
        if lt > tt:
            ax = box[2] - 140 - k * 70
            p = ease_out((lt - tt) / 0.4)
            y1 = py(a); y2 = y1 + (py(b) - y1) * p
            d.line((ax, y1, ax, y2), fill=PINK, width=6)
            d.polygon([(ax - 16, y2 - 22), (ax + 16, y2 - 22), (ax, y2)], fill=PINK)
    # candles
    for i in range(min(n_vis, N)):
        o, hi, lo, c = candles[i]
        x = box[0] + 40 + i * cw + cw / 2
        col = GREEN if c >= o else RED
        d.line((x, py(hi), x, py(lo)), fill=col, width=3)
        y_a, y_b = sorted([py(o), py(c)])
        d.rectangle((x - cw * 0.32, y_a, x + cw * 0.32, max(y_b, y_a + 3)), fill=col)
    if hit:
        f = F(BOLD, 74)
        p = ease_out_back((lt - 4.3) / 0.35)
        im = Image.new("RGBA", (980, 140), (0, 0, 0, 0))
        di = ImageDraw.Draw(im)
        txt = "LOSS: -3R"
        di.text((490 - di.textlength(txt, font=f) / 2, 10), txt, font=f, fill=RED)
        sw, sh = int(980 * p), max(1, int(140 * p))
        if sw > 0:
            im = im.resize((sw, sh), Image.LANCZOS)
            layer.alpha_composite(im, (int(W / 2 - sw / 2), int(1450 - sh / 2 + 40)))
        if lt > 4.6:
            text_center(d, 1560, "instead of -1R", F(BOLD, 60), WHITE)

def rules(layer, t):
    d = ImageDraw.Draw(layer)
    lt = t - 9.5
    text_center(d, 470, "THE RULE", F(BOLD, 96), PINK)
    items = [("Set your ", "STOP", " before you enter"),
             ("", "NEVER", " widen it"),
             ("Accept the ", "1R", " loss")]
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
        bounce_words(layer, ["Your", "stop", "loss"], 0.15, t, 640, 112, [WHITE, PINK, PINK])
        bounce_words(layer, ["isn't", "the", "problem."], 0.7, t, 790, 104, [WHITE] * 3)
        pos = bounce_words(layer, ["You", "moving", "it", "is."], 1.6, t, 1060, 118, [WHITE, PINK, WHITE, WHITE], gap=0.22)
        if t > 2.3:
            # underline "moving"
            p = ease_out((t - 2.3) / 0.4)
            mx, mw = pos[1]
            d.rounded_rectangle((mx, 1260, mx + mw * p, 1276), radius=8, fill=PINK)
    elif t < 9.5:
        chart(layer, t)
        lt = t - CH_T0
        if 4.3 < lt < 4.8:
            k = (4.8 - lt) / 0.5
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
    if 4.3 < lt < 4.6:
        a = int(170 * (1 - (lt - 4.3) / 0.3))
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
    # impact on the loss hit
    hit = CH_T0 + 4.3; j0 = int(hit * SR); j1 = min(n, j0 + int(1.2 * SR)); tq = np.arange(j1 - j0) / SR
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
for ts in (1.0, 3.2, 6.5, 8.2, 12.5, 15.5):
    frame(ts).resize((360, 640)).save(f"preview_{ts}.png")
print("done")
