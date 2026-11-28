"""Caroselli e storie in stile v3 IMT Liquid Glass (rosa/bianco, logo originale).
Usato da make_static.py quando la spec ha version >= 3 (default). Stessi tipi di slide
e stessi campi della v2 (cover, point, rule, cta, quiz, answer)."""
from PIL import Image, ImageDraw, ImageFilter
import imt_glass as G


def wrap(d, txt, f, maxw):
    words, lines, cur = txt.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def ctext(d, W, y, txt, f, fill):
    d.text(((W - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=fill)


def vcenter(f, cy):
    asc, desc = f.getmetrics()
    return cy - (asc + desc) / 2 + desc * 0.3


def glow_text(img, xy, txt, f, col, blur=14, a=170):
    gl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).text(xy, txt, font=f, fill=G.PINK + (a,))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(img).text(xy, txt, font=f, fill=col)


def text_block(d, txt, weight, size, maxw, max_lines, min_size=30):
    while True:
        f = G.font(size, weight); ls = wrap(d, txt, f, maxw)
        if len(ls) <= max_lines or size <= min_size: return f, ls
        size -= 2


def kicker(img, d, W, y, txt):
    f = G.font(30, "bold"); tr = 3
    tw = G.tracked_width(d, txt, f, tr)
    G.pill(img, (int((W - tw) / 2 - 30), y, int((W + tw) / 2 + 30), y + 60), "glass")
    G.draw_tracked(d, (W - tw) / 2, vcenter(f, y + 30), txt, f, G.PINK_L, tr)


def footprint(img, d, box, fp):
    x0, y0, x1, y1 = box
    G.paste_glass(img, box, 24)
    rows = fp["rows"]; n = len(rows)
    head = 52
    rh = (y1 - y0 - head - 16) / n
    cx = (x0 + x1) / 2
    fh = G.font(22, "semibold")
    d.text((x0 + 34, y0 + 18), "PRICE", font=fh, fill=G.GREY)
    d.text((cx - 40 - d.textlength("BID", font=fh), y0 + 18), "BID", font=fh, fill=G.GREY)
    d.text((cx + 40, y0 + 18), "ASK", font=fh, fill=G.GREY)
    fn = G.mono(min(34, int(rh * 0.55))); fp_ = G.mono(min(28, int(rh * 0.48)), bold=False)
    cw = 170
    for i, (p, b, a) in enumerate(rows):
        y = y0 + head + i * rh; cy = y + rh / 2
        if i == fp.get("poc"):
            d.rounded_rectangle((x0 + 18, y + 3, x1 - 18, y + rh - 3), radius=int(rh / 2 - 3), outline=G.GOLD, width=3)
            fpoc = G.font(18, "bold")
            d.text((x1 - 30 - d.textlength("POC", font=fpoc), vcenter(fpoc, cy)), "POC", font=fpoc, fill=G.GOLD)
        bcol = acol = G.TEXT
        if i in fp.get("sell_imb", []):
            G.pill(img, (int(cx - 22 - cw), int(y + 6), int(cx - 22), int(y + rh - 6)), "silver"); bcol = G.WHITE
        if i in fp.get("buy_imb", []):
            G.pill(img, (int(cx + 22), int(y + 6), int(cx + 22 + cw), int(y + rh - 6)), "pink"); acol = G.WHITE
        d.text((x0 + 34, vcenter(fp_, cy)), str(p), font=fp_, fill=G.GREY)
        bt, at = str(b), str(a)
        d.text((cx - 40 - d.textlength(bt, font=fn), vcenter(fn, cy)), bt, font=fn, fill=bcol)
        d.text((cx - d.textlength("x", font=fp_) / 2, vcenter(fp_, cy)), "x", font=fp_, fill=G.GREY)
        d.text((cx + 40, vcenter(fn, cy)), at, font=fn, fill=acol)


def render(slide, W, H, page, total, seed=0):
    img = G.background(W, H)
    d = ImageDraw.Draw(img)
    story = H > 1500
    G.paste_header(img, W, 150 if story else 64, 32, 70)
    k = slide["kind"]
    top = 330 if story else 222
    bottom = H - (300 if story else 110)
    if k == "cover":
        lines = slide["title"]
        size = 112
        while size > 60 and max(d.textlength(l, font=G.font(size, "extrabold")) for l in lines) > W - 250:
            size -= 4
        f = G.font(size, "extrabold"); lh = int(size * 1.22)
        hh = lh * len(lines) + 90
        y0 = top + 100
        if not story:   # blocco centrato tra kicker e SWIPE
            y0 = max(top + 100, int((top + 90 + H - 250 - hh - 120) / 2))
        if slide.get("kicker"): kicker(img, d, W, y0 - 100, slide["kicker"])
        G.paste_glass(img, (70, y0, W - 70, y0 + hh), 30)
        y = y0 + 45
        pinks = slide.get("pink", [])
        for i, l in enumerate(lines):
            x = (W - d.textlength(l, font=f)) / 2
            if i in pinks:
                glow_text(img, (x, y), l, f, G.PINK)
                if i == pinks[-1]:
                    uy = y + size * 1.1
                    d.rounded_rectangle((x, uy, x + d.textlength(l, font=f), uy + max(8, size * 0.09)), radius=5, fill=G.PINK)
            else:
                d.text((x, y), l, font=f, fill=G.WHITE)
            y += lh
        y = y0 + hh + 40
        if slide.get("sub"):
            fs, ls = text_block(d, slide["sub"], "medium", 42, W - 200, 2)
            for l in ls:
                ctext(d, W, y, l, fs, G.TEXT); y += int(fs.size * 1.35)
        if not story:
            fsw = G.font(34, "bold"); t = "SWIPE  >>>"
            tw = d.textlength(t, font=fsw)
            yb = max(y + 30, H - 230)
            G.pill(img, (int((W - tw) / 2 - 44), yb, int((W + tw) / 2 + 44), yb + 76), "pink")
            ctext(d, W, vcenter(fsw, yb + 38), t, fsw, G.WHITE)
    elif k == "point":
        r = 60
        G.paste_sphere(img, 80 + r, top + r, r, "pink")
        n = str(slide["num"]); fn = G.font(72, "extrabold")
        d.text((80 + r - d.textlength(n, font=fn) / 2, vcenter(fn, top + r)), n, font=fn, fill=G.WHITE)
        ft, tl = text_block(d, slide["title"], "extrabold", 58, W - 330, 2, 40)
        lh = int(ft.size * 1.18)
        ty = top + r - lh * len(tl) / 2
        for l in tl:
            d.text((240, ty + (lh - ft.size) / 2 - ft.size * 0.12), l, font=ft, fill=G.WHITE); ty += lh
        y = top + 2 * r + 34
        has_fp = bool(slide.get("footprint")); has_tip = bool(slide.get("tip"))
        fb, bl = text_block(d, slide["body"], "medium", 38 if has_fp else 42, W - 220, 5 if has_fp else 8, 30)
        blh = int(fb.size * 1.4)
        bh = blh * len(bl) + 56
        G.paste_glass(img, (70, y, W - 70, y + bh), 26)
        yy = y + 28
        for l in bl:
            d.text((110, yy), l, font=fb, fill=G.TEXT); yy += blh
        y += bh + 28
        tip_h = 0
        if has_tip:
            ftp, tl2 = text_block(d, slide["tip"], "bold", 38, W - 240, 3, 28)
            tip_h = int(ftp.size * 1.35) * len(tl2) + 50
        if has_fp:
            fpd = slide["footprint"]
            lab_h = 56 if fpd.get("label") else 0
            avail = bottom - y - lab_h - (tip_h + 24 if has_tip else 0)
            hgt = int(min(avail, 72 * len(fpd["rows"]) + 70))
            footprint(img, d, (130, y, W - 130, y + hgt), fpd)
            y += hgt
            if fpd.get("label"):
                fl, ll = text_block(d, fpd["label"], "semibold", 30, W - 160, 1, 22)
                ctext(d, W, y + 14, ll[0], fl, G.PINK_L)
                y += lab_h
            y += 24
        if has_tip:
            yb = y if has_fp else max(y, bottom - tip_h)
            G.paste_glass(img, (70, yb, W - 70, yb + tip_h), 26, tint=G.PINK, tint_a=0.16, border=G.PINK_L, border_a=0.5)
            yy = yb + 25
            for l in tl2:
                ctext(d, W, yy, l, ftp, G.WHITE); yy += int(ftp.size * 1.35)
    elif k == "rule":
        ft = G.font(92, "black")
        glow_text(img, ((W - d.textlength(slide.get("title", "THE RULE"), font=ft)) / 2, top), slide.get("title", "THE RULE"), ft, G.PINK)
        n = len(slide["items"])
        gap = min(200, (bottom - top - 170) // max(n, 1))
        for i, (a, b, c) in enumerate(slide["items"]):
            y = top + 160 + i * gap
            sh = min(150, gap - 30)
            G.paste_glass(img, (70, y, W - 70, y + sh), 26)
            G.paste_sphere(img, 70 + 30 + 50, y + sh / 2, 50, "pink")
            fn = G.font(56, "extrabold"); num = str(i + 1)
            d.text((150 - d.textlength(num, font=fn) / 2, vcenter(fn, y + sh / 2)), num, font=fn, fill=G.WHITE)
            size = 46
            while size > 28 and d.textlength(a + b + c, font=G.font(size, "bold")) > W - 70 - 240 - 40:
                size -= 2
            f = G.font(size, "bold"); x = 240
            for seg, col in ((a, G.WHITE), (b, G.PINK), (c, G.WHITE)):
                if seg:
                    d.text((x, vcenter(f, y + sh / 2)), seg, font=f, fill=col); x += d.textlength(seg, font=f)
    elif k == "cta":
        ls = 230
        G.paste_logo(img, (W - ls) / 2, top + 10, ls)
        y0 = top + 300
        fs, sl = text_block(d, slide.get("sub", ""), "bold", 50, W - 260, 3, 34)
        hh = 190 + int(fs.size * 1.3) * len(sl) + 50
        G.paste_glass(img, (90, y0, W - 90, y0 + hh), 30)
        ff = G.font(118, "black"); t = slide.get("title", "FOLLOW")
        glow_text(img, ((W - d.textlength(t, font=ff)) / 2, y0 + 40), t, ff, G.PINK)
        y = y0 + 195
        for l in sl:
            ctext(d, W, y, l, fs, G.WHITE); y += int(fs.size * 1.3)
        y = y0 + hh + 40
        ctext(d, W, y, "SAVE  ·  SHARE  ·  FOLLOW", G.font(36, "bold"), G.GREY)
        ctext(d, W, bottom - 40, "Educational content. Not financial advice.", G.font(28, "medium"), G.GREY)
    elif k in ("quiz", "answer"):
        kicker(img, d, W, top, slide.get("kicker", "QUIZ"))
        y = top + 110
        if k == "quiz":
            fq, ql = text_block(d, slide["question"], "bold", 58, W - 220, 6, 40)
            qlh = int(fq.size * 1.3)
            qh = qlh * len(ql) + 70
            G.paste_glass(img, (70, y, W - 70, y + qh), 30)
            yy = y + 35
            for l in ql:
                ctext(d, W, yy, l, fq, G.WHITE); yy += qlh
            y += qh + 46
            fo = G.font(44, "bold")
            for i, o in enumerate(slide["options"]):
                ol = wrap(d, o, fo, W - 360)
                hh = max(128, 64 + 56 * len(ol))
                G.paste_glass(img, (90, y, W - 90, y + hh), min(hh // 2, 64))
                G.paste_sphere(img, 90 + 26 + 44, y + hh / 2, 44, "pink")
                lab = "ABCD"[i]; fl = G.font(48, "extrabold")
                d.text((160 - d.textlength(lab, font=fl) / 2, vcenter(fl, y + hh / 2)), lab, font=fl, fill=G.WHITE)
                yy = y + hh / 2 - 56 * len(ol) / 2
                for l in ol:
                    d.text((240, vcenter(fo, yy + 28)), l, font=fo, fill=G.WHITE); yy += 56
                y += hh + 30
        else:
            r = 100
            G.paste_sphere(img, W / 2, y + r + 10, r, "pink")
            fl = G.font(130, "black"); c = slide["correct"]
            d.text((W / 2 - d.textlength(c, font=fl) / 2, vcenter(fl, y + r + 10)), c, font=fl, fill=G.WHITE)
            y += 2 * r + 60
            fa, al = text_block(d, slide["answer"], "extrabold", 58, W - 180, 3, 40)
            for l in al:
                ctext(d, W, y, l, fa, G.WHITE); y += int(fa.size * 1.25)
            y += 36
            fe, el = text_block(d, slide["explain"], "medium", 42, W - 240, 8, 30)
            elh = int(fe.size * 1.4)
            eh = elh * len(el) + 64
            G.paste_glass(img, (70, y, W - 70, y + eh), 30)
            yy = y + 32
            for l in el:
                ctext(d, W, yy, l, fe, G.TEXT); yy += elh
        if slide.get("footer"):
            ff, fl_ = text_block(d, slide["footer"], "bold", 42, W - 250, 1, 36)
            if len(fl_) > 1:
                ff, fl_ = text_block(d, slide["footer"], "bold", 42, W - 250, 3, 30)
            flh = int(ff.size * 1.35)
            fh = flh * len(fl_) + 54
            yb = bottom - fh
            G.paste_glass(img, (100, yb, W - 100, yb + fh), 30, tint=G.PINK, tint_a=0.16, border=G.PINK_L, border_a=0.5)
            yy = yb + 27
            for l in fl_:
                ctext(d, W, yy, l, ff, G.WHITE); yy += flh
    if not story:
        f = G.font(26, "medium")
        d.text((70, H - 66), "@institutionalmetatrading", font=f, fill=G.GREY)
        if total:
            t = f"{page}/{total}"
            d.text((W - 70 - d.textlength(t, font=f), H - 66), t, font=f, fill=G.GREY)
    return img.convert("RGB")
