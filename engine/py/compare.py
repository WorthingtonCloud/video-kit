#!/usr/bin/env python3
"""Did a change move any pixels? Compare two folders of frames (vs snap --every 1 --out <dir>, before and after):
    vs compare <before dir> <after dir>   → how many frames are identical, and where the rest differ and by how much
A refactor should leave every frame identical; a fix should change only the frames it meant to."""
import os, subprocess, sys
import numpy as np

a, b = sys.argv[1], sys.argv[2]


def png(p):
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                    "-of", "csv=p=0", p], capture_output=True, text=True, check=True).stdout.strip().split(","))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.int16)


# frames match by their time (the file name is the seconds), however each folder spelled it
at = lambda d: {round(float(f[:-4]), 3): os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png")}
A, B = at(a), at(b)
names = sorted(A)
same, diff, missing = 0, [], [n for n in names if n not in B]
for n in names:
    if n in missing: continue
    x, y = png(A[n]), png(B[n])
    if x.shape != y.shape: diff.append((n, "size differs", 0, 0)); continue
    d = np.abs(x - y).max(axis=2)
    if d.max() == 0: same += 1
    else:
        ys, xs = np.where(d > 8)
        box = f"x {xs.min()}–{xs.max()}, y {ys.min()}–{ys.max()}" if len(xs) else "faint"
        diff.append((n, int(d.max()), int((d > 8).sum()), box))
print(f"{same} identical, {len(diff)} differ, {len(missing)} missing (of {len(names)})")
for n, mx, cnt, box in diff[:60]:
    print(f"  {n:7.2f}s: max {mx}, {cnt} px changed, {box}")
