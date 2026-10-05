"""qa.py's warnings reach the review page: out/<name>-vN.review/qa.json, by element name where the map knows them."""
import json, os, subprocess
from conftest import vs


def test_a_word_under_the_status_bar_becomes_a_named_warning(tmp_path):
    d = tmp_path / "p"
    os.makedirs(d / "out")
    os.makedirs(d / "build")
    (d / "reel.json").write_text("{}")
    # 3 s of dark ground with a white bar at the very top from 1 to 2 s, plus a quiet tone so there's sound
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x101010:s=1080x1920:d=3:r=30",
                    "-f", "lavfi", "-i", "sine=frequency=220:duration=3", "-vf",
                    "drawbox=x=300:y=40:w=480:h=60:color=white:t=fill:enable='between(t,1,2)'", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-shortest", str(d / "out/p-v1.mp4")], check=True)
    json.dump({"fingerprint": "fp", "segments": [{"name": "s01", "t0": 0, "t1": 3, "kind": "scene"}]},
              open(d / "out/p-v1.timeline.json", "w"))
    json.dump({"fingerprint": "fp", "items": [{"id": "s01/kicker", "kind": "text", "on": [[0.9, 2.1]],
                                               "boxes": [[0.9, 0.28, 0.02, 0.72, 0.05]]}]}, open(d / "build/elements.json", "w"))
    r = vs(d, "qa", "out/p-v1.mp4")
    assert r.returncode == 0, r.stderr
    Q = json.load(open(d / "out/p-v1.review/qa.json"))
    top = [f for f in Q["items"] if f["check"] == "covered" and f["id"].startswith("q-covered-top")]
    assert len(top) == 1 and top[0]["elements"] == ["s01/kicker"] and top[0]["severity"] == "warning"
    assert 0.9 <= top[0]["t0"] <= 1.1 and 1.9 <= top[0]["t1"] <= 2.3 and top[0]["box_n"][3] > 0


def test_the_final_mix_flash_and_sound_density_checks(tmp_path):
    """Phase 3: qa.py's own new checks, on a final mix built to trip each one: the frame goes black to white in one frame
    (flash), the mix is far too quiet but one click hits full scale (loudness, true peak), and sixteen effects land within
    two seconds (cue density). Each is a warning; the thresholds come from contracts.json → checks."""
    d = tmp_path / "p"
    os.makedirs(d / "out/q-v1.review")
    (d / "reel.json").write_text("{}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=108x192:d=1:r=30",
                    "-f", "lavfi", "-i", "color=c=white:s=108x192:d=1:r=30",
                    "-f", "lavfi", "-i", "aevalsrc=0.003*sin(2*PI*440*t)+if(between(t\\,1\\,1.003)\\,0.99\\,0):s=48000:d=2",
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(d / "out/q-v1-mixed.mp4")], check=True)
    json.dump({"fingerprint": "fp", "segments": [{"name": "s01", "t0": 0, "t1": 2, "kind": "scene"}]},
              open(d / "out/q-v1.timeline.json", "w"))
    json.dump([{"el": f"sfx/tick1@s01#{k}", "t": 0.1 * k, "sound": "tick1", "db": -12} for k in range(1, 17)],
              open(d / "out/q-v1.review/cues.json", "w"))
    r = vs(d, "qa", "out/q-v1-mixed.mp4")
    assert r.returncode == 0, r.stderr
    Q = {f["check"]: f for f in json.load(open(d / "out/q-v1.review/qa.json"))["items"]}
    assert {"flash", "loudness", "true-peak", "cue-density"} <= set(Q), list(Q)
    assert 0.9 <= Q["flash"]["t1"] <= 1.1 and "brightens" in Q["flash"]["text"]
    assert "16 sound effects" in Q["cue-density"]["text"] and Q["cue-density"]["elements"][0].startswith("sfx/tick1@")
    assert all(f["severity"] == "warning" for f in Q.values())
    # a bare render's sound is a placeholder: its loudness isn't judged
    os.replace(d / "out/q-v1-mixed.mp4", d / "out/q-v1.mp4")
    vs(d, "qa", "out/q-v1.mp4")
    assert "loudness" not in {f["check"] for f in json.load(open(d / "out/q-v1.review/qa.json"))["items"]}


def test_shimmer_is_flicker_in_place_not_motion(tmp_path):
    """Oct 4, 2026 (an explainer, "the icons flicker"): thin lines that jump two pixels and back on
    alternate frames are shimmer; lines sliding across the frame change every pixel too, but they're motion. Only the
    flicker becomes a warning, boxed where it is."""
    import numpy as np
    d = tmp_path / "p"
    os.makedirs(d / "out")
    (d / "reel.json").write_text("{}")
    W, H = 216, 384
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", "30",
                            "-i", "-", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", "-c:v", "libx264", "-qp", "0",
                            "-pix_fmt", "yuv444p", "-shortest", str(d / "out/s-v1.mp4")], stdin=subprocess.PIPE)
    for k in range(60):
        f = np.full((H, W), 16, np.uint8)
        for x in range(8, W - 8, 10):  # top: lines flickering two pixels out and back
            f[40:140, x + 2 * (k % 2):x + 2 * (k % 2) + 2] = 230
        for x in range(0, W, 70):  # bottom: lines sliding right, nine pixels a frame
            x = (x + 9 * k) % W
            f[240:340, x:x + 2] = 230
        enc.stdin.write(f.tobytes())
    enc.stdin.close()
    assert enc.wait() == 0
    json.dump({"fingerprint": "fp", "segments": [{"name": "s01", "t0": 0, "t1": 2, "kind": "scene"}]},
              open(d / "out/s-v1.timeline.json", "w"))
    r = vs(d, "qa", "out/s-v1.mp4")
    assert r.returncode == 0, r.stderr
    sh = [f for f in json.load(open(d / "out/s-v1.review/qa.json"))["items"] if f["check"] == "shimmer"]
    assert len(sh) == 1 and sh[0]["severity"] == "warning" and sh[0]["t0"] == 0, sh
    x0, y0, x1, y1 = sh[0]["box_n"]
    assert y0 >= 0.1 and y1 <= 0.38, sh[0]["box_n"]  # the flickering band (40–140 of 384), not the sliding one
