"""The ledger and the one spend gate (vslib.log / amend / done / failed / gate). Nothing here can spend: the gate is
exercised for its refusals, and VIDEO_KIT_NO_SPEND is set for every test."""
import csv, importlib, json, os
import pytest
from conftest import write_tree

OLD = ("date,project,vendor,what,credits,usd,kept,note\n"
       "2026-09-27,reel,kie.ai,music takes 1-2,12,,rejected,suno\n"
       "2026-09-28,reel,openai,take check a.mp3,,0.01,,x\n")


@pytest.fixture
def studio(tmp_path, monkeypatch):
    write_tree(tmp_path, {"s/studio.json": {}, "s/projects/vid/reel.json": {"name": "vid"}, "s/ledger.csv": OLD})
    monkeypatch.setenv("VIDEO_STUDIO", str(tmp_path / "s"))
    monkeypatch.chdir(tmp_path / "s/projects/vid")
    import vslib
    return importlib.reload(vslib)


def ledger(v):
    return list(csv.DictReader(open(v.ledger_path())))


def test_an_old_ledger_gains_id_and_status_and_keeps_its_rows(studio):
    before = ledger(studio)
    rid = studio.log("elevenlabs", "voice t1 (acts 1-2)", credits=172, note="x")
    rows = ledger(studio)
    assert open(studio.ledger_path()).readline().strip().split(",") == studio.LEDGER_FIELDS
    assert [{k: r[k] for k in before[0]} for r in rows[:2]] == before
    assert rows[-1]["id"] == rid and rows[-1]["status"] == "submitted" and rows[-1]["project"] == "vid"


def test_a_row_ends_done_or_failed(studio):
    a, b = studio.log("kie.ai", "music A (submitted t1)", credits=12), studio.log("elevenlabs", "sfx zap", credits=11)
    studio.done(a)
    studio.failed(b, note="HTTP 401")
    rows = {r["id"]: r for r in ledger(studio)}
    assert rows[a]["status"] == "done" and rows[b]["status"] == "failed" and rows[b]["note"] == "HTTP 401"


def test_amend_by_old_row_index_still_works(studio):
    studio.amend(0, kept="kept")
    assert ledger(studio)[0]["kept"] == "kept"


def test_kie_credits_count_in_dollars(studio):
    assert studio.spent_usd(project="reel") == pytest.approx(12 * 0.005 + 0.01)


def gate_says(studio, capsys, **kw):
    with pytest.raises(SystemExit) as e:
        studio.gate("kie.ai", "two takes", **kw)
    return str(e.value) + capsys.readouterr().out


def test_the_gate_refuses_when_no_spend_is_set(studio, capsys):
    assert "VIDEO_KIT_NO_SPEND" in gate_says(studio, capsys, credits=12, yes=True)


def test_the_gate_asks_first(studio, capsys, monkeypatch):
    monkeypatch.delenv("VIDEO_KIT_NO_SPEND")
    out = gate_says(studio, capsys, credits=12)
    assert "about 12 kie.ai credits" in out and "$0.06" in out and "Re-run with --yes" in out


def test_the_gate_holds_the_credit_cap(studio, capsys, monkeypatch):
    monkeypatch.delenv("VIDEO_KIT_NO_SPEND")
    studio.log("kie.ai", "music A (submitted t1)", credits=40)
    out = gate_says(studio, capsys, credits=12, yes=True, cap_key="kie_credits_per_video", scope="music")
    assert "48-credit cap" in out


def test_the_gate_holds_the_dollar_budget(studio, capsys, monkeypatch):
    monkeypatch.delenv("VIDEO_KIT_NO_SPEND")
    json.dump({"name": "vid", "budget_usd": 0.05}, open("reel.json", "w"))
    out = gate_says(studio, capsys, credits=12, yes=True)
    assert "dollar budget" in out and "--over" in out


def test_the_gate_lets_a_go_through(studio, capsys, monkeypatch):
    monkeypatch.delenv("VIDEO_KIT_NO_SPEND")
    studio.gate("kie.ai", "two takes", credits=12, yes=True, cap_key="kie_credits_per_video", scope="music")
    assert "about 12 kie.ai credits" in capsys.readouterr().out


def test_estimate_mode_prices_a_step_and_spends_nothing(studio, tmp_path, monkeypatch):
    # vs review offer --paid asks a step for its price this way: the gate writes its numbers and the step stops (exit 0),
    # before anything is spent, even with VIDEO_KIT_NO_SPEND set
    out = tmp_path / "e.json"
    monkeypatch.setenv("VIDEO_KIT_ESTIMATE", str(out))
    before = ledger(studio)
    with pytest.raises(SystemExit) as e:
        studio.gate("kie.ai", "two takes", credits=12, cap_key="kie_credits_per_video", scope="music")
    E = json.load(open(out))
    assert e.value.code == 0 and E["cost"] == "12 kie.ai credits · $0.06" and E["usd"] == 0.06
    assert not E["over_cap"] and E["so_far"] == 0 and ledger(studio) == before  # the old music row is another video's
