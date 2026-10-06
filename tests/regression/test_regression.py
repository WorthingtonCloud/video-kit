"""Every scar a check can catch, pinned: one deliberately broken mini-project per folder here, and its expect.json says
what vs inspect or vs check must find, or must not. The scar ledger (each scars.md bullet's ‹test: regression/<name>›)
points at these folders. Slow: they build in a browser (vs test --fast skips them)."""
import json, os, shutil, subprocess
import pytest
from conftest import tone, vs, font_studio  # noqa: F401 (the fixture)

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = sorted(d for d in os.listdir(HERE) if os.path.exists(os.path.join(HERE, d, "expect.json")))


def middle_color(png):
    """The mean of the still's middle 200 px square, by its strongest channel: "red", "green", "blue", or "dark"."""
    rgb = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-vf", "crop=200:200:(iw-200)/2:(ih-200)/2,scale=1:1:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return "dark" if max(rgb) < 128 else ("red", "green", "blue")[rgb.index(max(rgb))]


@pytest.mark.slow
@pytest.mark.parametrize("name", CASES)
def test_scar(name, tmp_path, font_studio):
    E = json.load(open(os.path.join(HERE, name, "expect.json")))
    d = tmp_path / name
    shutil.copytree(os.path.normpath(os.path.join(HERE, name, E.get("use", "."))), d,
                    ignore=shutil.ignore_patterns("expect.json", "README.md"))
    for f, how in E.get("make", {}).items():
        os.makedirs(os.path.dirname(d / f), exist_ok=True)
        tone(d / f, float(how.split(":")[1]), freq=150, db=-20)
    for f, parts in E.get("clips", {}).items():  # ["red:3", "blue:3"]: solid colors one after another, a video's time made visible
        os.makedirs(os.path.dirname(d / f), exist_ok=True)
        ins = [a for p in parts for a in ("-f", "lavfi", "-i", f"color=c={p.split(':')[0]}:s=1080x1920:r=30:d={p.split(':')[1]}")]
        subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", f"concat=n={len(parts)}:v=1",
                        "-pix_fmt", "yuv420p", str(d / f)], check=True)

    if "snap" in E:  # what vs snap's stills show, not what inspect measures: the frame's middle must be this color
        S = E["snap"]
        r = vs(d, "build", "--no-render")
        assert r.returncode == 0, f"vs build failed:\n{r.stdout[-3000:]}\n{r.stderr[:3000]}"
        r = vs(d, "snap", *S["at"], "--no-sheet")
        assert r.returncode == 0 and "⚠" not in r.stdout, f"vs snap failed or warned:\n{r.stdout[-2000:]}\n{r.stderr[:2000]}"
        for t, want in S["at"].items():
            got = middle_color(d / "build/qa/snap" / (f"{float(t):.2f}".zfill(7) + ".png"))
            assert got == want, f"at {t}s the panel shows {got}, not {want} (snap shot it before the video got there)"
        if "broken" in S:  # a panel whose video can't load: snap must say so, by segment, not shoot it silently
            B = S["broken"]
            os.remove(d / B["remove"])
            r = vs(d, "snap", *map(str, B["at"]), "--no-sheet")
            assert r.returncode == 0 and all(w in r.stdout for w in B["warns_with"]), f"vs snap should warn:\n{r.stdout[-2000:]}"
        return

    if "steps" in E:  # a scar a step refuses or warns about, before anything is built
        for st in E["steps"]:
            r = vs(d, st["run"])
            out = r.stdout + r.stderr
            if "fails_with" in st:
                assert r.returncode != 0 and st["fails_with"] in out, f"vs {st['run']} should refuse:\n{out[-1500:]}"
            if "warns_with" in st:
                assert r.returncode == 0 and st["warns_with"] in out, f"vs {st['run']} should warn:\n{out[-1500:]}"
        return

    for step in (["build", "--no-render"], ["inspect"]):
        r = vs(d, *step)
        # all of it: a browser stall names its step at the top of its output, not the bottom
        assert r.returncode == 0, f"vs {' '.join(step)} failed:\n{r.stdout[-3000:]}\n{r.stderr[:3000]}"
    F = json.load(open(d / "build/findings.json"))
    found = F["items"]
    for e in E.get("expect", []):
        assert any(f["check"] == e["check"] and e["element"] in f["elements"] for f in found), \
            f"no {e['check']} on {e['element']}: {[(f['check'], f['elements']) for f in found]}"
    for e in E.get("expect_not", []):  # this check must not fire on this element (another one may, on purpose)
        assert not any(f["check"] == e["check"] and e["element"] in f["elements"] for f in found), \
            f"{e['check']} on {e['element']}: {[(f['check'], f['elements'], f['text']) for f in found]}"
    none = E.get("expect_none", [])
    bad = [f for f in found if none == "all" or f["check"] in none]
    assert not bad, f"false alarms: {[(f['check'], f['elements']) for f in bad]}"
    assert F["checked"] >= E.get("checked_min", 1)
    els = {e["id"]: e for e in json.load(open(d / "build/elements.json"))["items"]}
    for el, text in E.get("element_text", {}).items():
        assert els[el]["text"] == text
