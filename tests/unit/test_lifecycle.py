"""A video's path from first draft to final and back (engine/protocol/files.md; vs status / shape / finish / reopen): the
order is held by the commands, never by anyone remembering it (a reviewer, Oct 8, 2026: the widescreen and the
vertical were reviewed on two ports, and the widescreen was filed under the vertical's name)."""
import json, os, subprocess, sys
import pytest
from conftest import ENGINE, vs, write_tree

sys.path.insert(0, os.path.join(ENGINE, "py"))
import review  # noqa: E402

H, A = "human", "agent"


def video(path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x202020:s={size}:d=1:r=30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


def render(d, shape, v):
    """What vs build leaves behind, without the minutes: the render, its cover, its data folder and its sources."""
    f = d / f"drafts/v{v}/demo-{shape}-v{v}.mp4"
    video(f, "108x192" if shape == "vertical" else "192x108")
    (d / f"drafts/v{v}/demo-{shape}-v{v}-cover.jpg").write_bytes(b"jpg")
    data = d / f"drafts/v{v}/data/{shape}"
    (data / "source").mkdir(parents=True, exist_ok=True)
    (data / "timeline.json").write_text(json.dumps({"fingerprint": f"fp-{shape}-{v}", "end": 1.0}))
    for src in ("reel.json", "scenes.js"):
        if (d / src).exists():
            (data / "source" / src).write_bytes((d / src).read_bytes())
    return f"drafts/v{v}/demo-{shape}-v{v}.mp4"


def approve(path, cut, v, also=None):
    import argparse
    review._probes.clear()  # another test's file of the same name was another size
    review.open_round(argparse.Namespace(video=path, also=also, ask=False, stage="picture"))
    review.append([{"type": "version.approved", "version": v, "cut": cut, "video": path}], H)


@pytest.fixture
def studio(tmp_path, monkeypatch):
    st = tmp_path / "studio"
    write_tree(st, {"studio.json": {}, "profile.json": {"brand": {"settled": True}, "history": []}})
    monkeypatch.setenv("VIDEO_STUDIO", str(st))
    return st


def test_the_happy_path_and_back(studio, monkeypatch):
    r = vs(studio, "new", "demo", "--kind", "reel", "--shape", "vertical")
    assert r.returncode == 0, r.stderr
    d = studio / "projects/demo"
    V = json.load(open(d / "video.json"))
    assert (V["first"], V["building"], V["status"]) == ("vertical", "vertical", "first")
    assert json.load(open(d / "reel.json"))["size"] == [1080, 1920]
    monkeypatch.chdir(d)
    (d / "scenes.js").write_text("// the scenes\n")

    # the first shape: drafts, then an approval
    v1 = render(d, "vertical", 1)
    r = vs(d, "shape", "widescreen")
    assert r.returncode != 0 and "isn't approved yet" in r.stderr  # not before the vertical is approved
    assert "review v1" in vs(d, "status").stdout
    approve(v1, "9x16", 1)
    assert "vs shape widescreen" in vs(d, "status").stdout

    # the other shape: same project, same page, the switch at the top
    r = vs(d, "shape", "widescreen")
    assert r.returncode == 0, r.stderr
    assert json.load(open(d / "video.json"))["status"] == "second"
    w1 = render(d, "widescreen", 1)
    approve(w1, "16x9", 1)
    R = review.current(review.state())
    assert [c["cut"] for c in R["cuts"]] == ["16x9", "9x16"]  # both shapes, one round
    review.append([{"type": "version.approved", "version": 1, "cut": "9x16", "video": w1}], H)
    assert "vs finish" in vs(d, "status").stdout

    # finish: finals/<video>/ and latest/<video>/, named by the kit
    r = vs(d, "finish")
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(os.listdir(studio / "finals/demo")) == ["demo-vertical-v1-cover.jpg", "demo-vertical-v1.mp4",
                                                         "demo-widescreen-v1-cover.jpg", "demo-widescreen-v1.mp4"]
    assert sorted(os.listdir(studio / "latest/demo")) == ["demo-vertical-cover.jpg", "demo-vertical.mp4",
                                                         "demo-widescreen-cover.jpg", "demo-widescreen.mp4"]
    V = json.load(open(d / "video.json"))
    assert V["status"] == "done" and V["finals"][0]["files"]["widescreen"]["final"] == "finals/demo/demo-widescreen-v1.mp4"
    assert review.state()["finished"]["files"]
    assert "vs reopen demo" in vs(d, "status").stdout
    assert vs(d, "finish").returncode != 0  # finishing twice is refused

    # days later: a change. The sources go back to exactly what made the final; the next draft is v2
    (d / "scenes.js").write_text("// an experiment nobody approved\n")
    r = vs(studio, "reopen", "demo")
    assert r.returncode == 0, r.stderr
    assert (d / "scenes.js").read_text() == "// the scenes\n"
    aside = [x for x in os.listdir(d / "drafts") if x.startswith("reopened-")]
    assert len(aside) == 1 and (d / "drafts" / aside[0] / "scenes.js").read_text() == "// an experiment nobody approved\n"
    V = json.load(open(d / "video.json"))
    assert (V["status"], V["building"]) == ("first", "vertical")
    assert json.load(open(d / "reel.json"))["version"] == 2
    assert review.state()["finished"] is None  # the page stops saying Done

    # the next final replaces the one in latest/, and finals/ keeps both
    v2 = render(d, "vertical", 2)
    approve(v2, "9x16", 2)
    assert vs(d, "shape", "widescreen").returncode == 0
    w2 = render(d, "widescreen", 2)
    approve(w2, "16x9", 2)
    review.append([{"type": "version.approved", "version": 2, "cut": "9x16", "video": w2}], H)
    r = vs(d, "finish")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(os.listdir(studio / "finals/demo")) == 8
    assert "| demo | vertical | v2 |" in (studio / "latest/VERSIONS.md").read_text()
    assert len(json.load(open(d / "video.json"))["finals"]) == 2


def test_a_finished_video_never_renders_without_reopen(studio):
    vs(studio, "new", "demo", "--kind", "reel", "--shape", "vertical")
    d = studio / "projects/demo"
    V = json.load(open(d / "video.json"))
    V["status"] = "done"
    json.dump(V, open(d / "video.json", "w"))
    r = vs(d, "build")
    assert r.returncode != 0 and "vs reopen demo" in r.stderr


def test_the_second_shape_waits_for_the_first(studio):
    vs(studio, "new", "demo", "--kind", "reel", "--shape", "vertical")
    d = studio / "projects/demo"
    r = vs(d, "build", "--shape", "widescreen")
    assert r.returncode != 0 and "still on its first shape" in r.stderr
    r = vs(d, "shape", "widescreen", "--early", "the client only wants wide")
    assert r.returncode == 0
    assert json.load(open(d / "video.json"))["log"][-1]["why"] == "the client only wants wide"


def test_a_name_is_the_videos_own(studio):
    for bad in ("Demo", "demo-16x9", "demo-vertical", "demo-v2", "demo_x"):
        assert vs(studio, "new", bad, "--kind", "reel", "--shape", "vertical").returncode != 0, bad
    assert vs(studio, "new", "demo", "--kind", "reel").returncode != 0  # the shape it starts in is required


def test_finish_reads_the_pixels_and_never_overwrites(studio, monkeypatch):
    vs(studio, "new", "demo", "--kind", "reel", "--shape", "vertical")
    d = studio / "projects/demo"
    monkeypatch.chdir(d)
    liar = d / "drafts/v1/demo-vertical-v1.mp4"  # named vertical, drawn wide
    video(liar, "192x108")
    approve("drafts/v1/demo-vertical-v1.mp4", "16x9", 1)
    r = vs(d, "finish", "--one-shape", "--final", "drafts/v1/demo-vertical-v1.mp4")
    assert r.returncode != 0 and "never rename it" in r.stderr
    # a final already filed under that name with other bytes is never written over
    import video as V
    (studio / "finals/demo").mkdir(parents=True)
    (studio / "finals/demo/x.mp4").write_bytes(b"old")
    (d / "y.mp4").write_bytes(b"new")
    with pytest.raises(SystemExit, match="never overwritten"):
        V.file_into(str(d / "y.mp4"), str(studio / "finals/demo/x.mp4"), dry=False)
    assert (studio / "finals/demo/x.mp4").read_bytes() == b"old"
