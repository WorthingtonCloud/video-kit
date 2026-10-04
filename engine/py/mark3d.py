#!/usr/bin/env python3
"""A 3D end card, if Blender is installed: your mark built as a lit tile, rendered as see-through frames the end card
plays in place of the flat one. Free (it renders on this machine); optional (no Blender, the drawn mark plays).

    vs mark3d --quick          three stills (the tile swinging in, the point landing, at rest) to look at first: ~30 s
    vs mark3d                  all 132 frames into the studio's library, and the profile set to play them (a few minutes)
    vs mark3d --replace        the same, over a set the studio already has
    vs mark3d --off            stop playing it (the frames stay in the library)

What it builds: profile.json → brand.endcard.mark (the drawn mark: an SVG path of straight lines and an accent point
rectangle) in the profile's palette (card, ink, accent). The tile swings up, the lines draw in turn, the point drops and
lands on frame 33, which the end card puts on its beat, and a light sweeps the tile. A logo picture (endcard.logo) or a
path with curves can't be built: draw the mark with straight lines, or render your own frames (any 3D tool) into a
folder and set brand.endcard.mark3d = {"frames": "<folder>", "land_frame": <the frame the point lands>, "box": [x, y,
size]} by hand (box: where the frames sit on the 1080-wide end card; the drawn tile is 240 px at 420, 455).

Blender: found on the PATH (blender), at /Applications/Blender.app, or wherever BLENDER points. vs doctor says which.
Made from one studio's logo (Oct 4, 2026) and kept general."""
import argparse, glob, json, os, shutil, subprocess, sys, tempfile
import numpy as np
import vslib

ap = argparse.ArgumentParser()
ap.add_argument("--quick", action="store_true", help="three stills to look at, nothing kept")
ap.add_argument("--replace", action="store_true")
ap.add_argument("--off", action="store_true")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--px", type=int, default=416, help="the frames' size in the library (square)")
a = ap.parse_args()

S = vslib.studio_root() or sys.exit("⛔ no studio (vs setup)")
P_PATH = os.path.join(S, "profile.json")
LIB = "library/brand/mark3d"  # relative to the studio, as the profile stores it
TILE = (420, 455, 240)  # the drawn tile on the 1080-wide end card (engine/js/pipeline/css.mjs → .tileicon)


def blender():
    """Blender's command, or None: BLENDER, then the PATH, then the usual install places."""
    c = [os.environ.get("BLENDER"), shutil.which("blender"), "/Applications/Blender.app/Contents/MacOS/Blender",
         *sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"), reverse=True)]
    return next((x for x in c if x and os.path.exists(x)), None)


def save_profile(mark3d):
    P = vslib.read_json(P_PATH)
    end = P.setdefault("brand", {}).setdefault("endcard", {})
    if mark3d is None:
        end.pop("mark3d", None)
    else:
        end["mark3d"] = mark3d
    tmp = P_PATH + ".part"
    json.dump(P, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, P_PATH)


if a.off:
    save_profile(None)
    print("the end card plays the drawn mark again (the frames stay in the library)")
    sys.exit(0)

B = blender()
if not B:
    sys.exit("⛔ no Blender here: it's free (blender.org). Install it, or set BLENDER to its path; vs doctor checks")
pr = vslib.profile()
end = (pr.get("brand") or {}).get("endcard") or {}
mark = end.get("mark")
if not mark:
    sys.exit("⛔ profile.json → brand.endcard has no mark to build (a logo picture can't be): give it a mark "
             "{path, point, viewBox}, or render your own frames and set brand.endcard.mark3d by hand (vs help mark3d)")
dest = os.path.join(S, LIB)
if not a.quick and os.path.isdir(dest) and os.listdir(dest) and not a.replace:
    sys.exit(f"⛔ the studio already has a 3D mark ({LIB}): --replace builds a new one over it")

work = tempfile.mkdtemp(prefix="vk-mark3d-")
job = {"mark": mark, "palette": (pr.get("brand") or {}).get("palette") or {}, "out": os.path.join(work, "frames"),
       "size": 540 if a.quick else 1080, "samples": 16 if a.quick else a.samples, **({"frames": [14, 33, 132]} if a.quick else {})}
json.dump(job, open(os.path.join(work, "job.json"), "w"))
script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blender", "mark3d.py")
print(f"Blender: {B}\nbuilding {'three stills' if a.quick else 'the 3D mark, 132 frames'} …", flush=True)
p = subprocess.Popen([B, "-b", "--factory-startup", "--python", script, "--", os.path.join(work, "job.json")],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
tail = []
for line in p.stdout:
    tail = (tail + [line.rstrip()])[-30:]
    if line.startswith("FRAME ") and (a.quick or int(line.split()[1].split("/")[0]) % 22 == 0):
        print(f"  {line.split()[1]}", flush=True)
    if line.startswith("REFUSED:"):
        sys.exit("⛔ " + line[9:].strip())
if p.wait() != 0 or not os.path.exists(os.path.join(job["out"], "meta.json")):
    sys.exit("⛔ Blender failed:\n" + "\n".join(tail))
meta = json.load(open(os.path.join(job["out"], "meta.json")))

if a.quick:
    out = os.path.join(S, "library", "brand", "mark3d-quick.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    g = (pr.get("brand") or {}).get("palette", {}).get("ground", "#111114").lstrip("#")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *sum([["-i", os.path.join(job["out"], f"f{f:04d}.png")] for f in (14, 33, 132)], []),
                    "-f", "lavfi", "-i", f"color=0x{g}:s=1620x540", "-filter_complex",
                    "[0][1][2]hstack=3[m];[3][m]overlay=format=auto", "-frames:v", "1", out], check=True)
    shutil.rmtree(work, ignore_errors=True)
    print(f"✅ three stills: {out}\n   look at them; vs mark3d builds the whole thing")
    sys.exit(0)


def alpha(f, k=4):
    """A frame's see-through mask at a quarter size (ffmpeg decodes, numpy measures)."""
    n = meta["size"] // k
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-vf", f"alphaextract,scale={n}:{n}", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(n, n)


# one square crop holds every frame's pixels (the tile swings in from below, the point drops from above)
frames = sorted(glob.glob(os.path.join(job["out"], "f*.png")))
union = np.zeros_like(alpha(frames[0]), bool)
for f in frames:
    union |= alpha(f) > 4
ys, xs = np.nonzero(union)
k, N = 4, meta["size"]
x0, x1, y0, y1 = xs.min() * k - 8, (xs.max() + 1) * k + 8, ys.min() * k - 8, (ys.max() + 1) * k + 8
side = max(x1 - x0, y1 - y0)
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
x0, y0 = int(round(cx - side / 2)), int(round(cy - side / 2))
pad = max(0, -x0, -y0, x0 + side - N, y0 + side - N)  # a crop past the render's edge pads with see-through
stage = os.path.join(work, "lib")
os.makedirs(stage)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-start_number", "1", "-i", os.path.join(job["out"], "f%04d.png"),
                "-vf", f"pad={N + 2 * pad}:{N + 2 * pad}:{pad}:{pad}:color=0x00000000,crop={side}:{side}:{x0 + pad}:{y0 + pad},"
                f"scale={a.px}:{a.px}:flags=lanczos", "-start_number", "1", os.path.join(stage, "f%04d.png")], check=True)

# lay the tile at rest exactly over the drawn one: its front face, in the render's pixels → the library frame → the stage
s = a.px / side
tx0, ty0, tx1, _ = meta["tile_px"]
sc = TILE[2] / ((tx1 - tx0) * s)
box = [round(float(v), 1) for v in (TILE[0] - (tx0 - x0) * s * sc, TILE[1] - (ty0 - y0) * s * sc, a.px * sc)]
if os.path.isdir(dest):
    shutil.rmtree(dest)
shutil.move(stage, dest)
shutil.rmtree(work, ignore_errors=True)
save_profile({"frames": LIB, "fps": meta["fps"], "land_frame": meta["land_frame"], "box": box,
              "source": f"vs mark3d (Blender {meta['blender']}), {len(frames)} frames, cropped to {side} px of {N}, {a.px} px"})
print(f"✅ the 3D mark: {LIB} ({len(frames)} frames, {a.px} px), box {box}\n"
      "   profile.json → brand.endcard.mark3d set: the next build's end card plays it (vs mark3d --off goes back)")
