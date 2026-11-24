#!/usr/bin/env python3
"""Musica "immersiva" per i Reel v2 (dal 24/11/2026): stereo, riverbero, sidechain.

render(path, dur, hit, thuds, t_rules, t_outro, style, seed)
  - intro filtrata che si apre (0 -> 1,5 s), beat pieno subito
  - riser + 0,25 s di silenzio prima del colpo, poi impatto con coda di riverbero
  - drop pieno sulla regola, outro che si chiude in filtro
Stili: "dark_trap" (minore, 808, hi-hat in terzine, pad cinematico)
       "cinematic" (archi/pad larghi, tamburi epici, pulsazione in ottavi)
       "synthwave"  (basso in ottavi, arpeggio luminoso, rullante con gated reverb)
"""
import wave
import numpy as np
from scipy.signal import fftconvolve, lfilter

SR = 44100
STYLES = ("dark_trap", "cinematic", "synthwave")


def nf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def onepole_lp(x, cutoff):
    """Passa-basso a un polo con frequenza di taglio variabile (array o numero)."""
    cutoff = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    a = np.exp(-2 * np.pi * np.clip(cutoff, 20, SR / 2 - 100) / SR)
    # blocchi da 256 campioni a coefficiente costante: veloce e senza click udibili
    y = np.zeros_like(x); z = 0.0
    for i in range(0, len(x), 256):
        aa = a[i]; seg = x[i:i + 256]
        out, zf = lfilter([1 - aa], [1, -aa], seg, zi=[z * aa])
        y[i:i + 256] = out; z = out[-1]
    return y


def reverb_ir(seconds, seed, damp=3.0):
    rng = np.random.default_rng(seed)
    n = int(SR * seconds); t = np.arange(n) / SR
    env = np.exp(-t * damp / seconds * 2.2)
    irL = rng.normal(0, 1, n) * env; irR = rng.normal(0, 1, n) * env
    irL = onepole_lp(irL, 6000); irR = onepole_lp(irR, 6000)
    irL[:int(0.012 * SR)] = 0; irR[:int(0.017 * SR)] = 0   # pre-delay
    k = 1 / np.sqrt(np.sum(irL ** 2))
    return irL * k, irR * k


class Mix:
    def __init__(self, dur):
        self.n = int(SR * dur)
        self.dry = np.zeros((2, self.n)); self.wet = np.zeros((2, self.n))
        self.duck = np.zeros((2, self.n))   # strumenti che "respirano" col kick

    def add(self, sig, t0, gain=1.0, pan=0.0, rev=0.0, duck=False):
        i0 = int(t0 * SR)
        if i0 >= self.n or len(sig) == 0:
            return
        if i0 < 0:
            sig = sig[-i0:]; i0 = 0
        sig = sig[: self.n - i0] * gain
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        tgt = self.duck if duck else self.dry
        tgt[0, i0:i0 + len(sig)] += sig * l; tgt[1, i0:i0 + len(sig)] += sig * r
        if rev:
            self.wet[0, i0:i0 + len(sig)] += sig * l * rev; self.wet[1, i0:i0 + len(sig)] += sig * r * rev


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.1):
    t = np.arange(n) / SR; dur = n / SR
    e = np.where(t < a, t / a, s + (1 - s) * np.exp(-(t - a) / max(d, 1e-3)))
    rel = np.clip((dur - t) / r, 0, 1)
    return e * rel


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((t * f + phase) % 1) - 1


def supersaw(m, n, rng, voices=7, spread=0.18):
    out = np.zeros(n)
    for v in range(voices):
        det = (v - (voices - 1) / 2) / ((voices - 1) / 2) * spread
        out += saw(nf(m + det), n, rng.random())
    return out / voices


def kick(punch=1.0):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 160 * np.exp(-t * 38) * punch
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    click = np.random.default_rng(3).normal(0, 1, n) * np.exp(-t * 400) * 0.3
    return np.tanh((s + click) * 1.6)


def snare(rng, tone=190, length=0.35, noise=0.9):
    n = int(length * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * tone * t) * np.exp(-t * 22)
    nz = rng.normal(0, 1, n); nz = nz - onepole_lp(nz, 1800)
    return np.tanh((body * 0.8 + nz * noise * 0.7 * np.exp(-t * 26)) * 1.2)


def hat(rng, open_=False):
    n = int((0.25 if open_ else 0.05) * SR); t = np.arange(n) / SR
    nz = rng.normal(0, 1, n); nz = nz - onepole_lp(nz, 7000)
    return nz * np.exp(-t * (14 if open_ else 110))


def sub808(m, length, glide_from=None):
    n = int(length * SR); t = np.arange(n) / SR
    f = np.full(n, nf(m))
    if glide_from is not None:
        f = nf(m) + (nf(glide_from) - nf(m)) * np.exp(-t * 18)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    s = np.tanh(s * 2.2) * 0.8 + np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4
    att = np.minimum(1, t / 0.004)
    return s * att * np.exp(-t * 1.1) * np.clip((length - t) / 0.03, 0, 1)


def pluck(m, length=0.35, bright=1.0):
    n = int(length * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * nf(m) * t) + 0.5 * np.sin(2 * np.pi * nf(m) * 2 * t) * np.exp(-t * 12 * bright)
         + 0.25 * np.sign(np.sin(2 * np.pi * nf(m) * t)) * np.exp(-t * 30))
    return s * np.exp(-t * 7)


def riser(length, rng):
    n = int(length * SR); t = np.arange(n) / SR; p = t / length
    nz = rng.normal(0, 1, n)
    nz = onepole_lp(nz, 300 + 9000 * p ** 2) - onepole_lp(nz, 150 + 2000 * p ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * p ** 2) / SR) * 0.25
    return (nz * 1.6 + tone) * p ** 1.6


def impact(rng):
    n = int(2.2 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(32 + 90 * np.exp(-t * 6)) / SR) * np.exp(-t * 2.2)
    crash = rng.normal(0, 1, n); crash = crash - onepole_lp(crash, 3000)
    return np.tanh(boom * 1.8) + crash * np.exp(-t * 4.5) * 0.3


PROGS = {   # (accordi come note MIDI di base, bpm, radice per il basso)
    "dark_trap": ([[57, 60, 64], [53, 57, 60], [48, 52, 55], [52, 55, 59]], 140),   # Am F C Em
    "cinematic": ([[50, 53, 57], [46, 50, 53], [43, 46, 50], [45, 49, 52]], 120),   # Dm Bb Gm A
    "synthwave": ([[45, 48, 52], [41, 45, 48], [43, 47, 50], [40, 43, 47]], 110),   # Am F G Em
}


def render(path, dur, hit, thuds=(), t_rules=None, t_outro=None, style="dark_trap", seed=0):
    style = style if style in PROGS else "dark_trap"
    rng = np.random.default_rng(seed)
    chords, bpm = PROGS[style]
    beat = 60 / bpm; bar = beat * 4
    mx = Mix(dur)
    t_rules = t_rules or dur * 0.65; t_outro = t_outro or dur * 0.85
    gap0, gap1 = hit - 0.25, hit          # silenzio di tensione prima del colpo

    def silent(t):
        return gap0 <= t < gap1

    # ---- PAD / archi (sidechain) ----
    nbar = int(dur / bar) + 2
    for b in range(nbar):
        t0 = b * bar
        if t0 >= dur: break
        ch = chords[b % 4]; n = int(bar * SR) + int(0.3 * SR)
        for j, m in enumerate(ch):
            s = supersaw(m + 12, n, rng, voices=7 if style != "cinematic" else 9,
                         spread=0.22 if style == "cinematic" else 0.15)
            s *= env_adsr(n, a=0.08 if style == "cinematic" else 0.02, d=1.5, s=0.75, r=0.3)
            mx.add(s, t0, gain=0.07, pan=(j - 1) * 0.6, rev=0.5, duck=True)
        if style == "cinematic":   # ottava bassa d'archi
            s = supersaw(ch[0], n, rng, voices=5, spread=0.1) * env_adsr(n, a=0.15, d=2, s=0.8, r=0.3)
            mx.add(s, t0, gain=0.06, rev=0.4, duck=True)

    # ---- BASSO ----
    for b in range(nbar):
        t0 = b * bar; root = chords[b % 4][0] - 24
        if style == "dark_trap":
            for k, (pos, ln, gl) in enumerate(((0, 1.5, None), (1.75, 0.5, None), (2.5, 1.4, root + 7))):
                ts = t0 + pos * beat
                if ts < dur and not silent(ts):
                    mx.add(sub808(root if gl is None else root, ln * beat, glide_from=gl), ts, gain=0.55)
        else:
            for k in range(8):
                ts = t0 + k * beat / 2
                if ts >= dur or silent(ts): continue
                m = root + (12 if (style == "synthwave" and k % 2) else 0)
                n = int(beat / 2 * SR)
                s = onepole_lp(saw(nf(m), n), 900) * env_adsr(n, a=0.003, d=0.12, s=0.5, r=0.03)
                mx.add(s + sub808(m, beat / 2) * 0.5, ts, gain=0.32, duck=True)

    # ---- ARPEGGIO / plucks con delay ----
    step = beat / (3 if style == "dark_trap" else 4)
    k = 0
    while k * step < dur:
        ts = k * step; b = int(ts / bar); ch = chords[b % 4]
        if not silent(ts) and (style != "cinematic" or ts > 1.0):
            m = ch[(k * 2) % 3] + (24 if style != "cinematic" else 12) + (12 if k % 8 == 7 else 0)
            g = 0.05 if style == "dark_trap" else 0.07
            p = pluck(m, 0.3, bright=0.6 if style == "dark_trap" else 1.0)
            pan = 0.5 * np.sin(k * 0.9)
            mx.add(p, ts, gain=g, pan=pan, rev=0.35)
            mx.add(p, ts + beat * 0.75, gain=g * 0.45, pan=-pan, rev=0.4)   # eco ping-pong
        k += 1

    # ---- BATTERIA ----
    kk = kick(1.2 if style == "cinematic" else 1.0)
    kick_times = []
    for b in range(nbar):
        t0 = b * bar
        if style == "dark_trap":
            pats = [0, 2.75, 3.5] if b % 2 else [0, 1.5, 2.75]
            snares = [2]
        elif style == "cinematic":
            pats = [0, 1.5, 2, 3.5]; snares = [1, 3]
        else:
            pats = [0, 1, 2, 3]; snares = [1, 3]
        for p in pats:
            ts = t0 + p * beat
            if ts < dur and not silent(ts):
                mx.add(kk, ts, gain=0.9); kick_times.append(ts)
        for p in snares:
            ts = t0 + p * beat
            if ts < dur and not silent(ts):
                sn = snare(rng, tone=180 if style != "cinematic" else 120, length=0.5 if style == "cinematic" else 0.35)
                mx.add(sn, ts, gain=0.42, rev=0.45 if style == "synthwave" else 0.2)
                if style == "cinematic":
                    mx.add(kick(0.6), ts, gain=0.5, rev=0.6)      # tom profondo
    # hi-hat
    hstep = beat / 2 if style != "dark_trap" else beat / 2
    k = 0
    while k * hstep < dur:
        ts = k * hstep
        if not silent(ts) and ts > 0.2:
            if style == "dark_trap" and k % 8 == 6:      # rullata in terzine
                for r in range(3):
                    mx.add(hat(rng), ts + r * hstep / 3, gain=0.16, pan=0.3, rev=0.1)
            else:
                mx.add(hat(rng, open_=(k % 4 == 2 and style == "synthwave")), ts,
                       gain=0.14 if k % 2 else 0.1, pan=0.25, rev=0.1)
        k += 1

    # ---- TENSIONE: riser prima del colpo, impatto, colpi secondari ----
    rl = min(2.0, max(0.8, hit - 0.6))
    mx.add(riser(rl, rng), gap0 - rl, gain=0.22, rev=0.4)
    mx.add(impact(rng), hit, gain=0.75, rev=0.45)
    for th in thuds:
        if abs(th - hit) > 0.15:
            mx.add(kick(0.8), th, gain=0.55, rev=0.5)
    # whoosh ai cambi di scena
    for ts in (t_rules, t_outro):
        mx.add(riser(0.5, rng)[::-1] * 0.8, ts, gain=0.15, rev=0.5)

    # ---- SIDECHAIN sui pad ----
    sc = np.ones(mx.n)
    for kt in kick_times:
        i0 = int(kt * SR); ln = int(beat * SR * 0.9)
        seg = 1 - 0.75 * np.exp(-np.arange(ln) / SR * 9)
        sc[i0:i0 + ln] = np.minimum(sc[i0:i0 + ln], seg[: max(0, min(ln, mx.n - i0))])
    mx.dry += mx.duck * sc[None, :]

    # silenzio di tensione: taglio netto di tutto tranne il riser (gia' nel dry)
    i0, i1 = int(gap0 * SR), int(gap1 * SR)

    # ---- RIVERBERO ----
    irL, irR = reverb_ir(2.4 if style != "synthwave" else 1.6, seed + 11)
    wet = np.stack([fftconvolve(mx.wet[0], irL)[: mx.n], fftconvolve(mx.wet[1], irR)[: mx.n]])
    out = mx.dry + wet * 0.22

    # ---- FILTRI DI SCENA: intro che si apre, outro che si chiude ----
    t = np.arange(mx.n) / SR
    cut = np.full(mx.n, 18000.0)
    intro = t < 1.5
    cut[intro] = 600 + 17400 * (t[intro] / 1.5) ** 2
    oc = t > t_outro + 0.4
    cut[oc] = 18000 - 16500 * np.clip((t[oc] - t_outro - 0.4) / max(0.5, dur - t_outro - 0.4), 0, 1) ** 0.7
    out = np.stack([onepole_lp(out[0], cut), onepole_lp(out[1], cut)])
    out[:, i0:i1] *= np.linspace(1, 0.15, i1 - i0)[None, :]

    # ---- MASTER ----
    out = np.tanh(out * 1.25)
    fo = int(0.6 * SR); out[:, -fo:] *= np.linspace(1, 0, fo)[None, :]
    out /= max(1e-6, np.abs(out).max()) / 0.89
    pcm = (out.T * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    import sys
    st = sys.argv[1] if len(sys.argv) > 1 else "dark_trap"
    render(f"/tmp/music_{st}.wav", 9.3, 3.6, (), 5.8, 8.0, st)
    print("ok", st)
