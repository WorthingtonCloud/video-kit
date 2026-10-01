#!/usr/bin/env python3
"""Close-ups of the overlap audit's hits, three to a row, to look at before fixing:  vs crops 1,3,7,8
Needs `vs audit --shots` first (build/qa/overlaps.json + build/qa/overlaps/NN-*.png). Writes build/qa/overlaps/sheet-<ids>.png."""
import json, subprocess, sys, glob
W, H = json.load(open("reel.json"))["size"]
L = json.load(open("build/qa/overlaps.json")); want = [int(x) for x in sys.argv[1].split(",")]
files = []
for n in want:
    o = L[n - 1]; f = glob.glob(f"build/qa/overlaps/{n:02d}-*.png")[0]
    cx, cy = (o["box"][0] + o["box"][2]) / 2, (o["box"][1] + o["box"][3]) / 2
    x0, y0 = int(max(0, min(W - 540, cx - 270))), int(max(0, min(H - 400, cy - 200)))
    out = f"build/qa/overlaps/crop-{n:02d}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f, "-vf", f"crop=540:400:{x0}:{y0}", out], check=True); files.append(out)
while len(files) % 3: files.append(files[-1])
args = sum((["-i", f] for f in files), [])
rows = len(files) // 3
fc = [f"{''.join(f'[{r*3+j}]' for j in range(3))}hstack=3[r{r}]" for r in range(rows)]
fc.append(f"{''.join(f'[r{r}]' for r in range(rows))}vstack={rows}[o]" if rows > 1 else "[r0]copy[o]")
out = f"build/qa/overlaps/sheet-{sys.argv[1].replace(',', '_')}.png"
subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", ";".join(fc), "-map", "[o]", out], check=True)
print(out)
