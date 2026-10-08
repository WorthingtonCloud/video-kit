"""The contract, from Python: every case in cases.json (contract.test.mjs runs the same cases in JavaScript)."""
import importlib, json, os, sys
import pytest
from conftest import write_tree

CASES = json.load(open(os.path.join(os.path.dirname(__file__), "cases.json")))


def vslib():
    import vslib as v
    return importlib.reload(v)


def run_in(tmp_path, monkeypatch, case):
    write_tree(tmp_path, case.get("tree", {}))
    for k, v in (case.get("env") or {}).items():
        monkeypatch.setenv(k, v.replace("{root}", str(tmp_path)))
    monkeypatch.chdir(tmp_path / case["cwd"])


def expect(case, root):
    e = case["expect"]
    return e.replace("{root}", str(root)) if isinstance(e, str) else e


def dig(d, dotted):
    for k in dotted.split("."):
        d = d[k]
    return d


@pytest.mark.parametrize("case", CASES["studio"], ids=lambda c: c["name"])
def test_studio(tmp_path, monkeypatch, case):
    run_in(tmp_path, monkeypatch, case)
    got = vslib().studio_root()
    assert (os.path.realpath(got) if got else None) == (os.path.realpath(expect(case, tmp_path)) if case["expect"] else None)


@pytest.mark.parametrize("case", CASES["profile"], ids=lambda c: c["name"])
def test_profile(tmp_path, monkeypatch, case):
    run_in(tmp_path, monkeypatch, case)
    pr = vslib().profile()
    for k, v in case["expect"].items():
        assert dig(pr, k) == v, k


@pytest.mark.parametrize("case", CASES["keys"], ids=lambda c: c["name"])
def test_keys(tmp_path, monkeypatch, case):
    run_in(tmp_path, monkeypatch, case)
    assert vslib().find_key("K") == case["expect"]


@pytest.mark.parametrize("case", CASES["timing"], ids=lambda c: c["name"])
def test_timing(case):
    v = vslib()
    if case["expect"] is None:
        with pytest.raises(SystemExit):
            v.timeline(case["reel"])
        return
    T, TT, END = v.timeline(case["reel"])
    assert (T, TT, END) == (case["expect"]["T"], case["expect"]["TT"], case["expect"]["END"])


@pytest.mark.parametrize("case", CASES["words"]["cases"], ids=lambda c: c["spec"] + str(c["acts"]))
def test_words(case):
    v = vslib()
    if case["expect"] is None:
        with pytest.raises(ValueError):
            v.word_at(CASES["words"]["words"], case["spec"], case["acts"])
        return
    assert v.word_at(CASES["words"]["words"], case["spec"], case["acts"])[0] == case["expect"]


@pytest.mark.parametrize("case", CASES["hash"], ids=lambda c: repr(c["text"]))
def test_hash(tmp_path, case):
    p = tmp_path / "f"
    p.write_text(case["text"])
    assert vslib().file_hash(str(p)) == case["expect"]


@pytest.mark.parametrize("case", CASES["files"]["shape"], ids=lambda c: c["name"])
def test_files_shape(tmp_path, monkeypatch, case):
    monkeypatch.delenv("VS_SHAPE", raising=False)
    run_in(tmp_path, monkeypatch, case)
    assert vslib().active_shape() == case["expect"]


@pytest.mark.parametrize("case", CASES["files"]["draft"], ids=lambda c: c["expect"]["file"])
def test_files_draft(tmp_path, monkeypatch, case):
    (tmp_path / case["cwd"]).mkdir()
    monkeypatch.chdir(tmp_path / case["cwd"])
    v, e = vslib(), case["expect"]
    f = v.draft_file(*case["args"])
    assert f == e["file"]
    assert v.data_dir(f) == e["data"]
    assert v.cover_of(f) == e["cover"]
    assert v.parse_draft(f) == e["parsed"]


@pytest.mark.parametrize("case", CASES["files"]["reel"], ids=lambda c: c["name"])
def test_files_reel(tmp_path, monkeypatch, case):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reel.json").write_text(json.dumps(case["reel"]))
    R = vslib().reel(shape=case["shape"])
    assert "shapes" not in R
    for k, val in case["expect"].items():
        assert R[k] == val, k


@pytest.mark.parametrize("name", CASES["files"]["not_drafts"])
def test_files_not_drafts(name):
    assert vslib().parse_draft(name) is None
