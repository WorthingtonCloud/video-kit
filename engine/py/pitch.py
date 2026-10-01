#!/usr/bin/env python3
"""Rough 'is it monotone?' check: speaking rate + pitch range in semitones (autocorrelation F0, numpy only)."""
import json, subprocess, sys, numpy as np
def f0_track(path, sr=16000):
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
    n, hop, out = int(0.04 * sr), int(0.01 * sr), []
    lo, hi = sr // 350, sr // 70
    rms_all = np.sqrt(np.mean(x ** 2))
    for i in range(0, len(x) - n, hop):
        f = x[i:i + n] - x[i:i + n].mean()
        if np.sqrt(np.mean(f ** 2)) < 0.5 * rms_all: continue
        ac = np.correlate(f, f, "full")[n - 1:]
        if ac[0] <= 0: continue
        k = lo + np.argmax(ac[lo:hi]); 
        if ac[k] / ac[0] > 0.5: out.append(sr / k)
    return np.array(out)
for p in sys.argv[1:]:
    f0 = f0_track(p); st = 12 * np.log2(f0 / np.median(f0))
    words = json.load(open(p.replace(".mp3", ".words.json")))
    dur = words[-1]["t1"] - words[0]["t0"]
    print(f"{p.split('narration-')[-1]:34s} {len(words)/dur*60:5.0f} wpm   pitch spread {np.percentile(st,90)-np.percentile(st,10):4.1f} semitones   median {np.median(f0):4.0f} Hz")
