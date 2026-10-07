#!/usr/bin/env python3
"""HTR carousel + quote-card renderer. Brand system: Anton + Inter, black + gold."""
import argparse, json, os, re, sys

DISPLAY = "'Anton','Archivo','DejaVu Sans Condensed',Impact,sans-serif"
TEXT = "'Inter','DejaVu Sans','Liberation Sans',Arial,sans-serif"

PAL = {
 "gold": dict(bg="#0A0A0B", fg="#F7F3EA", accent="#D9A441", subfg="#DED8CB",
              muted="#8A8377", hair="rgba(217,164,65,.30)", vig="rgba(0,0,0,.60)",
              grainmode="overlay", hl="ul"),
 "bone": dict(bg="#EFEBE3", fg="#131313", accent="#8E1A1F", subfg="#2B2926",
              muted="#7A736A", hair="rgba(19,19,19,.22)", vig="rgba(0,0,0,.10)",
              grainmode="multiply", hl="ul"),
    "oxblood": dict(bg="#3B0D11", fg="#F7F3EA", accent="#E9B44C", subfg="#EADFD3",
                 muted="#B39A92", hair="rgba(233,180,76,.32)", vig="rgba(0,0,0,.45)",
                 grainmode="overlay", hl="ul"),
    "navy": dict(bg="#0D1B2E", fg="#F4F1EA", accent="#E9B44C", subfg="#D9DEE6",
                 muted="#8894A6", hair="rgba(233,180,76,.30)", vig="rgba(0,0,0,.45)",
                 grainmode="overlay", hl="ul"),
    "forest": dict(bg="#0F2A1E", fg="#F4F0E4", accent="#E9B44C", subfg="#D8E0D4",
                 muted="#8FA396", hair="rgba(233,180,76,.30)", vig="rgba(0,0,0,.45)",
                 grainmode="overlay", hl="ul"),
    "mustard": dict(bg="#D9A441", fg="#0E0E0F", accent="#6E0F14", subfg="#1F1B12",
                 muted="#5E4A1C", hair="rgba(14,14,15,.30)", vig="rgba(0,0,0,.12)",
                 grainmode="multiply", hl="ul"),
}
ROT = ["oxblood", "mustard", "navy", "forest", "bone"]
def auto_palette(mode, ratio, slug):
    """Give each asset its own colour scheme so consecutive posts on a platform differ.
    The hook card (rendered separately) is gold/bone, so gold is left out here except 16x9.
    The set shifts by one each day."""
    import datetime, re
    day = datetime.date.today().toordinal()
    if ratio == "16x9": return "gold"
    m = re.search(r"-q([123])$", slug)
    if mode == "quote":
        q = m.group(1) if m else "1"
        order = {"4x5": {"2": 0, "1": 1, "3": 3}, "9x16": {"2": 2, "1": 4, "3": 0}}.get(ratio, {})
        return ROT[(order.get(q, 0) + day) % len(ROT)]
    return ROT[((2 if ratio == "4x5" else 3) + day) % len(ROT)]

SIZES = {"4x5": (1080, 1350), "9x16": (1080, 1920), "1x1": (1080, 1080), "16x9": (1200, 675)}
# safe-zone padding per ratio: (top, bottom, side)
SAFE = {"4x5": (162, 243, 86), "9x16": (288, 422, 86), "1x1": (120, 150, 86), "16x9": (70, 90, 80)}

GRAIN = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'"
         "%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' "
         "numOctaves='3'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)'/%3E%3C/svg%3E")

def face(fd):
    if not fd: return ""
    f = "file://" + fd
    return ("@font-face{font-family:'Anton';src:url('%s/anton/files/anton-latin-400-normal.woff2') format('woff2')}"
            "@font-face{font-family:'Inter';src:url('%s/inter/files/inter-latin-500-normal.woff2') format('woff2');font-weight:500}"
            "@font-face{font-family:'Inter';src:url('%s/inter/files/inter-latin-700-normal.woff2') format('woff2');font-weight:700}"
            "@font-face{font-family:'Inter';src:url('%s/inter/files/inter-latin-800-normal.woff2') format('woff2');font-weight:800}"
            % (f, f, f, f))

def esc(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def fmt(t, cls):
    """escape FIRST, then insert breaks, then wrap accent spans."""
    s = "<br>".join(x.strip() for x in esc(t).split("|"))
    return re.sub(r"\*(.+?)\*", lambda m: '<span class="hl %s">%s</span>' % (cls, m.group(1)), s)

def shell(p, w, h, pt, pb, ps, fd, body, h1fs, bodyfs):
    return """<!doctype html><meta charset="utf-8"><style>
%(face)s
*{margin:0;padding:0;box-sizing:border-box}
body{background:#222}
.card{position:relative;width:%(w)spx;height:%(h)spx;overflow:hidden;background:%(bg)s;color:%(fg)s;font-family:%(TEXT)s}
.card::after{content:'';position:absolute;inset:0;pointer-events:none;background-image:url("%(grain)s");opacity:.05;mix-blend-mode:%(grainmode)s}
.card::before{content:'';position:absolute;inset:0;pointer-events:none;background:radial-gradient(120%% 80%% at 50%% 38%%, rgba(255,255,255,0) 40%%, %(vig)s 100%%)}
.inner{position:relative;z-index:3;display:flex;flex-direction:column;height:100%%;padding:%(pt)spx %(ps)spx %(pb)spx}
.kicker{display:flex;align-items:center;gap:20px;flex:none}
.kicker .dot{width:16px;height:16px;background:%(accent)s;border-radius:2px;flex:none}
.kicker .txt{font-weight:800;letter-spacing:.26em;font-size:23px;text-transform:uppercase;white-space:nowrap}
.kicker .rule{height:2px;background:%(hair)s;flex:1}
.kicker .num{font-weight:800;letter-spacing:.18em;font-size:22px;color:%(muted)s;white-space:nowrap}
.mid{flex:1;display:flex;flex-direction:column;justify-content:center;min-height:0;padding:40px 0}
h1{font-family:%(DISP)s;text-transform:uppercase;font-size:%(h1fs)spx;line-height:.93;letter-spacing:-.012em}
.body{font-weight:700;font-size:%(bodyfs)spx;line-height:1.3;letter-spacing:-.01em;color:%(subfg)s}
h1 + .body{margin-top:40px}
.body p{margin-bottom:.72em}
.body p:last-child{margin-bottom:0}
.hl{color:%(accent)s;position:relative;white-space:nowrap}
.hl.block{color:%(bg)s;background:%(accent)s;padding:0 .14em;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.hl.ul::after{content:'';position:absolute;left:0;right:0;bottom:-.14em;height:6px;background:%(accent)s}\nh1 .hl.ul::after,.quote .hl.ul::after{display:none}\nh1 .hl.block,.quote .hl.block{padding:0 .06em}
.quote{font-family:%(DISP)s;text-transform:uppercase;font-size:%(h1fs)spx;line-height:.95;letter-spacing:-.012em}
.attrib{margin-top:46px;font-weight:500;font-size:26px;letter-spacing:.16em;text-transform:uppercase;color:%(muted)s;line-height:1.6}
.footwrap{position:relative;padding-top:34px;flex:none}
.footwrap .rule{position:absolute;left:0;right:0;top:0;height:2px;background:%(hair)s}
.foot{display:flex;align-items:flex-end;justify-content:space-between;gap:40px}
.promise{font-weight:800;font-size:30px;line-height:1.35}
.promise em{font-style:normal;color:%(accent)s}
.mark{text-align:right;font-weight:500;font-size:17px;letter-spacing:.2em;text-transform:uppercase;color:%(muted)s;white-space:nowrap;line-height:1.5}
.swipe{font-weight:800;font-size:26px;letter-spacing:.2em;text-transform:uppercase;color:%(accent)s}
</style><div class="card"><div class="inner">%(body)s</div></div>
<script>
(function(){
  var mid=document.querySelector('.mid');
  if(!mid) return;
  var h1=mid.querySelector('h1,.quote'), bd=mid.querySelector('.body');
  var hs=%(h1fs)s, bs=%(bodyfs)s, g=0;
  function over(){return mid.scrollHeight>mid.clientHeight||(h1&&h1.scrollWidth>h1.clientWidth);}
  while(h1&&over()&&hs>44&&g++<300){hs-=3;h1.style.fontSize=hs+'px';}
  g=0;
  while(bd&&mid.scrollHeight>mid.clientHeight&&bs>24&&g++<300){bs-=1.5;bd.style.fontSize=bs+'px';}
})();
</script>""" % dict(p, face=face(fd), grain=GRAIN, w=w, h=h, pt=pt, pb=pb, ps=ps,
                    DISP=DISPLAY, TEXT=TEXT, body=body, h1fs=h1fs, bodyfs=bodyfs)

KICK = '<div class="kicker"><div class="dot"></div><div class="txt">Hard&nbsp;To&nbsp;Replace&trade;</div><div class="rule"></div>%s</div>'
FOOT = ('<div class="footwrap"><div class="rule"></div><div class="foot">'
        '<div class="promise">Become Strong. Become Useful.<br>Become <em>Hard To Replace&trade;</em></div>'
        '<div class="mark">The Method<br>Justin Boswell</div></div></div>')

def paras(t, cls):
    # blank line = new paragraph; single newline = line break (keeps numbered lists and stacked quotes on their own lines)
    return "".join("<p>%s</p>" % fmt(x.strip(), cls).replace("\n", "<br>") for x in t.split("\n\n") if x.strip())

def build_slide(s, p, idx, total):
    cls = p["hl"]
    num = '<div class="num">%02d / %02d</div>' % (idx, total) if idx else ""
    mid = ""
    if s.get("head"):
        mid += '<h1>%s</h1>' % fmt(s["head"], cls)
    if s.get("body"):
        mid += '<div class="body">%s</div>' % paras(s["body"], cls)
    foot = FOOT if s.get("type") in ("cover", "close") else (
        '<div class="footwrap"><div class="rule"></div><div class="foot">'
        '<div class="swipe">%s</div><div class="mark">Justin Boswell</div></div></div>'
        % ("Swipe &rarr;" if s.get("type") != "close" else "&nbsp;"))
    return KICK % num + '<div class="mid">%s</div>' % mid + foot

def build_quote(q, attrib, p):
    cls = p["hl"]
    mid = '<div class="quote">%s</div><div class="attrib">%s</div>' % (
        fmt(q, cls), esc(attrib).replace("|", "<br>"))
    return KICK % "" + '<div class="mid">%s</div>' % mid + FOOT

def render(pages, outpaths, w, h, fd, pal, h1fs, bodyfs, pt, pb, ps):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for body, out in zip(pages, outpaths):
            os.makedirs(os.path.expanduser("~/htr-engine"), exist_ok=True)
            f = os.path.expanduser("~/htr-engine/_r.html")
            open(f, "w").write(shell(PAL[pal], w, h, pt, pb, ps, fd, body, h1fs, bodyfs))
            pg = b.new_page(viewport={"width": w + 60, "height": min(h + 60, 2200)})
            pg.goto("file://" + f); pg.wait_for_timeout(700)
            pg.query_selector(".card").screenshot(path=out); pg.close()
            print("rendered", out)
        b.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["carousel", "quote"])
    ap.add_argument("--json", help="carousel slides json file")
    ap.add_argument("--quote", help="quote text (use | for forced breaks, *word* for accent)")
    ap.add_argument("--attrib", default="The Making of a High-Value Man|Justin Boswell")
    ap.add_argument("--ratio", default="4x5", choices=list(SIZES))
    ap.add_argument("--palette", default="auto", choices=list(PAL) + ["auto"])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--outdir", default=os.path.expanduser("~/htr-engine/cards"))
    a = ap.parse_args()
    if a.palette == "auto": a.palette = auto_palette(a.mode, a.ratio, a.slug)
    print("PALETTE:", a.palette)
    os.makedirs(a.outdir, exist_ok=True)
    fd = os.path.expanduser("~/htr-engine/node_modules/@fontsource")
    if not os.path.isdir(os.path.join(fd, "anton")):
        print("WARN: brand fonts missing, system faces will be used"); fd = None
    w, h = SIZES[a.ratio]; pt, pb, ps = SAFE[a.ratio]
    if a.mode == "carousel":
        slides = json.load(open(a.json))
        total = len(slides)
        pages, outs = [], []
        for i, s in enumerate(slides, 1):
            idx = 0 if s.get("type") == "cover" else i
            pages.append(build_slide(s, PAL[a.palette], idx, total))
            outs.append(os.path.join(a.outdir, "HTR_carousel_%s_%02d.png" % (a.slug, i)))
        render(pages, outs, w, h, fd, a.palette, 112, 42, pt, pb, ps)
    else:
        pages = [build_quote(a.quote, a.attrib, PAL[a.palette])]
        outs = [os.path.join(a.outdir, "HTR_quote_%s_%s.png" % (a.slug, a.ratio))]
        render(pages, outs, w, h, fd, a.palette, 118, 40, pt, pb, ps)
    print("STATUS: chromium — full brand quality")
    return 0

if __name__ == "__main__":
    sys.exit(main())
