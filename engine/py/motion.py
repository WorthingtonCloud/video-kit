"""Whooshes on the motion, not before it (vs mix uses this). A "peak" sound (a whoosh, a swish) puts its loudest moment
on its cue, and a cue is pinned to when a move STARTS; a move is fastest a beat later. Measured on an approved
explainer (Oct 6, 2026): the motion peaked 0.1–0.45 s after the cue (median 0.14 s), so every whoosh was heard before
the picture moved, and a reviewer caught it on a phone. Dings and clicks are pinned to landings and were fine.

So, after a render: the picture's motion, frame by frame (the share of pixels that change by more than 12 gray levels,
on a small gray copy), and for each peak cue the frame where its motion peaks, in [cue - 0.1, cue + 0.6] s. The sound
moves there (0 to 0.45 s later, never earlier). A cue whose window shows no clear motion (a peak under 0.3%, or under
twice the median of the second before the cue) stays where it is. After the shift the median motion peak to sound peak
gap on that explainer was 0.02 s.

Measurements are kept in the project's motion-sync.json, per render and cue time, so a re-mix of the same render is
deterministic and costs nothing; a hand-edited shift there is respected."""
import json, os, subprocess
import numpy as np

FILE = "motion-sync.json"
SHORT, LONG = 216, 384  # the small gray copy's sides (a 9:16 render → 216×384, a 16:9 one → 384×216)
LEVEL = 12              # a pixel "changes" when it moves more than this many gray levels between frames
WINDOW = (-0.1, 0.6)    # where to look for the motion's peak, around the cue
MAX_SHIFT = 0.45        # never more than this later; never earlier
FLOOR, OVER = 0.3, 2.0  # a peak counts if it's ≥ 0.3% of the picture AND ≥ 2× the median of the second before the cue


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                          "-of", "json", video], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(n) / float(d)


def curve(video):
    """(fps, m): m[i] = % of the picture that changed between frame i-1 and frame i (m[0] = 0), on a small gray copy."""
    w, h, fps = probe(video)
    W, H = (SHORT, LONG) if h >= w else (LONG, SHORT)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE)
    m, prev, size = [], None, W * H
    while True:  # streamed a frame at a time: a three-minute render never sits in memory
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        f = np.frombuffer(buf, np.uint8).astype(np.int16)
        m.append(0.0 if prev is None else float((np.abs(f - prev) > LEVEL).mean() * 100))
        prev = f
    if p.wait():
        raise RuntimeError(f"ffmpeg could not read {video}")
    return fps, np.array(m)


def shift_for(t, fps, m):
    """→ (seconds later, the motion peak in %) for a cue at t, or (None, peak) when there's no clear motion to land on.
    The change between frames i-1 and i is timed at their midpoint, (i - 0.5) / fps."""
    if not len(m):
        return None, 0.0
    i0, i1 = max(1, int(np.ceil((t + WINDOW[0]) * fps))), min(len(m) - 1, int(np.floor((t + WINDOW[1]) * fps)))
    if i1 < i0:
        return None, 0.0
    k = i0 + int(np.argmax(m[i0:i1 + 1]))
    peak = float(m[k])
    before = m[max(1, int(np.floor((t - 1) * fps))):max(1, int(np.ceil(t * fps)))]
    if peak < max(FLOOR, OVER * (float(np.median(before)) if len(before) else 0)):
        return None, peak
    return round(min(MAX_SHIFT, max(0.0, (k - 0.5) / fps - t)), 3), peak


def sync(video, times, path=FILE, again=False):
    """Every peak cue's shift for this render: {cue time (3 decimals): seconds later}, measured from the picture where
    motion-sync.json doesn't already have it (again=True measures them all afresh). Saves the file; returns
    (shifts, {cue time: note}) where a note is "moved", "on it" or "no clear motion"."""
    saved = json.load(open(path)) if os.path.exists(path) else {}
    key = os.path.basename(video)
    have = {} if again else saved.get(key, {}).get("cues", {})
    want = sorted({f"{t:.3f}" for t in times})
    todo = [t for t in want if t not in have]
    if todo:
        fps, m = curve(video)
        for t in todo:
            s, peak = shift_for(float(t), fps, m)
            have[t] = {"shift": s or 0.0, "peak": round(peak, 2), "why": "no clear motion" if s is None else ("moved" if s > 0 else "on it")}
    saved[key] = {"about": "cue time → seconds later that its whoosh lands (vs mix measures the render's motion; edit a "
                           "shift by hand and it stays)", "cues": {t: have[t] for t in sorted(have, key=float)}}
    json.dump(saved, open(path, "w"), indent=1)
    return {t: have[t]["shift"] for t in want}, {t: have[t]["why"] for t in want}
