#!/usr/bin/env python3
"""HTR carousel + quote-card renderer. Brand system: Anton + Inter, black + gold.

Quote cards also come in textured "styles" (--style): brush, paper and swipe add a
hand-lettered accent word, worn type and a lit, grained background. Carousels stay clean."""
import argparse, json, os, re, subprocess, sys, urllib.parse

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

# ---- quote-card styles -------------------------------------------------------
BRUSH = "'Permanent Marker','Anton',Impact,sans-serif"
STYLE_PAL = {
 "brush": dict(bg="#0B0908", fg="#EFE8DA", accent="#C9A06A", subfg="#DED8CB", muted="#8F877A",
               hair="rgba(201,160,106,.32)", vig="rgba(0,0,0,.70)", grainmode="overlay", hl="brushw"),
 "paper": dict(bg="#E3DAC8", fg="#16130F", accent="#8E1A1F", subfg="#2B2926", muted="#6B6256",
               hair="rgba(22,19,15,.28)", vig="rgba(70,45,10,.22)", grainmode="multiply", hl="brushw"),
 "swipe": dict(bg="#11161B", fg="#F1EDE4", accent="#D9A441", subfg="#D9DEE6", muted="#8894A6",
               hair="rgba(217,164,65,.30)", vig="rgba(0,0,0,.60)", grainmode="overlay", hl="swipew"),
}
STYLE_ROT = ["brush", "clean", "paper", "swipe"]
def auto_style(mode, slug):
    """Quote cards rotate through the styles: each of the day's three quotes gets a different
    one, and the set shifts by one each day. A quote keeps its style across ratios."""
    import datetime
    if mode != "quote": return "clean"
    m = re.search(r"-q([123])$", slug)
    q = int(m.group(1)) if m else 1
    return STYLE_ROT[(datetime.date.today().toordinal() + q) % len(STYLE_ROT)]

def svg_uri(svg): return "data:image/svg+xml," + urllib.parse.quote(svg)
def _svg(w, h, inner, extra=""):
    return "<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' %s>%s</svg>" % (w, h, extra, inner)
# speckle that eats small holes out of the type, and long streaks that read as a dry brush
SPECK = svg_uri(_svg(600, 600, "<filter id='g' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' "
    "baseFrequency='0.55' numOctaves='2' seed='7'/><feColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -16 12.2'/>"
    "</filter><rect width='600' height='600' filter='url(#g)'/>"))
STREAK = svg_uri(_svg(900, 600, "<filter id='g' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' "
    "baseFrequency='0.004 0.12' numOctaves='2' seed='3'/><feColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -14 11.2'/>"
    "</filter><rect width='900' height='600' filter='url(#g)'/>"))
WOOD = svg_uri(_svg(1200, 800, "<filter id='g' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' "
    "baseFrequency='0.0022 0.07' numOctaves='3' seed='11'/><feColorMatrix values='0 0 0 0 .78 0 0 0 0 .56 0 0 0 0 .34 0 0 0 2.4 -.85'/>"
    "</filter><rect width='1200' height='800' filter='url(#g)'/>"))
BLOTCH = svg_uri(_svg(1200, 1200, "<filter id='g' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' "
    "baseFrequency='0.006' numOctaves='4' seed='21'/><feColorMatrix values='0 0 0 0 .35 0 0 0 0 .24 0 0 0 0 .12 0 0 0 2.2 -.8'/>"
    "</filter><rect width='1200' height='1200' filter='url(#g)'/>"))
def stroke_uri(color, fat):
    """A rough hand-drawn paint stroke: thin = underline, fat = a swipe behind the word."""
    path = ("M46 51 C 110 48, 180 54, 250 50 S 320 48, 354 51" if fat else "M6 16 C 70 8, 140 20, 215 12 S 330 9, 394 14")
    return svg_uri(_svg(400, 100 if fat else 28,
        "<filter id='r' filterUnits='userSpaceOnUse' x='0' y='0' width='400' height='%d'><feTurbulence type='fractalNoise' baseFrequency='%s' "
        "numOctaves='2' seed='5'/><feDisplacementMap in='SourceGraphic' scale='%d'/></filter>"
        "<path d='%s' fill='none' stroke='%s' stroke-width='%d' stroke-linecap='round' filter='url(#r)'/>"
        % (100 if fat else 28, "0.012 0.22" if fat else "0.03 0.6", 9 if fat else 6, path, color, 84 if fat else 9),
        "viewBox='0 0 400 %d' preserveAspectRatio='none'" % (100 if fat else 28)))

def style_css(style, p, fd):
    if style == "clean": return "", ""
    font = ("@font-face{font-family:'Permanent Marker';src:url('file://%s/permanent-marker/files/"
            "permanent-marker-latin-400-normal.woff2') format('woff2')}" % fd)
    # the body type only gets fine speckle (letters stay whole); the dry-brush streaks go on the accent word alone
    worn = "-webkit-mask-image:url(\"%s\");mask-image:url(\"%s\");-webkit-mask-size:600px 600px;mask-size:600px 600px;" % (SPECK, SPECK)
    dry = "-webkit-mask-image:url(\"%s\");mask-image:url(\"%s\");-webkit-mask-size:900px 600px;mask-size:900px 600px;" % (STREAK, STREAK)
    css = font + ".card::after{opacity:.11}.tex{position:absolute;inset:0;pointer-events:none;z-index:1}"
    css += ".quote{%sline-height:1.02;padding:.12em .08em .1em 0;white-space:nowrap}" % worn
    css += (".quote .hl.brushw,.quote .hl.swipew{font-family:%s;display:inline-block;line-height:.86;"
            "letter-spacing:.01em;transform:rotate(-3deg);transform-origin:center;margin:0 .08em;vertical-align:baseline}" % BRUSH)
    css += (".quote .hl.brushw{" + dry + "font-size:1.2em;line-height:.74;padding-bottom:.17em;background:url(\"%s\") no-repeat left bottom/100%% .15em}"
            % stroke_uri(p["accent"], False))
    css += (".quote .hl.swipew{font-size:1em;line-height:.8;color:%s;padding:.2em .36em .12em;margin:0 -.04em;transform:rotate(-2deg);"
            "background:url(\"%s\") no-repeat center/100%% 100%%}" % (p["bg"], stroke_uri(p["accent"], True)))
    if style == "brush":
        css += (".glow{background:radial-gradient(70%% 46%% at 88%% 80%%,rgba(214,160,92,.30),rgba(214,160,92,0) 70%%),"
                "radial-gradient(60%% 30%% at 10%% 4%%,rgba(255,240,215,.07),rgba(0,0,0,0) 70%%)}"
                ".wood{top:auto;height:40%%;background:url(\"%s\") center bottom/cover;mix-blend-mode:screen;opacity:.2;"
                "-webkit-mask-image:linear-gradient(to bottom,transparent 0,#000 62%%);mask-image:linear-gradient(to bottom,transparent 0,#000 62%%)}"
                % WOOD)
    elif style == "paper":
        css += (".glow{background:radial-gradient(90%% 60%% at 22%% 18%%,rgba(255,250,236,.55),rgba(255,250,236,0) 70%%)}"
                ".wood{background:url(\"%s\") center/cover;mix-blend-mode:multiply;opacity:.3}" % BLOTCH)
    else:
        css += (".glow{background:radial-gradient(80%% 50%% at 14%% 12%%,rgba(120,150,180,.16),rgba(0,0,0,0) 70%%),"
                "radial-gradient(70%% 40%% at 90%% 92%%,rgba(217,164,65,.14),rgba(0,0,0,0) 70%%)}.wood{display:none}")
    return css.replace("%%", "%"), '<div class="tex wood"></div><div class="tex glow"></div>'

def ensure_brush_font(fd):
    """Install the hand-lettering face next to the brand fonts. False means: fall back to clean."""
    if not fd: return False
    path = os.path.join(fd, "permanent-marker", "files", "permanent-marker-latin-400-normal.woff2")
    if os.path.isfile(path): return True
    try:
        subprocess.run(["npm", "i", "--silent", "--no-audit", "--no-fund", "@fontsource/permanent-marker"],
                       cwd=os.path.dirname(os.path.dirname(fd)), check=True, timeout=300,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return False
    return os.path.isfile(path)

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

def shell(p, w, h, pt, pb, ps, fd, body, h1fs, bodyfs, style="clean"):
    xcss, xlayers = style_css(style, p, fd)
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
%(xcss)s
</style><div class="card">%(xlayers)s<div class="inner">%(body)s</div></div>
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
                    DISP=DISPLAY, TEXT=TEXT, body=body, h1fs=h1fs, bodyfs=bodyfs,
                    xcss=xcss, xlayers=xlayers)

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

def render(pages, outpaths, w, h, fd, pal, h1fs, bodyfs, pt, pb, ps, style="clean"):
    P = pal if isinstance(pal, dict) else PAL[pal]
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for body, out in zip(pages, outpaths):
            os.makedirs(os.path.expanduser("~/htr-engine"), exist_ok=True)
            f = os.path.expanduser("~/htr-engine/_r.html")
            open(f, "w").write(shell(P, w, h, pt, pb, ps, fd, body, h1fs, bodyfs, style))
            pg = b.new_page(viewport={"width": w + 60, "height": min(h + 60, 2200)})
            pg.goto("file://" + f); pg.wait_for_timeout(1100 if style != "clean" else 700)
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
    ap.add_argument("--style", default="auto", choices=["auto", "clean"] + list(STYLE_PAL),
                    help="quote cards only: clean, brush, paper, swipe; auto rotates them by day")
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
        style = auto_style(a.mode, a.slug) if a.style == "auto" else a.style
        if style != "clean" and not ensure_brush_font(fd):
            print("WARN: hand-lettering font unavailable, using the clean style"); style = "clean"
        print("STYLE:", style)
        pal = STYLE_PAL[style] if style != "clean" else PAL[a.palette]
        pages = [build_quote(a.quote, a.attrib, pal)]
        outs = [os.path.join(a.outdir, "HTR_quote_%s_%s.png" % (a.slug, a.ratio))]
        render(pages, outs, w, h, fd, pal, 118, 40, pt, pb, ps, style)
    print("STATUS: chromium — full brand quality")
    return 0

if __name__ == "__main__":
    sys.exit(main())
