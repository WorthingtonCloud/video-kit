#!/usr/bin/env python3
"""The newest final of every video, one folder per video: studio/latest/<video>/ (engine/protocol/files.md).

    vs latest            rebuild latest/ from finals/ (vs finish runs it after filing)
    vs latest --dry      say what it would hold, change nothing
    vs latest --make-web also make the web copy of any newest final that has none (finals filed before web copies)

finals/<video>/ keeps every version called done (<video>-vertical-v8.mp4, <video>-widescreen-v8.mp4 + covers).
latest/<video>/ holds only the newest of each shape, named without a version (<video>-vertical.mp4,
<video>-widescreen.mp4) plus its cover, so the current cut is always in the same place under the same name; VERSIONS.md
says which version each one is. Newest = the highest vN (a tie goes to the newer file).

Every final also gets a web copy: the same picture, size and frame rate, re-encoded small enough to upload where sites
cap a file's size (<video>-<shape>-vN-web.mp4 in finals/, <video>-<shape>-web.mp4 in latest/). The full file stays the
one to edit from. A web copy is made only when a video is called done: vs finish makes one for each final it files,
beside it in finals/, and this rebuild then replaces latest/'s copy, so latest/ only ever holds the web copy of the
newest final. A web copy is never bigger than its full file: if the re-encode doesn't save at least a tenth, it's the
full file's own streams, moved so playback starts before the download ends.

latest/ is derived: it is rebuilt from finals/ each time, so never edit or file into it; vs finish files into finals/
and runs this. Copies are APFS clones where the disk allows (no extra space)."""
import argparse, os, re, shutil, subprocess, sys, time
from datetime import datetime
import vslib

FINAL = re.compile(r"^(?P<video>.+)-(?P<shape>vertical|widescreen)-v(?P<v>\d+)(?P<web>-web)?\.mp4$")
# The web copy: H.264 (plays everywhere), constant quality. CRF 24 scored VMAF 95.5 (a 0-100 "looks the same as the
# original" score) on a 4-minute narrated video with footage, at about a third of the size; AAC 128k for the sound.
WEB_VIDEO = ["-c:v", "libx264", "-preset", "slow", "-crf", "24", "-pix_fmt", "yuv420p", "-profile:v", "high"]
WEB_AUDIO = ["-c:a", "aac", "-b:a", "128k"]
WEB_MIN_SAVING = 0.10


def web_of(final):
    """finals/<video>/<video>-<shape>-vN.mp4 → its web copy beside it."""
    return final[:-len(".mp4")] + "-web.mp4"


def make_web(src, dst):
    """Encode src's web copy into dst (atomic: a stopped run leaves only a .part, redone next time)."""
    tmp = dst[:-len(".mp4")] + ".part.mp4"
    enc = ["ffmpeg", "-v", "error", "-y", "-i", src, *WEB_VIDEO, *WEB_AUDIO, "-movflags", "+faststart", tmp]
    if subprocess.run(enc).returncode != 0:
        raise SystemExit(f"⛔ couldn't make the web copy of {src}")
    if os.path.getsize(tmp) > os.path.getsize(src) * (1 - WEB_MIN_SAVING):  # already small: keep its own streams
        if subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c", "copy", "-movflags", "+faststart",
                           tmp]).returncode != 0:
            raise SystemExit(f"⛔ couldn't make the web copy of {src}")
    os.replace(tmp, dst)


def make_webs(S, finals, quiet=False):
    """Make the web copy of each final (paths relative to finals/) that has none yet. vs finish calls this."""
    FIN = os.path.join(S, "finals")
    todo = [f for f in finals if not os.path.exists(os.path.join(FIN, web_of(f)))]
    for i, f in enumerate(todo):
        t = time.time()
        if not quiet:
            print(f"  web copy {i + 1}/{len(todo)}: finals/{web_of(f)} …", flush=True)
        make_web(os.path.join(FIN, f), os.path.join(FIN, web_of(f)))
        if not quiet:
            mb = lambda p: os.path.getsize(os.path.join(FIN, p)) / 1e6
            print(f"    {mb(f):.0f} MB → {mb(web_of(f)):.0f} MB in {time.time() - t:.0f} s", flush=True)


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
            if m["web"]:
                continue  # a web copy follows its full file (below), never competes with it
            rank = (int(m["v"]), os.path.getmtime(os.path.join(d, f)))
            if m["shape"] not in best or rank > best[m["shape"]][0]:
                best[m["shape"]] = (rank, f)
        for shape, ((v, _), f) in best.items():
            want[os.path.join(video, f"{video}-{shape}.mp4")] = os.path.join(video, f)
            want[os.path.join(video, f"{video}-{shape}-web.mp4")] = web_of(os.path.join(video, f))
            cre = re.compile(rf"^{re.escape(video)}-{shape}-v(\d+)-cover\.jpg$")
            covers = sorted((int(cm[1]), c) for c in os.listdir(d) if (cm := cre.match(c)) and int(cm[1]) <= v)
            if covers:  # its own cover, else the newest earlier one
                want[os.path.join(video, f"{video}-{shape}-cover.jpg")] = os.path.join(video, covers[-1][1])
    return want, odd


def same(src, dst):
    return os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst) and \
        int(os.path.getmtime(src)) == int(os.path.getmtime(dst))


def rebuild(S, dry=False, quiet=False, web=False):
    FIN, OUT = os.path.join(S, "finals"), os.path.join(S, "latest")
    want, odd = plan(S)
    changed = []
    missing = [f for o, f in sorted(want.items()) if o.endswith("-web.mp4") and not os.path.exists(os.path.join(FIN, f))]
    if web and missing and not dry:
        make_webs(S, [f[:-len("-web.mp4")] + ".mp4" for f in missing], quiet)
        missing = []
    for out, f in sorted(want.items()):
        src, dst = os.path.join(FIN, f), os.path.join(OUT, out)
        if not os.path.exists(src):  # a final filed before web copies: vs latest --make-web
            want.pop(out)
            continue
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
                "Each video also has a `-web` copy: the same picture, small enough to upload. Edit from the full file.", "",
                "| Video | Shape | Version | File | Full | Web | Filed |", "|---|---|---|---|---|---|---|"]
        mb = lambda p: f"{os.path.getsize(p) / 1e6:.0f} MB" if os.path.exists(p) else "not made yet"
        for out, f in sorted(want.items()):
            if not out.endswith(".mp4") or out.endswith("-web.mp4"):
                continue
            m = FINAL.match(os.path.basename(f))
            src = os.path.join(FIN, f)
            filed = datetime.fromtimestamp(os.path.getmtime(src)).strftime("%b %-d, %Y %-I:%M %p")
            rows.append(f"| {m['video']} | {m['shape']} | v{m['v']} | {out} | {mb(src)} | {mb(web_of(src))} | {filed} |")
        open(os.path.join(OUT, "VERSIONS.md"), "w").write("\n".join(rows) + "\n")
    if not quiet:
        n = sum(1 for k in want if k.endswith(".mp4") and not k.endswith("-web.mp4"))
        print(f"latest/: {n} videos" + (f" · {len(changed)} change(s)" if changed else " · already current") + (" (dry run)" if dry else ""))
        for c in changed:
            print(f"  {c}")
        if missing:
            print(f"  {len(missing)} final(s) have no web copy (filed before web copies): vs latest --make-web makes them")
        for o in odd:
            print(f"  ⚠️  finals/{o}: not a final's name (finals/<video>/<video>-<shape>-vN.mp4), left out")
    return changed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--make-web", action="store_true")
    a = ap.parse_args()
    rebuild(vslib.studio_root() or sys.exit("⛔ no studio (vs setup)"), a.dry, web=a.make_web)
