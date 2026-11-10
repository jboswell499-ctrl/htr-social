#!/usr/bin/env python3
"""Make sure a new swipe set never repeats an image and looks fresh next to everything TikTok has shown.

Justin, 2026-11-10: "Ensure that TikTok never posts the same image twice. Should look fresh to eyes daily."

Two checks against every swipe slide ever published (the dated folders of this repo) and the day's
other new sets:
  1. Same image: no new slide may be a copy or near-copy of any earlier slide (108x192 colour,
     mean difference under 1.2; two different slides have never been closer than 2.3).
  2. Fresh at a glance: the new set's first slide, the frame people see in the feed, must sit at
     least 20 apart (36x64 colour) from the first slide of every TikTok set already posted. The old
     repeating dark looks sat 4 to 7 apart from each other; clearly new designs sit 30 and up.

  tt_fresh_check.py <new slide png> [<more pngs>] [--outdir DIR] [--slug SLUG]
Exit 0 when both pass. Called by tiktok_slides.py, which redesigns the set when a check fails.
"""
import glob, os, re, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAME, GLANCE = 1.2, 20.0
CACHE = os.path.expanduser("~/htr-engine/.tt_thumbs.npz")


def _th(f, size):
    return np.asarray(Image.open(f).convert("RGB").resize(size), dtype=np.int16)


def _history():
    """Every published swipe slide: {path: (hi-res thumb, glance thumb)}, cached between runs."""
    files = sorted(glob.glob(os.path.join(HERE, "2026-*", "HTR_tt_*.jpg")) + glob.glob(os.path.join(HERE, "20[3-9]*", "HTR_tt_*.jpg")))
    cache = {}
    if os.path.isfile(CACHE):
        try:
            z = np.load(CACHE, allow_pickle=True); cache = z["d"].item()
        except Exception:
            cache = {}
    out, dirty = {}, False
    for f in files:
        k = os.path.relpath(f, HERE)
        if k not in cache:
            cache[k] = (_th(f, (108, 192)), _th(f, (36, 64))); dirty = True
        out[k] = cache[k]
    if dirty:
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            np.savez_compressed(CACHE, d=np.array(cache, dtype=object))
        except Exception:
            pass
    return out


def _set_of(name):
    m = re.match(r"HTR_tt_(.+)_\d\d\.(png|jpg)$", os.path.basename(name)); return m.group(1) if m else name


def check(new_files, outdir=None, slug=None):
    """Returns (ok, problems, glance distance of the new cover to its nearest earlier TikTok cover)."""
    hist = _history()
    problems = []
    newth = {f: (_th(f, (108, 192)), _th(f, (36, 64))) for f in new_files}
    # the day's other new sets (not yet published) count too
    others = {}
    if outdir and slug:
        for f in glob.glob(os.path.join(outdir, "HTR_tt_*.png")):
            if _set_of(f) != slug and f not in newth:
                others[f] = (_th(f, (108, 192)), _th(f, (36, 64)))
    pool = dict(hist); pool.update(others)
    for f, (hi, _) in newth.items():
        for k, (h2, _) in pool.items():
            if _set_of(k) == slug: continue                          # its own earlier render
            d = float(np.abs(hi - h2).mean())
            if d < SAME:
                problems.append("SAME IMAGE: %s repeats %s" % (os.path.basename(f), k))
                break
    cover = [f for f in new_files if f.endswith("_01.png") or f.endswith("_01.jpg")]
    nearest = None
    if cover:
        g = newth[cover[0]][1]
        covers = {k: v for k, v in pool.items() if re.search(r"_01\.(png|jpg)$", k) and _set_of(k) != slug
                  and re.search(r"-tt\d", _set_of(k))}
        if covers:
            nearest = min((float(np.abs(g - v[1]).mean()), k) for k, v in covers.items())
            if nearest[0] < GLANCE:
                problems.append("LOOKS LIKE AN EARLIER POST: first slide is %.1f from %s (needs %.0f)"
                                % (nearest[0], nearest[1], GLANCE))
    return not problems, problems, nearest


if __name__ == "__main__":
    args = sys.argv[1:]; outdir = slug = None
    if "--outdir" in args: i = args.index("--outdir"); outdir = args[i + 1]; del args[i:i + 2]
    if "--slug" in args: i = args.index("--slug"); slug = args[i + 1]; del args[i:i + 2]
    ok, probs, near = check(args, outdir, slug or (_set_of(args[0]) if args else None))
    for p in probs: print(p)
    if near: print("nearest earlier TikTok cover: %.1f (%s)" % near)
    print("FRESH CHECK: %s" % ("pass" if ok else "FAIL"))
    sys.exit(0 if ok else 1)
