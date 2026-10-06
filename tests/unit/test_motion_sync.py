"""Whooshes land on the motion, not before it (motion.py, vs mix). Oct 6, 2026: every "peak" sound sat on the cue where
its move STARTS, the move was fastest 0.1–0.45 s later, and a reviewer heard the whoosh before the picture moved."""
import json, os, shutil, subprocess, sys
import numpy as np
import pytest
from conftest import ENGINE, tone
import motion

FIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")
FPS, W, H = 30, 108, 192


def moving_box(path, secs, moves):
    """A white box on black that slides across the frame once per entry in `moves`, fastest at that time (a smooth
    step 0.5 s long), and sits still otherwise."""
    t = np.arange(int(secs * FPS)) / FPS
    x = sum(1 / (1 + np.exp(-(t - c) / 0.05)) for c in moves) % 2  # 0 → 1 → 0 …: one sweep per move
    frames = np.zeros((len(t), H, W), np.uint8)
    for i, xi in enumerate(x):
        x0 = int(round(min(xi, 2 - xi) * (W - 40)))
        frames[i, 70:120, x0:x0 + 40] = 255
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS),
                    "-i", "-", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(path)],
                   input=frames.tobytes(), check=True)
    return str(path)


def test_a_whoosh_moves_to_where_its_move_is_fastest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    v = moving_box(tmp_path / "v.mp4", 7, [1.3, 4.7, 5.6])
    shifts, why = motion.sync(str(v), [1.0, 3.0, 4.0, 5.7])
    assert shifts["1.000"] == pytest.approx(0.3, abs=1.5 / FPS) and why["1.000"] == "moved"  # fastest 0.3 s after the cue
    assert shifts["3.000"] == 0 and why["3.000"] == "no clear motion"  # nothing moves: the cue stays
    assert shifts["4.000"] == motion.MAX_SHIFT  # fastest 0.7 s later is past the window's edge: capped, never further
    assert shifts["5.700"] == 0 and why["5.700"] == "on it"  # the move already peaked: never earlier
    saved = json.load(open(motion.FILE))["v.mp4"]["cues"]
    assert set(saved) == {"1.000", "3.000", "4.000", "5.700"}


def test_a_kept_measurement_is_reused_and_a_hand_edit_stays(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    v = moving_box(tmp_path / "v.mp4", 3, [1.3])
    motion.sync(str(v), [1.0])
    f = json.load(open(motion.FILE))
    f["v.mp4"]["cues"]["1.000"]["shift"] = 0.12  # the human nudged it
    json.dump(f, open(motion.FILE, "w"))
    assert motion.sync(str(v), [1.0])[0]["1.000"] == 0.12
    assert motion.sync(str(v), [1.0], again=True)[0]["1.000"] == pytest.approx(0.3, abs=1.5 / FPS)  # --resync measures again


def test_vs_mix_plays_the_whoosh_on_the_motion_and_says_so(tmp_path):
    d = tmp_path / "tiny-explainer"
    shutil.copytree(os.path.join(FIX, "tiny-explainer"), d)
    tone(d / "voice/voice-bed-t1.wav", 13.6, freq=180, db=-20)
    (d / "cues.py").write_text("def cues(T, TT, C, END_T):\n"
                               "    return [(2.0, 'whoosh1', 'peak', -14), (2.0, 'tick1', 'on', -16)]\n")
    run = lambda *a: subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), *a],
                                    capture_output=True, text=True)
    assert run("plan").returncode == 0
    os.makedirs(d / "out")
    moving_box(d / "out/t-v1.mp4", 14, [2.25])
    r = run("mix", "--video", "out/t-v1.mp4", "--tag", "v1")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "whooshes on the motion: 1 of 1 moved later" in r.stdout
    whoosh, tick = json.load(open(d / "build/mix/cues.json"))
    assert whoosh["t"] == pytest.approx(2.25, abs=1.5 / FPS) and whoosh["moved"] > 0.2  # played where the box is fastest
    assert tick["t"] == 2.0 and "moved" not in tick  # a click is pinned to its moment and stays there
    assert "t-v1.mp4" in json.load(open(d / motion.FILE))
    r = run("mix", "--video", "out/t-v1.mp4", "--tag", "v1", "--no_sync")
    assert "whooshes on the motion" not in r.stdout and json.load(open(d / "build/mix/cues.json"))[0]["t"] == 2.0
