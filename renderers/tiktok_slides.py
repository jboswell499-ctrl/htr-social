#!/usr/bin/env python3
"""HTR TikTok swipe slides: one thought per slide, hook first, question last.

  tiktok_slides.py --json slides.json --slug ch06-fearless-tt2 [--palette gold] [--outdir ~/htr-engine/cards]

slides.json is a list of 4 to 7 objects:
  {"text": "4 things men say|instead of|\\"I'm *afraid*.\\"", "small": "optional supporting sentence"}
"text" is the big line: use | for line breaks (at most 4 lines, about 12 words) and wrap ONE
word or phrase in *asterisks* for the accent. "small" is optional, one sentence, 18 words or fewer.

Built for the TikTok feed, not as a brand card: no kicker, no rules, no footer promise. The only
furniture is a progress bar (it tells the viewer there is more to swipe) and a small byline.
Every slide keeps the top 15% (288 px) and bottom 22% (422 px) clear, and nothing sits under
TikTok's right-hand button rail. Writes HTR_tt_<slug>_01.png ... and prints a STATUS line.
Run hookcard.py first: it installs the brand fonts this needs.
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hookcard import PALETTES, DISPLAY_STACK, TEXT_STACK, ensure_fonts, face, esc

W, H, TOP, BOT, LEFT, RIGHT = 1080, 1920, 288, 422, 84, 150

def mark(t):
    return re.sub(r"\*(.+?)\*", r'<em>\1</em>', esc(t))

def page(slide, i, n, pal, fontdir):
    p = dict(PALETTES[pal])
    if pal == "bone": p["accent"] = "#8E1B1F"   # bone's own accent is black, which would hide the accent word
    lines = "".join("<span class='ln'>%s</span>" % mark(x.strip()) for x in slide["text"].split("|"))
    small = "<p class='small'>%s</p>" % mark(slide["small"]) if slide.get("small") else ""
    bars = "".join("<i class='%s'></i>" % ("on" if k <= i else "") for k in range(n))
    cue = "<span class='cue'>SWIPE &rarr;</span>" if i == 0 else ""
    return """<!doctype html><meta charset="utf-8"><style>
%(face)s
*{margin:0;padding:0;box-sizing:border-box}
body{background:#222}
.card{width:%(W)dpx;height:%(H)dpx;position:relative;overflow:hidden;background:%(bg)s;color:%(fg)s;font-family:%(TEXT)s}
.card:before{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 30%% 42%%,transparent 35%%,%(vig)s 100%%)}
.safe{position:absolute;top:%(TOP)dpx;bottom:%(BOT)dpx;left:%(LEFT)dpx;right:%(RIGHT)dpx;display:flex;flex-direction:column}
.bars{display:flex;gap:10px;height:8px;flex:none}
.bars i{flex:1;background:%(hair)s;border-radius:4px}
.bars i.on{background:%(accent)s}
.mid{flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center}
h1{font-family:%(DISP)s;font-weight:400;text-transform:uppercase;font-size:210px;line-height:.95;letter-spacing:-.01em}
h1 .ln{display:block;white-space:nowrap}
h1 em{font-style:normal;color:%(accent)s}
.small{margin-top:44px;font-weight:700;font-size:50px;line-height:1.25;color:%(subfg)s}
.small em{font-style:normal;color:%(accent)s}
.foot{flex:none;display:flex;justify-content:space-between;align-items:center;font-weight:800;letter-spacing:.2em;font-size:22px;color:%(muted)s}
.cue{color:%(accent)s;font-size:26px}
</style>
<div class="card"><div class="safe">
<div class="bars">%(bars)s</div>
<div class="mid"><h1>%(lines)s</h1>%(small)s</div>
<div class="foot"><span>JUSTIN BOSWELL</span>%(cue)s</div>
</div></div>
<script>
document.fonts.ready.then(function(){
  var mid=document.querySelector('.mid'),h1=document.querySelector('h1'),s=210,g=0;
  function wide(){var m=0;h1.querySelectorAll('.ln').forEach(function(l){m=Math.max(m,l.scrollWidth)});return m>mid.clientWidth}
  function tall(){var t=0;for(var c of mid.children){t+=c.offsetHeight+parseFloat(getComputedStyle(c).marginTop)}return t>mid.clientHeight-40}
  while((wide()||tall())&&s>70&&g++<300){s-=2;h1.style.fontSize=s+'px'}
  document.body.setAttribute('data-fs',s);document.body.setAttribute('data-ok',(wide()||tall())?'0':'1');
});
</script>""" % dict(p, face=face(fontdir), W=W, H=H, TOP=TOP, BOT=BOT, LEFT=LEFT, RIGHT=RIGHT,
                    DISP=DISPLAY_STACK, TEXT=TEXT_STACK, bars=bars, lines=lines, small=small, cue=cue)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True); ap.add_argument("--slug", required=True)
    ap.add_argument("--palette", default="gold", choices=list(PALETTES))
    ap.add_argument("--outdir", default=os.path.expanduser("~/htr-engine/cards"))
    ap.add_argument("--workdir", default=os.path.expanduser("~/htr-engine"))
    a = ap.parse_args()
    slides = json.load(open(a.json))
    if not 4 <= len(slides) <= 7:
        print("ERROR: need 4 to 7 slides, got %d" % len(slides)); return 1
    for k, s in enumerate(slides, 1):
        if len(s["text"].split("|")) > 4:
            print("ERROR: slide %d has more than 4 lines" % k); return 1
        if len(re.findall(r"\*.+?\*", s["text"])) != 1:
            print("ERROR: slide %d needs exactly one *accent*" % k); return 1
    os.makedirs(a.outdir, exist_ok=True)
    fontdir = ensure_fonts(a.workdir)
    from playwright.sync_api import sync_playwright
    bad = 0
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for i, s in enumerate(slides):
            f = os.path.join(a.workdir, "_tt_%02d.html" % (i + 1))
            open(f, "w").write(page(s, i, len(slides), a.palette, fontdir))
            pg = b.new_page(viewport={"width": W + 40, "height": H + 40})
            pg.goto("file://" + f); pg.wait_for_function("document.body.getAttribute('data-ok')!==null", timeout=15000)
            pg.wait_for_timeout(300)
            fs, ok = pg.get_attribute("body", "data-fs"), pg.get_attribute("body", "data-ok")
            out = os.path.join(a.outdir, "HTR_tt_%s_%02d.png" % (a.slug, i + 1))
            pg.query_selector(".card").screenshot(path=out); pg.close()
            note = "" if ok == "1" and int(fs) >= 110 else "  <-- TYPE TOO SMALL OR OVERFLOW: shorten this slide"
            bad += bool(note)
            print("rendered %s type=%spx%s" % (out, fs, note))
        b.close()
    print("STATUS: %s" % ("chromium - full brand quality" if fontdir else "chromium-fallback-fonts"))
    return 1 if bad or not fontdir else 0

if __name__ == "__main__":
    sys.exit(main())
