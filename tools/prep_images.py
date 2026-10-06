#!/usr/bin/env python3
"""Convert every PNG in SRC to JPEG (quality 92) in DEST and verify sizes.

  prep_images.py SRC_DIR DEST_DIR

Prints one line per file. Exits 1 if any image has an unexpected size.
"""
import sys, os, glob
from PIL import Image
OK = {(1080, 1350), (1080, 1920), (1080, 1080), (1200, 675)}
def main(src, dest):
    os.makedirs(dest, exist_ok=True); bad = 0
    files = sorted(glob.glob(os.path.join(src, "*.png")))
    if not files:
        print("ERROR: no PNG files in", src); return 1
    for f in files:
        im = Image.open(f).convert("RGB")
        out = os.path.join(dest, os.path.splitext(os.path.basename(f))[0] + ".jpg")
        im.save(out, quality=92)
        flag = "" if im.size in OK else "  <-- UNEXPECTED SIZE"
        bad += bool(flag)
        print("%s %dx%d %d bytes%s" % (os.path.basename(out), im.size[0], im.size[1], os.path.getsize(out), flag))
    return 1 if bad else 0
if __name__ == "__main__":
    if len(sys.argv) != 3: print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
