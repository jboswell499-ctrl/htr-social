#!/usr/bin/env python3
"""Pick today's look for each visual slot, favouring what is working while still testing the rest.

  pick_looks.py [YYYY-MM-DD]

Prints one line per slot, for example "TT-1 ledger". Reads style_scores.json (written by
style_report.py) from the repo root if it exists.

Rules
- Pool: classic (the original renderers) plus the five looks in renderers/looks.py.
- A look with fewer than 3 scored posts on that network is still being tested and goes first, so
  every look gets a fair sample. After that, looks are ranked by average views with likes per 100
  views as the tie-break, and the day decides the order among equals.
- One slot in four is always given to a non-leading look, so the ranking keeps getting checked.
- The four TikTok sets get four different looks, and the slot each look lands in rotates daily so
  a look is not judged by one posting time. The two Instagram Reels get two different looks.
"""
import datetime, json, os, sys

POOL = ["classic", "editorial", "ledger", "block", "notebook", "poster"]
MIN_N = 3

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

def picks_for(d):
    """All six picks for date d. Sunday is always classic (scripture day needs the cross motif)."""
    slots = ["TT-1", "TT-2", "TT-3", "TT-4", "IG-2", "IG-4"]
    if d.weekday() == 6: return dict.fromkeys(slots, "classic")
    p = os.path.join(HERE, "style_scores.json")
    scores = json.load(open(p)) if os.path.isfile(p) else {}
    day = d.toordinal()
    out = dict(zip(slots[:4], pick("tiktok", 4, scores, day)))
    out.update(zip(slots[4:], pick("instagram", 2, scores, day + 3)))
    return out

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

def record(slot, look, palette="-", d=None):
    """Note the look a slot was actually rendered in (it can fall back to classic)."""
    todays_look(slot, d); d = d or today_ny(); f = _path(d)
    rec = json.load(open(f)); rec["used"][slot] = {"look": look, "palette": palette}
    json.dump(rec, open(f, "w"), indent=1)

def main():
    d = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else today_ny()
    for slot, look in picks_for(d).items():
        print(slot, look)

if __name__ == "__main__":
    main()
