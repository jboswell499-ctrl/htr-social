#!/usr/bin/env python3
"""Add a day's visual posts to STYLE_LOG.csv from its RUN_STATUS.md and looks/DATE.json.

  log_today.py YYYY-MM-DD

Only slots marked "scheduled" in RUN_STATUS.md are logged (TT-1..TT-4, IG-2, IG-3, IG-4). IG-3 is the
Sunday focus list (added 2026-10-25); it is logged under the look "focus-list", which pick_looks never picks. The look comes
from the "used" record the renderers wrote; a slot with no record is logged as classic. Rows already
in the log for that date and slot are left alone, so running it twice is safe.
"""
import csv, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSIC_PAL = {"TT-1": "gold", "TT-2": "bone", "TT-3": "oxblood", "TT-4": "navy", "IG-4": "carousel"}

def main():
    date = sys.argv[1]
    rs = os.path.join(HERE, date, "RUN_STATUS.md")
    if not os.path.isfile(rs):
        print("no RUN_STATUS.md for %s" % date); return 1
    text = open(rs).read()
    m = re.search(r"Ch(\d+)", text); ch = m.group(1) if m else "?"
    lk = os.path.join(HERE, "looks", date + ".json")
    used = json.load(open(lk)).get("used", {}) if os.path.isfile(lk) else {}
    logp = os.path.join(HERE, "STYLE_LOG.csv")
    rows = list(csv.DictReader(open(logp)))
    have = {(r["date"], r["slot"]) for r in rows}
    new = []
    for line in text.splitlines():
        m = re.match(r"^(TT-[1-4]|IG-[234]) (\d\d:\d\d) (tiktok|instagram): scheduled(.*)$", line.strip())
        if not m or (date, m.group(1)) in have: continue
        slot, t, net, rest = m.groups()
        u = used.get(slot, {"look": "classic", "palette": CLASSIC_PAL.get(slot, "-")})
        if slot == "IG-3": u = {"look": "focus-list", "palette": "-"}
        if net == "tiktok":
            h = re.search(r"Slide 1:\s*(.+?)\s*$", rest); hook = h.group(1) if h else ""
            piece = "slides"
        else:
            hook = "Ch%s %s" % (ch, {"IG-2": "Daily Standard", "IG-3": "focus list"}.get(slot, "carousel"))
            piece = {"IG-2": "quote-reel", "IG-3": "focus-reel"}.get(slot, "carousel-reel")
        new.append(dict(date=date, slot=slot, network=net, time_et=t, piece=piece,
                        look=u["look"], palette=u.get("palette", "-"), hook=hook))
    if new:
        with open(logp, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date", "slot", "network", "time_et", "piece", "look", "palette", "hook"])
            for r in new: w.writerow(r)
    print("logged %d rows for %s: %s" % (len(new), date, ", ".join("%s %s" % (r["slot"], r["look"]) for r in new)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
