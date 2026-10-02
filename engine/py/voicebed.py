#!/usr/bin/env python3
"""The voice bed: the narration + 6 s of silence under the end card, and the word timings plan.py reads.

    vs voicebed --take voice/narration-v4.mp3 --out v4
        a full take → voice/voice-bed-v4.wav + voice/narration-v4.words.json (a copy of the take's timings)
    vs voicebed --base voice/narration-v4.mp3 --take voice/narration-v5-end.mp3 --out v5
        a re-recorded run of acts (narrate.py <tag> --acts 9-10) spliced onto the approved take: the base is cut in the
        quietest stretch between the act before the new run and the base's own take of it (measured in the audio: word
        timings run up to 0.2 s late), the new run starts 0.3 s before its first word. A run from the middle (--acts 5)
        keeps the base's later acts too: the run is cut 0.2 s after its last word, the base resumes in the quietest stretch
        before the next act
Then point plan.json → "words" and "voice" at the new files and re-run plan.py: every cue and title re-times itself.

Why: re-recording only the changed acts keeps the performance the human already approved, and costs a fraction of a full
take. The demo's first splice (Sep 30, 2026) cut at "new first word − its lead-in" and clipped the tail of "generously": the cut
has to come AFTER the old act's last word, so this prints the level around the join to check it."""
import argparse, json, os, subprocess, sys
from vslib import quietest, splice_plan

ap = argparse.ArgumentParser()
ap.add_argument("--take", required=True); ap.add_argument("--out", required=True); ap.add_argument("--base")
ap.add_argument("--tail", type=float, default=0.2, help="kept after the base's last word"); ap.add_argument("--lead", type=float, default=0.3, help="kept before the new run's first word")
a = ap.parse_args()
words = lambda mp3: json.load(open(mp3.replace(".mp3", ".words.json")))
bed, wout = f"voice/voice-bed-{a.out}.wav", f"voice/narration-{a.out}.words.json"
# a splice must not write over the timings it reads: "narrate v2 --acts 5" then "--out v2" would replace the run's own
# words with the spliced ones, and the run's timings would be gone (jev-explainer, Oct 1, 2026)
if a.base and os.path.abspath(wout) in {os.path.abspath(f.replace(".mp3", ".words.json")) for f in (a.take, a.base)}:
    sys.exit(f"⛔ --out {a.out} would write over {wout}, which this splice reads. Pick another --out (or rename the run: "
             f"narration-<tag>a5.mp3 + its .words.json).")
fmt = "aresample=48000,aformat=channel_layouts=stereo"

if not a.base:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.take, "-af", f"{fmt},apad=pad_dur=6", "-c:a", "pcm_s16le", bed], check=True)
    json.dump(words(a.take), open(wout, "w"), indent=0)
    print(f"{bed} + {wout}")
    raise SystemExit

WB, WN = words(a.base), words(a.take)
X = 0.03  # each join's crossfade
# the two base points come from the audio: the quietest stretch between the act before the run and the base's own take
# of the replaced act (word timings can run 0.2 s late: a cut 0.2 s after the last word kept "Pic-" of the old "Picture")
fa, la = min(w["act"] for w in WN), max(w["act"] for w in WN)
prev = [w for w in WB if w["act"] < fa]; rep = [w for w in WB if fa <= w["act"] <= la]; nxt = [w for w in WB if w["act"] > la]
cut_at = start2_at = None
try:
    if prev:
        ep = max(w["t1"] for w in prev)
        cut_at = quietest(a.base, ep - 0.3, min(w["t0"] for w in rep) + 0.05 if rep else ep + a.tail, prefer="last")
    if rep and nxt:
        start2_at = quietest(a.base, max(w["t1"] for w in rep) - 0.3, min(w["t0"] for w in nxt) + 0.05, prefer="first")
except Exception as e:  # no numpy here: the timing-based points, as before
    print(f"(the pause wasn't measured: {e}; cutting by the word timings)")
try: sp = splice_plan(WB, WN, a.tail, a.lead, X, cut_at, start2_at)
except ValueError as e: raise SystemExit(str(e))
W, cut, start, off, first_act, end_prev, first_new = (sp[k] for k in ("words", "cut", "start", "off", "first_act", "end_prev", "first_new"))
after = "cut2" in sp
fc = f"[0]atrim=0:{cut},{fmt}[a];[1]atrim=start={start}{{END}},asetpts=PTS-STARTPTS,{fmt}[b];[a][b]acrossfade=d={X}"
if after:   # a middle run: cut it after its last word, then the base picks up again before the next act
    cut2, start2 = sp["cut2"], sp["start2"]
    fc = fc.replace("{END}", f":end={cut2}") + f"[ab];[0]atrim=start={start2},asetpts=PTS-STARTPTS,{fmt}[c];[ab][c]acrossfade=d={X}"
fc = fc.replace("{END}", "") + ",apad=pad_dur=6[o]"
json.dump(W, open(wout, "w"), indent=0)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.base, "-i", a.take, "-filter_complex", fc, "-map", "[o]", "-c:a", "pcm_s16le", bed], check=True)
print(f"act {first_act - 1} ends {end_prev:.2f}s · cut {cut:.2f}s · act {first_act} now starts {first_new + off:.2f}s · last word {W[-1]['t1']:.2f}s")
joins = [end_prev] + ([max(w["t1"] for w in WN) + off] if after else [])
# the join, in 50 ms steps: the old word must fade out (to about -60 dB) BEFORE the cut, never be chopped mid-word
for j in joins:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", bed, "-ss", str(max(0, j - 0.5)), "-t", "1.4", "-ac", "1", "-f", "f32le", "-"], capture_output=True).stdout
    try:
        import numpy as np
        x = np.frombuffer(raw, np.float32); n = 2400
        print(f"level per 50 ms from 0.5 s before the join at {j:.2f}s:", [round(float(20 * np.log10(np.sqrt(np.mean(x[i:i + n] ** 2)) + 1e-9))) for i in range(0, len(x) - n, n)])
    except ImportError:
        print("(run with a Python that has numpy to see the level around the join)"); break
print(f"{bed} + {wout}")
