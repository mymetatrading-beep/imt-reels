"""Scene dei Reel in stile v3 IMT Liquid Glass (rosa/bianco, logo originale).
Usato da make_reel.py quando la spec ha version >= 3 (default). Mantiene struttura,
tempi e musica della v2: gancio leggibile dal fotogramma 0 sopra il grafico, grafico
in movimento da subito, regola 1-2-3, FOLLOW."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import imt_glass as G


def install(g):
    W, H = g["W"], g["H"]
    SPEC, CH = g["SPEC"], g["CH"]
    OHLC, STEP, C0, HIT = g["OHLC"], g["STEP"], g["C0"], g["HIT"]
    REV, SPIKE, MARK = g["REV"], g["SPIKE"], g["MARK"]
    YMIN, YMAX, LEVEL = g["YMIN"], g["YMAX"], g["LEVEL"]
    CH_T0, T_RULES, T_OUTRO = g["CH_T0"], g["T_RULES"], g["T_OUTRO"]
    ease_out_back, ease_out, clamp = g["ease_out_back"], g["ease_out"], g["clamp"]

    BG = G.background(W, H)
    BOX = (90, 566, W - 90, 1380)
    GX0, GX1, GY0, GY1 = 150, W - 150, 690, 1336

    def py(v): return GY1 - (v - YMIN) / (YMAX - YMIN) * (GY1 - GY0)
    CW = (GX1 - GX0) / len(OHLC)

    def ctext(d, y, txt, f, fill, x=W / 2):
        d.text((x - d.textlength(txt, font=f) / 2, y), txt, font=f, fill=fill)

    def fit(d, txt, weight, size, maxw, minsize=26):
        while size > minsize and d.textlength(txt, font=G.font(size, weight)) > maxw:
            size -= 2
        return G.font(size, weight)

    # ---------- gancio (precalcolato) ----------
    def build_hook():
        rows = SPEC["hook"]
        im = Image.new("RGBA", (W, 330), (0, 0, 0, 0)); di = ImageDraw.Draw(im)
        sizes = []
        for row in rows:
            sz = min(row.get("size", 96), 96 if len(rows) < 3 else 76)
            while sz > 50:
                ff = G.font(sz, "extrabold")
                tot = sum(di.textlength(w_, font=ff) for w_ in row["words"]) + sz * 0.26 * (len(row["words"]) - 1)
                if tot <= W - 130: break
                sz -= 4
            sizes.append(sz)
        lh = [int(sz * 1.28) for sz in sizes]
        y = max(0, (318 - sum(lh)) // 2)
        for row, sz, l in zip(rows, sizes, lh):
            ff = G.font(sz, "extrabold"); sp = sz * 0.26
            ws = [di.textlength(w_, font=ff) for w_ in row["words"]]
            x = (W - sum(ws) - sp * (len(ws) - 1)) / 2
            for j, (w_, ww) in enumerate(zip(row["words"], ws)):
                pink = j in row.get("pink", [])
                di.text((x, y), w_, font=ff, fill=G.PINK if pink else G.WHITE)
                if row.get("underline") == j:
                    uy = y + sz * 1.12
                    di.rounded_rectangle((x, uy, x + ww, uy + max(8, sz * 0.11)), radius=6, fill=G.PINK)
                x += ww + sp
            y += l
        # bagliore rosa leggero dietro al testo
        glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
        a = im.getchannel("A").filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.35))
        glow.paste(Image.new("RGBA", im.size, G.PINK + (255,)), (0, 0), a)
        glow.alpha_composite(im)
        return glow
    HOOK = build_hook()

    # ---------- lastra del grafico (statica) + subtitolo ----------
    PANEL = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    G.paste_glass(PANEL, BOX, 26)
    dp = ImageDraw.Draw(PANEL)
    fsub = fit(dp, CH["subtitle"], "semibold", 40, BOX[2] - BOX[0] - 80)
    ctext(dp, 596, CH["subtitle"], fsub, G.PINK_L)
    dp.line((BOX[0] + 60, 660, BOX[2] - 60, 660), fill=(255, 255, 255, 26), width=2)
    pm = np.zeros((H, W), np.float32)
    pm[BOX[1]:BOX[3], BOX[0]:BOX[2]] = np.asarray(G.rr_mask(BOX[2] - BOX[0], BOX[3] - BOX[1], 26), np.float32) / 255
    PMASK = pm[BOX[1]:BOX[3], BOX[0]:BOX[2]]
    yyp, xxp = np.mgrid[0:BOX[3] - BOX[1], 0:BOX[2] - BOX[0]].astype(np.float32)
    UU = xxp / (BOX[2] - BOX[0]) + yyp / (BOX[3] - BOX[1]) * 0.6

    def sheen(img, t, t0=0.25, dur=2.4):
        k = (t - t0) / dur
        if not 0 < k < 1: return
        pos = -0.3 + 1.9 * k
        a = np.exp(-((UU - pos) / 0.07) ** 2) * 0.07 * PMASK
        im = Image.fromarray(np.dstack([np.full(a.shape + (3,), 255, np.uint8), (a * 255).astype(np.uint8)]), "RGBA")
        img.alpha_composite(im, (BOX[0], BOX[1]))

    def label_pill(img, d, x, y, txt, kind, f, txtcol=G.WHITE, anchor="left", scale=1.0, op=1.0):
        tw = d.textlength(txt, font=f); h = int(f.size * 1.55)
        x0 = x if anchor == "left" else x - tw - 44
        G.pill(img, (int(x0), int(y), int(x0 + tw + 44), int(y + h)), kind, scale, op)
        if scale > 0.8:
            asc, desc = f.getmetrics()
            d.text((x0 + 22, y + h / 2 - (asc + desc) / 2 + desc * 0.3), txt, font=f, fill=txtcol)
        return x0, x0 + tw + 44, h

    def chart(img, t):
        lt = t - CH_T0
        img.alpha_composite(PANEL)
        sheen(img, t)
        d = ImageDraw.Draw(img)
        hit = lt > HIT
        if LEVEL:
            ly = py(LEVEL["value"])
            lc = G.GOLD + ((210,) if not hit else (110,))
            x = GX0
            while x < GX1:
                d.rounded_rectangle((x, ly - 2, min(x + 22, GX1), ly + 2), radius=2, fill=lc); x += 36
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
            bull = cc >= o
            cx = GX0 + CW * (i + 0.5)
            G.wick(d, cx, py(hh), py(ll), bull, 4)
            top, bot = py(max(o, cc)), py(min(o, cc))
            if bot - top < 6: bot = top + 6
            G.candle_body(img, cx - CW * 0.31, top, cx + CW * 0.31, bot, bull, rx=4)
        # bolle opzionali (big trades): {"candle", "y", "r", "buy"}
        for b in CH.get("bubbles", []):
            bt = lt - (C0 + (b["candle"] + 0.6) * STEP)
            if bt > 0:
                p = clamp(bt / 0.35)
                G.paste_sphere(img, GX0 + CW * (b["candle"] + 0.5), py(b["y"]), b.get("r", 26),
                               "pink" if b.get("buy", True) else "silver", 0.4 + 0.6 * ease_out_back(p), p)
        if LEVEL:
            lab = LEVEL["label"] if not hit else LEVEL.get("label_after", LEVEL["label"])
            fl = G.font(30, "bold")
            lyl = ly + (14 if LEVEL.get("below") else -62)
            if LEVEL.get("right"):
                label_pill(img, d, GX1 + 10, lyl, lab, "gold" if not hit else "pink", fl, anchor="right")
            else:
                label_pill(img, d, GX0 - 10, lyl, lab, "gold" if not hit else "pink", fl)
        if MARK is not None:
            M = CH["marker"]
            bt = lt - (C0 + (MARK + 1) * STEP)
            if bt > 0:
                bx = GX0 + CW * (MARK + 0.5); by = py(M["y"])
                p = clamp(bt / 0.3)
                good = M.get("good", True)
                kind = ("pink" if good else "silver") if not hit else "pink"
                lab = M["label"] if not hit else M.get("label_after", M["label"])
                fb = G.font(32, "bold")
                tx = py(OHLC[MARK][3]) - 12
                x0, x1, hh = label_pill(img, d, bx - 34, by - 26, lab, kind, fb, anchor="right",
                                        scale=0.6 + 0.4 * ease_out_back(p), op=p)
                if p > 0.6:
                    d.line((x1 - 4, by + hh / 2 - 26, bx, tx), fill=G.PINK_L if kind == "pink" else G.SILVER, width=3)
                    G.paste_sphere(img, bx, tx, 11, "pink" if kind == "pink" else "silver")
        if hit:
            txt = CH["impact"]
            p = clamp((lt - HIT) / 0.35)
            s = 0.6 + 0.4 * ease_out_back(p)
            slab = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
            G.paste_glass(slab, (90, 40, W - 90, 200), 26, tint=G.PINK if CH.get("impact_bad", True) else None,
                          tint_a=0.08)
            ds = ImageDraw.Draw(slab)
            fi = fit(ds, txt, "black", 104 if len(txt) <= 12 else 84, W - 260, 50)
            col = G.PINK if CH.get("impact_bad", True) else G.WHITE
            asc, desc = fi.getmetrics()
            ty = 120 - (asc + desc) / 2 + desc * 0.35
            gl = Image.new("RGBA", slab.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(gl)
            ctext(dg, ty, txt, fi, G.PINK + (200,))
            slab.alpha_composite(gl.filter(ImageFilter.GaussianBlur(14)))
            ctext(ds, ty, txt, fi, col)
            G.paste(img, slab, (0, 1370), s, p)
            if lt > HIT + 0.6:
                s1, s2 = CH["punch"]
                fa = G.font(50, "bold")
                for sz in (50, 46, 42, 38):
                    fa = G.font(sz, "bold")
                    if d.textlength(s1, font=fa) + d.textlength(s2, font=fa) <= W - 100: break
                w1, w2 = d.textlength(s1, font=fa), d.textlength(s2, font=fa)
                pa = clamp((lt - HIT - 0.6) / 0.25)
                xs = (W - w1 - w2) / 2
                d.text((xs, 1612), s1, font=fa, fill=G.WHITE + (int(255 * pa),))
                d.text((xs + w1, 1612), s2, font=fa, fill=G.PINK + (int(255 * pa),))

    def rules(img, t):
        d = ImageDraw.Draw(img)
        lt = t - T_RULES
        ctext(d, 420, SPEC.get("rules_title", "THE RULE"), G.font(96, "black"), G.PINK)
        items = [tuple(x) for x in SPEC["rules"]]
        for i, (a, b, c) in enumerate(items):
            it = clamp((lt - 0.15 - i * 0.5) / 0.35)
            if it <= 0: continue
            y = 640 + i * 240
            s = 0.85 + 0.15 * ease_out_back(it)
            slab = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
            G.paste_glass(slab, (70, 45, W - 70, 215), 26)
            G.paste_sphere(slab, 70 + 34 + 52, 130, 52, "pink")
            ds = ImageDraw.Draw(slab)
            fn = G.font(58, "extrabold"); num = str(i + 1)
            asc, desc = fn.getmetrics()
            ds.text((156 - ds.textlength(num, font=fn) / 2, 130 - (asc + desc) / 2 + desc * 0.3), num, font=fn, fill=G.WHITE)
            f = fit(ds, a + b + c, "bold", 48, W - 70 - 250 - 40, 30)
            asc, desc = f.getmetrics()
            x = 250; ty = 130 - (asc + desc) / 2 + desc * 0.3
            for seg, colr in ((a, G.WHITE), (b, G.PINK), (c, G.WHITE)):
                if seg:
                    ds.text((x, ty), seg, font=f, fill=colr); x += ds.textlength(seg, font=f)
            G.paste(img, slab, (0, y - 45), s, it)

    def outro(img, t):
        d = ImageDraw.Draw(img)
        lt = t - T_OUTRO
        p = clamp(lt / 0.4)
        G.paste_logo(img, W / 2 - 130, 330, 260, 0.7 + 0.3 * ease_out_back(p), p)
        p2 = clamp((lt - 0.1) / 0.4)
        slab = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
        G.paste_glass(slab, (110, 50, W - 110, 370), 30)
        ds = ImageDraw.Draw(slab)
        gl = Image.new("RGBA", slab.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(gl)
        ctext(dg, 92, "FOLLOW", G.font(124, "black"), G.PINK + (200,))
        slab.alpha_composite(gl.filter(ImageFilter.GaussianBlur(16)))
        ctext(ds, 92, "FOLLOW", G.font(124, "black"), G.PINK)
        cta = SPEC.get("cta", "for tomorrow's rule")
        ctext(ds, 262, cta, fit(ds, cta, "bold", 56, W - 300), G.WHITE)
        G.paste(img, slab, (0, 690), 0.85 + 0.15 * ease_out_back(p2), p2)
        if lt > 0.3:
            bob = math.sin(lt * 8) * 16
            ax, ay = W / 2, 1180 + bob
            d.rounded_rectangle((ax - 8, ay, ax + 8, ay + 140), radius=8, fill=G.PINK)
            d.polygon([(ax - 48, ay + 118), (ax + 48, ay + 118), (ax, ay + 186)], fill=G.PINK)
        ctext(d, 1700, "Educational content. Not financial advice.", G.font(32, "medium"), G.GREY)

    def frame(t):
        img = BG.copy()
        shake = (0, 0)
        if t < T_RULES:
            chart(img, t)
            s = 1 + 0.07 * (1 - ease_out(t / 0.35))
            G.paste(img, HOOK, (0, 226), s, 1.0)
            lt = t - CH_T0
            if HIT < lt < HIT + 0.5:
                k = (HIT + 0.5 - lt) / 0.5
                shake = (int(math.sin(lt * 90) * 20 * k), int(math.cos(lt * 70) * 14 * k))
        elif t < T_OUTRO:
            rules(img, t)
        else:
            outro(img, t)
        G.paste_header(img, W, 92)
        if shake != (0, 0):
            img = img.transform(img.size, Image.AFFINE, (1, 0, -shake[0], 0, 1, -shake[1]),
                                fillcolor=G.BG + (255,))
        lt = t - CH_T0
        if HIT < lt < HIT + 0.3:
            a = int(120 * (1 - (lt - HIT) / 0.3))
            img.alpha_composite(Image.new("RGBA", (W, H), G.PINK + (a,)))
        for st in (T_RULES, T_OUTRO):
            if st <= t < st + 0.2:
                a = int(255 * (1 - (t - st) / 0.2))
                img.alpha_composite(Image.new("RGBA", (W, H), G.BG + (a,)))
        return img.convert("RGB")

    return frame
