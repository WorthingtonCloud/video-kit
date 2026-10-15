"""vs pack: a video packed for a model that can't watch video. The scar it was built around: review sheets made with the
fps filter showed each frame about 0.5 s after the time printed under it, so a moment picked off a sheet landed half a
second late in the strips. Here every sheet frame is an exact seek, the same call the strips make, and the fixture video
proves it: each second starts dark for a quarter second, then turns bright, so a frame picked late reads bright."""
import json, os, runpy, subprocess, sys, zipfile
import pytest
from conftest import ENGINE, write_tree

PIL = pytest.importorskip("PIL", reason="vs pack draws with Pillow: vs setup adds it to the engine's Python")
from PIL import Image, ImageStat  # noqa: E402


def video(path, secs=6, size="320x180", db=-6):
    """Each second: dark for its first 0.25 s, bright after; a 440 Hz tone peaking at db dBFS under it."""
    vol = 10 ** (db / 20) * 8  # ffmpeg's sine peaks at 1/8
    subprocess.run(["ffmpeg", "-v", "error", "-y",
                    "-f", "lavfi", "-i", f"color=c=gray:s={size}:r=30:d={secs},geq=lum='if(lt(mod(T\\,1)\\,0.25)\\,30\\,220)':cb=128:cr=128",
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}", "-af", f"volume={vol}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(path)], check=True)
    return str(path)


@pytest.fixture
def pack(tmp_path, monkeypatch):
    """Run `vs pack <args>` in a project inside a fresh studio; returns the exit code (None when it ran through)."""
    write_tree(tmp_path, {"s/studio.json": {}, "s/projects/vid/plan.json": {"name": "vid"}})
    monkeypatch.setenv("VIDEO_STUDIO", str(tmp_path / "s"))
    monkeypatch.chdir(tmp_path / "s/projects/vid")

    def go(*args):
        monkeypatch.setattr(sys, "argv", ["pack.py", *map(str, args)])
        try:
            runpy.run_path(os.path.join(ENGINE, "py", "pack.py"), run_name="__main__")
        except SystemExit as e:
            return e.code
    go.project = tmp_path / "s/projects/vid"
    go.studio = tmp_path / "s"
    return go


def cells(sheet, n, cw=300, ch=168, cols=6):
    im = Image.open(sheet).convert("L")
    return [ImageStat.Stat(im.crop((6 + (i % cols) * (cw + 6), 6 + (i // cols) * (ch + 30),
                                    6 + (i % cols) * (cw + 6) + cw, 6 + (i // cols) * (ch + 30) + ch))).mean[0] for i in range(n)]


def test_sheet_frames_are_the_strips_frames(pack, tmp_path):
    v = video(tmp_path / "clip.mp4")
    assert pack("survey", v) is None
    info = json.load(open(pack.project / "pack/survey.json"))
    assert info["frames"] == 6 and info["sheets"] == 1
    # every labeled second is the dark quarter: the frame AT the label, not ~0.5 s after it (the fps filter's bright frame)
    assert all(m < 100 for m in cells(pack.project / "pack/survey/sheet-01.jpg", 6))


def test_soundtrack_and_loudness_are_what_the_build_reads(pack, tmp_path):
    v = video(tmp_path / "clip.mp4", db=-6)
    pack("survey", v)
    a = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,bit_rate", "-of", "json",
                                   str(pack.project / "pack/audio.mp3")], capture_output=True, text=True).stdout)["streams"][0]
    assert a["codec_name"] == "mp3" and int(a["bit_rate"]) == 192000
    ld = json.load(open(pack.project / "pack/loudness.json"))
    assert ld["step"] == 0.1 and 59 <= len(ld["db"]) <= 61
    mid = sorted(ld["db"][10:50])[20]
    assert abs(mid - (-6 - 3.01)) < 1.0  # a sine's RMS sits 3 dB under its peak


def test_a_kit_render_starts_the_plan_and_its_words_are_free(pack, tmp_path):
    final = pack.studio / "finals/vid/vid-vertical-v1.mp4"
    final.parent.mkdir(parents=True)
    video(final)
    write_tree(pack.project, {
        "drafts/v1/data/vertical/timeline.json": {"segments": [{"name": "s01_hook", "t0": 0, "t1": 3.2}, {"name": "s02_end", "t0": 3.2, "t1": 6}]},
        "drafts/v1/data/vertical/cues.json": [{"el": "sfx/pop@s02_end", "t": 3.25, "sound": "pop"}],
        "voice/narration-v1.words.json": [{"w": "One", "t0": 0.2, "t1": 0.5, "act": 1}, {"w": "line.", "t0": 0.5, "t1": 0.9, "act": 1},
                                          {"w": "Another", "t0": 1.0, "t1": 1.4, "act": 1}, {"w": "here", "t0": 1.4, "t1": 1.8, "act": 1},
                                          {"w": "Act", "t0": 3.3, "t1": 3.6, "act": 2}, {"w": "two", "t0": 3.6, "t1": 4.0, "act": 2}],
        "plan.json": {"name": "vid", "words": "voice/narration-v1.words.json"}})
    assert pack("survey") is None  # no VIDEO: this video's newest final
    plan = json.load(open(pack.project / "pack/plan.json"))
    assert plan["video"] == str(final)
    assert plan["sound"]["sections"] == [{"name": "hook", "t0": 0, "t1": 3.2}, {"name": "end", "t0": 3.2, "t1": 6}]
    assert plan["sound"]["sfx"] == [{"t": 3.25, "name": "pop", "what": "at end"}]
    assert pack("words") is None  # the kit's own timings: no key, no spend
    segs = json.load(open(pack.project / "pack/transcript.json"))["segments"]
    assert [s["text"] for s in segs] == ["One line.", "Another here", "Act two"]
    assert segs[2]["start"] == 3.3 and not (pack.studio / "ledger.csv").exists()


def test_a_timing_file_with_an_offset(pack, tmp_path):
    write_tree(pack.project, {"t.json": {"lines": [{"t0": 0.0, "t1": 1.5, "text": " Build it ", "words": [{"w": "Build", "t0": 0.0, "t1": 0.5}]}]}})
    os.makedirs(pack.project / "pack")
    assert pack("words", "--timing", "t.json", "--offset", "2") is None
    T = json.load(open(pack.project / "pack/transcript.json"))
    assert T["segments"] == [{"start": 2.0, "end": 3.5, "text": "Build it"}] and T["words"] == [{"w": "Build", "t": 2.0}]


def test_whisper_waits_for_the_gate(pack, tmp_path):
    pack("survey", video(tmp_path / "clip.mp4"))
    code = pack("words")  # no timing file, no kit words: whisper, and VIDEO_KIT_NO_SPEND is set
    assert "VIDEO_KIT_NO_SPEND" in str(code)
    assert not (pack.project / "pack/transcript.json").exists() and not (pack.studio / "ledger.csv").exists()


def test_build_zips_only_once_the_prompt_is_written(pack, tmp_path):
    v = video(tmp_path / "clip.mp4")
    pack("survey", v)
    plan = json.load(open(pack.project / "pack/plan.json"))
    plan["strips"] = [{"slug": "open", "title": "Open → close", "cols": 3, "t": [0.0, 2.0, 9.0], "labels": {"2.0": "dark"}}]
    plan["sound"] = {"sections": [{"name": "all", "t0": 0, "t1": 6}], "music": [], "sfx": [{"t": 2, "name": "tick", "what": "x"}]}
    json.dump(plan, open(pack.project / "pack/plan.json", "w"))
    assert "PROMPT.md" in str(pack("build"))
    out = pack.project / "pack/clip-for-review"  # not a kit render: named after its file
    assert sorted(os.listdir(out)) == ["00-sound-map.png", "01-open.jpg", "soundtrack.mp3"]  # 9.0 s is past the end: left out
    assert Image.open(out / "01-open.jpg").width == 3 * 640 + 2 * 14 + 2 * 22
    (out / "PROMPT.md").write_text("# test\n")
    assert pack("build") is None
    z = zipfile.ZipFile(str(out) + ".zip")
    assert sorted(os.path.basename(n) for n in z.namelist() if not n.endswith("/")) == \
        ["00-sound-map.png", "01-open.jpg", "PROMPT.md", "soundtrack.mp3"]


def test_the_profile_says_where_packs_go(pack, tmp_path):
    write_tree(pack.studio, {"profile.json": {"pack": {"out": str(tmp_path / "Downloads")}}})
    pack("survey", video(tmp_path / "clip.mp4"))
    (tmp_path / "Downloads").mkdir()
    pack("build")
    assert (tmp_path / "Downloads/clip-for-review/soundtrack.mp3").exists()
