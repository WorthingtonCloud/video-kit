"""Every scar a check can catch, pinned: one deliberately broken mini-project per folder here, and its expect.json says
what vs inspect or vs check must find, or must not. The scar ledger (each scars.md bullet's ‹test: regression/<name>›)
points at these folders. Slow: they build in a browser (vs test --fast skips them)."""
import json, os, shutil
import pytest
from conftest import tone, vs, font_studio  # noqa: F401 (the fixture)

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = sorted(d for d in os.listdir(HERE) if os.path.exists(os.path.join(HERE, d, "expect.json")))


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
    none = E.get("expect_none", [])
    bad = [f for f in found if none == "all" or f["check"] in none]
    assert not bad, f"false alarms: {[(f['check'], f['elements']) for f in bad]}"
    assert F["checked"] >= E.get("checked_min", 1)
    els = {e["id"]: e for e in json.load(open(d / "build/elements.json"))["items"]}
    for el, text in E.get("element_text", {}).items():
        assert els[el]["text"] == text
