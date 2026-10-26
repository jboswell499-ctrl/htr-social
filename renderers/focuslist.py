#!/usr/bin/env python3
"""HTR Sunday focus list: a short numbered list of what to hold onto for a set stretch of time,
over a Christian image. Added 2026-10-25 at Justin's request, after he pointed to a faith "focus
list" post he liked and asked for posts SIMILAR to it (not a copy) in the Sunday rotation. The same
day he added: each post has to look different, never the same layout or graphic over and over.

  focuslist.py --json LIST.json --slug SLUG [--look auto|window|ledger|timeline|split|column]
               [--avoid LOOK] [--date YYYY-MM-DD] [--outdir DIR] [--workdir DIR]

LIST.json:
  {"head": "Next 90 days,|*count* these four.",
   "items": [{"word": "Prayer", "line": "Before the phone, every morning."}, ...]}

- head: 2 short lines (| forces a break), exactly one *accent* word or phrase.
- items: 3 to 5. "word" is 1 or 2 words, 12 characters or fewer; "line" is one plain sentence of
  32 characters or fewer (it never wraps), saying what holding that item looks like in practice.

FIVE LOOKS, each a different layout AND a different image (no two share either):
  window    centred type under a cross-shaped window of light cut into a dark stone wall
  ledger    aged paper, ink type in ledger rows, a letterpress-printed cross in the right margin
  timeline  deep colour field, a thin gold cross down the left edge, each item a gold node on it
  split     a backlit wooden cross photographed in the top panel, the list on a solid colour panel
  column    list on the left, a rough wooden cross in warm side or back light on the right
--look auto rotates them by Sunday (one step per week from 2026-11-01), so consecutive Sundays
never share a layout or an image and a look comes back only every fifth week. --avoid LOOK skips
that look if the rotation lands on it (pass last Sunday's look). Within a look the colours and
light still change from week to week (seeded by the slug).

Writes HTR_focus_<SLUG>_4x5.png (1080x1350, Facebook) and HTR_focus_<SLUG>_9x16.png (1080x1920,
the Reel and Story; type kept out of the top 288 px and bottom 422 px). Type is kept clear of the
cross automatically. Prints LOOK, STATUS like the other renderers, and "TYPE TOO SMALL OR OVERFLOW"
if the copy had to shrink too far to fit.

What keeps this HTR's own and not the reference post: no sky, clouds, mountain or sunrise, no
distressed type or white brush underline; Anton and Inter; every item carries a plain line.
"""
import argparse, base64, datetime, hashlib, io, json, os, re, string, sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hookcard import ensure_fonts, face, esc  # noqa: E402

LOOKS = ["window", "ledger", "timeline", "split", "column"]
ROT_START = datetime.date(2026, 11, 1)
RATIOS = {"4x5": dict(w=1080, h=1350, padtop=118, padbot=112, pad=92),
          "9x16": dict(w=1080, h=1920, padtop=288, padbot=422, pad=92)}
# type sizes per look and ratio: head, num, word, line, foot
SIZES = {"column":   {"4x5": (124, 64, 90, 31, 20), "9x16": (136, 70, 98, 34, 22)},
         "window":   {"4x5": (100, 0, 64, 27, 19), "9x16": (116, 0, 74, 30, 21)},
         "ledger":   {"4x5": (118, 58, 84, 30, 19), "9x16": (132, 64, 92, 32, 21)},
         "timeline": {"4x5": (112, 30, 84, 30, 19), "9x16": (124, 34, 92, 33, 21)},
         "split":    {"4x5": (100, 48, 66, 27, 18), "9x16": (112, 54, 72, 29, 20)}}
LIGHTS = {"amber": (255, 166, 84), "candle": (255, 199, 128), "dawn": (242, 214, 172)}
FIELDS = {"forest": (15, 42, 30), "navy": (13, 27, 46), "oxblood": (59, 13, 17), "charcoal": (24, 23, 22)}
PAPERS = {"linen": (234, 225, 205), "wheat": (228, 211, 178), "ash": (226, 222, 212)}
MIN_SCALE = 0.70

# ---------------------------------------------------------------- noise helpers

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

def finish(img, rng, vig=0.55, grain=0.018):
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = np.sqrt(((xx - W * 0.5) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
    img = img * (1 - vig * np.clip((v - 0.30) / 0.45, 0, 1))[..., None]
    img = img + rng.normal(0, grain, (H, W, 1)).astype(np.float32)
    return img

def encode(img):
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB")
    buf = io.BytesIO(); out.save(buf, "JPEG", quality=93)
    return base64.b64encode(buf.getvalue()).decode()

# ---------------------------------------------------------------- scenes

def wood_scene(W, H, rng, kind, light, geo):
    """A rough-hewn wooden cross on a dark plaster wall. Returns (float image, keep-out boxes)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    L = np.array(LIGHTS[light], np.float32) / 255.0
    base = np.array([12, 10, 9], np.float32) / 255.0
    cx, bw, bt, bl = W * geo["cx"], W * geo["bw"], W * geo["bt"], W * geo["bl"]
    top = H * (geo["top"] + 0.02 * rng.random())
    yc = top + H * geo["bar"]
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
    img *= (1 - 0.75 * np.clip((yy / H - 0.70) / 0.30, 0, 1) ** 1.4)[..., None]

    jit = lambda n, k, a: (noise1(n, rng, k) - 0.5) * a
    ev_l, ev_r = jit(H, 60, 5), jit(H, 60, 5)
    eh_t, eh_b = jit(W, 40, 4), jit(W, 40, 4)
    up = (xx > cx - bw / 2 + ev_l[:, None]) & (xx < cx + bw / 2 + ev_r[:, None]) & (yy > top + jit(W, 8, 6)[None, :])
    bar = (yy > yc - bt / 2 + eh_t[None, :]) & (yy < yc + bt / 2 + eh_b[None, :]) & (np.abs(xx - cx) < bl / 2 + jit(H, 8, 6)[:, None])
    mask = blur((up | bar).astype(np.float32), 0.8)

    lowv = fbm2(H, W, rng, base=2, octaves=3)
    fine = noise2(H, W, rng, 40, 400)
    fineh = noise2(H, W, rng, 400, 40)
    ring_v = 0.5 + 0.5 * np.sin(2 * np.pi * ((xx - cx) / bw * 3.2 + 2.2 * lowv))
    ring_h = 0.5 + 0.5 * np.sin(2 * np.pi * ((yy - yc) / bt * 3.0 + 2.2 * lowv))
    on_bar = bar & ~(up & (np.abs(yy - yc) > bt / 2))
    grain = np.where(on_bar, 0.55 * ring_h + 0.45 * fineh, 0.55 * ring_v + 0.45 * fine)
    dark, mid, lite = (np.array(c, np.float32) / 255 for c in ((30, 20, 13), (74, 51, 32), (128, 92, 58)))
    t = np.clip(grain, 0, 1)[..., None]
    wood = np.where(t < 0.5, dark + (mid - dark) * (t / 0.5), mid + (lite - mid) * ((t - 0.5) / 0.5))
    across_v = np.clip((xx - (cx - bw / 2)) / bw, 0, 1)
    across_h = np.clip((yy - (yc - bt / 2)) / bt, 0, 1)
    if kind == "backlit":
        shade = 0.30 + 0.10 * np.where(on_bar, 1 - across_h, 1 - across_v)
        edge = np.where(on_bar, np.minimum(across_h, 1 - across_h) * bt, np.minimum(across_v, 1 - across_v) * bw)
        rim = np.exp(-edge / 5.0) * np.clip(glow / 0.9, 0, 1.2)
    else:
        shade = 0.28 + 0.85 * np.where(on_bar, 0.55 + 0.45 * (1 - across_h), across_v) ** 1.3
        rim = np.exp(-np.where(on_bar, across_h * bt, (1 - across_v) * bw) / 4.0) * 0.55
    shade = shade * (1 - 0.55 * np.clip((yy / H - 0.62) / 0.38, 0, 1))
    woodlit = wood * shade[..., None] + rim[..., None] * L[None, None, :] * 0.85
    if kind == "sidelit":
        dx, dy = int(W * 0.07), int(H * 0.015)
        sh = np.zeros_like(mask); sh[dy:, :W - dx] = mask[:H - dy, dx:]
        img *= (1 - 0.55 * blur(sh, W * 0.018))[..., None]
    img = img * (1 - mask[..., None]) + woodlit * mask[..., None]
    hi = np.clip(img - 0.55, 0, 1)
    img = img + np.stack([blur(hi[..., c], W * 0.02) for c in range(3)], -1) * 0.8
    dust = blur((rng.random((H, W)) > 0.99975).astype(np.float32), 1.4) * 2.2
    img += (dust * np.clip(glow * 2.2, 0, 1))[..., None] * L[None, None, :]
    boxes = [[cx - bw / 2, top, cx + bw / 2, H], [cx - bl / 2, yc - bt / 2, cx + bl / 2, yc + bt / 2]]
    return img, boxes

def stone_window_scene(W, H, rng, light, win):
    """A dark ashlar stone wall with a cross-shaped window of light cut into it."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    L = np.array(LIGHTS[light], np.float32) / 255.0
    rh = W * 0.085
    blockv = np.zeros((H, W), np.float32); mortar = np.zeros((H, W), np.float32)
    rows = int(H / rh) + 2
    for r in range(rows):
        y0, y1 = int(r * rh), min(H, int((r + 1) * rh))
        if y0 >= H: break
        widths = rh * (1.3 + rng.random(40) * 1.1)
        bounds = np.cumsum(widths) - rng.random() * rh * 1.8
        idx = np.searchsorted(bounds, np.arange(W))
        vals = rng.normal(0, 0.07, len(bounds) + 2).astype(np.float32)
        blockv[y0:y1, :] = vals[idx][None, :]
        near = np.min(np.abs(np.arange(W)[:, None] - bounds[None, :]), axis=1) < 3
        mortar[y0:y1, near] = 1
        mortar[y0:min(H, y0 + 4), :] = 1
    tex = 0.80 + blockv + 0.22 * (fbm2(H, W, rng, base=5) - 0.5) + 0.06 * (noise2(H, W, rng, 300, 300) - 0.5)
    tex = tex * (1 - 0.45 * blur(mortar, 1.2))
    img = (np.array([36, 33, 30], np.float32) / 255)[None, None, :] * tex[..., None]

    cx, y0, wh, vw = win["cx"], win["y0"], win["wh"], win["vw"]
    ww, yc = win["ww"], win["yc"]
    m = (((np.abs(xx - cx) < vw / 2) & (yy > y0) & (yy < y0 + wh)) |
         ((np.abs(yy - yc) < vw / 2) & (np.abs(xx - cx) < ww / 2))).astype(np.float32)
    m = blur(m, 1.0)
    ring = np.clip(blur(m, 9) - m, 0, 1)
    glow = blur(m, W * 0.07) * 1.1 + blur(m, W * 0.018) * 0.7
    wb = y0 + wh
    spread = np.clip(yy - wb, 0, None)
    beam = np.clip(1 - (np.abs(xx - cx) - (ww * 0.20 + spread * 0.30)) / (W * 0.10), 0, 1)
    beam = beam * (yy > wb - 10) * np.exp(-spread / (H * 0.45)) * 0.10
    interior = (np.array([255, 244, 222], np.float32) / 255) * (0.92 + 0.08 * (1 - np.abs(yy - yc) / wh))[..., None]
    img = img + (glow * 0.55 + ring * 0.55 + beam)[..., None] * L[None, None, :] * (0.6 + 0.4 * tex[..., None])
    img = img * (1 - m[..., None]) + interior * m[..., None]
    dust = blur((rng.random((H, W)) > 0.9997).astype(np.float32), 1.3) * 2.0
    img += (dust * np.clip(beam * 8 + glow, 0, 1))[..., None] * L[None, None, :]
    pad = 26
    boxes = [[cx - vw / 2 - pad, y0 - pad, cx + vw / 2 + pad, wb + pad], [cx - ww / 2 - pad, yc - vw / 2 - pad, cx + ww / 2 + pad, yc + vw / 2 + pad]]
    return img, boxes

def paper_scene(W, H, rng, tone, cross):
    """Aged paper with a ledger margin and a letterpress-printed cross."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.array(PAPERS[tone], np.float32) / 255
    stains = fbm2(H, W, rng, base=3)
    fibers = noise2(H, W, rng, 900, 40)
    img = base[None, None, :] * (0.90 + 0.14 * stains)[..., None] * (1 - 0.035 * (fibers - 0.5))[..., None]
    e = np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy)) / W
    burn = np.clip(1 - e / 0.10, 0, 1) ** 2 * (0.6 + 0.4 * fbm2(H, W, rng, base=6))
    img = img * (1 - 0.30 * burn)[..., None] * (1 - 0.08 * burn[..., None] * np.array([0, 0.4, 0.9], np.float32))
    spots = blur((rng.random((H, W)) > 0.999993).astype(np.float32), 9) * 70
    img = img * (1 - np.clip(spots, 0, 0.18)[..., None] * np.array([0.3, 0.6, 0.9], np.float32))
    ink = np.array([110, 26, 24], np.float32) / 255
    for x in (58, 68):                                  # ledger margin double rule
        a = np.exp(-((xx - x) / 1.4) ** 2) * 0.55
        img = img * (1 - a[..., None]) + ink * a[..., None]
    x0, y0, x1, y1 = cross                        # a letterpress-printed cross in the accent ink
    cw, ch = x1 - x0, y1 - y0
    t = cw * 0.19
    cxm = (x0 + x1) / 2
    yb = y0 + ch * 0.29
    ev = (noise1(H, rng, 420) - 0.5) * 2.4
    eh = (noise1(W, rng, 420) - 0.5) * 2.4
    vert = (np.abs(xx - cxm) < t / 2 + ev[:, None]) & (yy > y0) & (yy < y1)
    horz = (np.abs(yy - yb) < t / 2 + eh[None, :]) & (xx > x0) & (xx < x1)
    speck = blur((noise2(H, W, rng, 420, 240) > 0.78).astype(np.float32), 0.7)
    press = 0.86 + 0.12 * fbm2(H, W, rng, base=6)
    a = blur((vert | horz).astype(np.float32), 0.7) * np.clip(press - 0.30 * speck, 0, 1)
    img = img * (1 - a[..., None]) + ink * a[..., None]
    boxes = [[cxm - t / 2, y0, cxm + t / 2, y1], [x0, yb - t / 2, x1, yb + t / 2]]
    return img, boxes

def field_scene(W, H, rng, field, glowpt):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.array(FIELDS[field], np.float32) / 255
    img = base[None, None, :] * (0.85 + 0.30 * fbm2(H, W, rng, base=3))[..., None]
    gx, gy = glowpt
    d = np.sqrt(((xx - gx) / W) ** 2 + ((yy - gy) / W) ** 2)
    img = img + (0.22 * np.exp(-(d / 0.35) ** 2))[..., None] * (np.array([255, 196, 110], np.float32) / 255)
    return img

# ---------------------------------------------------------------- layouts

FIT_JS = """
<script>
document.fonts.ready.then(function(){
 var inner=document.querySelector('.inner'), s=1, g=0, hs=1, BOX=$boxjs;
 function hit(q, cr){ for(var k=0;k<BOX.length;k++){var b=BOX[k], m=22;
     if(q.right-cr.left>b[0]-m && q.left-cr.left<b[2]+m && q.bottom-cr.top>b[1]-m && q.top-cr.top<b[3]+m) return true;} return false;}
 function hover(){ var ir=inner.getBoundingClientRect(), cr=document.querySelector('.card').getBoundingClientRect();
   var rs=document.querySelector('h1 .t').getClientRects();
   for(var j=0;j<rs.length;j++){ if(rs[j].right>ir.right+1||rs[j].left<ir.left-1||hit(rs[j],cr)) return true;} return false;}
 while(hover()&&g++<60){hs-=0.02;inner.style.setProperty('--hs',hs);}
 g=0;
 function over(){
   if(inner.scrollHeight>inner.clientHeight+1) return true;
   var l=document.querySelector('.list'); if(l.scrollHeight>l.clientHeight+1) return true;
   var ir=inner.getBoundingClientRect(), cr=document.querySelector('.card').getBoundingClientRect();
   var ts=document.querySelectorAll('.t');
   for(var i=0;i<ts.length;i++){var rs=ts[i].getClientRects();
     for(var j=0;j<rs.length;j++){var q=rs[j]; if(q.right>ir.right+1||q.left<ir.left-1||hit(q,cr)) return true;}}
   return false;}
 while(over()&&g++<80){s-=0.02;inner.style.setProperty('--s',s);}
 document.body.setAttribute('data-scale',s.toFixed(2)); document.body.setAttribute('data-hs',hs.toFixed(2));
 document.body.setAttribute('data-done','1');
});
</script>"""

BASE_CSS = """$face
*{margin:0;padding:0;box-sizing:border-box}
body{background:#111}
.card{position:relative;width:${w}px;height:${h}px;overflow:hidden;background:#0b0a09 url(data:image/jpeg;base64,$bg) center/cover;font-family:'Inter',sans-serif}
.inner{position:absolute;display:flex;flex-direction:column;--s:1;--hs:1}
.list{flex:1;display:flex;flex-direction:column;justify-content:space-evenly;min-height:0}
h1{white-space:nowrap;font-family:'Anton',Impact,sans-serif;font-weight:400;text-transform:uppercase;font-size:calc(${head}px*var(--s)*var(--hs));line-height:.96;letter-spacing:-.005em}
.word{font-family:'Anton',Impact,sans-serif;text-transform:uppercase;font-size:calc(${word}px*var(--s));line-height:1;letter-spacing:.03em;white-space:nowrap}
.line{margin-top:calc(9px*var(--s));font-weight:600;font-size:calc(${line}px*var(--s));line-height:1.25;white-space:nowrap}
.foot{margin-top:calc(20px*var(--s));font-weight:700;font-size:${foot}px;letter-spacing:.24em;text-transform:uppercase}
.kick{display:flex;align-items:center;gap:16px;font-weight:800;font-size:calc(${kfs}px*var(--s));letter-spacing:.26em;text-transform:uppercase}
.kick i{display:block;width:15px;height:15px;border-radius:2px}
.kick b{flex:1;height:2px}
"""

LOOK_CSS = {
 "column": """
.card{color:#F4EFE6}
.shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(6,5,4,.82) 0%,rgba(6,5,4,.62) 48%,rgba(6,5,4,0) 66%)}
.inner{left:${pad}px;right:${pad}px;top:${padtop}px;bottom:${padbot}px}
.kick i{background:#D9A441}.kick b{background:rgba(217,164,65,.35)}
h1{margin-top:calc(34px*var(--s));text-shadow:0 3px 22px rgba(0,0,0,.65)}
.acc{color:#E0AE4E}
.rule{margin:calc(30px*var(--s)) 0 calc(18px*var(--s));width:132px;height:7px;background:#D9A441}
.row{display:flex;align-items:flex-start;gap:calc(26px*var(--s))}
.num{font-family:'Anton',Impact,sans-serif;color:#D9A441;font-size:calc(${num}px*var(--s));line-height:1;width:calc(${num}px*1.3*var(--s));padding-top:calc(${word}px*.10*var(--s));flex:none}
.word{text-shadow:0 3px 18px rgba(0,0,0,.7)} .line{color:#E4DDD0;text-shadow:0 2px 12px rgba(0,0,0,.85)} .foot{color:#B8AE9E}
""",
 "window": """
.card{color:#F3EEE4}
.inner{left:${pad}px;right:${pad}px;top:${padtop}px;bottom:${padbot}px;align-items:center;text-align:center}
.gap{height:${gap}px;flex:none}
h1{text-shadow:0 3px 24px rgba(0,0,0,.8)}
.acc{color:#E8B95E}
.rule{margin:calc(22px*var(--s)) auto calc(10px*var(--s));width:110px;height:6px;background:#D9A441}
.list{align-items:center}
.row{text-align:center}
.word .n{color:#D9A441;margin-right:.32em;font-size:.6em;vertical-align:.2em}
.row+.row{margin-top:calc(16px*var(--s))}
.word{text-shadow:0 3px 18px rgba(0,0,0,.85)} .line{color:#E7E0D3;text-shadow:0 2px 12px rgba(0,0,0,.9)} .foot{color:#A99F90}
""",
 "ledger": """
.card{color:#1B1714}
.inner{left:${padl}px;right:${pad}px;top:${padtop}px;bottom:${padbot}px}
.kick{color:#7A1C1C}.kick i{background:#7A1C1C}.kick b{background:rgba(122,28,28,.30)}
h1{margin-top:calc(30px*var(--s))}
.acc{color:#7A1C1C}
.rule{margin:calc(26px*var(--s)) 0 calc(8px*var(--s));width:120px;height:6px;background:#7A1C1C}
.row{display:flex;align-items:flex-start;gap:calc(24px*var(--s));width:${roww}px;border-bottom:2px solid rgba(122,28,28,.26);padding-bottom:calc(14px*var(--s))}
.num{font-family:'Anton',Impact,sans-serif;color:#7A1C1C;font-size:calc(${num}px*var(--s));line-height:1;width:calc(${num}px*1.3*var(--s));padding-top:calc(${word}px*.10*var(--s));flex:none}
.line{color:#3D322B} .foot{color:#6B5A4C}
""",
 "timeline": """
.card{color:#F2EDE3}
.vline{position:absolute;left:${vx}px;top:${vtop}px;bottom:0;width:8px;background:linear-gradient(#E3B65C,#B0802F)}
.hbar{position:absolute;left:${hx}px;top:${hy}px;width:${hw}px;height:8px;background:#E3B65C}
.inner{left:${tx}px;right:${pad}px;top:${padtop}px;bottom:${padbot}px}
h1{margin-top:${headtop}px;text-shadow:0 3px 18px rgba(0,0,0,.5)}
.acc{color:#E8BA60}
.rule{margin:calc(26px*var(--s)) 0 calc(8px*var(--s));width:110px;height:6px;background:#E3B65C}
.row{position:relative}
.node{position:absolute;left:${nodel}px;top:calc(${word}px*var(--s)*.5 - ${r}px);width:${d}px;height:${d}px;border-radius:50%;background:#E3B65C;
 color:${fieldhex};font-family:'Anton',Impact,sans-serif;font-size:${nfs}px;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 7px ${fieldhex}}
.line{color:#DCD6CA} .foot{color:#B9AF9D}
""",
 "split": """
.card{color:#F3EEE4}
.panel{position:absolute;left:0;right:0;top:${ph}px;bottom:0;background:${fieldhex}}
.panel::after{content:'';position:absolute;inset:0;background:radial-gradient(120% 70% at 30% 0%,rgba(255,255,255,.07),rgba(0,0,0,.25))}
.seam{position:absolute;left:0;right:0;top:${seamy}px;height:6px;background:#D9A441}
.inner{left:${pad}px;right:${pad}px;top:${itop}px;bottom:${padbot}px}
.acc{color:#E8B95E}
.rule{margin:calc(22px*var(--s)) 0 calc(6px*var(--s));width:110px;height:6px;background:#D9A441}
.row{display:flex;align-items:flex-start;gap:calc(22px*var(--s))}
.num{font-family:'Anton',Impact,sans-serif;color:#D9A441;font-size:calc(${num}px*var(--s));line-height:1;width:calc(${num}px*1.3*var(--s));padding-top:calc(${word}px*.10*var(--s));flex:none}
.line{color:#E2DBCE} .foot{color:#B5AB9B}
"""}

def rows_html(look, items):
    out = []
    for i, it in enumerate(items):
        w, l = esc(it["word"]), esc(it.get("line", ""))
        if look == "window":
            out.append('<div class="row"><div class="word"><span class="t"><span class="n">%02d</span>%s</span></div>'
                       '<div class="line"><span class="t">%s</span></div></div>' % (i + 1, w, l))
        elif look == "timeline":
            out.append('<div class="row"><div class="node">%d</div><div class="word"><span class="t">%s</span></div>'
                       '<div class="line"><span class="t">%s</span></div></div>' % (i + 1, w, l))
        else:
            out.append('<div class="row"><div class="num">%02d</div><div class="txt"><div class="word"><span class="t">%s</span></div>'
                       '<div class="line"><span class="t">%s</span></div></div></div>' % (i + 1, w, l))
    return "".join(out)

KICK = '<div class="kick"><i></i><span>Hard&nbsp;To&nbsp;Replace&trade;</span><b></b></div>'

def body_html(look, head, rows):
    h1 = '<h1><span class="t">%s</span></h1><div class="rule"></div>' % head
    lst = '<div class="list">%s</div>' % rows
    if look == "column":
        return '<div class="shade"></div><div class="inner">%s%s%s<div class="foot">Justin Boswell</div></div>' % (KICK, h1, lst)
    if look == "window":
        return '<div class="inner"><div class="gap"></div>%s%s<div class="foot">Justin Boswell &middot; Hard To Replace</div></div>' % (h1, lst)
    if look == "ledger":
        return '<div class="inner">%s%s%s<div class="foot">Justin Boswell</div></div>' % (KICK, h1, lst)
    if look == "timeline":
        return ('<div class="vline"></div><div class="hbar"></div><div class="inner">%s%s'
                '<div class="foot">Justin Boswell &middot; Hard To Replace</div></div>' % (h1, lst))
    if look == "split":
        return ('<div class="panel"></div><div class="seam"></div><div class="inner">%s%s'
                '<div class="foot">Justin Boswell &middot; Hard To Replace</div></div>' % (h1, lst))

def hexc(rgb): return "#%02x%02x%02x" % rgb

def build(look, data, rk, r, seed, fontdir):
    """Return (html, variant description) for one look at one ratio."""
    rng = np.random.default_rng(seed)
    W, H, pad, ptop, pbot = r["w"], r["h"], r["pad"], r["padtop"], r["padbot"]
    hs, ns, wsz, ls, fs = SIZES[look][rk]
    v = dict(w=W, h=H, pad=pad, padtop=ptop, padbot=pbot, head=hs, num=ns, word=wsz, line=ls, foot=fs,
             kfs=21 if rk == "4x5" else 23, face=face(fontdir))
    if look == "column":
        kind = ["backlit", "sidelit"][seed % 2]; light = list(LIGHTS)[(seed >> 3) % 3]
        geo = (dict(cx=0.83, top=0.335, bar=0.115, bw=0.082, bt=0.074, bl=0.28) if rk == "4x5"
               else dict(cx=0.79, top=0.335, bar=0.090, bw=0.090, bt=0.080, bl=0.34))
        img, boxes = wood_scene(W, H, rng, kind, light, geo)
        img = finish(img, rng); desc = "%s wooden cross, %s light" % (kind, light)
    elif look == "window":
        light = ["candle", "dawn", "amber"][(seed >> 3) % 3]
        wh = 330 if rk == "9x16" else 230
        win = dict(cx=W / 2, y0=ptop + 6, wh=wh, vw=wh * 0.16, ww=wh * 0.62)
        win["yc"] = win["y0"] + wh * 0.30
        img, boxes = stone_window_scene(W, H, rng, light, win)
        img = finish(img, rng, vig=0.5); desc = "cross window in stone, %s light" % light
        v["gap"] = int(win["y0"] - ptop + wh + 76)
    elif look == "ledger":
        tone = list(PAPERS)[(seed >> 3) % 3]
        cw = int(W * 0.20); ch = int(cw * 1.8)
        ymid = ptop + (H - ptop - pbot) * (0.62 if rk == "9x16" else 0.64)
        cross = (W - 72 - cw, int(ymid - ch / 2), W - 72, int(ymid + ch / 2))
        img, boxes = paper_scene(W, H, rng, tone, cross)
        img = finish(img, rng, vig=0.18, grain=0.012); desc = "%s paper, printed cross" % tone
        v["padl"] = pad + 6; v["roww"] = int(cross[0] - 40 - (pad + 6))
    elif look == "timeline":
        field = list(FIELDS)[(seed >> 3) % 4]
        vx = pad + 36; hy = ptop + 30; arm = 70
        img = field_scene(W, H, rng, field, (vx, hy)); boxes = []
        img = finish(img, rng, vig=0.45); desc = "gold line cross on %s" % field
        R = SIZES[look][rk][1]
        v.update(vx=vx - 4, vtop=ptop - 30, hx=vx - arm, hy=hy - 4, hw=2 * arm, tx=vx + 74, headtop=84,
                 r=R, d=2 * R, nodel=-(74 + R), nfs=int(R * 1.05), fieldhex=hexc(FIELDS[field]))
    elif look == "split":
        field = ["oxblood", "navy", "forest", "charcoal"][(seed >> 3) % 4]
        light = list(LIGHTS)[(seed >> 5) % 3]
        ph = int(H * (0.34 if rk == "9x16" else 0.33))
        top_img, _ = wood_scene(W, ph, rng, "backlit", light, dict(cx=0.5, top=0.10, bar=0.24, bw=0.075, bt=0.065, bl=0.44))
        img = np.zeros((H, W, 3), np.float32); img[:ph] = top_img
        img[ph:] = np.array(FIELDS[field], np.float32) / 255
        img = finish(img, rng, vig=0.35); boxes = [[0, 0, W, ph - 24]]
        desc = "backlit cross panel over %s, %s light" % (field, light)
        v.update(ph=ph, seamy=ph - 3, itop=ph + 46, fieldhex=hexc(FIELDS[field]))
    v["bg"] = encode(img)
    v["boxjs"] = json.dumps([[round(x) for x in b] for b in boxes])
    head = "<br>".join(re.sub(r"\*(.+?)\*", r'<span class="acc">\1</span>', esc(x.strip())) for x in data["head"].split("|"))
    css = string.Template(BASE_CSS + LOOK_CSS[look]).safe_substitute(v)
    html = ('<!doctype html><meta charset="utf-8"><style>%s</style><div class="card">%s</div>%s'
            % (css, body_html(look, head, rows_html(look, data["items"])), string.Template(FIT_JS).safe_substitute(v)))
    return html, desc

def pick_look(date, avoid=None):
    i = ((date - ROT_START).days // 7) % len(LOOKS)
    lk = LOOKS[i]
    if avoid and lk == avoid:
        lk = LOOKS[(i + 1) % len(LOOKS)]
    return lk

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--look", default="auto", choices=["auto"] + LOOKS)
    ap.add_argument("--avoid", default=None, help="a look to skip if the rotation lands on it (last Sunday's)")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD for the rotation (default: today in New York)")
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
    if a.date:
        d = datetime.date.fromisoformat(a.date)
    else:
        import zoneinfo
        d = datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York")).date()
    look = a.look if a.look != "auto" else pick_look(d, a.avoid)
    seed = int(hashlib.sha1(a.slug.encode()).hexdigest(), 16) % (2 ** 32)
    os.makedirs(a.outdir, exist_ok=True); os.makedirs(a.workdir, exist_ok=True)
    fontdir = ensure_fonts(a.workdir)
    from playwright.sync_api import sync_playwright
    bad, desc = False, ""
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for rk, r in RATIOS.items():
            html, desc = build(look, data, rk, r, seed, fontdir)
            f = os.path.join(a.workdir, "_focus_%s.html" % rk)
            open(f, "w").write(html)
            pg = b.new_page(viewport={"width": r["w"] + 40, "height": r["h"] + 40})
            pg.goto("file://" + f); pg.wait_for_selector("body[data-done]", state="attached", timeout=20000); pg.wait_for_timeout(200)
            s = float(pg.evaluate("document.body.getAttribute('data-scale')") or 1)
            hsc = float(pg.evaluate("document.body.getAttribute('data-hs')") or 1)
            out = os.path.join(a.outdir, "HTR_focus_%s_%s.png" % (a.slug, rk))
            pg.query_selector(".card").screenshot(path=out); pg.close()
            flag = "  TYPE TOO SMALL OR OVERFLOW" if s < MIN_SCALE or s * hsc < 0.58 else ""
            bad = bad or bool(flag)
            print("rendered %s scale=%.2f head=%.2f%s" % (out, s, s * hsc, flag))
        b.close()
    print("LOOK: %s (%s)" % (look, desc))
    print("STATUS: %s" % ("chromium - full brand quality" if fontdir else "chromium-fallback-fonts - DEGRADED: brand fonts unavailable"))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
