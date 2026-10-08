#!/usr/bin/env python3
"""The newest final of every video, one folder per video: studio/latest/<video>/ (engine/protocol/files.md).

    vs latest            rebuild latest/ from finals/ (vs finish runs it after filing)
    vs latest --dry      say what it would hold, change nothing

finals/<video>/ keeps every version called done (<video>-vertical-v8.mp4, <video>-widescreen-v8.mp4 + covers).
latest/<video>/ holds only the newest of each shape, named without a version (<video>-vertical.mp4,
<video>-widescreen.mp4) plus its cover, so the current cut is always in the same place under the same name; VERSIONS.md
says which version each one is. Newest = the highest vN; a tie goes to the full file over a "-web" copy, then to the
newer file. latest/ is derived: it is rebuilt from finals/ each time, so never edit or file into it; vs finish files
into finals/ and runs this. Copies are APFS clones where the disk allows (no extra space)."""
import argparse, os, re, shutil, subprocess, sys
from datetime import datetime
import vslib

FINAL = re.compile(r"^(?P<video>.+)-(?P<shape>vertical|widescreen)-v(?P<v>\d+)(?P<web>-web)?\.mp4$")


def plan(S):
    """{latest/ path (relative): finals/ path (relative)}, and every finals/ file it couldn't read (said, never moved)."""
    fin, want, odd = os.path.join(S, "finals"), {}, []
    for video in sorted(os.listdir(fin)) if os.path.isdir(fin) else []:
        d = os.path.join(fin, video)
        if not os.path.isdir(d):
            odd.append(video)
            continue
        best = {}
        for f in sorted(os.listdir(d)):
            m = FINAL.match(f)
            if not m:
                if not f.endswith("-cover.jpg") and not f.startswith("."):
                    odd.append(f"{video}/{f}")
                continue
            if m["video"] != video:
                odd.append(f"{video}/{f} (names another video)")
                continue
            rank = (int(m["v"]), not m["web"], os.path.getmtime(os.path.join(d, f)))
            if m["shape"] not in best or rank > best[m["shape"]][0]:
                best[m["shape"]] = (rank, f)
        for shape, ((v, _, _), f) in best.items():
            want[os.path.join(video, f"{video}-{shape}.mp4")] = os.path.join(video, f)
            cre = re.compile(rf"^{re.escape(video)}-{shape}-v(\d+)-cover\.jpg$")
            covers = sorted((int(cm[1]), c) for c in os.listdir(d) if (cm := cre.match(c)) and int(cm[1]) <= v)
            if covers:  # its own cover, else the newest earlier one
                want[os.path.join(video, f"{video}-{shape}-cover.jpg")] = os.path.join(video, covers[-1][1])
    return want, odd


def same(src, dst):
    return os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst) and \
        int(os.path.getmtime(src)) == int(os.path.getmtime(dst))


def rebuild(S, dry=False, quiet=False):
    FIN, OUT = os.path.join(S, "finals"), os.path.join(S, "latest")
    want, odd = plan(S)
    changed = []
    for out, f in sorted(want.items()):
        src, dst = os.path.join(FIN, f), os.path.join(OUT, out)
        if same(src, dst):
            continue
        changed.append(f"{out} ← finals/{f}")
        if dry:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = dst + ".part"
        if subprocess.run(["cp", "-c", "-p", src, tmp], capture_output=True).returncode != 0:
            shutil.copy2(src, tmp)  # not APFS: a plain copy
        os.replace(tmp, dst)
    # anything else in latest/ is no longer the newest of anything: it goes (latest/ only ever holds copies)
    for root, dirs, files in os.walk(OUT, topdown=False) if os.path.isdir(OUT) else []:
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), OUT)
            if rel not in want and rel != "VERSIONS.md":
                changed.append(f"{rel} removed (no longer the newest of anything)")
                if not dry:
                    os.remove(os.path.join(root, f))
        if root != OUT and not dry and not os.listdir(root):
            os.rmdir(root)
    if not dry:
        os.makedirs(OUT, exist_ok=True)
        rows = ["# Latest versions", "",
                "The newest final of every video, one folder per video. Rebuilt by `vs latest` from `finals/` (every "
                "version lives there): never edit this folder.", "",
                "| Video | Shape | Version | File | Filed |", "|---|---|---|---|---|"]
        for out, f in sorted(want.items()):
            if not out.endswith(".mp4"):
                continue
            m = FINAL.match(os.path.basename(f))
            filed = datetime.fromtimestamp(os.path.getmtime(os.path.join(FIN, f))).strftime("%b %-d, %Y %-I:%M %p")
            rows.append(f"| {m['video']} | {m['shape']} | v{m['v']} | {out} | {filed} |")
        open(os.path.join(OUT, "VERSIONS.md"), "w").write("\n".join(rows) + "\n")
    if not quiet:
        n = sum(1 for k in want if k.endswith(".mp4"))
        print(f"latest/: {n} videos" + (f" · {len(changed)} change(s)" if changed else " · already current") + (" (dry run)" if dry else ""))
        for c in changed:
            print(f"  {c}")
        for o in odd:
            print(f"  ⚠️  finals/{o}: not a final's name (finals/<video>/<video>-<shape>-vN.mp4), left out")
    return changed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    rebuild(vslib.studio_root() or sys.exit("⛔ no studio (vs setup)"), a.dry)
