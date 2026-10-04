#!/usr/bin/env python3
"""The newest version of every video, by its plain name, in one folder: studio/latest/.

    vs latest            rebuild latest/ from finals/ (vs learn runs it after filing finals)
    vs latest --dry      say what it would hold, change nothing

finals/ keeps every version (corporate-job-v5-take1.mp4, …-16x9-v5-take1.mp4). latest/ holds only the newest of each
video and shape, named without a version (corporate-job.mp4, corporate-job-16x9.mp4) plus its cover, so the current cut
is always in the same place under the same name. Newest = the highest vN; a tie goes to the full file over a "-web"
copy, then to the newer file. latest/ is derived: it is rebuilt from finals/ each time, so never edit or file into it;
file into finals/ and run vs latest. Copies are APFS clones where the disk allows (no extra space)."""
import argparse, os, re, shutil, subprocess, sys
from datetime import datetime
import vslib

ap = argparse.ArgumentParser()
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()
S = vslib.studio_root() or sys.exit("⛔ no studio (vs setup)")
FIN, OUT = os.path.join(S, "finals"), os.path.join(S, "latest")
VID = re.compile(r"^(?P<name>.+?)-v(?P<v>\d+)(?P<tail>(?:-take\d+|-sfx|-web)?)\.mp4$")
COVER = re.compile(r"^(?P<name>.+?)-v(?P<v>\d+)-cover\.jpg$")

files = sorted(os.listdir(FIN)) if os.path.isdir(FIN) else []
best, covers = {}, {}
for f in files:
    m = VID.match(f)
    if m:
        p = os.path.join(FIN, f)
        rank = (int(m["v"]), m["tail"] != "-web", os.path.getmtime(p))
        if m["name"] not in best or rank > best[m["name"]][0]:
            best[m["name"]] = (rank, f)
    m = COVER.match(f)
    if m:
        covers.setdefault(m["name"], []).append((int(m["v"]), f))

want = {}  # latest/ name -> finals/ file
for name, ((v, _, _), f) in best.items():
    want[f"{name}.mp4"] = f
    cs = [c for c in sorted(covers.get(name, [])) if c[0] <= v]  # its own cover, else the newest earlier one
    if cs:
        want[f"{name}-cover.jpg"] = cs[-1][1]


def same(src, dst):
    return os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst) and \
        int(os.path.getmtime(src)) == int(os.path.getmtime(dst))


changed = []
if not a.dry:
    os.makedirs(OUT, exist_ok=True)
for out, f in sorted(want.items()):
    src, dst = os.path.join(FIN, f), os.path.join(OUT, out)
    if same(src, dst):
        continue
    changed.append(f"{out} ← {f}")
    if a.dry:
        continue
    tmp = dst + ".part"
    if subprocess.run(["cp", "-c", "-p", src, tmp], capture_output=True).returncode != 0:
        shutil.copy2(src, tmp)  # not APFS: a plain copy
    os.replace(tmp, dst)
stale = [f for f in (os.listdir(OUT) if os.path.isdir(OUT) else []) if f not in want and f != "VERSIONS.md"]
for f in stale:
    changed.append(f"{f} removed (no longer the newest of anything)")
    if not a.dry:
        os.remove(os.path.join(OUT, f))

if not a.dry:
    rows = ["# Latest versions", "",
            "Rebuilt by `vs latest` from `finals/` (every version lives there). Don't edit this folder; file into finals/.",
            "", "| File | Version | From | Filed |", "|---|---|---|---|"]
    for out, f in sorted(want.items()):
        if not out.endswith(".mp4"):
            continue
        v = VID.match(f)["v"]
        filed = datetime.fromtimestamp(os.path.getmtime(os.path.join(FIN, f))).strftime("%b %-d, %Y %-I:%M %p")
        rows.append(f"| {out} | v{v} | {f} | {filed} |")
    with open(os.path.join(OUT, "VERSIONS.md"), "w") as fh:
        fh.write("\n".join(rows) + "\n")

n = sum(1 for k in want if k.endswith(".mp4"))
print(f"latest/: {n} videos" + (f" · {len(changed)} change(s)" if changed else " · already current") + (" (dry run)" if a.dry else ""))
for c in changed:
    print(f"  {c}")
