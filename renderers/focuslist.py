#!/usr/bin/env python3
"""HTR Sunday focus list: a short numbered list of what to hold onto for a set stretch of time,
set over a generated scene of a plain wooden cross in warm light. Added 2026-10-25 at Justin's
request, after he pointed to a faith "focus list" post he liked and asked for posts SIMILAR to it
(not a copy) in the Sunday rotation.

  focuslist.py --json LIST.json --slug SLUG [--scene auto|backlit|sidelit] [--light auto|amber|candle|dawn]
               [--outdir DIR] [--workdir DIR]

LIST.json:
  {"head": "Next 90 days,|keep *four* counts.",
   "items": [{"word": "Prayer", "line": "Before the phone, every morning."}, ...]}

- head: 2 or 3 short lines (| forces a break), one *accent* word or phrase in gold.
- items: 3 to 5. "word" is 1 or 2 words, 12 characters or fewer; "line" is one plain sentence,
  9 words or fewer, saying what holding that item looks like in practice.

Writes HTR_focus_<SLUG>_4x5.png (1080x1350, Facebook) and HTR_focus_<SLUG>_9x16.png (1080x1920,
the Reel and Story; type kept out of the top 288 px and bottom 422 px). The scene (backlit or
side-lit cross, light colour, cross height) is picked from the slug unless given, so consecutive
Sundays do not look alike. Prints STATUS like the other renderers, and "TYPE TOO SMALL OR OVERFLOW"
if the copy had to shrink too far to fit.

What makes this HTR's own and not the reference post: no sky, clouds or mountain; the cross is a
rough-hewn beam in warm interior light on a near-black wall; Anton and Inter with gold numerals and
one gold accent word; every item carries a plain line saying what to do with it.
"""
import argparse, base64, hashlib, io, json, os, sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hookcard import ensure_fonts, face, esc  # noqa: E402

RATIOS = {"4x5": dict(w=1080, h=1350, padtop=118, padbot=112, pad=92, head=124, num=64, word=90, line=31, kfs=21, foot=20, linew=500,
                     geo=dict(cx=0.83, top=0.335, bar=0.115, bw=0.082, bt=0.074, bl=0.28)),
          "9x16": dict(w=1080, h=1920, padtop=288, padbot=422, pad=92, head=136, num=70, word=98, line=34, kfs=23, foot=22, linew=480,
                     geo=dict(cx=0.79, top=0.305, bar=0.090, bw=0.090, bt=0.080, bl=0.34))}
LIGHTS = {"amber": (255, 166, 84), "candle": (255, 199, 128), "dawn": (242, 214, 172)}
MIN_SCALE = 0.70

# ---------------------------------------------------------------- scene

def noise2(h, w, rng, gy, gx):
    g = rng.random((gy, gx)).astype(np.float32)
    return np.asarray(Image.fromarray(g, mode="F").resize((w, h), Image.BICUBIC), np.float32)

def fbm2(h, w, rng, base=3, octaves=5, persist=0.55):
    acc = np.zeros((h, w), np.float32); amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        acc += amp * noise2(h, w, rng, max(2, int(n * h / w)) + 1, n + 1); tot += amp; amp *= persist
    return acc / tot

def blur(a, sigma):
    """Gaussian blur of a float array (scipy if present, else 8-bit Pillow on the normalised range)."""
    try:
        from scipy.ndimage import gaussian_filter
        return gaussian_filter(a, sigma).astype(np.float32)
    except ImportError:
        lo, hi = float(a.min()), float(a.max()) or 1.0
        im = Image.fromarray(((a - lo) / (hi - lo + 1e-9) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(sigma))
        return np.asarray(im, np.float32) / 255 * (hi - lo) + lo

def noise1(n, rng, k):
    g = rng.random(k + 1).astype(np.float32)
    return np.interp(np.linspace(0, k, n), np.arange(k + 1), g).astype(np.float32)

def scene(W, H, seed, kind, light, geo):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    L = np.array(LIGHTS[light], np.float32) / 255.0
    base = np.array([12, 10, 9], np.float32) / 255.0

    # cross geometry (right side, crossing a little below the middle of the type area)
    cx = W * geo["cx"]
    bw = W * geo["bw"]                   # upright thickness
    bt = W * geo["bt"]                   # crossbar thickness
    top = H * (geo["top"] + 0.02 * rng.random())
    yc = top + H * geo["bar"]            # crossbar centre
    bl = W * geo["bl"]                   # crossbar length

    # backdrop: near-black plaster with a warm pool of light
    if kind == "backlit":
        gx, gy, r1, r2 = cx, yc - H * 0.02, 0.30, 0.075
    else:
        gx, gy, r1, r2 = W * 1.02, yc - H * 0.10, 0.55, 0.16
    d = np.sqrt(((xx - gx) / W) ** 2 + ((yy - gy) / W) ** 2)
    glow = 0.62 * np.exp(-(d / r1) ** 2) + (0.55 if kind == "backlit" else 0.20) * np.exp(-(d / r2) ** 2)
    plaster = 0.88 + 0.24 * fbm2(H, W, rng, base=4)
    img = base[None, None, :] * plaster[..., None] + glow[..., None] * L[None, None, :] * (0.55 + 0.45 * plaster[..., None])
    if kind == "backlit":
        ang = np.arctan2(yy - gy, xx - gx)
        rays = noise1(4096, rng, 90)[((ang + np.pi) / (2 * np.pi) * 4095).astype(int)]
        rays = np.clip((rays - 0.55) * 2.6, 0, 1) ** 2 * np.exp(-d / 0.55) * 0.20
        img += rays[..., None] * L[None, None, :]
    # floor falls away into darkness
    img *= (1 - 0.75 * np.clip((yy / H - 0.70) / 0.30, 0, 1) ** 1.4)[..., None]

    # cross mask with rough edges
    jit = lambda n, k, a: (noise1(n, rng, k) - 0.5) * a
    ev_l, ev_r = jit(H, 60, 5), jit(H, 60, 5)
    eh_t, eh_b = jit(W, 40, 4), jit(W, 40, 4)
    up = (xx > cx - bw / 2 + ev_l[:, None]) & (xx < cx + bw / 2 + ev_r[:, None]) & (yy > top + jit(W, 8, 6)[None, :])
    bar = (yy > yc - bt / 2 + eh_t[None, :]) & (yy < yc + bt / 2 + eh_b[None, :]) & (np.abs(xx - cx) < bl / 2 + jit(H, 8, 6)[:, None])
    mask = (up | bar).astype(np.float32)
    mask = blur(mask, 0.8)

    # wood: grain runs along each beam
    lowv = fbm2(H, W, rng, base=2, octaves=3)
    fine = noise2(H, W, rng, 40, 400)                     # streaks across x (upright grain)
    fineh = noise2(H, W, rng, 400, 40)                    # streaks across y (crossbar grain)
    ring_v = 0.5 + 0.5 * np.sin(2 * np.pi * ((xx - cx) / bw * 3.2 + 2.2 * lowv))
    ring_h = 0.5 + 0.5 * np.sin(2 * np.pi * ((yy - yc) / bt * 3.0 + 2.2 * lowv))
    on_bar = bar & ~(up & (np.abs(yy - yc) > bt / 2))
    grain = np.where(on_bar, 0.55 * ring_h + 0.45 * fineh, 0.55 * ring_v + 0.45 * fine)
    dark, mid, lite = (np.array(c, np.float32) / 255 for c in ((30, 20, 13), (74, 51, 32), (128, 92, 58)))
    t = np.clip(grain, 0, 1)[..., None]
    wood = np.where(t < 0.5, dark + (mid - dark) * (t / 0.5), mid + (lite - mid) * ((t - 0.5) / 0.5))

    # light on the wood
    across_v = np.clip((xx - (cx - bw / 2)) / bw, 0, 1)          # 0 left face .. 1 right face
    across_h = np.clip((yy - (yc - bt / 2)) / bt, 0, 1)          # 0 top .. 1 bottom
    if kind == "backlit":
        shade = 0.30 + 0.10 * np.where(on_bar, 1 - across_h, 1 - across_v)
        edge = np.where(on_bar, np.minimum(across_h, 1 - across_h) * bt, np.minimum(across_v, 1 - across_v) * bw)
        rim = np.exp(-edge / 5.0) * np.clip(glow / 0.9, 0, 1.2)
    else:
        shade = 0.28 + 0.85 * np.where(on_bar, 0.55 + 0.45 * (1 - across_h), across_v) ** 1.3
        rim = np.exp(-np.where(on_bar, across_h * bt, (1 - across_v) * bw) / 4.0) * 0.55
    shade = shade * (1 - 0.55 * np.clip((yy / H - 0.62) / 0.38, 0, 1))
    woodlit = wood * shade[..., None] + rim[..., None] * L[None, None, :] * 0.85

    if kind == "sidelit":   # soft cast shadow on the wall, to the left
        dx, dy = int(W * 0.07), int(H * 0.015)
        sh = np.zeros_like(mask); sh[dy:, :W - dx] = mask[:H - dy, dx:]   # shift left and down, no wrap
        sh = blur(sh, W * 0.018)
        img *= (1 - 0.55 * sh)[..., None]
    img = img * (1 - mask[..., None]) + woodlit * mask[..., None]

    # bloom, dust, grain, vignette
    hi = np.clip(img - 0.55, 0, 1)
    hi = np.stack([blur(hi[..., c], W * 0.02) for c in range(3)], -1)
    img = img + hi * 0.8
    dust = (rng.random((H, W)) > 0.99975).astype(np.float32)
    dust = blur(dust, 1.4) * 2.2
    img += (dust * np.clip(glow * 2.2, 0, 1))[..., None] * L[None, None, :]
    vig = np.sqrt(((xx - W * 0.5) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
    img *= (1 - 0.55 * np.clip((vig - 0.30) / 0.45, 0, 1))[..., None]
    img += rng.normal(0, 0.018, (H, W, 1)).astype(np.float32)
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB")
    buf = io.BytesIO(); out.save(buf, "JPEG", quality=93)
    boxes = [[cx - bw / 2, top, cx + bw / 2, H], [cx - bl / 2, yc - bt / 2, cx + bl / 2, yc + bt / 2]]
    return base64.b64encode(buf.getvalue()).decode(), [[round(v) for v in b] for b in boxes]

# ---------------------------------------------------------------- type

def accent(s):
    import re
    return re.sub(r"\*(.+?)\*", r'<span class="acc">\1</span>', esc(s))

def page(data, r, bg, boxes, fontdir):
    head = "<br>".join(accent(x.strip()) for x in data["head"].split("|"))
    rows = "".join('<div class="row"><div class="num">%02d</div><div class="txt"><div class="word"><span class="t">%s</span></div>'
                   '<div class="line"><span class="t">%s</span></div></div></div>' % (i + 1, esc(it["word"]), esc(it.get("line", "")))
                   for i, it in enumerate(data["items"]))
    return """<!doctype html><meta charset="utf-8"><style>
%(face)s
*{margin:0;padding:0;box-sizing:border-box}
body{background:#111}
.card{position:relative;width:%(w)spx;height:%(h)spx;overflow:hidden;background:#0b0a09 url(data:image/jpeg;base64,%(bg)s) center/cover;
 font-family:'Inter',sans-serif;color:#F4EFE6}
.shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(6,5,4,.82) 0%%,rgba(6,5,4,.62) 48%%,rgba(6,5,4,.0) 66%%)}
.inner{position:absolute;left:%(pad)spx;right:%(pad)spx;top:%(padtop)spx;bottom:%(padbot)spx;display:flex;flex-direction:column;--s:1}
.kick{display:flex;align-items:center;gap:16px;font-weight:800;font-size:calc(%(kfs)spx*var(--s));letter-spacing:.26em;text-transform:uppercase}
.kick i{display:block;width:15px;height:15px;background:#D9A441;border-radius:2px}
.kick b{flex:1;height:2px;background:rgba(217,164,65,.35)}
h1{margin-top:calc(34px*var(--s));font-family:'Anton',Impact,sans-serif;font-weight:400;text-transform:uppercase;
 font-size:calc(%(head)spx*var(--s));line-height:.96;letter-spacing:-.005em;text-shadow:0 3px 22px rgba(0,0,0,.65)}
.acc{color:#E0AE4E}
.rule{margin:calc(30px*var(--s)) 0 calc(18px*var(--s));width:132px;height:7px;background:#D9A441}
.list{flex:1;display:flex;flex-direction:column;justify-content:space-evenly;min-height:0}
.row{display:flex;align-items:flex-start;gap:calc(26px*var(--s))}
.num{font-family:'Anton',Impact,sans-serif;color:#D9A441;font-size:calc(%(num)spx*var(--s));line-height:1;width:calc(%(num)spx*1.3*var(--s));
 padding-top:calc(%(word)spx*.10*var(--s));flex:none;text-shadow:0 2px 14px rgba(0,0,0,.6)}
.word{font-family:'Anton',Impact,sans-serif;text-transform:uppercase;font-size:calc(%(word)spx*var(--s));line-height:1;letter-spacing:.03em;
 white-space:nowrap;text-shadow:0 3px 18px rgba(0,0,0,.7)}
.line{margin-top:calc(10px*var(--s));font-weight:600;font-size:calc(%(line)spx*var(--s));line-height:1.25;color:#E4DDD0;white-space:nowrap;
 text-shadow:0 2px 12px rgba(0,0,0,.85)}
.foot{margin-top:calc(22px*var(--s));font-weight:700;font-size:%(foot)spx;letter-spacing:.24em;text-transform:uppercase;color:#B8AE9E}
</style>
<div class="card"><div class="shade"></div><div class="inner">
 <div class="kick"><i></i><span>Hard&nbsp;To&nbsp;Replace&trade;</span><b></b></div>
 <h1><span class="t">%(head)s_H1</span></h1><div class="rule"></div>
 <div class="list">%(rows)s</div>
 <div class="foot">Justin Boswell</div>
</div></div>
<script>
(function(){
 var inner=document.querySelector('.inner'), s=1, g=0, BOX=%(boxjs)s;
 function over(){
   if(inner.scrollHeight>inner.clientHeight+1) return true;
   var l=document.querySelector('.list'); if(l.scrollHeight>l.clientHeight+1) return true;
   var ir=inner.getBoundingClientRect(), cr=document.querySelector('.card').getBoundingClientRect();
   var ts=document.querySelectorAll('.t');
   for(var i=0;i<ts.length;i++){var rs=ts[i].getClientRects();
     for(var j=0;j<rs.length;j++){var q=rs[j]; if(q.right>ir.right+1) return true;
       for(var k=0;k<BOX.length;k++){var b=BOX[k], m=22;   // keep type clear of the cross
         if(q.right-cr.left>b[0]-m && q.left-cr.left<b[2]+m && q.bottom-cr.top>b[1]-m && q.top-cr.top<b[3]+m) return true;}}}
   return false;}
 while(over()&&g++<80){s-=0.02;inner.style.setProperty('--s',s);}
 document.body.setAttribute('data-scale',s.toFixed(2));
})();
</script>""".replace("%(head)s_H1", head.replace("%", "%%")) % dict(r, face=face(fontdir), bg=bg, rows=rows, boxjs=json.dumps(boxes))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--scene", default="auto", choices=["auto", "backlit", "sidelit"])
    ap.add_argument("--light", default="auto", choices=["auto"] + list(LIGHTS))
    ap.add_argument("--outdir", default=os.path.expanduser("~/htr-engine/cards"))
    ap.add_argument("--workdir", default=os.path.expanduser("~/htr-engine"))
    a = ap.parse_args()
    data = json.load(open(a.json))
    items = data.get("items", [])
    probs = []
    if not 3 <= len(items) <= 5: probs.append("needs 3 to 5 items, got %d" % len(items))
    for it in items:
        if len(it.get("word", "")) > 12: probs.append("word too long: %r" % it["word"])
        if len(it.get("line", "")) > 32: probs.append("line over 32 characters: %r" % it["line"])
    if data["head"].count("*") != 2: probs.append("head needs exactly one *accent*")
    if probs:
        for p in probs: print("ERROR:", p)
        return 1
    h = int(hashlib.sha1(a.slug.encode()).hexdigest(), 16)
    kind = a.scene if a.scene != "auto" else ["backlit", "sidelit"][h % 2]
    light = a.light if a.light != "auto" else list(LIGHTS)[(h >> 3) % len(LIGHTS)]
    os.makedirs(a.outdir, exist_ok=True); os.makedirs(a.workdir, exist_ok=True)
    fontdir = ensure_fonts(a.workdir)
    from playwright.sync_api import sync_playwright
    bad = False
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for rk, r in RATIOS.items():
            bg, boxes = scene(r["w"], r["h"], h % (2 ** 32), kind, light, r["geo"])
            f = os.path.join(a.workdir, "_focus_%s.html" % rk)
            open(f, "w").write(page(data, r, bg, boxes, fontdir))
            pg = b.new_page(viewport={"width": r["w"] + 40, "height": r["h"] + 40})
            pg.goto("file://" + f); pg.wait_for_timeout(900)
            s = float(pg.evaluate("document.body.getAttribute('data-scale')") or 1)
            out = os.path.join(a.outdir, "HTR_focus_%s_%s.png" % (a.slug, rk))
            pg.query_selector(".card").screenshot(path=out); pg.close()
            flag = "  TYPE TOO SMALL OR OVERFLOW" if s < MIN_SCALE else ""
            bad = bad or bool(flag)
            print("rendered %s scale=%.2f%s" % (out, s, flag))
        b.close()
    print("SCENE: %s cross, %s light" % (kind, light))
    print("STATUS: %s" % ("chromium - full brand quality" if fontdir else "chromium-fallback-fonts - DEGRADED: brand fonts unavailable"))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
