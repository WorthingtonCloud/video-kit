#!/usr/bin/env python3
"""Fit a take to a length: shorten the long pauses, then speed the read up (pitch kept), and move every word timing with it.

    vs fit --take voice/narration-v1.mp3 --secs 174 --out v1fit [--pause 0.25 | --pause none]
        → voice/narration-v1fit.mp3 + voice/narration-v1fit.words.json, ready for vs voicebed --take
    vs fit … --rush "5:Teams..Jira" --rush "13:Recessions..transformation#3" [--rush-speed 1.3]
        the lists go faster than the rest: each span (an act, its first word, its last word, #n = that word's nth
        time after the first) is sped up --rush-speed times more than everything else

--pause: every silence longer than this keeps only this much (its middle goes; the edges stay, so no word is clipped);
"none" leaves every pause alone, so the comic timing scales with the speed. Then the rest is sped up uniformly to --secs
(ffmpeg atempo; never slowed down). It prints the words a minute before and after: past ~240 a listener starts to work.

Why: a script that's longer than its slot. Re-recording "faster" is paid and a v4 voice doesn't take a speed setting; a
712-word script had to fit 3:00 (Oct 2, 2026)."""
import argparse, json, subprocess, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--take", required=True); ap.add_argument("--secs", type=float, required=True); ap.add_argument("--out", required=True)
ap.add_argument("--pause", default="0.25", help="longest pause kept, in seconds, or none")
ap.add_argument("--floor", type=float, default=-40, help="below this (dBFS, 10 ms windows) is a pause")
ap.add_argument("--rush", action="append", default=[], help='a span read faster: "act:first..last[#n]"')
ap.add_argument("--rush-speed", type=float, default=1.3)
a = ap.parse_args()
SR = 44100
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.take, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(pcm, dtype=np.float32)
words = json.load(open(a.take.replace(".mp3", ".words.json")))
n0 = len(x) / SR

# the cuts: (start, end) in seconds of the take, the middle of every pause longer than --pause
cuts = []
if a.pause != "none":
    cap, W = float(a.pause), int(SR * 0.01)
    rms = np.sqrt(np.mean(x[: len(x) // W * W].reshape(-1, W) ** 2, axis=1) + 1e-12)
    quiet = 20 * np.log10(rms) < a.floor
    i = 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            s, e = i * 0.01, j * 0.01
            if 0 < s and e < n0 - 0.05 and e - s > cap:  # never the head or the tail of the take
                cuts.append((s + cap / 2, e - cap / 2))
            i = j
        else:
            i += 1
keep = np.ones(len(x), bool)
for s, e in cuts:
    keep[int(s * SR): int(e * SR)] = False
y = x[keep]
n1 = len(y) / SR


def cut_t(t):
    """A time in the take → the same moment once the pauses are cut."""
    gone = 0.0
    for s, e in cuts:
        if t >= e:
            gone += e - s
        elif t > s:
            gone += t - s
    return t - gone


norm = lambda w: "".join(c for c in w.lower() if c.isalnum())


def span(spec):
    """'5:Teams..Jira' → (from, to) in the cut file: from the gap before its first word to the gap after its last."""
    act, rest = spec.split(":", 1) if ":" in spec.split("..")[0] else (None, spec)
    first, last = rest.split("..")
    last, nth = (last.split("#") + ["1"])[:2]
    idx = [i for i, w in enumerate(words) if act is None or str(w.get("act")) == act]
    i0 = next((i for i in idx if norm(words[i]["w"]) == norm(first)), None)
    hits = [i for i in idx if i0 is not None and i >= i0 and norm(words[i]["w"]) == norm(last)]
    if i0 is None or len(hits) < int(nth):
        sys.exit(f"⛔ --rush {spec}: no such words" + (f" in act {act}" if act else ""))
    i1 = hits[int(nth) - 1]
    gap = lambda i, j: (words[i]["t1"] + words[j]["t0"]) / 2
    a0 = gap(i0 - 1, i0) if i0 > 0 else words[i0]["t0"]
    a1 = gap(i1, i1 + 1) if i1 + 1 < len(words) else words[i1]["t1"]
    return cut_t(a0), cut_t(a1)


# the cut file in pieces: (from, to, how much faster than the rest)
rushes = sorted(span(r) for r in a.rush)
pieces, t = [], 0.0
for s, e in rushes:
    if s > t:
        pieces.append((t, s, 1.0))
    pieces.append((max(s, t), e, a.rush_speed))
    t = e
pieces.append((t, n1, 1.0))
pieces = [p for p in pieces if p[1] - p[0] > 0.01]
factor = max(1.0, sum((e - s) / k for s, e, k in pieces) / a.secs)


def move(t):
    """A time in the take → the same moment in the fitted file: the pauses cut before it, then each piece's speed."""
    t, at = cut_t(t), 0.0
    for s, e, k in pieces:
        if t <= e:
            return (at + (max(t, s) - s) / k) / factor
        at += (e - s) / k
    return at / factor


def tempo(seg, k):
    return np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", f"atempo={k:.5f}",
                                         "-f", "f32le", "-"], input=seg.tobytes(), capture_output=True, check=True).stdout, np.float32)


z = np.concatenate([tempo(y[int(s * SR): int(e * SR)], k * factor) for s, e, k in pieces])
out = f"voice/narration-{a.out}.mp3"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                "-c:a", "libmp3lame", "-b:a", "192k", out], input=z.tobytes(), check=True)
json.dump([{**w, "t0": round(move(w["t0"]), 3), "t1": round(move(w["t1"]), 3)} for w in words],
          open(out.replace(".mp3", ".words.json"), "w"), indent=0)
got = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out], capture_output=True, text=True).stdout)
wpm = lambda secs: round(len(words) / secs * 60)
print(f"{a.take}: {n0:.1f} s, {wpm(n0)} words a minute")
print(f"  pauses: {len(cuts)} shortened to {a.pause} s, {n0 - n1:.1f} s saved" if cuts else "  pauses: left alone")
print(f"  speed: ×{factor:.3f}" + (f", the {len(rushes)} rushed span(s) ×{factor * a.rush_speed:.3f}" if rushes else "")
      + ("  ⚠️ past ×1.5 the voice starts to smear" if factor * (a.rush_speed if rushes else 1) > 1.5 else ""))
print(f"→ {out}: {got:.1f} s, {wpm(got)} words a minute (+ its .words.json)")
if got > a.secs + 0.5:
    sys.exit(f"⛔ {got:.1f} s is still over {a.secs:g} s")
