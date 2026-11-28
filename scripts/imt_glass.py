#!/usr/bin/env python3
"""IMT Liquid Glass v3 (dal 28/11/2026): primitive grafiche condivise da
make_reel.py e make_static.py.

Colori originali IMT: rosa #FF66C4 (chiaro #FFB8E2, scuro #A8287A) e bianco/argento
(#FFFFFF, #E4EAF2 > #8C96A6) su fondo #05070D. Oro #FFC24B solo per POC/livelli chiave.
Logo = marchio originale IMT in vettoriale (anello rosa aperto in basso, due barre rosa,
barra centrale bianca piu' alta), mai una sfera con scritto IMT.
"""
import numpy as np
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

# ---------------- palette ----------------
BG = (5, 7, 13)
PINK = (255, 102, 196); PINK_L = (255, 184, 226); PINK_D = (168, 40, 122)
WHITE = (255, 255, 255); SILVER = (228, 234, 242); SILVER_D = (140, 150, 166)
SILVER_M = (185, 195, 209); GOLD = (255, 194, 75); GOLD_L = (255, 210, 122)
GREY = (154, 166, 184)          # testo secondario #9AA6B8
TEXT = (228, 234, 242)           # testo principale #E4EAF2

# ---------------- font ----------------
INTER = "/usr/share/fonts/opentype/inter/"
MONT = "/usr/share/fonts/truetype/google-fonts/ofl/montserrat/Montserrat[wght].ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
_W = {"regular": "Regular", "medium": "Medium", "semibold": "SemiBold", "bold": "Bold",
      "extrabold": "ExtraBold", "black": "Black"}


@lru_cache(maxsize=256)
def font(size, weight="bold"):
    return ImageFont.truetype(INTER + f"Inter-{_W[weight]}.otf", int(size))


@lru_cache(maxsize=64)
def mont(size, weight="SemiBold"):
    try:
        f = ImageFont.truetype(MONT, int(size)); f.set_variation_by_name(weight); return f
    except Exception:
        return ImageFont.truetype("/usr/share/fonts/truetype/google-fonts/Poppins-SemiBold.ttf", int(size))


@lru_cache(maxsize=64)
def mono(size, bold=True):
    return ImageFont.truetype(MONO_B if bold else MONO, int(size))


def lerp3(stops, t):
    """stops: [(pos, (r,g,b)), ...]; t: ndarray 0..1 -> (...,3)"""
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    for (p0, c0), (p1, c1) in zip(stops[:-1], stops[1:]):
        m = (t >= p0) & (t <= p1)
        k = ((t - p0) / max(p1 - p0, 1e-6))[m][:, None]
        out[m] = np.array(c0) * (1 - k) + np.array(c1) * k
    return out


# ---------------- fondo ----------------
def background(W, H):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    bg = np.ones((H, W, 3), np.float32) * np.array(BG, np.float32)

    def glow(cx, cy, R, col, a):
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / R
        g = np.clip(1 - d / 0.65, 0, 1) ** 1.6 * a
        return g[..., None] * (np.array(col, np.float32) - bg)
    bg += glow(W * 0.08, H * 0.06, W * 1.05, PINK, 0.22)
    bg += glow(W * 0.95, H * 0.95, W * 1.1, (170, 180, 230), 0.10)
    # leggero dithering contro il banding
    bg += np.random.default_rng(3).normal(0, 0.6, bg.shape)
    return Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")


# ---------------- maschere ----------------
def rr_mask(w, h, r, ss=3):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius=r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


# ---------------- lastra di vetro ----------------
@lru_cache(maxsize=128)
def glass(w, h, r=22, tint=None, tint_a=0.0, border=None, border_a=0.12, fill_a=0.06,
          shadow=True, sheen=True):
    """RGBA della lastra (con margine `pad` per l'ombra). Ritorna (img, pad)."""
    w, h, r = int(w), int(h), int(r)
    pad = 44 if shadow else 0
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    mask = rr_mask(w, h, r)
    if shadow:
        sh = Image.new("L", out.size, 0)
        sh.paste(mask, (pad, pad + 14))
        sh = sh.filter(ImageFilter.GaussianBlur(20)).point(lambda v: int(v * 0.5))
        out.paste(Image.new("RGBA", out.size, (0, 0, 0, 255)), (0, 0), sh)
    m = np.asarray(mask, np.float32) / 255
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # riempimento: bianco ~6% + gradiente verticale tenue + tinta opzionale
    col = np.ones((h, w, 3), np.float32) * 255
    a = np.full((h, w), fill_a, np.float32) + 0.05 * np.clip(1 - yy / (h * 0.6), 0, 1)
    if tint is not None:
        k = tint_a / (tint_a + a)
        col = col * (1 - k[..., None]) + np.array(tint, np.float32) * k[..., None]
        a = a + tint_a
    if sheen:   # riflesso diagonale tenue
        u = (xx / max(w, 1)) * 0.8 + (yy / max(h, 1)) * 0.5
        a += 0.045 * np.exp(-((u - 0.28) / 0.09) ** 2)
    # bordo chiaro sottile + filo di luce in alto
    er = np.asarray(mask.filter(ImageFilter.MinFilter(3)), np.float32) / 255
    edge = np.clip(m - er, 0, 1)
    top = np.clip(1 - yy / max(r * 1.6, 8), 0, 1)
    bcol = np.array(border or WHITE, np.float32)
    ea = edge * (border_a + 0.33 * top)
    tot = a * m
    rgb = (col * tot[..., None] * (1 - ea[..., None]) + bcol * ea[..., None]) / np.maximum(tot + ea - tot * ea, 1e-4)[..., None]
    alpha = np.clip(tot + ea - tot * ea, 0, 1)
    # linea di luce interna (1px sotto il bordo alto)
    hl = np.zeros((h, w), np.float32)
    hl[1:3, :] = 1
    hl *= np.clip(np.sin(np.pi * np.clip((xx - r * 0.6) / max(w - r * 1.2, 1), 0, 1)), 0, 1) * 0.30 * m
    rgb = rgb * (1 - hl[..., None]) + 255 * hl[..., None]
    alpha = np.clip(alpha + hl, 0, 1)
    pane = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8), "RGBA")
    out.alpha_composite(pane, (pad, pad))
    return out, pad


def paste_glass(img, box, r=22, scale=1.0, opacity=1.0, **kw):
    x0, y0, x1, y1 = [int(v) for v in box]
    g, pad = glass(x1 - x0, y1 - y0, r, **kw)
    paste(img, g, (x0 - pad, y0 - pad), scale, opacity)


def paste(img, im, xy, scale=1.0, opacity=1.0):
    """Incolla `im` in xy, con scala attorno al centro e dissolvenza."""
    if scale <= 0.01 or opacity <= 0.01:
        return
    x, y = xy
    if abs(scale - 1) > 0.002:
        cx, cy = x + im.width / 2, y + im.height / 2
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
        x, y = cx - im.width / 2, cy - im.height / 2
    if opacity < 0.999:
        im = im.copy(); a = im.getchannel("A").point(lambda v: int(v * opacity)); im.putalpha(a)
    img.alpha_composite(im, (int(round(x)), int(round(y))))


# ---------------- sfere ----------------
@lru_cache(maxsize=64)
def sphere(r, kind="pink"):
    r = int(r); ss = 3; R = r * ss; pad = int(r * 0.6)
    size = 2 * r + 2 * pad
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # ombra morbida sotto
    sh = Image.new("L", (size, size), 0)
    ImageDraw.Draw(sh).ellipse((pad, pad + r * 0.30, pad + 2 * r, pad + 2 * r + r * 0.30), fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(max(2, r * 0.22))).point(lambda v: int(v * 0.5))
    shc = (120, 20, 80) if kind == "pink" else (0, 0, 0)
    out.paste(Image.new("RGBA", (size, size), shc + (255,)), (0, 0), sh)
    yy, xx = np.mgrid[0:2 * R, 0:2 * R].astype(np.float32)
    d = np.sqrt((xx - 0.32 * 2 * R) ** 2 + (yy - 0.28 * 2 * R) ** 2) / (2 * R * 0.78)
    if kind == "pink":
        stops = [(0, WHITE), (0.14, PINK_L), (0.42, PINK), (1.0, PINK_D)]
    elif kind == "gold":
        stops = [(0, WHITE), (0.14, GOLD_L), (0.45, GOLD), (1.0, (150, 100, 20))]
    else:
        stops = [(0, WHITE), (0.14, (243, 246, 250)), (0.45, SILVER_M), (1.0, (90, 100, 116))]
    rgb = lerp3(stops, d)
    dc = np.sqrt((xx - R) ** 2 + (yy - R) ** 2)
    m = np.clip(R - dc, 0, 1)
    # ombra interna in basso
    inner = np.clip((yy - R) / R, 0, 1) * np.clip(dc / R, 0, 1) * 0.35
    rgb = rgb * (1 - inner[..., None])
    s = Image.fromarray(np.dstack([rgb, m * 255]).astype(np.uint8), "RGBA").resize((2 * r, 2 * r), Image.LANCZOS)
    out.alpha_composite(s, (pad, pad))
    # riflesso ellittico bianco
    hl = Image.new("L", (size, size), 0)
    ImageDraw.Draw(hl).ellipse((pad + r * 0.34, pad + r * 0.20, pad + r * 1.02, pad + r * 0.58), fill=150)
    hl = hl.filter(ImageFilter.GaussianBlur(max(1, r * 0.06)))
    out.paste(Image.new("RGBA", (size, size), (255, 255, 255, 255)), (0, 0), hl)
    return out, pad


def paste_sphere(img, cx, cy, r, kind="pink", scale=1.0, opacity=1.0):
    s, pad = sphere(int(r), kind)
    paste(img, s, (cx - r - pad, cy - r - pad), scale, opacity)


# ---------------- pillole ----------------
def pill(img, box, kind="glass", scale=1.0, opacity=1.0):
    x0, y0, x1, y1 = box; h = y1 - y0
    if kind == "pink":
        paste_glass(img, box, h // 2, scale, opacity, tint=PINK, tint_a=0.34, border=PINK_L, border_a=0.55)
    elif kind == "silver":
        paste_glass(img, box, h // 2, scale, opacity, tint=SILVER, tint_a=0.20, border=WHITE, border_a=0.45)
    elif kind == "gold":
        paste_glass(img, box, h // 2, scale, opacity, tint=GOLD, tint_a=0.22, border=GOLD_L, border_a=0.5)
    else:
        paste_glass(img, box, h // 2, scale, opacity)


# ---------------- logo originale IMT ----------------
@lru_cache(maxsize=16)
def logo(size):
    """Logo IMT originale in vetro, `size` = larghezza del box 472. Ritorna (img, pad)."""
    ss = 3; k = size / 472 * ss
    Wl, Hl = int(472 * k), int(470 * k)
    def P(pts): return [(x * k, y * k) for x, y in pts]
    ring = Image.new("L", (Wl, Hl), 0); dr = ImageDraw.Draw(ring)
    dr.ellipse(P([(236 - 218, 230 - 218), (236 + 218, 230 + 218)]), fill=255)
    dr.ellipse(P([(236 - 168, 230 - 168), (236 + 168, 230 + 168)]), fill=0)   # evenodd
    dr.rectangle(P([(132, 300), (340, 470)]), fill=0)                          # aperto in basso
    bars = Image.new("L", (Wl, Hl), 0); db = ImageDraw.Draw(bars)
    db.polygon(P([(132, 266), (180, 236), (180, 446), (132, 446)]), fill=255)
    db.polygon(P([(292, 282), (340, 252), (340, 446), (292, 446)]), fill=255)
    pinkm = ImageChops.lighter(ring, bars)
    whitem = Image.new("L", (Wl, Hl), 0)
    ImageDraw.Draw(whitem).polygon(P([(212, 190), (264, 152), (264, 446), (212, 446)]), fill=255)
    union = ImageChops.lighter(pinkm, whitem)
    yy, xx = np.mgrid[0:Hl, 0:Wl].astype(np.float32)
    tdiag = (xx / Wl * 0.55 + yy / Hl * 0.45)
    prgb = lerp3([(0, PINK_L), (0.45, PINK), (1.0, PINK_D)], (tdiag - 0.05) / 0.9)
    tw = ((xx - 212 * k) / (52 * k) * 0.25 + (yy - 152 * k) / (294 * k) * 0.75)
    wrgb = lerp3([(0, WHITE), (0.45, (243, 246, 250)), (1.0, SILVER_M)], tw)
    pm = np.asarray(pinkm, np.float32)[..., None] / 255
    wm = np.asarray(whitem, np.float32)[..., None] / 255
    rgb = prgb * pm + wrgb * wm
    um = np.asarray(union, np.float32) / 255
    # riflesso bianco tenue in alto a sinistra, ritagliato sulle forme
    hl = Image.new("L", (Wl, Hl), 0)
    ImageDraw.Draw(hl).ellipse(P([(40, 20), (300, 190)]), fill=255)
    hl = np.asarray(hl.filter(ImageFilter.GaussianBlur(28 * k)), np.float32) / 255 * 0.42
    rgb = rgb * (1 - hl[..., None]) + 255 * hl[..., None]
    # bordo chiaro sottile
    er = np.asarray(union.filter(ImageFilter.MinFilter(max(3, int(3 * k) | 1))), np.float32) / 255
    edge = np.clip(um - er, 0, 1) * 0.45
    rgb = rgb * (1 - edge[..., None]) + 255 * edge[..., None]
    shape = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), um * 255]).astype(np.uint8), "RGBA")
    pad = int(70 * k)
    canvas = Image.new("RGBA", (Wl + 2 * pad, Hl + 2 * pad), (0, 0, 0, 0))
    # ombra morbida sotto
    sh = Image.new("L", canvas.size, 0); sh.paste(union, (pad, pad + int(22 * k)))
    sh = sh.filter(ImageFilter.GaussianBlur(22 * k)).point(lambda v: int(v * 0.55))
    canvas.paste(Image.new("RGBA", canvas.size, (0, 0, 0, 255)), (0, 0), sh)
    # alone rosa sfocato dietro l'anello
    halo = Image.new("L", canvas.size, 0); halo.paste(ring, (pad, pad))
    halo = halo.filter(ImageFilter.GaussianBlur(30 * k)).point(lambda v: int(v * 0.55))
    canvas.paste(Image.new("RGBA", canvas.size, PINK + (255,)), (0, 0), halo)
    canvas.alpha_composite(shape, (pad, pad))
    out = canvas.resize((canvas.width // ss, canvas.height // ss), Image.LANCZOS)
    return out, pad // ss


def paste_logo(img, x, y, size, scale=1.0, opacity=1.0):
    """(x, y) = angolo in alto a sinistra del box 472x470 scalato a `size`."""
    lg, pad = logo(int(size))
    paste(img, lg, (x - pad, y - pad), scale, opacity)


# ---------------- testo ----------------
def tracked_width(d, txt, f, tr):
    return sum(d.textlength(c, font=f) for c in txt) + tr * (len(txt) - 1)


def draw_tracked(d, x, y, txt, f, fill, tr, dot=PINK):
    for c in txt:
        d.text((x, y), c, font=f, fill=dot if c == "·" else fill)
        x += d.textlength(c, font=f) + tr


BRAND = "IMT · SMC ORDER FLOW"


@lru_cache(maxsize=8)
def header_img(W, fsize=34, lsize=74):
    """Pillola di vetro con logo originale + 'IMT · SMC ORDER FLOW'. Ritorna (img, pad)."""
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    f = mont(fsize, "SemiBold"); tr = fsize * 0.16
    tw = tracked_width(tmp, BRAND, f, tr)
    h = int(lsize + 30); w = int(lsize + 26 + tw + 68)
    g, pad = glass(w, h, h // 2)
    im = g.copy(); d = ImageDraw.Draw(im)
    paste_logo(im, pad + 30, pad + (h - lsize * 470 / 472) / 2, lsize)
    asc, desc = f.getmetrics()
    ty = pad + h / 2 - (asc + desc) / 2 + desc * 0.25
    draw_tracked(d, pad + 30 + lsize + 22, ty, BRAND, f, WHITE, tr)
    return im, pad


def paste_header(img, W, y, fsize=34, lsize=74, opacity=1.0):
    im, pad = header_img(W, fsize, lsize)
    paste(img, im, ((W - im.width) / 2, y - pad), 1.0, opacity)


# ---------------- candele cilindriche ----------------
@lru_cache(maxsize=64)
def _cyl_row(w, bull):
    x = np.linspace(0, 1, max(w, 1))
    stops = ([(0, WHITE), (0.35, SILVER), (1.0, SILVER_D)] if bull
             else [(0, PINK_L), (0.35, PINK), (1.0, PINK_D)])
    return lerp3(stops, x)


def candle_body(img, x0, y0, x1, y1, bull, rx=3):
    w, h = int(round(x1 - x0)), int(round(y1 - y0))
    w = max(w, 2); h = max(h, 2)
    row = _cyl_row(w, bull)
    arr = np.repeat(row[None, :, :], h, 0)
    m = rr_mask(w, h, min(rx, w // 2, h // 2), ss=2)
    im = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA"); im.putalpha(m)
    img.alpha_composite(im, (int(round(x0)), int(round(y0))))


def wick(d, cx, ya, yb, bull, width=4):
    col = SILVER if bull else PINK
    d.rounded_rectangle((cx - width / 2, min(ya, yb), cx + width / 2, max(ya, yb)), radius=width / 2, fill=col)
