#!/usr/bin/env python3
"""Extract a page range of the book PDF to clean text, and check quotes against it.

  extract_chapter.py extract <saved-download.json | book.pdf> FIRST LAST OUT.txt
  extract_chapter.py check OUT.txt "sentence one" "sentence two" ...

extract: accepts either the JSON file the Drive download tool saves ({"content": base64})
or a plain PDF. Printed page numbers equal PDF page numbers. Exits 1 if any
non-breaking space survives.
check: exits 1 unless every sentence is found in the text. Whitespace runs and
curly/straight quote differences are ignored; everything else must match exactly.
Source is pure ASCII on purpose: special characters are written as chr() codes.
"""
import sys, re, json, base64, unicodedata

LS, PS, SHY, NBSP = chr(0x2028), chr(0x2029), chr(0xad), chr(0xa0)
QUOTES = {chr(0x2018): "'", chr(0x2019): "'", chr(0x201c): '"', chr(0x201d): '"'}

def clean(t):
    t = t.replace(LS, "\n").replace(PS, "\n\n")
    t = unicodedata.normalize("NFKC", t)          # nbsp -> space, fi/fl/ff ligatures folded
    t = t.replace(SHY, "-")
    t = re.sub(r"^\s*\d{1,3}\s*$", "", t, flags=re.M)   # bare page numbers
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()

def norm(t):
    for k, v in QUOTES.items():
        t = t.replace(k, v)
    return re.sub(r"\s+", " ", t).strip()

def extract(src, first, last, out):
    import pymupdf
    raw = open(src, "rb").read()
    if not raw.startswith(b"%PDF"):
        raw = base64.b64decode(json.loads(raw)["content"])
    d = pymupdf.open(stream=raw, filetype="pdf")
    if len(d) < last:
        print("ERROR: PDF has %d pages, asked for %d" % (len(d), last)); return 1
    t = clean("\n".join(d[p - 1].get_text() for p in range(first, last + 1)))
    open(out, "w").write(t)
    stray = t.count(NBSP)
    print("pages %d-%d | chars: %d | stray nbsp: %d" % (first, last, len(t), stray))
    print(t[:600])
    return 1 if stray or len(t) < 2000 else 0

def check(txt, sentences):
    hay = norm(open(txt).read()); bad = 0
    for s in sentences:
        ok = norm(s) in hay
        bad += not ok
        print(("MATCH    " if ok else "NO MATCH ") + s)
    print("%d of %d matched" % (len(sentences) - bad, len(sentences)))
    return 1 if bad else 0

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 5 and a[0] == "extract":
        sys.exit(extract(a[1], int(a[2]), int(a[3]), a[4]))
    if len(a) >= 3 and a[0] == "check":
        sys.exit(check(a[1], a[2:]))
    print(__doc__); sys.exit(2)
