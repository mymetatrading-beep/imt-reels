#!/usr/bin/env python3
"""IMT Reel con VOCE sintetica - serie "The OPEN decides the trade", Ep. 2: apertura sotto la VAL.
Uso: python3 reel_vp_ep2_open_below_val.py <cartella_voce> out.mp4
La cartella voce contiene 00.mp3 ... 08.mp3 (generati dal workflow tts.yml).
Il ritmo del video segue la durata reale di ogni frase."""
import os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music_v2

VOICE_DIR, OUT = sys.argv[1], sys.argv[2]
WORK = os.path.dirname(os.path.abspath(OUT))
W, H, FPS, SR = 1080, 1920, 30, 44100
FD = "/usr/share/fonts/truetype/google-fonts/"
def F(n, s): return ImageFont.truetype(FD + n, s)
BOLD, MED, REG = "Poppins-Bold.ttf", "Poppins-Medium.ttf", "Poppins-Regular.ttf"
PINK = (255, 60, 172); MAG = (214, 0, 160); WHITE = (245, 245, 250)
GREY = (150, 150, 170); RED = (255, 70, 90); GREEN = (40, 220, 150); BG = (8, 6, 16)

CAPTIONS = [
    "Price opened below value. Most traders panic. Here's what I watch.",
    "This is the POC: where the most volume traded yesterday.",
    "This line is the VAL: the bottom of fair value.",
    "Now watch price come back to it.",
    "Big buyer. Right at the VAL.",
    "CVD turns up. Aggressive buyers are stepping in.",
    "Back inside value, the target is the POC.",
    "That's not a random bounce. That's the trade.",
    "Follow for the other two setups.",
]

# ---------------- voce: decodifica, taglio silenzi, tempi ----------------
def load_mp3(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    idx = np.where(np.abs(x) > 0.02)[0]
    a, b = max(0, idx[0] - int(0.03 * SR)), min(len(x), idx[-1] + int(0.08 * SR))
    return x[a:b]

VO = [load_mp3(os.path.join(VOICE_DIR, f"{i:02d}.mp3")) for i in range(len(CAPTIONS))]
GAP = [0.35, 0.3, 0.3, 0.15, 0.35, 0.3, 0.3, 0.45]
S = [0.3]
for i in range(len(VO) - 1):
    S.append(S[-1] + len(VO[i]) / SR + GAP[i])
E = [S[i] + len(VO[i]) / SR for i in range(len(VO))]
DUR = E[-1] + 1.6
N_FR = int(DUR * FPS)
T_HIT = S[4] + 0.12           # bolla del big trade
T_OUTRO = S[8] - 0.1

def ease_out_back(t):
    t = min(max(t, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def ease_out(t):
    t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def clamp(t): return min(max(t, 0), 1)
def lerp(a, b, k): return a + (b - a) * k

# ---------------- sfondo ----------------
yy, xx = np.mgrid[0:H, 0:W]
def glow(cx, cy, r, col, k):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    return (np.exp(-d ** 2) * k)[..., None] * np.array(col)[None, None, :]
bg = np.ones((H, W, 3)) * np.array(BG)
bg += glow(W * 0.85, H * 0.1, 700, MAG, 0.5)
bg += glow(W * 0.1, H * 0.88, 800, (120, 0, 200), 0.4)
bg += ((xx % 90 == 0) | (yy % 90 == 0)).astype(float)[..., None] * 9
BG_IMG = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))

def tc(d, y, txt, f, fill, x=W // 2):
    d.text((x - d.textlength(txt, font=f) / 2, y), txt, font=f, fill=fill)

def header(d):
    f = F(BOLD, 44); txt = "IMT · ORDER FLOW SMC"
    w = d.textlength(txt, font=f); x0 = (W - w) / 2 - 34; y0 = 110
    d.rounded_rectangle((x0, y0, x0 + w + 68, y0 + 84), radius=42, outline=PINK, width=4)
    tc(d, y0 + 14, txt, f, PINK)

def pop_text(layer, txt, t0, t, y, size, col, x=W // 2):
    lt = (t - t0) / 0.35
    if lt <= 0: return
    f = F(BOLD, size)
    d0 = ImageDraw.Draw(layer)
    ww = d0.textlength(txt, font=f)
    im = Image.new("RGBA", (int(ww + 40), int(size * 1.45)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 0), txt, font=f, fill=col)
    s = ease_out_back(lt)
    sw, sh = max(1, int(im.width * s)), max(1, int(im.height * s))
    im = im.resize((sw, sh), Image.LANCZOS)
    layer.alpha_composite(im, (int(x - sw / 2), int(y + size * 0.72 - sh / 2)))

# ---------------- dati di mercato ----------------
VAH, POC, VAL = 90.0, 72.0, 52.0
YMIN, YMAX = 28.0, 100.0
OHLC = [(44, 45, 41, 42), (42, 43, 38, 39), (39, 41, 36, 40), (40, 41, 35, 36), (36, 39, 34, 38),
        (38, 40, 36, 37), (37, 39, 35, 38),                                   # apertura sotto valore
        (38, 42, 37, 41), (41, 45, 40, 44), (44, 48, 43, 47), (47, 51.5, 46, 51), (51, 52.5, 47, 48),  # ritorno alla VAL
        (48, 53.5, 46.5, 53),                                                 # big buyer
        (53, 57, 52, 56), (56, 59, 54, 55), (55, 60, 54.5, 59),               # CVD gira
        (59, 63, 58, 62), (62, 66, 61, 65), (65, 67, 62, 63), (63, 69, 62.5, 68), (68, 72.6, 67, 72)]  # target POC
DELTA = [-3, -4, 1, -4, 1, -1, 0, 1, 2, 2, 2, -2, 7, 4, 1, 3, 3, 3, -1, 3, 3]
CVD = np.cumsum(DELTA).astype(float)
BIG = 12

def spread(a, b, n): return [lerp(a, b, k / n) for k in range(n)]
RT = [-0.6, -0.3] + spread(S[0] + 0.4, S[3] - 0.2, 5)            # 0-6
RT += spread(S[3], E[3] + 0.1, 5)                                 # 7-11
RT += [S[4] - 0.05]                                                # 12
RT += spread(S[5] + 0.1, E[5], 3)                                  # 13-15
RT += spread(S[6], E[6] - 0.2, 5)                                  # 16-20
CDUR = [0.3] * len(OHLC); CDUR[BIG] = 0.55

BOX = (40, 600, W - 40, 1420)
PX0, PX1 = 60, 330                      # volume profile
CX0, CX1 = 380, 990                     # candele
GY0, GY1 = 640, 1390
def py(v): return GY1 - (v - YMIN) / (YMAX - YMIN) * (GY1 - GY0)
CW = (CX1 - CX0) / len(OHLC)
def cx(i): return CX0 + (i + 0.5) * CW

PROF_P = np.arange(29, 99, 2.5)
rng = np.random.default_rng(7)
PROF_V = np.exp(-((PROF_P - POC) / 11) ** 2) + 0.35 * np.exp(-((PROF_P - 88) / 4) ** 2) + 0.12 + rng.uniform(0, 0.12, len(PROF_P))
PROF_V /= PROF_V.max()
POC_I = int(np.argmin(np.abs(PROF_P - POC)))

def candle_state(i, t):
    o, h, l, c = OHLC[i]
    ct = t - RT[i]
    if ct < 0: return None
    k = clamp(ct / CDUR[i])
    if i == BIG:   # prima il wick sotto, poi la spinta
        if k < 0.35:
            q = ease_out(k / 0.35); cc = lerp(o, l, q); return o, o, cc, cc
        q = ease_out((k - 0.35) / 0.65); cc = lerp(l, c, q); return o, max(o, cc), l, cc
    cc = lerp(o, c, ease_out(k))
    return o, max(o, cc) + (h - max(o, cc)) * k, min(o, cc) + (l - min(o, cc)) * k, cc

def dashed(d, x0, x1, y, col, w=4, dash=22, gap=14):
    x = x0
    while x < x1:
        d.line((x, y, min(x + dash, x1), y), fill=col, width=w); x += dash + gap

def pill(d, x, y, txt, fill, tcol, size=34):
    f = F(BOLD, size); w = d.textlength(txt, font=f)
    d.rounded_rectangle((x, y - size * 0.75, x + w + 36, y + size * 0.75), radius=int(size * 0.75), fill=fill)
    d.text((x + 18, y - size * 0.68), txt, font=f, fill=tcol)
    return w + 36

# sprite del glow per la bolla
_g = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
ImageDraw.Draw(_g).ellipse((110, 110, 290, 290), fill=GREEN + (230,))
GLOW = _g.filter(ImageFilter.GaussianBlur(38))

def scene(layer, t):
    d = ImageDraw.Draw(layer)
    a = clamp((t + 0.5) / 0.4)
    d.rounded_rectangle(BOX, radius=28, fill=(14, 10, 28, int(225 * a)), outline=(70, 40, 110), width=3)
    # value area evidenziata da seg 2
    va = clamp((t - S[2]) / 0.5)
    if va > 0:
        d.rectangle((PX0, py(VAH), CX1 + 10, py(VAL)), fill=(120, 60, 200, int(38 * va)))
    # profilo che cresce
    g = ease_out((t - S[0] - 0.2) / 1.2) if t > S[0] else 0.0
    bh = abs(py(0) - py(2.5)) - 4
    poc_on = t > S[1] + 0.1
    for p, v in zip(PROF_P, PROF_V):
        inside = VAL <= p <= VAH
        col = (150, 70, 230) if inside else (80, 70, 120)
        if poc_on and p == PROF_P[POC_I]:
            col = PINK
        y = py(p)
        d.rectangle((PX0, y - bh / 2, PX0 + (PX1 - PX0) * v * g, y + bh / 2), fill=col)
    # POC
    if poc_on:
        k = ease_out((t - S[1] - 0.1) / 0.6)
        y = py(POC); dashed(d, PX0, lerp(PX0, CX1 + 10, k), y, PINK, 4, 12, 10)
        if k > 0.6: pill(d, CX1 - 105, y - 34, "POC", PINK, (20, 0, 20))
    # VAH (tenue) e VAL
    if t > S[2] + 0.1:
        k = ease_out((t - S[2] - 0.1) / 0.6)
        y = py(VAL); dashed(d, PX0, lerp(PX0, CX1 + 10, k), y, WHITE, 5)
        dashed(d, PX0, lerp(PX0, CX1 + 10, k), py(VAH), (110, 100, 150), 3)
        if k > 0.6:
            pill(d, CX1 - 105, y + 36, "VAL", WHITE, (20, 10, 30))
            d.text((CX1 - 92, py(VAH) - 52), "VAH", font=F(BOLD, 30), fill=(140, 130, 180))
    # candele
    last = None
    for i in range(len(OHLC)):
        st = candle_state(i, t)
        if st is None: break
        o, h, l, c = st; last = (i, c)
        col = GREEN if c >= o else (190, 80, 255)
        x = cx(i)
        d.line((x, py(h), x, py(l)), fill=col, width=4)
        y0, y1 = sorted((py(o), py(c)))
        d.rectangle((x - CW * 0.32, y0, x + CW * 0.32, max(y1, y0 + 3)), fill=col)
    # etichetta "OPEN" sulla prima candela
    if t < S[3]:
        d.text((cx(0) - 40, py(46.5) - 46), "OPEN", font=F(BOLD, 30), fill=GREY)
    # bolla big trade
    if t > T_HIT:
        k = (t - T_HIT) / 0.45
        r = 64 * ease_out_back(k)
        bx, by = cx(BIG), py(VAL)
        gs = int(400 * (r / 64) * (1 + 0.06 * np.sin(t * 6)))
        if gs > 4:
            layer.alpha_composite(GLOW.resize((gs, gs)), (int(bx - gs / 2), int(by - gs / 2)))
        d.ellipse((bx - r, by - r, bx + r, by + r), fill=(60, 235, 170))
        if k > 0.5:
            fb = F(BOLD, 32); bw = d.textlength("BIG BUYER 1,250", font=fb) + 36
            pill(d, bx - 70 - bw, by - 95, "BIG BUYER 1,250", WHITE, (10, 30, 20), 32)
            d.line((bx - 70, by - 95, bx - r * 0.7, by - r * 0.7), fill=WHITE, width=3)
    # target raggiunto
    if t > E[6] - 0.15:
        k = clamp((t - E[6] + 0.15) / 0.4)
        x = cx(len(OHLC) - 1); y = py(POC)
        d.ellipse((x - 22 * k, y - 22 * k, x + 22 * k, y + 22 * k), outline=PINK, width=5)
    # pannello CVD
    cb = (380, 1450, W - 40, 1680)
    d.rounded_rectangle((40, 1450, W - 40, 1680), radius=24, fill=(14, 10, 28, 225), outline=(70, 40, 110), width=3)
    hot = t > S[5]
    d.text((70, 1470), "CVD", font=F(BOLD, 40), fill=GREEN if hot else GREY)
    if hot and t < E[6]:
        d.text((70, 1530), "turning", font=F(MED, 30), fill=GREEN)
        d.text((70, 1566), "UP", font=F(BOLD, 40), fill=GREEN)
        d.polygon([(150, 1606), (186, 1606), (168, 1578)], fill=GREEN)
    if last is not None:
        lo, hi = CVD.min() - 1, CVD.max() + 1
        def cy(v): return cb[3] - 25 - (v - lo) / (hi - lo) * (cb[3] - cb[1] - 50)
        n, c = last
        k = clamp((t - RT[n]) / CDUR[n])
        pts = [(cx(j), cy(CVD[j])) for j in range(n)]
        prev = CVD[n - 1] if n > 0 else 0
        pts.append((cx(n), cy(lerp(prev, CVD[n], k))))
        dashed(d, cx(0), CX1, cy(0), (80, 70, 110), 2, 8, 8)
        for j in range(1, len(pts)):
            col = GREEN if (hot and j >= BIG) else (200, 200, 220)
            d.line((pts[j - 1], pts[j]), fill=col, width=5)

def wrap(d, txt, f, maxw):
    lines, cur = [], ""
    for w_ in txt.split():
        tst = (cur + " " + w_).strip()
        if d.textlength(tst, font=f) <= maxw: cur = tst
        else: lines.append(cur); cur = w_
    lines.append(cur); return lines

KEYWORDS = [(1, "POC", PINK), (2, "VAL", WHITE), (3, "THE RETEST", WHITE), (4, "BIG BUYER", GREEN),
            (5, "CVD TURNS UP", GREEN), (6, "TARGET: POC", PINK), (7, "THE TRADE", PINK)]

def frame(t):
    img = BG_IMG.copy().convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    header(d)
    # gancio persistente
    pop_text(layer, "Opened", S[0] - 0.25, t, 225, 100, WHITE, x=W // 2 - 250)
    pop_text(layer, "BELOW", S[0] - 0.05, t, 225, 100, PINK, x=W // 2 + 150)
    pop_text(layer, "value?", S[0] + 0.25, t, 345, 100, WHITE)
    if t > S[0] + 0.5:
        k = ease_out((t - S[0] - 0.5) / 0.3)
        f = F(BOLD, 100); w = d.textlength("BELOW", font=f)
        x0 = W // 2 + 150 - w / 2
        d.rounded_rectangle((x0, 350, x0 + w * k, 362), radius=6, fill=PINK)
    # parola chiave del momento
    for seg, txt, col in KEYWORDS:
        end = S[seg + 1] if seg + 1 < len(S) else DUR
        if S[seg] - 0.05 <= t < end - 0.05:
            pop_text(layer, txt, S[seg] - 0.05, t, 470, 84, col)
    scene(layer, t)
    # sottotitoli
    for i, txt in enumerate(CAPTIONS[:8]):
        if S[i] - 0.05 <= t < (S[i + 1] - 0.05):
            f = F(BOLD, 44)
            a = int(255 * clamp((t - S[i] + 0.05) / 0.2))
            for j, ln in enumerate(wrap(d, txt, f, 960)):
                tc(d, 1710 + j * 58, ln, f, (255, 255, 255, a))
    # finale
    if t > T_OUTRO:
        k = clamp((t - T_OUTRO) / 0.35)
        ov = Image.new("RGBA", (W, H), (8, 6, 16, int(225 * k)))
        layer.alpha_composite(ov)
        d = ImageDraw.Draw(layer)
        header(d)
        pop_text(layer, "FOLLOW", T_OUTRO + 0.1, t, 700, 190, PINK)
        if t > T_OUTRO + 0.35:
            tc(d, 1000, "for the other 2 setups:", F(MED, 54), WHITE)
            tc(d, 1075, "open INSIDE · open ABOVE value", F(BOLD, 50), PINK)
            ay = 1230 + 18 * np.sin((t - T_OUTRO) * 7)
            d.polygon([(W / 2 - 50, ay), (W / 2 + 50, ay), (W / 2, ay + 60)], fill=PINK)
        tc(d, 1780, "Educational content. Not financial advice.", F(REG, 34), GREY)
    img.alpha_composite(layer)
    # impatto: lampo + vibrazione
    if T_HIT <= t < T_HIT + 0.3:
        k = 1 - (t - T_HIT) / 0.3
        fl = Image.new("RGBA", (W, H), (120, 255, 200, int(70 * k)))
        img.alpha_composite(fl)
        dx = int(14 * k * np.sin(t * 90)); dy = int(10 * k * np.cos(t * 70))
        img = Image.fromarray(np.roll(np.roll(np.array(img), dx, axis=1), dy, axis=0))
    return img.convert("RGB")

if __name__ == "__main__":
    if os.environ.get("PREVIEW"):
        for ts in os.environ["PREVIEW"].split(","):
            frame(float(ts)).save(os.path.join(WORK, f"prev_{float(ts):05.1f}.png"))
        print("DUR", round(DUR, 2), "S", [round(x, 2) for x in S]); sys.exit()
    # audio: musica sotto + voce
    mpath = os.path.join(WORK, "music.wav")
    music_v2.render(mpath, DUR, T_HIT, [T_HIT], S[6], T_OUTRO, "dark_trap")
    with wave.open(mpath) as w_:
        ch = w_.getnchannels(); m = np.frombuffer(w_.readframes(w_.getnframes()), np.int16).astype(np.float64) / 32768
    m = m.reshape(-1, ch) if ch > 1 else np.repeat(m[:, None], 2, 1)
    n = int(DUR * SR); mix = np.zeros((n, 2)); mix[:min(n, len(m))] = m[:n] * 0.22
    v = np.zeros(n)
    for s, x in zip(S, VO):
        a = int(s * SR); v[a:a + len(x)] += x[:max(0, n - a)]
    v *= 0.9 / max(1e-9, np.abs(v).max())
    duck = np.convolve((np.abs(v) > 0.02).astype(float), np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
    mix *= (1 - 0.45 * np.clip(duck * 3, 0, 1))[:, None]
    mix += v[:, None]
    mix *= 0.95 / np.abs(mix).max()
    apath = os.path.join(WORK, "mix.wav")
    with wave.open(apath, "wb") as w_:
        w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR)
        w_.writeframes((mix * 32767).astype(np.int16).tobytes())
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", apath,
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
                         stdin=subprocess.PIPE)
    for fi in range(N_FR):
        p.stdin.write(frame(fi / FPS).tobytes())
    p.stdin.close(); p.wait()
    print("OK", OUT, round(DUR, 2))
