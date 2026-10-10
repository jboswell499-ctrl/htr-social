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
- `tools/extract_chapter.py` — pulls a page range from the book PDF and checks
  quotes against it.
- `tools/prep_images.py` — PNG to JPEG (quality 92) with a size check.

Images in the repo root are from 2026-10-06, before the dated folders.

## Colour schemes

renderers/htrcards.py picks a palette per asset when --palette is not given (auto), so consecutive posts on a platform never share a scheme and the set shifts by one each day. Palettes: gold, bone, oxblood, navy, forest, mustard. Pass --palette to override. hookcard.py takes the same palette names.
