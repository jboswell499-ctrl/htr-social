#!/usr/bin/env python3
"""HTR "looks": five additional visual styles for quote cards, carousel slides and TikTok slides.

  looks.py --mode quote  --look editorial --quote "Line one|line *two*" --attrib "Book|Ch. 9, p. 159" \
           --slug ch09-x-q1 --ratio 4x5
  looks.py --mode slides --look ledger --json slides.json --slug ch09-x-tt1 --ratio 9x16 [--prefix tt]

Looks:
  editorial  cream newsprint, serif display type, oxblood italic accent, hanging quote mark
  ledger     receipt paper on near-black, typewriter type, accent stamped in red ink
  block      solid colour block carrying the accent word huge, the line set below it
  notebook   graph paper, marker handwriting, accent circled in red pen
  poster     centred poster layout, ghost chapter numeral behind, accent filled gold

Slides JSON: a list of objects with "text" (or "head") and optional "small" (or "body").
Use | for line breaks and wrap exactly one word or phrase in *asterisks* for the accent.
Every 9x16 output keeps the top 15% and bottom 22% free of type (same SAFE bands as htrcards.py).
Prints STATUS and flags any slide whose type had to shrink below a readable size.
Source is ASCII on purpose: special characters are written as HTML entities.
"""
import argparse, json, os, re, subprocess, sys, tempfile

SIZES = {"4x5": (1080, 1350), "9x16": (1080, 1920), "1x1": (1080, 1080), "16x9": (1200, 675)}
SAFE = {"4x5": (162, 243, 86), "9x16": (288, 422, 86), "1x1": (120, 150, 86), "16x9": (70, 90, 80)}
LOOKS = ["editorial", "ledger", "block", "notebook", "poster"]
FONTS = {
    "anton": ("anton", "anton-latin-400-normal"),
    "inter5": ("inter", "inter-latin-500-normal"), "inter7": ("inter", "inter-latin-700-normal"),
    "inter8": ("inter", "inter-latin-800-normal"),
    "serif": ("dm-serif-display", "dm-serif-display-latin-400-normal"),
    "serifi": ("dm-serif-display", "dm-serif-display-latin-400-italic"),
    "type": ("special-elite", "special-elite-latin-400-normal"),
    "mono": ("ibm-plex-mono", "ibm-plex-mono-latin-500-normal"),
    "mono7": ("ibm-plex-mono", "ibm-plex-mono-latin-700-normal"),
    "black": ("archivo-black", "archivo-black-latin-400-normal"),
    "hand": ("caveat", "caveat-latin-700-normal"),
}
PKGS = sorted({"@fontsource/" + v[0] for v in FONTS.values()})

def ensure_fonts():
    work = os.path.expanduser("~/htr-engine")
    fd = os.path.join(work, "node_modules", "@fontsource")
    need = [k for k, (pkg, f) in FONTS.items() if not os.path.isfile(os.path.join(fd, pkg, "files", f + ".woff2"))]
    if need:
        os.makedirs(work, exist_ok=True)
        if not os.path.isfile(os.path.join(work, "package.json")):
            subprocess.run(["npm", "init", "-y"], cwd=work, check=False, stdout=subprocess.DEVNULL)
        subprocess.run(["npm", "i", "--silent", "--no-audit", "--no-fund"] + PKGS, cwd=work, check=False,
                       timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    miss = [k for k, (pkg, f) in FONTS.items() if not os.path.isfile(os.path.join(fd, pkg, "files", f + ".woff2"))]
    return fd, miss

def faces(fd):
    out = []
    for name, (pkg, f) in FONTS.items():
        out.append("@font-face{font-family:'%s';src:url('file://%s/%s/files/%s.woff2') format('woff2')}" % (name, fd, pkg, f))
    return "".join(out)

GRAIN = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'"
         "%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' "
         "numOctaves='3'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)'/%3E%3C/svg%3E")

def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def fmt(t):
    s = "<br>".join(x.strip() for x in esc(t).split("|"))
    return re.sub(r"\*(.+?)\*([.,!?;:]*)", r'<span class="nw"><span class="hl">\1</span>\2</span>', s)
def plain(t): return re.sub(r"[*|]", " ", t).replace("  ", " ").strip()
def accent_word(t):
    m = re.search(r"\*(.+?)\*", t); return m.group(1) if m else ""

# ---------------------------------------------------------------------------------------------
CSS_BASE = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:%(w)spx;height:%(h)spx;overflow:hidden}
.card{position:relative;width:%(w)spx;height:%(h)spx;overflow:hidden}
.inner{position:absolute;left:%(ps)spx;right:%(ps)spx;top:%(pt)spx;bottom:%(pb)spx;display:flex;flex-direction:column}
.mid{flex:1;display:flex;flex-direction:column;justify-content:center;min-height:0;overflow:hidden}
.big{font-size:%(bigfs)spx}
.small{font-size:%(smfs)spx}
.hl,.nw{white-space:nowrap}
"""

LOOK_CSS = {
"editorial": """
.card{background:#EEE6D8;color:#1B1714}
.card:after{content:'';position:absolute;inset:0;background:url("%(grain)s");opacity:.10;mix-blend-mode:multiply}
.top{display:flex;justify-content:space-between;align-items:center;border-top:4px solid #1B1714;padding-top:14px;
 font-family:inter8;font-size:%(lab)spx;letter-spacing:.24em;text-transform:uppercase}
.top:before{content:'';position:absolute;left:0;right:0;top:9px;border-top:1px solid #1B1714}
.top{position:relative}
.qm{font-family:serif;color:#8E1B1B;font-size:%(qm)spx;line-height:.6;height:%(qmh)spx;margin-bottom:6px}
.big{font-family:serif;line-height:1.04;letter-spacing:-.01em}
.big .hl{font-family:serifi;color:#8E1B1B}
.small{font-family:inter5;line-height:1.35;margin-top:30px;color:#3A332D;max-width:92%%}
.attr{margin-top:34px;font-family:inter7;font-size:%(lab)spx;letter-spacing:.2em;text-transform:uppercase;line-height:1.8;color:#5A5048}
.attr:before{content:'';display:block;width:70px;border-top:3px solid #8E1B1B;margin-bottom:16px}
.foot{display:flex;justify-content:space-between;border-top:1px solid #1B1714;padding-top:16px;
 font-family:inter8;font-size:%(lab)spx;letter-spacing:.24em;text-transform:uppercase}
""",
"ledger": """
.card{background:#141414}
.paper{position:absolute;left:%(ps)spx;right:%(ps)spx;top:%(pt)spx;bottom:%(pb)spx;background:#F3EFE6;
 -webkit-mask:conic-gradient(from -45deg at bottom,#0000,#000 1deg 89deg,#0000 90deg) bottom/26px 51%% repeat-x,
             conic-gradient(from 135deg at top,#0000,#000 1deg 89deg,#0000 90deg) top/26px 51%% repeat-x}
.paper:after{content:'';position:absolute;inset:0;background:url("%(grain)s");opacity:.12;mix-blend-mode:multiply}
.inner{left:%(ps2)spx;right:%(ps2)spx;top:%(pt2)spx;bottom:%(pb2)spx;color:#1E1E1E}
.top{font-family:mono7;font-size:%(lab)spx;letter-spacing:.14em;text-transform:uppercase;text-align:center;line-height:1.7}
.top .dash,.foot .dash{display:block;overflow:hidden;white-space:nowrap;letter-spacing:.35em;color:#777}
.big{font-family:type;line-height:1.14;text-transform:uppercase;letter-spacing:.01em}
.big .hl{display:inline-block;color:#B3261E;border:5px solid #B3261E;padding:.02em .16em 0;margin:.06em 0;
 transform:rotate(-3deg);border-radius:6px;box-shadow:inset 0 0 0 2px rgba(179,38,30,.25)}
.small{font-family:mono;line-height:1.4;margin-top:28px;color:#3B3B3B}
.attr{margin-top:30px;font-family:mono;font-size:%(lab)spx;line-height:1.9;text-transform:uppercase;color:#333}
.attr .row{display:flex;gap:10px}.attr .row .lead{flex:1;border-bottom:3px dotted #999;margin-bottom:.55em}
.foot{font-family:mono7;font-size:%(lab)spx;letter-spacing:.14em;text-transform:uppercase;text-align:center;line-height:1.7}
.bars{height:%(barh)spx;margin:10px auto 6px;width:60%%;background:repeating-linear-gradient(90deg,#1E1E1E 0 3px,#0000 3px 7px,#1E1E1E 7px 12px,#0000 12px 14px,#1E1E1E 14px 15px,#0000 15px 21px)}
""",
"block": """
.card{background:#0E0E0E;color:#F4EFE6}
.blk{position:absolute;left:0;right:0;top:0;height:%(blkh)spx;background:#E3A83B}
.blk:after{content:'';position:absolute;inset:0;background:url("%(grain)s");opacity:.10;mix-blend-mode:multiply}
.bw{position:absolute;left:%(ps)spx;right:%(ps)spx;top:%(pt)spx;height:%(bwh)spx;display:flex;align-items:flex-end;z-index:2}
.bw span{font-family:black;text-transform:uppercase;color:#0E0E0E;line-height:.86;letter-spacing:-.02em;white-space:nowrap;font-size:400px}
.inner{top:%(midtop)spx}
.top{display:none}
.big{font-family:inter8;line-height:1.12;letter-spacing:-.015em}
.big .hl{color:#E3A83B}
.small{font-family:inter5;line-height:1.35;margin-top:26px;color:#BDB6AA}
.attr{margin-top:30px;font-family:inter7;font-size:%(lab)spx;letter-spacing:.2em;text-transform:uppercase;line-height:1.8;color:#8C857A}
.foot{display:flex;justify-content:space-between;font-family:inter8;font-size:%(lab)spx;letter-spacing:.24em;text-transform:uppercase;color:#8C857A}
.foot b{color:#E3A83B;font-weight:inherit}
.mid{justify-content:flex-start;padding-top:%(gap)spx}
""",
"notebook": """
.card{background:#F6F4EC;
 background-image:linear-gradient(#C9D6E8 2px,#0000 2px),linear-gradient(90deg,#C9D6E8 2px,#0000 2px);
 background-size:54px 54px;color:#18213A}
.card:before{content:'';position:absolute;top:0;bottom:0;left:%(margin)spx;border-left:3px solid #E07B7B;opacity:.8}
.card:after{content:'';position:absolute;inset:0;background:url("%(grain)s");opacity:.08;mix-blend-mode:multiply}
.tape{position:absolute;left:50%%;top:%(tapetop)spx;width:280px;height:70px;margin-left:-140px;background:rgba(222,205,160,.75);
 transform:rotate(-4deg);box-shadow:0 2px 6px rgba(0,0,0,.08)}
.inner{left:%(ps3)spx}
.top{font-family:hand;font-size:%(hlab)spx;color:#5B6478}
.big{font-family:hand;line-height:1.02}
.big .hl{position:relative;display:inline-block}
.ring{position:absolute;pointer-events:none;overflow:visible}
.small{font-family:hand;line-height:1.15;margin-top:24px;color:#3A4560}
.attr{margin-top:30px;font-family:hand;font-size:%(hlab)spx;color:#5B6478;line-height:1.2}
.foot{font-family:inter8;font-size:%(lab)spx;letter-spacing:.24em;text-transform:uppercase;color:#5B6478}
""",
"poster": """
.card{background:radial-gradient(120%% 80%% at 50%% 45%%,#5E1717 0,#3A0C0C 70%%,#2A0808 100%%);color:#F6EFE3;text-align:center}
.card:after{content:'';position:absolute;inset:0;background:url("%(grain)s");opacity:.14;mix-blend-mode:overlay}
.ghost{position:absolute;left:0;right:0;top:50%%;transform:translateY(-52%%);font-family:anton;font-size:%(ghost)spx;line-height:1;
 color:transparent;-webkit-text-stroke:3px rgba(246,239,227,.10);text-align:center;letter-spacing:-.02em}
.top{font-family:mono7;font-size:%(lab)spx;letter-spacing:.3em;text-transform:uppercase;color:#E3A83B}
.top:after{content:'';display:block;width:56px;border-top:3px solid #E3A83B;margin:18px auto 0}
.big{font-family:anton;text-transform:uppercase;line-height:1.2;letter-spacing:.005em}
.big .hl{color:#1A0505;background:#E3A83B;padding:.02em .14em 0;line-height:1;display:inline-block;-webkit-box-decoration-break:clone}
.small{font-family:inter7;line-height:1.35;margin-top:30px;color:#E9DCCB;margin-left:auto;margin-right:auto;max-width:90%%}
.attr{margin-top:34px;font-family:mono;font-size:%(lab)spx;letter-spacing:.16em;text-transform:uppercase;line-height:1.8;color:#D9C7AE}
.foot{font-family:mono7;font-size:%(lab)spx;letter-spacing:.3em;text-transform:uppercase;color:#D9C7AE}
""",
}

FIT_JS = """<script>
document.fonts.ready.then(function(){
 var mid=document.querySelector('.mid'),big=document.querySelector('.big'),sm=document.querySelector('.small');
 var bs=parseFloat(getComputedStyle(big).fontSize),ss=sm?parseFloat(getComputedStyle(sm).fontSize):0,g=0;
 function wide(){var r=big.getBoundingClientRect();var o=false;big.querySelectorAll('.hl').forEach(function(e){
   if(e.getBoundingClientRect().right>r.right+2)o=true});return big.scrollWidth>big.clientWidth+2||o}
 function over(){return mid.scrollHeight>mid.clientHeight+1||wide()}
 while(over()&&g++<400){ if(sm&&ss>bs*0.42&&ss>30){ss-=1.5;sm.style.fontSize=ss+'px'} bs-=2;big.style.fontSize=bs+'px';}
 var start=bs,forced=big.querySelectorAll('br').length+1;
 function lines(){var lh=parseFloat(getComputedStyle(big).lineHeight)||bs*1.1;return Math.round(big.offsetHeight/lh)}
 g=0;while(lines()>forced&&bs>start*0.72&&g++<200){bs-=2;big.style.fontSize=bs+'px';}
 document.body.setAttribute('data-bs',Math.round(bs));
 var bw=document.querySelector('.bw span');
 if(bw){var box=document.querySelector('.bw'),f=400;while((bw.scrollWidth>box.clientWidth||bw.offsetHeight>box.clientHeight)&&f>60){f-=4;bw.style.fontSize=f+'px'}}
 document.querySelectorAll('.notebook .hl').forEach(function(e){
   var w=e.offsetWidth,h=e.offsetHeight,s=document.createElementNS('http://www.w3.org/2000/svg','svg');
   s.setAttribute('class','ring');s.setAttribute('width',w+20);s.setAttribute('height',40);
   s.style.left='-10px';s.style.top=(h*0.80)+'px';
   var d='M 4 18 C '+(w*0.25)+' 8, '+(w*0.5)+' 26, '+(w*0.75)+' 14 S '+(w+6)+' 10, '+(w+16)+' 16 M 14 30 C '+(w*0.4)+' 22, '+(w*0.7)+' 30, '+(w+8)+' 24';
   s.innerHTML='<path d="'+d+'" fill="none" stroke="#C8302A" stroke-width="6" stroke-linecap="round"/>';
   e.appendChild(s)});
 document.body.setAttribute('data-done','1');
});
</script>"""

def build(look, w, h, ratio, fd, big, small, attrib, top, foot, ghost, n=None, total=None):
    pt, pb, ps = SAFE[ratio]
    short = min(w, h)
    lab = max(18, round(short * 0.021)) if ratio != "16x9" else 15
    p = dict(w=w, h=h, pt=pt, pb=pb, ps=ps, grain=GRAIN, lab=lab, hlab=round(lab * 2.2),
             bigfs=round(short * (0.115 if ratio != "16x9" else 0.06)), smfs=round(short * 0.036),
             qm=round(short * 0.30), qmh=round(short * 0.15))
    if look == "ledger":
        p.update(ps2=ps + 44, pt2=pt + 56, pb2=pb + 56, barh=round(short * .05))
        p["bigfs"] = round(short * 0.095)
    if look == "block":
        bwh = round((h - pt - pb) * (0.30 if ratio != "16x9" else 0.34))
        p.update(bwh=bwh, blkh=pt + bwh + round(short * .045), gap=round(short * .02))
        p["midtop"] = p["blkh"] + round(short * .045)
        p["bigfs"] = round(short * (0.115 if ratio == "9x16" else 0.085))
    if look == "notebook":
        p.update(margin=ps + 28, ps3=ps + 64, tapetop=max(20, pt - 110))
        p["bigfs"] = round(short * 0.15); p["smfs"] = round(short * 0.06)
    if look == "poster":
        p["ghost"] = round(h * 0.62) if ratio != "16x9" else 560
    css = (CSS_BASE + LOOK_CSS[look]) % p
    counter = ("%02d / %02d" % (n, total)) if n else ""
    if look == "editorial":
        topl = '<div class="top"><span>%s</span><span>%s</span></div>' % (top, counter or "No. %s" % ghost)
        qm = '<div class="qm">&ldquo;</div>' if attrib else ""
        footl = '<div class="foot"><span>Justin Boswell</span><span>%s</span></div>' % foot
        mid = qm + '<div class="big">%s</div>' % big
    elif look == "ledger":
        topl = ('<div class="top">%s%s<span class="dash">- - - - - - - - - - - - - - - - - - - - - - - - - -</span></div>'
                % ("Hard To Replace&trade;<br>" + (top if not counter else "Ch. %s" % ghost), (" &middot; " + counter) if counter else ""))
        footl = ('<div class="foot"><span class="dash">- - - - - - - - - - - - - - - - - - - - - - - - - -</span>'
                 '<div class="bars"></div>Justin Boswell</div>')
        mid = '<div class="big">%s</div>' % big
    elif look == "block":
        topl = ""
        footl = '<div class="foot"><span>Justin Boswell</span><span>%s</span></div>' % (counter or "<b>Hard To Replace&trade;</b>")
        mid = '<div class="big">%s</div>' % big
    elif look == "notebook":
        topl = '<div class="top">%s</div>' % (counter or top)
        footl = '<div class="foot">Justin Boswell &middot; Hard To Replace&trade;</div>'
        mid = '<div class="big">%s</div>' % big
    else:  # poster
        topl = '<div class="top">%s</div>' % (counter or top)
        footl = '<div class="foot">Justin Boswell</div>'
        mid = '<div class="big">%s</div>' % big
    if small: mid += '<div class="small">%s</div>' % small
    if attrib:
        a = attrib.split("|")
        if look == "ledger":
            rows = "".join('<div class="row"><span>%s</span><span class="lead"></span><span>%s</span></div>' % tuple(x)
                           for x in ledger_rows(a))
            mid += '<div class="attr">%s</div>' % rows
        elif look == "notebook":
            ref = next((x for x in a if re.search(r"Ch\.", x)), a[-1]).split(chr(183))[0].strip()
            mid += '<div class="attr">&mdash; %s</div>' % esc(ref)
        else:
            mid += '<div class="attr">%s</div>' % "<br>".join(esc(x) for x in a)
    layers = ""
    if look == "ledger": layers = '<div class="paper"></div>'
    if look == "block": layers = '<div class="blk"></div><div class="bw"><span>%s</span></div>' % (esc(ACCENT[0]) or counter or ghost)
    if look == "notebook": layers = '<div class="tape"></div>'
    if look == "poster": layers = '<div class="ghost">%s</div>' % ghost
    html = ('<!doctype html><meta charset="utf-8"><style>%s%s</style><body><div class="card %s">%s'
            '<div class="inner">%s<div class="mid">%s</div>%s</div></div></body>%s'
            % (faces(fd), css, look, layers, topl, mid, footl, FIT_JS))
    return html, p["bigfs"]

ACCENT = [""]
def ledger_rows(a):
    rows = [("Source", "HTR")]
    for x in a:
        m = re.match(r"Ch\.\s*(\d+),\s*p\.\s*(\d+)", x)
        if m: rows = [("Chapter", m.group(1).zfill(2)), ("Page", m.group(2))]; break
    rows.insert(0, ("Book", "High-Value Man"))
    return rows

def render(jobs, look):
    from playwright.sync_api import sync_playwright
    flags = 0
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for html, out, w, h, start in jobs:
            pg = b.new_page(viewport={"width": w, "height": h})
            f = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False); f.write(html); f.close()
            pg.goto("file://" + f.name); pg.wait_for_selector("body[data-done]", timeout=15000)
            pg.wait_for_timeout(300)
            pg.screenshot(path=out)
            bs = int(pg.evaluate("document.body.getAttribute('data-bs')"))
            warn = ""
            if bs < start * 0.55 or bs < 44:
                warn = "  <-- TYPE TOO SMALL OR OVERFLOW: shorten this slide"; flags += 1
            print("rendered %s look=%s type=%dpx%s" % (out, look, bs, warn))
            pg.close(); os.unlink(f.name)
        b.close()
    return flags

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["quote", "slides"], required=True)
    ap.add_argument("--look", choices=LOOKS, required=True)
    ap.add_argument("--ratio", default="4x5", choices=list(SIZES))
    ap.add_argument("--slug", required=True)
    ap.add_argument("--quote"); ap.add_argument("--attrib", default="")
    ap.add_argument("--json"); ap.add_argument("--prefix", default="tt", help="file prefix for slides: tt or carousel")
    ap.add_argument("--chapter", default="09", help="chapter number for labels and the poster numeral")
    ap.add_argument("--outdir", default=os.path.expanduser("~/htr-engine/cards"))
    a = ap.parse_args()
    fd, miss = ensure_fonts()
    if miss:
        print("STATUS: fonts missing (%s) - do not publish these renders" % ", ".join(miss)); sys.exit(1)
    os.makedirs(a.outdir, exist_ok=True)
    w, h = SIZES[a.ratio]; jobs = []
    ch = a.chapter.zfill(2)
    if a.mode == "quote":
        ACCENT[0] = accent_word(a.quote)
        html, st = build(a.look, w, h, a.ratio, fd, fmt(a.quote), "", a.attrib,
                         "The Making of a High-Value Man", "Hard To Replace&trade;", ch)
        jobs.append((html, os.path.join(a.outdir, "HTR_quote_%s_%s.png" % (a.slug, a.ratio)), w, h, st))
    else:
        slides = json.load(open(a.json)); n = len(slides)
        for i, s in enumerate(slides, 1):
            t = s.get("text") or s.get("head") or ""; sm = s.get("small") or s.get("body") or ""
            ACCENT[0] = accent_word(t)
            smh = "<br>".join(esc(x) for x in sm.split("\n")) if sm else ""
            smh = re.sub(r"\*(.+?)\*", r"\1", smh)
            html, st = build(a.look, w, h, a.ratio, fd, fmt(t), smh, "",
                             "Ch. %s &middot; Hard To Replace&trade;" % ch, "Hard To Replace&trade;", ch,
                             n=i if n > 1 else None, total=n)
            name = ("HTR_tt_%s_%02d.png" if a.prefix == "tt" else "HTR_carousel_%s_%02d.png") % (a.slug, i)
            jobs.append((html, os.path.join(a.outdir, name), w, h, st))
    flags = render(jobs, a.look)
    print("STATUS: chromium - full brand quality" + (" (%d flagged)" % flags if flags else ""))

if __name__ == "__main__":
    main()
