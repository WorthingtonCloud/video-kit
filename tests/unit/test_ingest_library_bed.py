"""vs ingest on a bed already in the studio's music library: it becomes the video's next take, as it is. Re-encoding it
onto itself cut two winning beds to 1.4 s stubs and wiped their index entries (Oct 9, 2026)."""
import json, os, subprocess
from conftest import tone, vs


def secs(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True, check=True).stdout)


def test_a_library_bed_becomes_a_take_untouched(tmp_path, monkeypatch):
    studio = tmp_path / "studio"
    (studio / "library" / "music").mkdir(parents=True)
    (studio / "studio.json").write_text("{}")
    bed = studio / "library" / "music" / "winner.mp3"
    tone(str(bed.with_suffix(".wav")), secs=6.0)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bed.with_suffix(".wav")), str(bed)], check=True)
    os.remove(bed.with_suffix(".wav"))
    entry = {"kind": "music", "file": "winner.mp3", "label": "modern pulse", "won": "an earlier video", "secs": round(secs(str(bed)), 2)}
    (studio / "library" / "music" / "index.json").write_text(json.dumps({"items": {"winner": entry}}))
    monkeypatch.setenv("VIDEO_STUDIO", str(studio))
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "plan.json").write_text("{}")
    before = open(bed, "rb").read()
    r = vs(str(proj), "ingest", str(bed), "--as", "music")
    assert r.returncode == 0, r.stderr
    assert open(bed, "rb").read() == before  # the library's file is untouched
    idx = json.loads((studio / "library" / "music" / "index.json").read_text())["items"]["winner"]
    assert idx == entry  # and so is its record (what it won)
    takes = json.loads((proj / "music" / "takes.json").read_text())
    assert takes["take1"]["label"] == "modern pulse" and abs(secs(str(proj / "music" / "take1.mp3")) - entry["secs"]) < 0.1
    assert not (studio / "library" / "originals" / "winner.mp3").exists()  # nothing to keep: it is the original
