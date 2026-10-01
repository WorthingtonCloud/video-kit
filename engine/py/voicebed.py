#!/usr/bin/env python3
"""The voice bed: the narration + 6 s of silence under the end card, and the word timings plan.py reads.

    vs voicebed --take voice/narration-v4.mp3 --out v4
        a full take → voice/voice-bed-v4.wav + voice/narration-v4.words.json (a copy of the take's timings)
    vs voicebed --base voice/narration-v4.mp3 --take voice/narration-v5-end.mp3 --out v5
        a re-recorded run of acts (narrate.py <tag> --acts 9-10) spliced onto the approved take: the base is cut 0.2 s after
        the last word of the act before the new run, the new run starts 0.3 s before its first word. A run from the middle
        (--acts 5-5) keeps the base's later acts too: the run is cut 0.2 s after its last word, the base resumes 0.3 s before
        the next act's first word
Then point plan.json → "words" and "voice" at the new files and re-run plan.py: every cue and title re-times itself.

Why: re-recording only the changed acts keeps the performance the human already approved, and costs a fraction of a full
take. The demo's first splice (Sep 30, 2026) cut at "new first word − its lead-in" and clipped the tail of "generously": the cut
has to come AFTER the old act's last word, so this prints the level around the join to check it."""
import argparse, json, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--take", required=True); ap.add_argument("--out", required=True); ap.add_argument("--base")
ap.add_argument("--tail", type=float, default=0.2, help="kept after the base's last word"); ap.add_argument("--lead", type=float, default=0.3, help="kept before the new run's first word")
a = ap.parse_args()
words = lambda mp3: json.load(open(mp3.replace(".mp3", ".words.json")))
bed, wout = f"voice/voice-bed-{a.out}.wav", f"voice/narration-{a.out}.words.json"
fmt = "aresample=48000,aformat=channel_layouts=stereo"

if not a.base:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.take, "-af", f"{fmt},apad=pad_dur=6", "-c:a", "pcm_s16le", bed], check=True)
    json.dump(words(a.take), open(wout, "w"), indent=0)
    print(f"{bed} + {wout}")
    raise SystemExit

WB, WN = words(a.base), words(a.take)
first_act, last_act, X = min(w["act"] for w in WN), max(w["act"] for w in WN), 0.03   # X = each join's crossfade
prev, after = [w for w in WB if w["act"] < first_act], [w for w in WB if w["act"] > last_act]
if not prev: raise SystemExit(f"the base has no acts before act {first_act}")
end_prev, first_new = max(w["t1"] for w in prev), min(w["t0"] for w in WN)
cut, start = round(end_prev + a.tail, 3), round(max(0, first_new - a.lead), 3)
off = round(cut - start - X, 3)
W = prev + [{**w, "t0": round(w["t0"] + off, 3), "t1": round(w["t1"] + off, 3)} for w in WN]
fc = f"[0]atrim=0:{cut},{fmt}[a];[1]atrim=start={start}{{END}},asetpts=PTS-STARTPTS,{fmt}[b];[a][b]acrossfade=d={X}"
if after:   # a middle run: cut it after its last word, then the base picks up again before the next act
    cut2, start2 = round(max(w["t1"] for w in WN) + a.tail, 3), round(min(w["t0"] for w in after) - a.lead, 3)
    off2 = round(off + cut2 - start2 - X, 3)
    W += [{**w, "t0": round(w["t0"] + off2, 3), "t1": round(w["t1"] + off2, 3)} for w in after]
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
