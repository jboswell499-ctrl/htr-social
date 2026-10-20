#!/usr/bin/env python3
"""Join STYLE_LOG.csv with Metricool per-post metrics and rank the looks by views and likes.

  style_report.py TIKTOK.json REELS.json [--log STYLE_LOG.csv] [--out STYLE_REPORT.md]

TIKTOK.json: the raw result of getAnalyticsDataByMetrics with metrics, in this order,
  ["TKPO02","TKPO05","TKPO07","TKPO08","TKPO09","TKPO10"]  (time UTC, text, views, likes, comments, shares)
REELS.json: same for Instagram Reels with
  ["IGRE02","IGRE03","IGRE23","IGRE10","IGRE07","IGRE21"]  (time UTC, text, views, likes, comments, shares)
Either file may be "-" to skip it. A post is matched to its log row by network and publish time
(within 30 minutes). Posts younger than 48 hours are shown but left out of the scores, since their
numbers are still climbing. Writes STYLE_REPORT.md and style_scores.json next to the log.

Also left out of the scores (still listed, with the reason):
- posts inside an EXCLUDE window, when the whole account's reach was down and the numbers say nothing
  about the look;
- matches that are not clear: another post on the same network landed less than 10 minutes further
  from the slot time than the chosen one, so the views may belong to a different post.
"""
import argparse, csv, datetime, json, os, sys, zoneinfo

NY = zoneinfo.ZoneInfo("America/New_York"); UTC = datetime.timezone.utc
SETTLE_H = 48
AMBIG_MIN = 10
# (network, from, to) in America/New_York, inclusive. TikTok reach fell to 0-6 views per post from
# midday 2026-10-16, after posting went from 4 to 12-14 a day; the publisher runs 2 a day through
# 2026-10-26 to recover. Nothing posted in that stretch is evidence for or against a look.
EXCLUDE = [("tiktok", "2026-10-16T12:00", "2026-10-26T23:59", "TikTok reach drop")]

def excluded(network, t):
    for net, lo, hi, why in EXCLUDE:
        lo = datetime.datetime.fromisoformat(lo).replace(tzinfo=NY)
        hi = datetime.datetime.fromisoformat(hi).replace(tzinfo=NY)
        if net == network and lo <= t <= hi: return why
    return None

def load_rows(path, network):
    if path == "-" or not os.path.isfile(path): return []
    d = json.load(open(path))
    rows = d.get("rows", d) if isinstance(d, dict) else d
    out = []
    for r in rows:
        try:
            t = datetime.datetime.strptime(str(r[0])[:14], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        except ValueError:
            continue
        num = lambda x: float(x) if str(x).replace(".", "", 1).isdigit() else 0.0
        out.append(dict(network=network, t=t, text=r[1], views=num(r[2]), likes=num(r[3]),
                        comments=num(r[4]), shares=num(r[5])))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tiktok"); ap.add_argument("reels")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--log", default=os.path.join(here, "STYLE_LOG.csv"))
    ap.add_argument("--out", default=os.path.join(here, "STYLE_REPORT.md"))
    a = ap.parse_args()
    posts = load_rows(a.tiktok, "tiktok") + load_rows(a.reels, "instagram")
    log = list(csv.DictReader(open(a.log)))
    now = datetime.datetime.now(UTC)
    matched, unmatched = [], 0
    for row in log:
        t = datetime.datetime.fromisoformat("%sT%s" % (row["date"], row["time_et"])).replace(tzinfo=NY).astimezone(UTC)
        cand = [p for p in posts if p["network"] == row["network"] and abs((p["t"] - t).total_seconds()) <= 1800]
        if not cand:
            unmatched += 1; continue
        cand.sort(key=lambda p: abs((p["t"] - t).total_seconds()))
        p = cand[0]
        age = (now - p["t"]).total_seconds() / 3600
        gap = lambda q: abs((q["t"] - t).total_seconds())
        if len(cand) > 1 and gap(cand[1]) - gap(p) < AMBIG_MIN * 60:
            why = "two posts at that time"
        else:
            why = excluded(row["network"], p["t"])
        if not why and age < SETTLE_H: why = "new"
        matched.append(dict(row, **{k: p[k] for k in ("views", "likes", "comments", "shares")},
                            settled=not why, why=why or ""))
    # scores per look (settled posts only), overall and per network
    def agg(items):
        n = len(items)
        if not n: return None
        v = sum(i["views"] for i in items); l = sum(i["likes"] for i in items)
        s = sum(i["shares"] for i in items); c = sum(i["comments"] for i in items)
        return dict(n=n, avg_views=round(v / n, 1), avg_likes=round(l / n, 2),
                    likes_per_100_views=round(100 * l / v, 2) if v else 0.0,
                    shares=int(s), comments=int(c))
    looks = sorted({m["look"] for m in matched})
    scores = {"updated": now.astimezone(NY).strftime("%Y-%m-%d %H:%M"), "looks": {}, "by_network": {}}
    for lk in looks:
        r = agg([m for m in matched if m["look"] == lk and m["settled"]])
        if r: scores["looks"][lk] = r
        for net in ("tiktok", "instagram"):
            r = agg([m for m in matched if m["look"] == lk and m["network"] == net and m["settled"]])
            if r: scores["by_network"].setdefault(net, {})[lk] = r
    json.dump(scores, open(os.path.join(os.path.dirname(a.log), "style_scores.json"), "w"), indent=1)

    L = ["# HTR style report", "", "Updated %s (America/New_York). Scores use posts at least %d hours old; "
         "newer posts are listed but not scored." % (scores["updated"], SETTLE_H), ""]
    for net, lo, hi, why in EXCLUDE:
        L.extend(["Not scored: %s posts from %s to %s (%s)." % (net.capitalize(), lo.replace("T", " "),
                  hi.replace("T", " "), why), ""])
    def table(title, d):
        L.extend(["## " + title, "", "| Look | Posts | Avg views | Avg likes | Likes per 100 views | Shares | Comments |",
                  "|---|---|---|---|---|---|---|"])
        for lk, r in sorted(d.items(), key=lambda kv: -kv[1]["avg_views"]):
            L.append("| %s | %d | %.1f | %.2f | %.2f | %d | %d |" % (lk, r["n"], r["avg_views"], r["avg_likes"],
                     r["likes_per_100_views"], r["shares"], r["comments"]))
        L.append("")
    table("All networks", scores["looks"])
    for net, d in scores["by_network"].items(): table(net.capitalize(), d)
    L.extend(["Read with care: fewer than 3 posts per look is noise, and TikTok views swing with the hook "
              "as much as with the look.", "", "## Every logged post", "",
              "| Date | Slot | Look | Palette | Views | Likes | Shares | Scored | Hook |", "|---|---|---|---|---|---|---|---|---|"])
    for m in sorted(matched, key=lambda m: (m["date"], m["time_et"])):
        L.append("| %s | %s | %s | %s | %d | %d | %d | %s | %s |" % (m["date"], m["slot"], m["look"], m["palette"],
                 m["views"], m["likes"], m["shares"], "yes" if m["settled"] else "no (%s)" % m["why"], m["hook"].replace("|", "/")))
    L.extend(["", "%d logged posts matched, %d not found in the metrics yet." % (len(matched), unmatched)])
    open(a.out, "w").write("\n".join(L) + "\n")
    print("matched %d, unmatched %d, looks scored: %s" % (len(matched), unmatched, ", ".join(scores["looks"]) or "none"))

if __name__ == "__main__":
    main()
