#!/usr/bin/env python3
"""Pick today's look for each visual slot, favouring what is working while still testing the rest.

  pick_looks.py [YYYY-MM-DD]

Prints one line per slot, for example "TT-1 ledger". Reads style_scores.json (written by
style_report.py) from the repo root if it exists.

Rules
- FROM 2026-11-10 THE SWIPE SETS DO NOT USE THESE PICKS. Justin: "It needs to be different everyday.
  Not rotate between 5." tiktok_slides.py now builds a brand-new design for every set with
  renderers/fresh.py and records it here with record(..., spec=...). The rotation below is only what
  you get if someone passes --look explicitly, and it still feeds the quote card and carousel.
- Pool: classic (the original renderers) plus the looks in renderers/looks.py.
- EVERY SWIPE SET LOOKS DIFFERENT (Justin's call on 2026-11-09: "why are all the TikToks looking
  exactly the same"). The two TikTok sets (TT-1, TT-3) and the Instagram Reel (IG-1) no longer follow
  the scores. They walk the pool in a fixed rotation: the day's three sets get three different looks,
  no TikTok look repeats on the next day, the Reel never repeats the day before, and every look takes
  its turn at 10:00 and at 16:00. The scores are still reported every night; a look that keeps losing
  is taken out by adding it to RETIRED.
- Sunday is always classic (the scripture day needs the cross motif), so Saturday and Monday skip
  classic. A classic set takes its colour from classic_palette(): the colour used least recently.
- The quote card (IG-2) and the carousel (IG-4) keep the old score-based pick: a look with fewer than
  3 scored posts goes first, then looks are ranked by average views.
- Retired looks (RETIRED below) are never picked. Their old posts stay in the log and the report.
- Two TikToks a day: from 2026-10-20 only TT-1 and TT-3 are posted (permanent from 2026-10-26).
"""
import datetime, glob, json, os, sys

# poster retired 2026-10-19 on Justin's call: 24 views on its one Instagram Reel (classic averaged 69)
# and 2 views on each of its two TikToks.
RETIRED = {"poster": "2026-10-19"}
POOL = [lk for lk in ["classic", "editorial", "ledger", "block", "notebook", "poster"] if lk not in RETIRED]
MIN_N = 3

# TikTok reach collapsed on 2026-10-16 after the account went from 4 to 12-14 posts a day. From
# 2026-10-20 the publisher posts only TT-1 and TT-3; on 2026-10-26 Justin made two a day permanent.
TT_TWO_FROM = datetime.date(2026, 10, 20)

def tiktok_slots(d):
    return ["TT-1", "TT-3"] if d >= TT_TWO_FROM else ["TT-1", "TT-2", "TT-3", "TT-4"]

def ranked(scores, net, day):
    d = scores.get("by_network", {}).get(net, {})
    rot = POOL[day % len(POOL):] + POOL[:day % len(POOL)]
    testing = [lk for lk in rot if d.get(lk, {}).get("n", 0) < MIN_N]
    proven = sorted([lk for lk in rot if lk not in testing],
                    key=lambda lk: (-d[lk]["avg_views"], -d[lk]["likes_per_100_views"]))
    return testing, proven

def pick(net, k, scores, day):
    testing, proven = ranked(scores, net, day)
    if not proven:
        order = testing
    else:
        best = proven[: max(1, k - 1)]
        rest = [lk for lk in testing + proven if lk not in best]
        order = best + rest
    chosen = order[:k]
    shift = day % k
    return chosen[shift:] + chosen[:shift]

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def swipe_picks(d):
    """Looks for (TT-1, TT-3, IG-1) on date d: a fixed walk through POOL, two steps a day."""
    n = len(POOL); day = d.toordinal()
    tt1, tt3, reel = POOL[(2 * day) % n], POOL[(2 * day + 1) % n], POOL[(2 * day + 3) % n]
    if d.weekday() in (5, 0) and n >= 5:        # Saturday and Monday sit next to an all-classic Sunday
        spare = POOL[(2 * day + 4) % n]
        if tt1 == "classic": tt1 = spare
        elif tt3 == "classic": tt3 = spare
    return tt1, tt3, reel

def picks_for(d):
    """All picks for date d. Sunday is always classic (scripture day needs the cross motif)."""
    slots = ["TT-1", "TT-2", "TT-3", "TT-4", "IG-1", "IG-2", "IG-4"]
    if d.weekday() == 6: return dict.fromkeys(slots, "classic")
    p = os.path.join(HERE, "style_scores.json")
    scores = json.load(open(p)) if os.path.isfile(p) else {}
    day = d.toordinal()
    out = dict.fromkeys(slots[:4], "classic")
    out.update(zip(slots[4:], pick("instagram", 3, scores, day + 3)))
    out["TT-1"], out["TT-3"], out["IG-1"] = swipe_picks(d)
    return out

CLASSIC_PALS = ["gold", "oxblood", "bone", "navy", "forest", "mustard"]

def classic_palette(slot, d=None):
    """Colour for a classic swipe set: the one used least recently, so classic never looks the same twice running."""
    d = d or today_ny(); f = _path(d)
    if os.path.isfile(f):
        u = json.load(open(f)).get("used", {}).get(slot, {})
        if u.get("look") == "classic" and u.get("palette") in CLASSIC_PALS: return u["palette"]   # a re-render keeps its colour
    if d.weekday() == 6 and slot in ("TT-1", "TT-3"):      # Sunday's two classic sets: a different pair of colours each week
        pair = CLASSIC_PALS[2 * (d.isocalendar()[1] % 3):][:2]
        return pair[0] if slot == "TT-1" else pair[1]
    recent = []
    for g in sorted(glob.glob(os.path.join(HERE, "looks", "*.json")), reverse=True)[:40]:
        if os.path.basename(g)[:10] > d.isoformat(): continue
        try: used = json.load(open(g)).get("used", {})
        except Exception: continue
        for s in ("IG-1", "TT-3", "TT-1"):
            u = used.get(s, {})
            if u.get("look") == "classic" and u.get("palette") in CLASSIC_PALS: recent.append(u["palette"])
    fresh = [c for c in CLASSIC_PALS if c not in recent]
    return fresh[0] if fresh else max(CLASSIC_PALS, key=recent.index)

def today_ny():
    import zoneinfo
    return datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York")).date()

def _path(d): return os.path.join(HERE, "looks", "%s.json" % d.isoformat())

def todays_look(slot, d=None):
    """The look for a slot today. The day's picks are frozen in looks/DATE.json on first use."""
    d = d or today_ny(); f = _path(d)
    if os.path.isfile(f):
        rec = json.load(open(f))
    else:
        rec = {"date": d.isoformat(), "picked": picks_for(d), "used": {}}
        os.makedirs(os.path.dirname(f), exist_ok=True); json.dump(rec, open(f, "w"), indent=1)
    return rec["picked"].get(slot, "classic")

def record(slot, look, palette="-", d=None, spec=None):
    """Note the look a slot was actually rendered in (it can fall back to classic)."""
    todays_look(slot, d); d = d or today_ny(); f = _path(d)
    rec = json.load(open(f)); rec["used"][slot] = {"look": look, "palette": palette}
    if spec: rec["used"][slot]["spec"] = spec
    json.dump(rec, open(f, "w"), indent=1)

def main():
    d = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else today_ny()
    for slot, look in picks_for(d).items():
        print(slot, look)

if __name__ == "__main__":
    main()
