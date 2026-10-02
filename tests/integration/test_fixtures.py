"""The two fixture projects, built and inspected for real in a headless browser (slow: vs test --fast skips them).
Without a studio the kit's default look is used and no font is downloaded, so these pin what fonts can't move: the
timing, the moments checked, the names, the source lines, the whole loop running."""
import json, os, shutil, subprocess, sys
import pytest
from conftest import KIT, ENGINE, tone, font_studio  # noqa: F401 (the fixture)

pytestmark = pytest.mark.slow
FIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")


def vs(d, *args):
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), *args], capture_output=True, text=True)
    assert r.returncode == 0, f"vs {' '.join(args)} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
    return r.stdout


def elements(d):
    return {e["id"]: e for e in json.load(open(os.path.join(d, "build/elements.json")))["items"]}


def test_the_beat_reel_builds_inspects_and_names_everything(tmp_path, font_studio):
    d = tmp_path / "beat-reel"
    shutil.copytree(os.path.join(FIX, "beat-reel"), d)
    os.makedirs(d / "music")
    tone(d / "music/take1.mp3", 40, freq=110, db=-12)
    vs(d, "build", "--no-render")
    out = vs(d, "inspect")
    assert "checked 132 moments" in out  # 1.0.1: the audit used to check 0 here and say "no overlaps"
    els = elements(d)
    assert {"s03_hub/ring-layer-1-label", "s03_hub/node-files", "s05_sources/source-paper", "s08_end/wordmark"} <= set(els)
    for f in json.load(open(d / "build/findings.json"))["items"]:
        assert set(f["elements"]) <= set(els), f["id"]
    tl = json.load(open(d / "build/timeline.json"))
    assert tl["end"] == pytest.approx(25.77) and [s["name"] for s in tl["segments"]][:2] == ["s01_open", "s02_turn"]
    # versions are never overwritten: a render onto an existing one stops before it starts (Oct 1, 2026: a re-render
    # without the version bump replaced the v1 a review round was looking at)
    os.makedirs(d / "out", exist_ok=True)
    (d / "out/beat-reel-v1.mp4").write_bytes(b"v1")
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), "build"], capture_output=True, text=True)
    assert r.returncode and "versions are never overwritten" in r.stdout + r.stderr and "--replace" in r.stdout + r.stderr
    os.makedirs(d / "review")
    sys.path.insert(0, os.path.join(ENGINE, "py"))
    import review
    json.dump(review.fold([{"type": "round.opened", "by": "agent", "version": 1, "cut": "9x16",
                            "video": "out/beat-reel-v1-mixed.mp4"}]), open(d / "review/state.json", "w"))
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), "build", "--replace"], capture_output=True, text=True)
    assert r.returncode and "a review round played it" in r.stdout + r.stderr
    assert (d / "out/beat-reel-v1.mp4").read_bytes() == b"v1"


def test_the_tiny_explainer_plans_builds_inspects_and_mixes(tmp_path, font_studio):
    d = tmp_path / "tiny-explainer"
    shutil.copytree(os.path.join(FIX, "tiny-explainer"), d)
    tone(d / "voice/voice-bed-t1.wav", 13.6, freq=180, db=-20)
    vs(d, "plan")
    reel = json.load(open(d / "reel.json"))
    assert reel["schema_version"] == 2 and [a["act"] for a in reel["acts"]] == [1, 2, 3]
    vs(d, "build", "--no-render")
    tl = json.load(open(d / "build/timeline.json"))
    assert [v["el"] for v in tl["voice"]] == ["voice/act-1", "voice/act-2", "voice/act-3"]
    assert "checked" in vs(d, "inspect")
    els = elements(d)
    board = els["s01_plan/the-board"]
    assert board["named"] and board["src"] == "scenes.js:5" and board["on"]
    assert "s01_plan/~ex-k:the-plan" in els and "s01_plan/~ex-chip:pinned-to-a" in els
    assert "s02_words/the-board" in els  # one scene drawing two segments: names are unique per segment
    os.makedirs(d / "out", exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=108x192:d={tl['end']}:r=30",
                    "-c:v", "libx264", "-preset", "ultrafast", str(d / "out/t-v1.mp4")], check=True)
    # a take linked in from somewhere else (a scratch copy of a real project) is replaced, never written through:
    # Oct 1, 2026 a scratch re-mix wrote through such a link into an approved final (identical bytes, by luck)
    elsewhere = tmp_path / "someone-elses-final.mp4"
    elsewhere.write_bytes(b"the approved final")
    os.symlink(elsewhere, d / "out/t-v1-sfx.mp4")
    vs(d, "mix", "--video", "out/t-v1.mp4", "--tag", "v1")
    assert os.path.exists(d / "build/mix/stem-voice.wav") and json.load(open(d / "build/mix/cues.json")) == []
    assert elsewhere.read_bytes() == b"the approved final" and not os.path.islink(d / "out/t-v1-sfx.mp4")
    assert json.load(open(d / "build/mixer/config.json"))["video"] == "out/t-v1.mp4"  # the Mix panel knows its video
    assert json.load(open(d / "out/t-v1.review/cues.json")) == []  # and the version keeps the cues it was mixed with


def test_the_mix_hands_the_review_page_what_plays_live(tmp_path, font_studio):
    """Phase 3: the Mix panel ducks live (the music comes un-ducked, with vs mix's envelope) and plays one effect alone.
    What the page computes must be what vs mix bakes."""
    import numpy as np
    d = tmp_path / "tiny-explainer"
    shutil.copytree(os.path.join(FIX, "tiny-explainer"), d)
    tone(d / "voice/voice-bed-t1.wav", 13.6, freq=180, db=-20)
    os.makedirs(d / "music")
    tone(d / "music/take1.mp3", 16, freq=220, db=-14)
    (d / "cues.py").write_text("def cues(T, TT, C, END_T):\n    return [(1.0, 'tick1', 'on', -12), (2.5, 'tick1', 'on', -6)]\n")
    vs(d, "plan")
    vs(d, "build", "--no-render")
    end = json.load(open(d / "build/timeline.json"))["end"]
    os.makedirs(d / "out", exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=108x192:d={end}:r=30",
                    "-c:v", "libx264", "-preset", "ultrafast", str(d / "out/t-v1.mp4")], check=True)
    vs(d, "mix", "--video", "out/t-v1.mp4", "--tag", "v1")
    media = d / "build/mixer/media"
    cfg = json.load(open(d / "build/mixer/config.json"))
    D = json.load(open(media / "duck.json"))
    assert cfg["duck"] == "duck.json" and D["rate"] == 100 and D["db"] == 6 and len(D["env"]) == pytest.approx(end * 100, abs=2)
    c1, c2 = json.load(open(d / "build/mix/cues.json"))
    assert c1["file"] == c2["file"] == "sfx/1.m4a" and os.path.exists(media / "sfx/1.m4a")  # one sound, one file
    assert c2["gain_db"] - c1["gain_db"] == pytest.approx(6, abs=0.01) and c1["lead"] >= 0
    # the page's ducking (un-ducked music × the envelope, end card and all) is the baked stem
    load = lambda p: np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "2", "-ar", "48000", "-"],
                                                  capture_output=True, check=True).stdout, np.float32).reshape(-1, 2)
    raw, baked = load(d / "build/mix/_raw.wav"), load(d / "build/mix/stem-music1.wav")
    t = np.arange(len(raw)) / 48000
    e = np.interp(t * D["rate"], np.arange(len(D["env"])), D["env"])
    g = 10 ** (-D["db"] * e / 20)
    g = np.where(t >= D["end_t"], np.minimum(1, g + (t - D["end_t"]) / 0.6) * 10 ** (np.clip((t - D["end_t"]) / 0.6, 0, 1) * 5 / 20), g)
    err = raw * g[:, None] - baked
    assert 20 * np.log10(np.sqrt((err ** 2).mean()) / np.sqrt((baked ** 2).mean())) < -50


def test_done_scenes_and_keep_clear_zones_are_enforced(tmp_path, font_studio):
    """Phase 3: the human's standing rules. A scene marked done is held to the version it was approved in (its kept
    composition, snapped against this build's); a keep-clear zone flags what enters it in its scene."""
    d = tmp_path / "beat-reel"
    shutil.copytree(os.path.join(FIX, "beat-reel"), d)
    os.makedirs(d / "music")
    tone(d / "music/take1.mp3", 40, freq=110, db=-12)
    vs(d, "build", "--no-render")
    vs(d, "inspect")
    # what a render keeps (js/lib/archive.mjs): its timeline and its composition
    os.makedirs(d / "out/beat-reel-v1.review")
    shutil.copy(d / "build/timeline.json", d / "out/beat-reel-v1.review/timeline.json")
    shutil.copy(d / "build/comp/index.html", d / "out/beat-reel-v1.review/comp.html")
    sys.path.insert(0, os.path.join(ENGINE, "py"))
    import review
    S = review.fold([{**e, "at": "2026-10-01T19:00:00-04:00"} for e in [
        {"type": "round.opened", "by": "agent", "version": 1, "cut": "9x16", "video": "out/beat-reel-v1.mp4"},
        {"type": "scene.done", "by": "human", "segment": "s02_turn"},
        {"type": "note.added", "by": "human", "note": {"id": "n-0001", "time": {"t": 13.0}, "segment": "s03_hub", "comment": "keep the middle clear",
         "also": [{"type": "keep-clear", "box": [0.39, 0.28, 0.61, 0.42], "keeps": ["s03_hub/core", "s03_hub/core-disc", "s03_hub/~mono:agent"]}]}},
        {"type": "round.sent", "by": "human"}]])
    os.makedirs(d / "review")
    json.dump(S, open(d / "review/state.json", "w"))
    out = vs(d, "inspect")  # nothing changed: the done scene matches; the hub's rings grow out through the middle
    assert "done-changed" not in out and "keep-clear     s03_hub/ring-layer-1-label" in out
    R = json.load(open(d / "reel.json"))
    R["titles"]["t_sources"]["text"] = "Every source<br>on the record."  # another scene: the lock doesn't care
    json.dump(R, open(d / "reel.json", "w"))
    vs(d, "build", "--no-render")
    assert "done-changed" not in vs(d, "inspect")
    R["titles"]["t_turn"]["text"] = "This one<br>forgets<br><span class=a>nothing.</span>"  # the done scene
    json.dump(R, open(d / "reel.json", "w"))
    vs(d, "build", "--no-render")
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), "inspect"], capture_output=True, text=True)
    F = {f["check"]: f for f in json.load(open(d / "build/findings.json"))["items"]}
    assert F["done-changed"]["elements"] == ["title/t_turn"] and F["done-changed"]["severity"] == "error"
    assert "s02_turn changed since v1" in F["done-changed"]["text"] and not os.listdir(d / "build/comp/assets") == []
    assert not [f for f in os.listdir(d / "build/comp") if f.startswith(".done")]  # the old composition's copy is gone
