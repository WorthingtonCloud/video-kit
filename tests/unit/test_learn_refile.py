"""vs learn --final on a re-render (an explainer, Oct 4, 2026): the library bed another video won first kept its first
win only by hand, three times, and the profile got a second history line for the same video (its spend counted twice).
A bed keeps its first win and lists this video in also_won once; a video has one history line, whatever re-files it."""
import json, os
from conftest import write_tree, vs


def test_refiling_finals_keeps_the_first_win_and_one_history_line(tmp_path, monkeypatch):
    st = tmp_path / "studio"
    write_tree(st, {"studio.json": {}, "profile.json": {"brand": {"settled": True}, "history": []},
                    "library/music/index.json": {"items": {"bed": {"kind": "music", "file": "bed.mp3", "label": "pulse",
                                                                   "won": "first", "date": "2026-10-01"}}}})
    monkeypatch.setenv("VIDEO_STUDIO", str(st))
    d = tmp_path / "second"
    write_tree(d, {"reel.json": {}, "mix.json": {"take": 1, "music_db": -17, "sfx_db": 0},
                   "music/takes.json": {"take1": {"label": "pulse", "from": "library/music/bed.mp3"}},
                   "music/take1.mp3": "x", "drafts/v2/second-vertical-v2-take1.mp4": "x", "drafts/v3/second-vertical-v3-take1.mp4": "x"})
    for v in (2, 3):
        r = vs(d, "learn", "--final", f"drafts/v{v}/second-vertical-v{v}-take1.mp4")
        assert r.returncode == 0, r.stderr
    bed = json.load(open(st / "library/music/index.json"))["items"]["bed"]
    assert bed["won"] == "first" and bed["date"] == "2026-10-01"
    assert [x.split(" (")[0] for x in bed["also_won"]] == ["second"]
    hist = [h for h in json.load(open(st / "profile.json"))["history"] if h["project"] == "second"]
    assert len(hist) == 1 and hist[0]["finals"] == ["second-vertical-v3-take1.mp4"] and hist[0]["replaced_finals"] == ["second-vertical-v2-take1.mp4"]
