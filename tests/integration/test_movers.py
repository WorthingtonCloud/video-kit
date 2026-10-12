"""A mover drawn on a canvas (exTrack) is held to the overlap rules: vs inspect samples its path and finds a stretch of
a quarter second or more on words people are reading (rests-on-text), but not a quick pass in front of them, and not a
rest beside a line's glyphs inside its frame-wide box (the false alarm a first scratch version raised, Oct 12, 2026).
Slow: it builds in a browser (vs test --fast skips it)."""
import json, os, shutil
import pytest
from conftest import tone, vs, font_studio  # noqa: F401 (the fixture)

pytestmark = pytest.mark.slow
FIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "mover-on-words")


def test_a_drawn_mover_resting_on_words_is_an_error_and_passing_is_not(tmp_path, font_studio):
    d = tmp_path / "movers"
    shutil.copytree(FIX, d)
    os.makedirs(d / "music")
    tone(d / "music/take1.mp3", 6, freq=150, db=-20)
    for step in (["build", "--no-render"], ["inspect"]):
        r = vs(d, *step)
        assert r.returncode == 0, f"vs {' '.join(step)} failed:\n{r.stdout[-3000:]}\n{r.stderr[:3000]}"
    found = [f for f in json.load(open(d / "build/findings.json"))["items"] if f["check"] == "rests-on-text"]
    assert [f["elements"] for f in found] == [["s01_movers/track:sits", "s01_movers/rests-headline"]], found
    f = found[0]
    assert f["severity"] == "error" and 0.9 <= f["t1"] - f["t0"] <= 1.05 and 1.2 <= f["at"] <= 2.2
    assert '"WHERE IT RESTS"' in f["text"] and "passing in front is fine" in f["text"]
    # every mover joins the map, with the line of scenes.js that registered it
    els = {e["id"]: e for e in json.load(open(d / "build/elements.json"))["items"]}
    for k in ("sits", "passes", "beside"):
        e = els[f"s01_movers/track:{k}"]
        assert e["kind"] == "mover" and e["on"] and e["src"].startswith("scenes.js:"), e
