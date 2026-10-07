#!/usr/bin/env python3
"""Turn one or more 1080x1920 images into a silent-audio MP4 Reel (H.264, 30 fps).

  make_reel.py OUT.mp4 SECONDS_PER_IMAGE IMG [IMG ...]

One image gives a still held for SECONDS_PER_IMAGE; several give a slide sequence
with a short crossfade. Instagram attaches the chosen song on top of this file.
Exits 1 if ffmpeg fails or the result is not 1080x1920.
"""
import sys, subprocess, json
def main(out, sec, imgs):
    sec = float(sec); fade = 0.4; cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for i in imgs: cmd += ["-loop", "1", "-t", str(sec + (fade if len(imgs) > 1 else 0)), "-i", i]
    total = sec * len(imgs) + (fade if len(imgs) > 1 else 0)
    cmd += ["-f", "lavfi", "-t", str(total), "-i", "anullsrc=r=44100:cl=stereo"]
    if len(imgs) == 1:
        fc = "[0:v]scale=1080:1920,format=yuv420p,fps=30[v]"
    else:
        parts = ["[%d:v]scale=1080:1920,format=yuv420p,fps=30[s%d]" % (i, i) for i in range(len(imgs))]
        prev = "s0"
        for i in range(1, len(imgs)):
            parts.append("[%s][s%d]xfade=transition=fade:duration=%s:offset=%s[x%d]" % (prev, i, fade, sec * i, i)); prev = "x%d" % i
        fc = ";".join(parts) + ";[%s]null[v]" % prev
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "%d:a" % len(imgs), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", out]
    if subprocess.run(cmd).returncode: return 1
    p = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration,size", "-of", "json", out]))
    w, h = p["streams"][0]["width"], p["streams"][0]["height"]
    print("%s %dx%d %.1fs %s bytes" % (out, w, h, float(p["format"]["duration"]), p["format"]["size"]))
    return 0 if (w, h) == (1080, 1920) else 1
if __name__ == "__main__":
    if len(sys.argv) < 4: print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3:]))
