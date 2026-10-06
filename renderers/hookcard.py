#!/usr/bin/env python3
"""HTR hook card renderer. Brand system: Anton + Inter, black + gold."""
import argparse, os, re, subprocess, sys, glob

FONTPKGS = ["@fontsource/anton", "@fontsource/inter"]
DISPLAY_STACK = "'Anton','Archivo','DejaVu Sans Condensed','Liberation Sans Narrow',Impact,sans-serif"
TEXT_STACK = "'Inter','DejaVu Sans','Liberation Sans',Arial,sans-serif"

PALETTES = {
    "gold": dict(bg="#0A0A0B", fg="#F7F3EA", accent="#D9A441", subfg="#DED8CB",
                 muted="#8A8377", hair="rgba(217,164,65,.30)", vig="rgba(0,0,0,.60)",
                 grainmode="overlay", hl="ul"),
    "bone": dict(bg="#EFEBE3", fg="#131313", accent="#131313", subfg="#2B2926",
                 muted="#7A736A", hair="rgba(19,19,19,.22)", vig="rgba(0,0,0,.10)",
                 grainmode="multiply", hl="block"),
}
RGB = {"gold": dict(bg=(10,10,11), fg=(247,243,234), accent=(217,164,65),
                    subfg=(222,216,203), muted=(138,131,119), hair=(70,57,30)),
       "bone": dict(bg=(239,235,227), fg=(19,19,19), accent=(19,19,19),
                    subfg=(43,41,38), muted=(122,115,106), hair=(198,193,184))}
RATIOS = {"9x16": dict(w=1080, h=1920, pad=104, padtop=200, padbot=380, h1=176, sub=54, submt=52, subw=880,
                       kfs=25, dot=17, kgap=22, promise=35, mark=19, footpt=40, ulh=7),
          "1x1":  dict(w=1080, h=1080, pad=88,  padtop=120, padbot=150, h1=126, sub=41, submt=36, subw=880,
                       kfs=22, dot=15, kgap=18, promise=28, mark=16, footpt=30, ulh=5)}

def ensure_fonts(workdir):
    fd = os.path.join(workdir, "node_modules", "@fontsource")
    if os.path.isdir(os.path.join(fd, "anton")) and os.path.isdir(os.path.join(fd, "inter")):
        return fd
    try:
        subprocess.run(["npm", "init", "-y"], cwd=workdir, check=True, timeout=120,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["npm", "i", "--silent"] + FONTPKGS, cwd=workdir, check=True, timeout=300,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return fd if os.path.isdir(os.path.join(fd, "anton")) else None
    except Exception as e:
        print("WARN: brand font install failed (%s) — falling back to system faces" % e.__class__.__name__)
        return None

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def mark_accent(text, hlclass):
    return re.sub(r"\*(.+?)\*", lambda m: '<span class="hl %s">%s</span>' % (hlclass, m.group(1)), esc(text))

def face(fontdir):
    if not fontdir:
        return ""
    f = "file://" + fontdir
    return ("@font-face{font-family:'Anton';src:url('%s/anton/files/anton-latin-400-normal.woff2') format('woff2')}"
            "@font-face{font-family:'Inter';src:url('%s/inter/files/inter-latin-500-normal.woff2') format('woff2');font-weight:500}"
            "@font-face{font-family:'Inter';src:url('%s/inter/files/inter-latin-700-normal.woff2') format('woff2');font-weight:700}"
            "@font-face{font-family:'Inter';src:url('%s/inter/files/inter-latin-800-normal.woff2') format('woff2');font-weight:800}"
            % (f, f, f, f))

def page(head, sub, pal, r, fontdir):
    p = PALETTES[pal]
    headhtml = "<br>".join(esc(x.strip()) for x in head.split("|"))
    subhtml = mark_accent(sub, p["hl"])
    grain = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'"
             "%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' "
             "numOctaves='3'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)'/%3E%3C/svg%3E")
    return """<!doctype html><meta charset="utf-8"><style>
%(face)s
*{margin:0;padding:0;box-sizing:border-box}
body{background:#222}
.card{position:relative;width:%(w)spx;height:%(h)spx;overflow:hidden;background:%(bg)s;
 color:%(fg)s;font-family:%(TEXT)s}
.card::after{content:'';position:absolute;inset:0;pointer-events:none;background-image:url("%(grain)s");
 opacity:.05;mix-blend-mode:%(grainmode)s}
.card::before{content:'';position:absolute;inset:0;pointer-events:none;
 background:radial-gradient(120%% 80%% at 50%% 38%%, rgba(255,255,255,0) 40%%, %(vig)s 100%%)}
.inner{position:relative;z-index:3;display:flex;flex-direction:column;height:100%%;padding:%(padtop)spx %(pad)spx %(padbot)spx}
.kicker{display:flex;align-items:center;gap:%(kgap)spx}
.kicker .dot{width:%(dot)spx;height:%(dot)spx;background:%(accent)s;border-radius:2px;flex:none}
.kicker .txt{font-weight:800;letter-spacing:.26em;font-size:%(kfs)spx;text-transform:uppercase;white-space:nowrap}
.kicker .rule{height:2px;background:%(hair)s;flex:1}
.mid{flex:1;display:flex;flex-direction:column;justify-content:center;min-height:0}
h1{font-family:%(DISP)s;text-transform:uppercase;font-size:%(h1)spx;line-height:.93;letter-spacing:-.012em}
.sub{margin-top:%(submt)spx;font-weight:700;font-size:%(sub)spx;line-height:1.22;
 letter-spacing:-.01em;color:%(subfg)s;max-width:%(subw)spx}
.hl{color:%(accent)s;position:relative;white-space:nowrap}
.hl.block{color:%(bg)s;background:%(accent)s;padding:0 .16em;
 box-decoration-break:clone;-webkit-box-decoration-break:clone}
.hl.ul::after{content:'';position:absolute;left:0;right:0;bottom:-.16em;height:%(ulh)spx;background:%(accent)s}
.footwrap{position:relative;padding-top:%(footpt)spx}
.footwrap .rule{position:absolute;left:0;right:0;top:0;height:2px;background:%(hair)s}
.foot{display:flex;align-items:flex-end;justify-content:space-between;gap:40px}
.promise{font-weight:800;font-size:%(promise)spx;line-height:1.35}
.promise em{font-style:normal;color:%(accent)s}
.mark{text-align:right;font-weight:500;font-size:%(mark)spx;letter-spacing:.2em;
 text-transform:uppercase;color:%(muted)s;white-space:nowrap;line-height:1.5}
</style>
<div class="card"><div class="inner">
 <div class="kicker"><div class="dot"></div><div class="txt">Hard&nbsp;To&nbsp;Replace&trade;</div><div class="rule"></div></div>
 <div class="mid"><h1>%(headhtml)s</h1><div class="sub">%(subhtml)s</div></div>
 <div class="footwrap"><div class="rule"></div><div class="foot">
   <div class="promise">Become Strong. Become Useful.<br>Become <em>Hard To Replace&trade;</em></div>
   <div class="mark">The Method<br>Justin Boswell</div>
 </div></div>
</div></div>
<script>
(function(){
  var mid=document.querySelector('.mid'),h1=document.querySelector('h1'),sub=document.querySelector('.sub');
  var hs=%(h1)s, ss=%(sub)s, g=0;
  function over(){return mid.scrollHeight>mid.clientHeight||h1.scrollWidth>h1.clientWidth;}
  while(over()&&hs>72&&g++<200){hs-=3;h1.style.fontSize=hs+'px';}
  g=0;
  while(mid.scrollHeight>mid.clientHeight&&ss>28&&g++<200){ss-=1.5;sub.style.fontSize=ss+'px';}
})();
</script>""" % dict(p, **dict(r, face=face(fontdir), grain=grain, headhtml=headhtml,
                             subhtml=subhtml, DISP=DISPLAY_STACK, TEXT=TEXT_STACK))

def find_ttf(*names):
    for n in names:
        for root in ("/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")):
            hits = glob.glob(os.path.join(root, "**", n), recursive=True)
            if hits:
                return hits[0]
    return None

def render_pil(head, sub, pal, r, outpath):
    from PIL import Image, ImageDraw, ImageFont
    c = RGB[pal]
    disp_p = find_ttf("DejaVuSansCondensed-Bold.ttf", "LiberationSansNarrow-Bold.ttf", "DejaVuSans-Bold.ttf")
    text_p = find_ttf("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf")
    if not disp_p or not text_p:
        raise RuntimeError("no usable TTF on this box")
    W, H, pad = r["w"], r["h"], r["pad"]
    ptop, pbot = r.get("padtop", pad), r.get("padbot", pad)
    im = Image.new("RGB", (W, H), c["bg"]); d = ImageDraw.Draw(im)
    def F(path, size): return ImageFont.truetype(path, int(size))
    def wrap(words, font, maxw):
        lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= maxw or not cur: cur = t
            else: lines.append(cur); cur = w
        if cur: lines.append(cur)
        return lines
    kf = F(text_p, r["kfs"] * .95)
    d.rectangle([pad, ptop, pad + r["dot"], ptop + r["dot"]], fill=c["accent"])
    d.text((pad + r["dot"] + r["kgap"], ptop - 2), "H A R D  T O  R E P L A C E", font=kf, fill=c["fg"])
    forced = [x.strip() for x in head.split("|")]
    size = r["h1"]
    while size > 60:
        hf = F(disp_p, size)
        lines = []
        for seg in forced: lines += wrap(seg.upper().split(), hf, W - 2 * pad)
        hh = len(lines) * size * .96
        sf = F(text_p, r["sub"])
        slines = wrap(re.sub(r"\*", "", sub).split(), sf, r["subw"])
        sh = len(slines) * r["sub"] * 1.22
        if hh + r["submt"] + sh < H - ptop - pbot - 260: break
        size -= 4
    top, bot = ptop + r["kfs"] * 4, H - pbot - r["promise"] * 4.2
    y = top + (bot - top - (hh + r["submt"] + sh)) / 2
    for ln in lines:
        d.text((pad, y), ln, font=hf, fill=c["fg"]); y += size * .96
    y += r["submt"]
    accent_words = {w.strip(".,!?'\"").lower() for ph in re.findall(r"\*(.+?)\*", sub) for w in ph.split()}
    for ln in slines:
        x = pad
        for w in ln.split():
            col = c["accent"] if w.strip(".,!?'\"").lower() in accent_words else c["subfg"]
            d.text((x, y), w, font=sf, fill=col)
            x += d.textlength(w + " ", font=sf)
        y += r["sub"] * 1.22
    fy = H - pbot - r["promise"] * 2.9
    d.line([pad, fy - r["footpt"], W - pad, fy - r["footpt"]], fill=c["hair"], width=2)
    pf = F(text_p, r["promise"])
    d.text((pad, fy), "Become Strong. Become Useful.", font=pf, fill=c["fg"])
    d.text((pad, fy + r["promise"] * 1.35), "Become Hard To Replace", font=pf, fill=c["accent"])
    mf = F(text_p, r["mark"])
    for i, t in enumerate(("T H E  M E T H O D", "J U S T I N  B O S W E L L")):
        d.text((W - pad - d.textlength(t, font=mf), fy + r["promise"] * 1.35 + i * r["mark"] * 1.5),
               t, font=mf, fill=c["muted"])
    im.save(outpath)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", required=True)
    ap.add_argument("--sub", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--palette", default="gold", choices=list(PALETTES))
    ap.add_argument("--outdir", default="cards")
    ap.add_argument("--workdir", default=os.path.expanduser("~/htr-engine"))
    ap.add_argument("--padtop", type=int, default=None, help="top safe-zone padding px")
    ap.add_argument("--padbot", type=int, default=None, help="bottom safe-zone padding px")
    ap.add_argument("--force-pil", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.workdir, exist_ok=True); os.makedirs(a.outdir, exist_ok=True)
    for _rk, _r in RATIOS.items():
        _r.setdefault("padtop", _r["pad"]); _r.setdefault("padbot", _r["pad"])
        if a.padtop is not None: _r["padtop"] = a.padtop
        if a.padbot is not None: _r["padbot"] = a.padbot
    fontdir = ensure_fonts(a.workdir)
    outs = {rk: os.path.join(a.outdir, "HTR_hookcard_%s_%s.png" % (a.slug, rk)) for rk in RATIOS}
    mode = None
    if not a.force_pil:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                b = pw.chromium.launch()
                for rk, r in RATIOS.items():
                    f = os.path.join(a.workdir, "_card_%s.html" % rk)
                    open(f, "w").write(page(a.head, a.sub, a.palette, r, fontdir))
                    pg = b.new_page(viewport={"width": r["w"] + 80, "height": min(r["h"] + 80, 2200)})
                    pg.goto("file://" + f); pg.wait_for_timeout(900)
                    pg.query_selector(".card").screenshot(path=outs[rk]); pg.close()
                b.close()
            mode = "chromium" if fontdir else "chromium-fallback-fonts"
        except Exception as e:
            print("WARN: Chromium render failed (%s: %s)" % (e.__class__.__name__, str(e)[:120]))
    if mode is None:
        for rk, r in RATIOS.items():
            render_pil(a.head, a.sub, a.palette, r, outs[rk])
        mode = "pillow"
    for rk in RATIOS: print("rendered", outs[rk])
    note = {"chromium": "full brand quality",
            "chromium-fallback-fonts": "DEGRADED: brand fonts unavailable, system faces used",
            "pillow": "DEGRADED: Chromium unavailable, simplified Pillow render"}[mode]
    print("STATUS: %s — %s" % (mode, note))
    return 0

if __name__ == "__main__":
    sys.exit(main())
