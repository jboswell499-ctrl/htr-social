#!/usr/bin/env python3
"""HTR "fresh" swipe slides: a new design every single post.

Justin's call on 2026-11-09: "It needs to be different everyday. Not rotate between 5."

Instead of a handful of fixed looks, every set is built from six independent choices:
colours (16), typeface (7), layout (5), background (7), accent treatment (5) and progress
marks (3): about 58,000 designs. design_for() picks one for a slot and a date so that
  - the exact design has never been used before (history: looks/*.json),
  - it shares no colours, typeface, layout or background with the other sets of the same day,
  - it shares no colours or typeface with the previous five sets, and no background with the
    previous three.
A re-render of the same slot on the same day keeps its design.

Slides carry no chapter label, no slide number and no hashtags (the stop test). Every slide keeps
the top 15% and bottom 22% clear and stays out from under TikTok's right-hand buttons.
Called by tiktok_slides.py; prints rendered lines and returns the number of flagged slides.
"""
import glob, hashlib, json, os, random, re, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, TOP, BOT, LEFT, RIGHT = 1080, 1920, 288, 422, 84, 150

# name: (background, text, accent, muted)
PALETTES = {
    "ink-gold": ("#0A0A0B", "#F7F3EA", "#D9A441", "#8A8377"),
    "oxblood": ("#3B0D11", "#F7F3EA", "#E9B44C", "#B39A92"),
    "bone-red": ("#EFEBE3", "#131313", "#8E1B1F", "#7A736A"),
    "navy-gold": ("#0D1B2E", "#F4F1EA", "#E9B44C", "#8894A6"),
    "forest": ("#0F2A1E", "#F4F0E4", "#E9B44C", "#8FA396"),
    "mustard": ("#D9A441", "#0E0E0F", "#6E0F14", "#5E4A1C"),
    "cream-wine": ("#EEE6D8", "#1B1714", "#8E1B1B", "#6A5F55"),
    "coal-orange": ("#1C1C1E", "#F2EFE9", "#FF6B2C", "#8D8A85"),
    "paper-navy": ("#F6F4EC", "#18213A", "#C8302A", "#5B6478"),
    "plum": ("#2A1533", "#F4EEF7", "#F2B84B", "#A593AE"),
    "teal": ("#0E3B43", "#F1EFE6", "#F4A259", "#8FB0B3"),
    "rust": ("#A8421F", "#FFF4E6", "#16110D", "#F1C9B0"),
    "slate": ("#2F3E46", "#F0EDE5", "#E9C46A", "#9DB0B5"),
    "sand": ("#D8C3A5", "#1A1A1A", "#8E1B1B", "#6B5B45"),
    "black-red": ("#0B0B0B", "#F5F5F0", "#E63946", "#8C8C88"),
    "olive": ("#3A3D1F", "#F3EFD9", "#E9B44C", "#A9AB86"),
}
# name: (css family, package, file, start px, line height, uppercase, letter spacing)
FONTS = {
    "anton": ("anton", "anton", "anton-latin-400-normal", 210, .95, True, "-.01em"),
    "black": ("archivo", "archivo-black", "archivo-black-latin-400-normal", 132, 1.03, False, "-.02em"),
    "inter": ("inter8", "inter", "inter-latin-800-normal", 130, 1.08, False, "-.02em"),
    "serif": ("dmserif", "dm-serif-display", "dm-serif-display-latin-400-normal", 150, 1.05, False, "-.01em"),
    "type": ("elite", "special-elite", "special-elite-latin-400-normal", 118, 1.16, True, ".01em"),
    "hand": ("caveat", "caveat", "caveat-latin-700-normal", 190, 1.0, False, "0"),
    "marker": ("marker", "permanent-marker", "permanent-marker-latin-400-normal", 124, 1.12, False, "0"),
}
EXTRA = {"inter7": ("inter", "inter-latin-700-normal"), "serifi": ("dm-serif-display", "dm-serif-display-latin-400-italic")}
LAYOUTS = ["mid", "low", "high", "center", "ruled"]
BACKS = ["glow", "grid", "stripes", "dots", "frame", "bar", "corner"]
ACCENTS = ["colour", "underline", "box", "stamp", "swipe"]
MARKS = ["bars", "dots", "squares"]
DIMS = ("pal", "font", "layout", "back", "accent", "marks")
MINPX = {"anton": 110, "hand": 96}       # smallest readable size; other faces 62


def ensure_fonts(work=os.path.expanduser("~/htr-engine")):
    fd = os.path.join(work, "node_modules", "@fontsource")
    need = [(v[1], v[2]) for v in FONTS.values()] + [(v[0], v[1]) for v in EXTRA.values()]
    def missing(): return [p for p, f in need if not os.path.isfile(os.path.join(fd, p, "files", f + ".woff2"))]
    if missing():
        os.makedirs(work, exist_ok=True)
        if not os.path.isfile(os.path.join(work, "package.json")):
            subprocess.run(["npm", "init", "-y"], cwd=work, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["npm", "i", "--silent", "--no-audit", "--no-fund"] + sorted({"@fontsource/" + p for p in missing()}),
                       cwd=work, check=False, timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return fd, missing()


def _history(date):
    """Designs already used, newest first: (date, slot, spec)."""
    out = []
    for g in sorted(glob.glob(os.path.join(HERE, "looks", "*.json")), reverse=True):
        d = os.path.basename(g)[:10]
        if d > date: continue
        try: used = json.load(open(g)).get("used", {})
        except Exception: continue
        for slot in ("IG-1", "TT-3", "TT-1"):
            sp = used.get(slot, {}).get("spec")
            if sp: out.append((d, slot, sp))
    return out


def _prev_days(date, n):
    import datetime
    d = datetime.date.fromisoformat(date)
    return {(d - datetime.timedelta(days=k)).isoformat() for k in range(1, n + 1)}


def design_for(slot, date, avoid_fonts=(), avoid_specs=(), new=False, salt=""):
    """The design for a slot on a date (YYYY-MM-DD). Never a repeat; see the rules at the top.

    TikTok (2026-11-10, Justin: "Ensure that TikTok never posts the same image twice. Should look fresh
    to eyes daily"): a TikTok set also shares no colours with any TikTok set of the previous 3 days, and
    no typeface, layout or background with yesterday's TikTok sets. new=True skips "a re-render keeps
    its design" and picks a different one; avoid_specs are designs already rejected this run."""
    hist = _history(date)
    if not new:
        for d, s, sp in hist:
            if d == date and s == slot: return sp                  # a re-render keeps its design
    fonts = [f for f in FONTS if f not in avoid_fonts] or list(FONTS)
    today = [sp for d, s, sp in hist if d == date and s != slot]
    recent = [sp for d, s, sp in hist if not (d == date and s == slot)][:5]
    tt = slot.startswith("TT")
    tt3 = [sp for d, s, sp in hist if s.startswith("TT") and d in _prev_days(date, 3)]
    tt1 = [sp for d, s, sp in hist if s.startswith("TT") and d in _prev_days(date, 1)]
    VIS = ("pal", "font", "layout", "back")           # what the eye sees first: never the same four twice
    seen = {tuple(sp.get(k) for k in VIS) for _, _, sp in hist}
    seen |= {tuple(sp.get(k) for k in VIS) for sp in avoid_specs}
    seed = int(hashlib.sha256(("%s|%s|%s|%s|%d" % (date, slot, ",".join(sorted(avoid_fonts)), salt,
                                                    len(avoid_specs))).encode()).hexdigest(), 16)
    rnd = random.Random(seed)
    tiers = [None, None, None]                        # strictest first; fall back only if nothing passes
    for attempt in range(6000):
        sp = dict(pal=rnd.choice(list(PALETTES)), font=rnd.choice(fonts), layout=rnd.choice(LAYOUTS),
                  back=rnd.choice(BACKS), accent=rnd.choice(ACCENTS), marks=rnd.choice(MARKS))
        if sp["font"] == "hand" and sp["accent"] in ("box", "stamp"): continue      # boxes fight the handwriting
        if tuple(sp[k] for k in VIS) in seen: continue
        if any(sp[k] == o.get(k) for o in today for k in ("pal", "font", "layout", "back", "accent")): continue
        tiers[2] = tiers[2] or sp
        if any(sp[k] == o.get(k) for o in recent for k in ("pal", "font")): continue
        if any(sp["back"] == o.get("back") for o in recent[:3]): continue
        if recent and sp["layout"] == recent[0].get("layout"): continue
        tiers[1] = tiers[1] or sp
        if tt:
            if any(sp["pal"] == o.get("pal") for o in tt3): continue
            if any(sp[k] == o.get(k) for o in tt1 for k in ("font", "layout", "back", "accent")): continue
        return sp
    return tiers[1] or tiers[2]


def _faces(fd):
    out = ["@font-face{font-family:'%s';src:url('file://%s/%s/files/%s.woff2') format('woff2')}" % (v[0], fd, v[1], v[2])
           for v in FONTS.values()]
    out += ["@font-face{font-family:'%s';src:url('file://%s/%s/files/%s.woff2') format('woff2')}" % (k, fd, v[0], v[1])
            for k, v in EXTRA.items()]
    return "".join(out)

def _esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def _mark(t): return re.sub(r"\*(.+?)\*", r"<em>\1</em>", _esc(t))
def _rgba(hexc, a):
    h = hexc.lstrip("#"); return "rgba(%d,%d,%d,%s)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def page(slide, i, n, sp, fd):
    bg, fg, ac, mu = PALETTES[sp["pal"]]
    fam, _, _, start, lh, upper, ls = FONTS[sp["font"]]
    lines = "".join("<span class='ln'>%s</span>" % _mark(x.strip()) for x in slide["text"].split("|"))
    small = "<p class='small'>%s</p>" % _mark(slide["small"]) if slide.get("small") else ""
    marks = "".join("<i class='%s'></i>" % ("on" if k <= i else "") for k in range(n))
    back = {
        "glow": ".card:before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at 28%% 40%%,%s,transparent 62%%)}" % _rgba(ac, .16),
        "grid": ".card:before{content:'';position:absolute;inset:0;background-image:linear-gradient(%s 2px,transparent 2px),linear-gradient(90deg,%s 2px,transparent 2px);background-size:60px 60px}" % (_rgba(fg, .07), _rgba(fg, .07)),
        "stripes": ".card:before{content:'';position:absolute;inset:0;background:repeating-linear-gradient(-45deg,%s 0 3px,transparent 3px 46px)}" % _rgba(fg, .07),
        "dots": ".card:before{content:'';position:absolute;inset:0;background-image:radial-gradient(%s 4px,transparent 5px);background-size:54px 54px}" % _rgba(fg, .11),
        "frame": ".card:before{content:'';position:absolute;left:40px;right:40px;top:230px;bottom:360px;border:5px solid %s}" % _rgba(fg, .30),
        "bar": ".card:before{content:'';position:absolute;left:0;top:0;bottom:0;width:30px;background:%s}" % ac,
        "corner": ".card:before{content:'';position:absolute;right:-260px;top:-140px;width:900px;height:900px;border-radius:50%%;background:%s}" % _rgba(ac, .14),
    }[sp["back"]]
    layout = {
        "mid": ".mid{justify-content:center}",
        "low": ".mid{justify-content:flex-end;padding-bottom:70px}",
        "high": ".mid{justify-content:flex-start;padding-top:110px}",
        "center": ".mid{justify-content:center;text-align:center;align-items:center}.small{margin-left:auto;margin-right:auto}",
        "ruled": ".mid{justify-content:center}h1{border-top:8px solid %s;padding-top:44px}" % ac,
    }[sp["layout"]]
    accent = {
        "colour": "h1 em{color:%s}" % ac,
        "underline": "h1 em{color:%s;border-bottom:.07em solid %s;padding-bottom:.02em}" % (fg, ac),
        "box": "h1 em{background:%s;color:%s;padding:.02em .14em 0;margin:0 -.04em}" % (ac, bg),
        "stamp": "h1 em{color:%s;border:.045em solid %s;padding:.0em .12em;border-radius:.06em}" % (ac, ac),
        "swipe": "h1 em{color:%s;background:linear-gradient(transparent 80%%,%s 80%% 97%%,transparent 97%%);padding-bottom:.06em}" % (fg, ac),
    }[sp["accent"]]
    if sp["font"] == "serif": accent += "h1 em{font-family:serifi}"
    mk = {
        "bars": ".marks{display:flex;gap:10px;height:8px}.marks i{flex:1;background:%s;border-radius:4px}.marks i.on{background:%s}" % (_rgba(fg, .22), ac),
        "dots": ".marks{display:flex;gap:14px}.marks i{width:22px;height:22px;border-radius:50%%;border:3px solid %s}.marks i.on{background:%s;border-color:%s}" % (_rgba(fg, .45), ac, ac),
        "squares": ".marks{display:flex;gap:10px}.marks i{width:40px;height:14px;background:%s}.marks i.on{background:%s}" % (_rgba(fg, .22), fg),
    }[sp["marks"]]
    pad = 40 if sp["back"] == "frame" else 0
    return """<!doctype html><meta charset="utf-8"><style>
%(faces)s
*{margin:0;padding:0;box-sizing:border-box}
body{background:#222}
.card{width:%(W)dpx;height:%(H)dpx;position:relative;overflow:hidden;background:%(bg)s;color:%(fg)s;font-family:inter7}
%(back)s
.safe{z-index:2;position:absolute;top:%(TOP)dpx;bottom:%(BOT)dpx;left:%(L)dpx;right:%(RIGHT)dpx;display:flex;flex-direction:column}
.marks{flex:none}
.mid{flex:1;min-height:0;display:flex;flex-direction:column}
h1{font-family:'%(fam)s';font-weight:400;font-size:%(start)dpx;line-height:%(lh)s;letter-spacing:%(ls)s;%(tt)s}
h1 .ln{display:block;white-space:nowrap}
h1 em{font-style:normal;display:inline-block;line-height:1}
.small{margin-top:44px;font-family:inter7;font-size:48px;line-height:1.28;color:%(fg)s;opacity:.86;max-width:100%%}
.small em{font-style:normal}
.foot{flex:none;font-family:inter8;letter-spacing:.2em;font-size:22px;color:%(mu)s}
%(layout)s
%(accent)s
%(mk)s
</style>
<div class="card"><div class="safe">
<div class="marks">%(marks)s</div>
<div class="mid"><h1>%(lines)s</h1>%(small)s</div>
<div class="foot">JUSTIN BOSWELL</div>
</div></div>
<script>
document.fonts.ready.then(function(){
  var mid=document.querySelector('.mid'),h1=document.querySelector('h1'),s=%(start)d,g=0;
  var cs=getComputedStyle(mid),padv=parseFloat(cs.paddingTop)+parseFloat(cs.paddingBottom);
  function wide(){var m=0;h1.querySelectorAll('.ln').forEach(function(l){m=Math.max(m,l.scrollWidth)});return m>mid.clientWidth}
  function tall(){var t=0;for(var c of mid.children){t+=c.offsetHeight+parseFloat(getComputedStyle(c).marginTop)}return t>mid.clientHeight-padv-30}
  while((wide()||tall())&&s>40&&g++<400){s-=2;h1.style.fontSize=s+'px'}
  document.body.setAttribute('data-fs',s);document.body.setAttribute('data-ok',(wide()||tall())?'0':'1');
});
</script>""" % dict(faces=_faces(fd), W=W, H=H, TOP=TOP, BOT=BOT, L=LEFT + pad, RIGHT=RIGHT, bg=bg, fg=fg, mu=mu,
                    back=back, fam=fam, start=start, lh=lh, ls=ls, tt="text-transform:uppercase;" if upper else "",
                    layout=layout, accent=accent, mk=mk, marks=marks, lines=lines, small=small)


def render(slides, slug, sp, outdir, motif="none", workdir=os.path.expanduser("~/htr-engine")):
    """Render a set. Returns (flagged slides, fonts ok)."""
    fd, miss = ensure_fonts(workdir)
    if miss:
        print("fonts missing: %s" % ", ".join(miss)); return len(slides), False
    from playwright.sync_api import sync_playwright
    os.makedirs(outdir, exist_ok=True)
    bad = 0; floor = MINPX.get(sp["font"], 62)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for i, s in enumerate(slides):
            html = page(s, i, len(slides), sp, fd)
            if motif != "none":
                import motif as _m
                html = _m.apply(html, motif, PALETTES[sp["pal"]][2], W, H, TOP + 40, BOT + 60, RIGHT)
            f = os.path.join(workdir, "_fresh_%02d.html" % (i + 1)); open(f, "w").write(html)
            pg = b.new_page(viewport={"width": W + 40, "height": H + 40})
            pg.goto("file://" + f); pg.wait_for_function("document.body.getAttribute('data-ok')!==null", timeout=15000)
            pg.wait_for_timeout(300)
            fs, ok = int(pg.get_attribute("body", "data-fs")), pg.get_attribute("body", "data-ok")
            out = os.path.join(outdir, "HTR_tt_%s_%02d.png" % (slug, i + 1))
            pg.query_selector(".card").screenshot(path=out); pg.close()
            note = "" if ok == "1" and fs >= floor else "  <-- TYPE TOO SMALL OR OVERFLOW: shorten this slide"
            bad += bool(note)
            print("rendered %s type=%dpx%s" % (out, fs, note))
        b.close()
    return bad, True


def label(sp):
    return "%s type on %s, %s layout, %s background" % (sp["font"], sp["pal"], sp["layout"], sp["back"])
