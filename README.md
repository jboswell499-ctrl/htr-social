# htr-social

Public image host and tooling for the Hard To Replace daily posts.

- `YYYY-MM-DD/` — that day's post images (JPEG). Public URL:
  `https://raw.githubusercontent.com/jboswell499-ctrl/htr-social/main/YYYY-MM-DD/<file>.jpg`
- `renderers/hookcard.py` — hook card, 1080x1920 and 1080x1080, gold and bone.
- `renderers/htrcards.py` — carousel slides and the Daily Standard quote card
  (`--ratio 4x5 | 9x16 | 1x1 | 16x9`). In slide bodies a blank line starts a new
  paragraph and a single newline is a line break.
- `renderers/tiktok_slides.py` — TikTok swipe slides (5 to 7 per post, one thought per slide, hook first,
  question last, no brand furniture). Files `HTR_tt_<slug>-ttN_NN`. Added 2026-10-10 after quote cards
  stalled at 100 to 200 views with 2 to 5 seconds of attention.
- `renderers/motif.py` — `--motif cross` on any of the three renderers puts a quiet cross behind the type. Used on
  Sunday scripture days so every image carries Christian imagery.
- `tools/extract_chapter.py` — pulls a page range from the book PDF and checks
  quotes against it.
- `tools/prep_images.py` — PNG to JPEG (quality 92) with a size check.

Images in the repo root are from 2026-10-06, before the dated folders.

## Colour schemes

renderers/htrcards.py picks a palette per asset when --palette is not given (auto), so consecutive posts on a platform never share a scheme and the set shifts by one each day. Palettes: gold, bone, oxblood, navy, forest, mustard. Pass --palette to override. hookcard.py takes the same palette names.

## Looks and style tracking (added 2026-10-13)

- `renderers/looks.py` adds five looks: editorial, ledger, block, notebook, poster.
- Each day `tools/pick_looks.py` picks a look for TT-1..TT-4, IG-2 (Q1 Reel and Story) and IG-4 (carousel Reel, also FB-4 and LI-3). The pick is frozen in `looks/DATE.json` the first time a renderer asks for it.
- `tiktok_slides.py` (slugs ending -ttN), `htrcards.py --mode carousel` and `htrcards.py --mode quote` for `-q1` at 9x16 hand off to looks.py automatically when the pick is not classic. Pass `--look classic` to force the original look. `--motif cross` (Sunday) always stays classic.
- Nightly: `tools/log_today.py DATE` adds the day's posts to `STYLE_LOG.csv`; `tools/style_report.py` joins the log with Metricool per-post views and likes and writes `STYLE_REPORT.md` and `style_scores.json`, which the next day's picks read. Looks that win on views get used more; looks with fewer than 3 scored posts keep being tested.

## TikTok recovery and retired looks (2026-10-19)

- TikTok reach fell to 0-6 views per post from midday 2026-10-16, right after the account went from 4 posts a day to 12-14 (a separate batch of short videos was posting alongside the publisher, sometimes in the same minute). The last two queued videos of that batch (2026-10-20 10:15 and 12:15) were turned into drafts.
- 2026-10-20 to 2026-10-26: the publisher posts only TT-1 (10:00) and TT-3 (16:00), and skips a TikTok slot if another TikTok is within 2 hours of it. All four slots return on 2026-10-27. `pick_looks.TT_RECOVERY` holds the dates.
- `style_report.py` does not score TikTok posts from 2026-10-16 12:00 to 2026-10-26 (`EXCLUDE`), or a post when another one landed at nearly the same time, so the looks are not blamed for the account-wide drop.
- `poster` is retired (`pick_looks.RETIRED`): 24 views on its one Instagram Reel against a 69 average for classic, and 2 views on each of its TikToks.

## Sunday focus list (2026-10-25)

- `renderers/focuslist.py --json LIST.json --slug SLUG` renders the Sunday focus list: a short numbered list (3 to 5 items,
  each with one plain line on what to do with it) over a generated scene of a rough-hewn wooden cross in warm interior light.
  Writes `HTR_focus_<slug>_4x5.png` (Facebook) and `HTR_focus_<slug>_9x16.png` (Reel and Story, type outside the top 288 px
  and bottom 422 px). The scene (backlit or side-lit, amber, candle or dawn light) is chosen from the slug, and the type is
  kept clear of the cross automatically; it flags "TYPE TOO SMALL OR OVERFLOW" if the copy had to shrink too far.
- Added at Justin's request after he shared a faith "focus list" post he liked, asking for posts similar to it, not a copy:
  no sky, clouds or mountain, no distressed type or brush underline, and every item carries a plain line.
- Scheduled each Sunday as IG-3 (15:00 Reel), ST-3 (15:02 Story) and FB-3 (15:00 post). `log_today.py` logs IG-3 under the
  look `focus-list`, which `pick_looks.py` never picks for the other slots.
