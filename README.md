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
