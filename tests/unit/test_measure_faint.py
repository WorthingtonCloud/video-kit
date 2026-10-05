"""A faint change still counts: dim shapes on a dark ground that a reviewer asked to remove change the picture by only
a few shades, under the grain line, and the round said "nothing measurable changed" (video-kit reel, Oct 2, 2026)."""
import os, subprocess, sys
from conftest import ENGINE

sys.path.insert(0, os.path.join(ENGINE, "py"))
import review  # noqa: E402


def _clip(path, square):
    """One second of the dark ground, with or without a dim square 18 levels brighter over a quarter of the frame."""
    vf = "drawbox=x=0:y=0:w=32:h=32:color=0x232327:t=fill" if square else "null"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x111114:s=64x64:r=30:d=1", "-vf", vf,
                    "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv444p", str(path)], check=True)
    return str(path)


def test_dim_shapes_leaving_a_dark_frame_count_as_a_change(tmp_path):
    a, b = _clip(tmp_path / "a.mp4", True), _clip(tmp_path / "b.mp4", False)
    px = review.measure_pixels(a, b, 0.5)
    assert px["changed"] < 0.005  # under the grain line on its own
    assert px["faint"] > 0.2
    assert review._moved(px)
    assert "faintly" in review._describe_pixels(px)


def test_an_unchanged_frame_is_still_unchanged(tmp_path):
    a, b = _clip(tmp_path / "a.mp4", True), _clip(tmp_path / "b.mp4", True)
    px = review.measure_pixels(a, b, 0.5)
    assert not review._moved(px)
    assert review._describe_pixels(px) == "its pixels didn't change"


def test_a_note_on_the_last_frame_can_be_measured(tmp_path):
    """A note at the end card's last frame (corporate-job, Oct 2; an explainer, Oct 4, 2026: 2:40.00 of a 160 s video)
    read "couldn't be measured: no frame at 159.99s". The moment clamps to the last frame instead."""
    a, b = _clip(tmp_path / "a.mp4", True), _clip(tmp_path / "b.mp4", False)
    for t in (0.99, 1.0):
        px = review.measure_pixels(a, b, t)
        assert px["faint"] > 0.2, (t, px)
