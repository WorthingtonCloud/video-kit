"""vs qa's sheets show the frame AT each cell's time. The scar: the contact sheet was made with the fps filter, which keeps
the last frame that rounds to each slot, so cell k showed about step·k + 0.47 s while qa printed "cell k = step·k
seconds" (Oct 15, 2026: on a 1080p60 final, its "30.0 s" frame was the 30.5 s seek's). The fixture videos prove it: every
half second starts dark for a tenth of a second, then turns bright, so a frame picked late reads bright, at a one-second
step and at --clip's half second alike."""
import json, os, subprocess
import pytest
from conftest import vs

PIL = pytest.importorskip("PIL", reason="the sheets are measured with Pillow: vs setup adds it to the engine's Python")
from PIL import Image, ImageStat  # noqa: E402


def video(path, secs=6, size="320x180", lo=30, hi=220, bar=None):
    """Each half second: luma lo for its first 0.1 s, hi after; a quiet tone under it. bar = (x, y, w, h, t0, t1): a white
    box shown from t0 to t1."""
    vf = f"geq=lum='if(lt(mod(T\\,0.5)\\,0.1)\\,{lo}\\,{hi})':cb=128:cr=128"
    if bar:
        x, y, w, h, t0, t1 = bar
        vf += f",drawbox=x={x}:y={y}:w={w}:h={h}:color=white:t=fill:enable='between(t,{t0},{t1})'"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=gray:s={size}:r=30:d={secs}",
                    "-f", "lavfi", "-i", f"sine=frequency=220:duration={secs}", "-vf", vf,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(path)], check=True)
    return str(path)


def cells(sheet, n, cw, ch, cols, crop=(0, 0, 1, 1)):
    """Mean luma of the first n tiles (tile's layout: padding 4 between cells, no margin), over crop (fractions)."""
    im = Image.open(sheet).convert("L")
    x0, y0, x1, y1 = crop
    out = []
    for i in range(n):
        x, y = (i % cols) * (cw + 4), (i // cols) * (ch + 4)
        out.append(ImageStat.Stat(im.crop((x + int(cw * x0), y + int(ch * y0), x + int(cw * x1), y + int(ch * y1)))).mean[0])
    return out


def test_contact_sheet_cell_k_is_the_frame_at_step_k(tmp_path):
    d = tmp_path / "p"
    video(d / "clip.mp4")
    (d / "reel.json").write_text("{}")
    r = vs(d, "qa", "clip.mp4")
    assert r.returncode == 0, r.stderr
    assert all(m < 100 for m in cells(d / "build/qa/clip-sheet.jpg", 6, 320, 180, 8)), "a cell shows a later frame"
    assert "6 frames, one every 1.0s" in r.stdout  # 6.0 s is past the last frame
    r = vs(d, "qa", "clip.mp4", "--clip")  # a generated clip: a frame every half second, five to a row
    assert r.returncode == 0, r.stderr
    assert all(m < 100 for m in cells(d / "build/qa/clip-sheet.jpg", 12, 320, 180, 5))
    assert "12 frames, one every 0.5s" in r.stdout
    assert not [f for f in os.listdir(d / "build/qa") if f.startswith("_")], "qa leaves its working frames behind"


def test_the_safe_sheet_and_the_scan_tell_the_same_time(tmp_path):
    """Vertical: the safe-zone sheet shades the contact sheet's frames, and the four-a-second scan's sample i is the frame
    at i/4 s, the moment its hit still seeks to. A word under the status bar for the first 0.08 s of second 1 is found
    at 1.0 s (the fps filter's default rounding sampled 1.1 s, after it left), and its still shows it."""
    d = tmp_path / "p"
    os.makedirs(d / "drafts/v1/data/vertical")
    (d / "reel.json").write_text("{}")
    video(d / "drafts/v1/p-vertical-v1.mp4", secs=3, size="540x960", lo=20, hi=120, bar=(150, 20, 240, 30, 1, 1.08))
    json.dump({"fingerprint": "fp", "segments": [{"name": "s01", "t0": 0, "t1": 3, "kind": "scene"}]},
              open(d / "drafts/v1/data/vertical/timeline.json", "w"))
    r = vs(d, "qa", "drafts/v1/p-vertical-v1.mp4")
    assert r.returncode == 0, r.stderr
    # the middle of each cell, clear of every shaded zone: the dark tenth at 0, 1 and 2 s
    assert all(m < 70 for m in cells(d / "build/qa/p-vertical-v1-safe.jpg", 3, 216, 384, 8, (0.3, 0.3, 0.7, 0.55)))
    top = [f for f in json.load(open(d / "drafts/v1/data/vertical/qa.json"))["items"]
           if f["check"] == "covered" and f["id"].startswith("q-covered-top")]
    assert len(top) == 1 and top[0]["t0"] == 1.0, top
    hit = Image.open(d / "build/qa/p-vertical-v1-safe-hits.jpg").convert("L")  # one still, 270 wide
    assert ImageStat.Stat(hit.crop((90, 12, 180, 22))).mean[0] > 150, "the hit still doesn't show the word the scan found"
