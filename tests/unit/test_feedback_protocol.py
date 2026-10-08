"""The feedback protocol (engine/py/feedback.py) and how Review Studio implements it (engine/py/review.py): the life of a
note from observation to acceptance, the verdict that a claim alone never earns, the hand-off between the page and the
agent, and learning that only ever happens on the human's say. These protect the architecture, not the pixels."""
import json, os, re, subprocess, sys, time
import pytest
from conftest import ENGINE, KIT, vs

sys.path.insert(0, os.path.join(ENGINE, "py"))
import feedback  # noqa: E402
import review  # noqa: E402

H, A = "human", "agent"


def video(path, secs=2.0, color="0x202020", size="108x192"):
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(str(path)) or ".", "data", "widescreen" if "-widescreen-" in str(path) else "vertical"), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={size}:d={secs}:r=30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


@pytest.fixture
def proj(tmp_path, monkeypatch):
    d = tmp_path / "p"
    d.mkdir()
    (d / "reel.json").write_text("{}")
    video(d / "drafts/v1/p-vertical-v1.mp4")
    (d / "drafts/v1/data/vertical/timeline.json").write_text(json.dumps({"fingerprint": "fp1", "end": 2.0}))
    monkeypatch.chdir(d)
    return d


@pytest.fixture
def studio(tmp_path, monkeypatch):
    s = tmp_path / "studio"
    s.mkdir()
    (s / "studio.json").write_text("{}")
    (s / "lessons.md").write_text("# Lessons\n\n## Story and words\n\n## Picture\n\n- an older rule, written by hand (Sep 28)\n\n## Sound\n")
    (s / "profile.json").write_text(json.dumps({"mix": {"music_db": -16}}))
    monkeypatch.setenv("VIDEO_STUDIO", str(s))
    return s


def opened(video_="drafts/v1/p-vertical-v1.mp4", version=1):
    return review.append([{"type": "round.opened", "version": version, "cut": "9x16", "video": video_}], A)


TARGET = {"el": "s01/label", "box": [0.1, 0.1, 0.3, 0.2], "text": "OLD", "on": [1.0, 3.0]}


def note(t=2.0, **kw):
    return {"type": "note.added", "note": {"time": {"t": t}, "comment": "too small", **kw}}


def emap(*items, fp="fp2"):
    return {"fingerprint": fp, "step": 0.15, "items": [{"id": i, "text": t, "on": on, "boxes": bx} for i, t, on, bx in items]}


def answered(**kw):
    n = {"id": "n-0001", "version": 1, "time": {"t": 2.0}, "target": dict(TARGET), "mark": {"type": "none"}, "also": [],
         "resolution": {"outcome": "resolved", "said": "fixed"}}
    n.update(kw)
    return n


def cmd(*a):
    return vs(".", "review", *a)


# ── the record: generic fields, the video's address carried untouched, the version kept ──
def test_a_note_becomes_a_feedback_record_with_its_address_intact(proj):
    opened()
    mark = {"type": "arrow", "from": [0.2, 0.15], "to": [0.6, 0.15], "under_from": ["s01/label"], "under_to": []}
    keep = {"type": "keep-clear", "box": [0.5, 0.5, 0.9, 0.9], "over": [], "keeps": []}
    review.append([note(target=dict(TARGET), mark=mark, also=[keep], segment="s01", scene="hub", visible=["s01/label"],
                        ask="bigger", scope="project"), {"type": "round.sent"}], H)
    rec = json.loads(cmd("show", "--json").stdout)["records"][0]
    assert rec["artifact"] == {"project": "p", "kind": "reel", "version": 1, "rendition": "9x16"}
    a = rec["address"]
    assert a["domain"] == "video" and a["t"] == 2.0 and a["segment"] == "s01" and a["element"] == "s01/label"
    assert a["box"] == TARGET["box"] and a["mark"] == mark and a["also"] == [keep] and a["visible"] == ["s01/label"]
    assert rec["intent"] == {"words": "too small", "ask": "bigger", "scope": "project", "follows": None, "findings": []}
    assert rec["phase"] == "intent" and rec["waits_on"] == "agent"
    assert (rec["implemented"], rec["verified"], rec["accepted"]) == (False, False, False)
    # the protocol knows nothing of a video's addressing (and imports nothing of the engine): the address is the caller's
    code = open(os.path.join(ENGINE, "py/feedback.py")).read().split('"""', 2)[2]
    assert not re.search(r"\b(segment|fps|element|box|frame|vslib|import review)\b", code)
    # nor reads a video note's own fields (a shape is a "cut", a sound's ask lives on the sound) or names a video scope
    assert not re.search(r'\.get\("(cut|sound)"\)|\["(cut|sound)"\]|"video"', code)


def test_an_ask_or_a_reach_off_the_list_is_refused(proj):
    opened()
    with pytest.raises(review.Refused, match="ask 'prettier'"):
        review.append([note(ask="prettier")], H)
    with pytest.raises(review.Refused, match="scope 'galaxy'"):
        review.append([note(scope="galaxy")], H)
    review.append([note(), {"type": "round.sent"}], H)
    with pytest.raises(review.Refused, match="expect 'vibes'"):
        review.append([{"type": "note.resolved", "id": "n-0001", "said": "x", "outcome": "resolved", "expect": "vibes"}], A)


# ── the phases: observation → intent → verification → acceptance → closed ──
def test_a_notes_phase_and_who_moves_it_next(proj):
    opened()
    review.append([{**note(target=dict(TARGET)), "held": True}], H)
    ph = lambda S, i="n-0001": feedback.phase(S["notes"][i], S["notes"])
    assert ph(review.state("human")) == ("observation", "human")
    review.append([{"type": "round.sent"}], H)
    assert ph(review.state()) == ("intent", "agent")
    review.append([{"type": "note.question", "id": "n-0001", "text": "how much bigger?"}], A)
    assert ph(review.state()) == ("intent", "human")
    review.append([{"type": "note.answered", "id": "n-0001", "text": "twice"}], H)
    review.append([{"type": "note.resolved", "id": "n-0001", "said": "twice the size", "outcome": "resolved"}], A)
    S = review.state()
    assert ph(S) == ("verification", "tooling") and feedback.acceptance(S["notes"]["n-0001"], S["notes"]) == "pending"
    review.append([{"type": "note.measured", "id": "n-0001", "measured": {"verdict": "changed", "from": 1, "to": 2}}], A)
    assert ph(review.state()) == ("acceptance", "human")
    review.append([{"type": "note.accepted", "id": "n-0001"}], H)
    S = review.state()
    assert ph(S) == ("closed", None) and feedback.acceptance(S["notes"]["n-0001"], S["notes"]) == "accepted"


def test_a_follow_up_supersedes_the_note_it_follows(proj):
    opened()
    review.append([note(), {"type": "round.sent"}], H)
    review.append([{"type": "note.resolved", "id": "n-0001", "said": "done", "outcome": "resolved"}], A)
    review.append([{**note(follows="n-0001", comment="closer, but"), "held": True}, {"type": "round.sent"}], H)
    S = review.state()
    assert feedback.acceptance(S["notes"]["n-0001"], S["notes"]) == "superseded"
    assert feedback.phase(S["notes"]["n-0001"], S["notes"])[0] == "closed"


# ── verification: implemented ≠ verified ≠ accepted; an unchanged target is never verified ──
def test_an_unchanged_target_is_never_verified():
    E = emap(("s01/label", "OLD", [[1.0, 3.0]], [[1.0, 0.1, 0.1, 0.3, 0.2]]))
    m = review.measure(answered(), E, [1000, 2000])
    assert m["verdict"] == "unchanged" and m["flag"].startswith("nothing measurable") and not feedback.verified(m)


def test_a_rename_alone_is_not_a_change():
    E = emap(("s01/new-label", "OLD", [[1.0, 3.0]], [[1.0, 0.1, 0.1, 0.3, 0.2]]))
    m = review.measure(answered(resolution={"outcome": "resolved", "said": "renamed", "renamed": "s01/new-label"}), E, [1000, 2000])
    assert m["el"] == "s01/new-label" and m["verdict"] == "unchanged"


@pytest.mark.parametrize("ask, new_box, on, visible, verdict", [
    ("bigger", [0.05, 0.05, 0.35, 0.25], [1.0, 3.0], None, "changed"),
    ("bigger", [0.15, 0.12, 0.25, 0.18], [1.0, 3.0], None, "contrary"),
    ("bigger", [0.3, 0.1, 0.5, 0.2], [1.0, 3.0], None, "other"),  # it moved; its size is the same
    ("smaller", [0.15, 0.12, 0.25, 0.18], [1.0, 3.0], None, "changed"),
    ("longer", [0.1, 0.1, 0.3, 0.2], [1.0, 4.0], None, "changed"),
    ("shorter", [0.1, 0.1, 0.3, 0.2], [1.0, 4.0], None, "contrary"),
    ("move", [0.3, 0.1, 0.5, 0.2], [1.0, 3.0], None, "changed"),
    ("simpler", [0.1, 0.1, 0.3, 0.2], [1.0, 3.0], ["s01/label"], "changed"),  # the clutter is gone
    ("simpler", [0.1, 0.1, 0.3, 0.2], [1.0, 3.0], ["s01/label", "s01/a", "s01/b", "s01/c"], "contrary"),
])
def test_an_ask_is_measured_in_its_own_dimension_and_direction(ask, new_box, on, visible, verdict):
    items = [("s01/label", "OLD", [on], [[1.0, *new_box]])]
    if visible:
        items += [(v, "", [[0.0, 3.0]], [[0.0, 0.6, 0.6, 0.7, 0.7]]) for v in visible if v != "s01/label"]
    n = answered(ask=ask, visible=["s01/label", "s01/a", "s01/b"])
    m = review.measure(n, emap(*items), [1000, 2000])
    assert m["verdict"] == verdict, (m["changes"], m["flag"])
    assert feedback.verified(m) == (verdict == "changed")


def test_an_arrow_says_which_way_counts_as_moved():
    mk = {"type": "arrow", "from": [0.2, 0.15], "to": [0.8, 0.15]}
    toward = review.measure(answered(ask="move", mark=mk), emap(("s01/label", "OLD", [[1.0, 3.0]], [[1.0, 0.4, 0.1, 0.6, 0.2]])), [1000, 2000])
    away = review.measure(answered(ask="move", mark=mk), emap(("s01/label", "OLD", [[1.0, 3.0]], [[1.0, 0.0, 0.1, 0.2, 0.2]])), [1000, 2000])
    assert toward["verdict"] == "changed" and away["verdict"] == "contrary"


def test_the_agents_expected_change_is_checked_too():
    E = emap(("s01/label", "OLD", [[1.0, 3.0]], [[1.0, 0.3, 0.1, 0.5, 0.2]]))  # it moved
    m = review.measure(answered(resolution={"outcome": "resolved", "said": "bigger", "expect": "size"}), E, [1000, 2000])
    assert m["verdict"] == "other" and m["expected_met"] is False
    m = review.measure(answered(resolution={"outcome": "resolved", "said": "moved", "expect": "place"}), E, [1000, 2000])
    assert m["verdict"] == "changed" and m["expected_met"] is True


def test_judge_rules_hold_on_their_own():
    assert feedback.judge({})[0] == "unchanged"
    assert feedback.judge({"presence": -1})[0] == "gone"  # gone, and the answer didn't say so
    assert feedback.judge({"presence": -1}, removed=True)[0] == "removed"
    assert feedback.judge({"presence": -1}, removed=True, ask="remove")[0] == "removed"
    assert feedback.judge({"presence": -1}, removed=True, ask="bigger")[0] == "other"
    assert feedback.judge({"level": 3.0}, ask="quieter")[0] == "contrary"
    assert feedback.judge({"pixels": True}, expect="color") == ("changed", True, None)
    assert feedback.judge({"place": 1}, ask="longer", can=("pixels",))[0] == "unmeasured"  # can't see time: nothing stands in
    assert feedback.judge({}, outcome="wontdo") == ("unchanged", None, None)  # nothing to verify, nothing flagged
    # an older measurement (no verdict written) still reads right
    assert feedback.verdict({"flag": "nothing measurable changed (its place…)"}) == "unchanged"
    assert feedback.verdict({"flag": None, "dx": 4}) == "changed"
    assert feedback.verdict({"gone": True, "flag": None}) == "removed"  # gone with nothing flagged: the answer said so


def test_a_removal_the_answer_named_is_its_own_verdict():
    """Gone on purpose (removed) and gone by accident (gone) are different facts; neither reads as "it changed"."""
    E = emap(("s01/other", "X", [[1.0, 3.0]], [[1.0, 0.5, 0.5, 0.6, 0.6]]))  # s01/label isn't in the new version
    said = lambda **kw: {"outcome": "resolved", "said": "took it out", "removed": True, **kw}
    for n in (answered(ask="remove", resolution=said()), answered(resolution=said())):
        m = review.measure(n, E, [1000, 2000])
        assert m["verdict"] == "removed" and feedback.verified(m) and m["flag"] is None
        assert review.describe_measured(m).startswith("removed in this version, as the answer said")
    m = review.measure(answered(ask="bigger", resolution=said()), E, [1000, 2000])
    assert m["verdict"] == "other" and not feedback.verified(m)  # asked bigger: taking it out isn't that
    m = review.measure(answered(ask="remove"), E, [1000, 2000])
    assert m["verdict"] == "gone" and not feedback.verified(m)  # asked to go, but the answer never said it went


def test_a_dimension_the_note_cant_see_is_never_verified_by_another(proj):
    """Asked longer on a moment with no element: the picture changing there proves nothing about time on screen, so the
    verdict is unmeasured (with what it did see), never "changed"."""
    video(proj / "drafts/v2/p-vertical-v2.mp4", color="0xd02020")  # every pixel changed
    n = {"id": "n-0001", "version": 1, "time": {"t": 1.0}, "ask": "longer", "resolution": {"outcome": "resolved", "said": "held it 1 s longer"}}
    m = review.measure_moment(n, "drafts/v1/p-vertical-v1.mp4", "drafts/v2/p-vertical-v2.mp4")
    assert m["changes"].get("pixels") and m["verdict"] == "unmeasured" and not feedback.verified(m)
    assert m["why"] == "asked longer, and this note's measurement can't see time"
    assert review.describe_measured(m).startswith("its pixels changed")  # what it did see stays in the evidence
    # the same with no element map: a target's old place changing color doesn't show it got bigger
    tn = answered(ask="bigger")
    tn["time"] = {"t": 1.0}
    m = review.measure_note(tn, "drafts/v1/p-vertical-v1.mp4", "drafts/v2/p-vertical-v2.mp4", None, [108, 192], None)
    assert m["basis"] == "pixels" and m["verdict"] == "unmeasured" and "can't see size" in m["why"]
    # nothing asked and nothing expected: any measured change counts, and the record says that's all it is
    m = review.measure_moment({**n, "ask": None}, "drafts/v1/p-vertical-v1.mp4", "drafts/v2/p-vertical-v2.mp4")
    assert m["verdict"] == "changed" and m["strength"] == "any"


def test_less_busy_is_measured_by_a_stand_in_and_says_so():
    items = [("s01/label", "OLD", [[1.0, 3.0]], [[1.0, 0.1, 0.1, 0.3, 0.2]])]
    m = review.measure(answered(ask="simpler", visible=["s01/label", "s01/a", "s01/b"]), emap(*items), [1000, 2000])
    assert m["verdict"] == "changed" and m["strength"] == "proxy"
    m = review.measure(answered(ask="bigger"), emap(("s01/label", "OLD", [[1.0, 3.0]], [[1.0, 0.05, 0.05, 0.35, 0.25]])), [1000, 2000])
    assert m["verdict"] == "changed" and m["strength"] == "direct"
    assert feedback.strength("simpler", None, "unmeasured") is None  # no verdict to back, no strength
    assert set(feedback.STRENGTH) == {"direct", "proxy", "any"} and feedback.PROXY <= set(feedback.DIMS)


def test_the_human_may_accept_over_the_measurement_and_it_is_kept(proj, studio):
    """Implemented, verified and accepted stay three facts: the human's eyes outrank the instrument, and the record keeps
    the verdict they accepted over (the page says so, the report counts it, the studio line carries it)."""
    opened()
    review.append([note(target=dict(TARGET), ask="bigger"), note(1.0, target=dict(TARGET), ask="bigger"), {"type": "round.sent"}], H)
    review.append([{"type": "note.resolved", "id": i, "said": "bigger", "outcome": "resolved", "tags": ["type.size"]} for i in ("n-0001", "n-0002")]
                  + [{"type": "note.measured", "id": "n-0001", "measured": {"verdict": "unchanged", "flag": "nothing measurable changed", "changes": {}, "from": 1, "to": 2}},
                     {"type": "note.measured", "id": "n-0002", "measured": {"verdict": "changed", "flag": None, "changes": {"size": 0.4}, "from": 1, "to": 2}}], A)
    review.append([{"type": "note.accepted", "id": "n-0001"}, {"type": "note.accepted", "id": "n-0002"}], H)
    S = review.state()
    assert S["notes"]["n-0001"]["accepted"]["verdict"] == "unchanged"
    recs = {r["id"]: r for r in json.loads(cmd("status", "--json").stdout)["records"]}
    r1, r2 = recs["n-0001"], recs["n-0002"]
    assert (r1["implemented"], r1["verified"], r1["accepted"], r1["accepted_over"]) == (True, False, True, "unchanged")
    assert (r2["verified"], r2["accepted"], r2["accepted_over"]) == (True, True, None)
    lines = [json.loads(l) for l in open(studio / "feedback.jsonl")]
    assert [x.get("verdict") for x in lines if x["kind"] == "note"] == ["unchanged", "changed"]
    assert "accepted over the measurement (no change measured)" in cmd("show", "n-0001").stdout
    assert re.search(r"accepted over the measurement\s+1\b", cmd("report").stdout)


def test_a_note_that_cant_be_measured_says_so(proj):
    """No element map, no cues: the round says "not measured" and why, instead of nothing (which read as no news)."""
    video(proj / "drafts/v2/p-vertical-v2.mp4")
    (proj / "drafts/v2/data/vertical/timeline.json").write_text(json.dumps({"fingerprint": "fp2", "end": 2.0}))
    opened()
    review.append([note(sound={"el": "sfx/tick1@s01", "t": 1.0, "sound": "tick1", "db": -12, "ask": "quieter"}, target={"el": "sfx/tick1@s01"}),
                   note(1.0, target=dict(TARGET)), {"type": "round.sent"}], H)
    review.append([{"type": "note.resolved", "id": i, "said": "done", "outcome": "resolved"} for i in ("n-0001", "n-0002")], A)
    r = cmd("open", "--video", "drafts/v2/p-vertical-v2.mp4")
    assert r.returncode == 0, r.stderr
    S = review.state()
    m1, m2 = S["notes"]["n-0001"]["measured"], S["notes"]["n-0002"]["measured"]
    # (before verdicts, a version with no cues yet read as "the sound is gone, but the answer didn't say --removed")
    assert m1["verdict"] == "unmeasured" and "vs mix" in m1["why"]
    # no element map: the target's old place is compared pixel by pixel (both renders are the same flat gray)
    assert m2["basis"] == "pixels" and m2["verdict"] == "unchanged" and not feedback.verified(m2)
    out = cmd("show").stdout
    assert "not measured: no sound cues" in out and "[no change measured]" in out


# ── the hand-off: conversation → the page → conversation, decided from the diary alone ──
def test_the_turn_moves_between_agent_page_and_agent_again(proj):
    who = lambda: json.loads(cmd("status", "--json").stdout)["turn"]
    assert who() == "agent"  # nothing in review yet
    opened()
    assert who() == "human"  # the page holds the turn
    review.append([{**note(), "held": True}], H)
    st = json.loads(cmd("status", "--json").stdout)
    assert st["turn"] == "human" and "not sent" in st["why"]
    review.append([{"type": "round.sent"}], H)
    assert who() == "returned"  # structured intent is back, unread
    cmd("show")
    assert who() == "agent"  # read: the agent owes n-0001
    review.append([{"type": "note.resolved", "id": "n-0001", "said": "done", "outcome": "resolved"}], A)
    assert who() == "agent"  # answered: the next version is the agent's work


def test_the_review_may_end_only_when_every_exit_check_holds(proj):
    opened()
    r = cmd("status", "--ready")
    assert r.returncode == 1 and "the person approved v1" in r.stderr
    review.append([note(), {"type": "version.approved", "version": 1, "cut": "9x16", "video": "drafts/v1/p-vertical-v1.mp4"}, {"type": "round.sent"}], H)
    r = cmd("status", "--ready")
    assert r.returncode == 1 and "everything they sent has been read" in r.stderr
    cmd("show")
    r = cmd("status", "--ready")
    assert r.returncode == 1 and "every note answered (owed: n-0001)" in r.stderr  # approved, but a note is still owed
    review.append([{"type": "note.resolved", "id": "n-0001", "said": "done", "outcome": "resolved"}], A)
    assert cmd("status", "--ready").returncode == 0
    st = json.loads(cmd("status", "--json").stdout)
    assert st["exit"]["ready"] and st["turn"] == "agent"
    # not a gate, but said out loud: the fix hasn't been measured yet, so nothing claims it's verified
    assert st["records"][0]["implemented"] and not st["records"][0]["verified"] and st["records"][0]["phase"] == "verification"


def test_a_wait_hands_control_back_the_moment_the_human_sends(proj):
    opened()
    p = subprocess.Popen([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", ".", "review", "wait", "--hours", "0.02"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for _ in range(50):
            if os.path.exists("review/waiting.json"):
                break
            time.sleep(0.1)
        assert json.loads(cmd("status", "--json").stdout)["waiting"] is True
        review.append([note(), {"type": "round.sent"}], H)
        out, _ = p.communicate(timeout=30)
    finally:
        p.kill()
        p.wait()
    assert p.returncode == 0 and "sent: round 1" in out and "too small" in out
    assert json.loads(cmd("status", "--json").stdout)["turn"] == "agent"  # the wait read it: the agent's move


# ── learning: counted by code, worded by the agent, decided by the human, written by the tooling ──
def lesson(proj, tag="pacing.reveal", text="Reveal one thing at a time"):
    opened()
    for t in (1.0, 1.1, 1.2):
        S, new = review.append([note(t)], H)
        nid = new[0]["note"]["id"]
        if review.current(S)["status"] == "open":
            review.append([{"type": "round.sent"}], H)
        review.append([{"type": "note.resolved", "id": nid, "said": "done", "outcome": "resolved", "tags": [tag]}], A)
        review.append([{"type": "note.accepted", "id": nid}], H)
    assert cmd("propose", tag, text).returncode == 0
    return "l-0001"


def test_a_rule_is_written_only_after_the_human_decides(proj, studio):
    before = (studio / "lessons.md").read_text()
    lid = lesson(proj)
    r = cmd("promote", lid)
    assert r.returncode and "waits for the human" in r.stderr and (studio / "lessons.md").read_text() == before
    with pytest.raises(review.Refused, match="written by the human"):  # the agent can't decide for them
        review.append([{"type": "lesson.decided", "id": lid, "decision": "remember"}], A)
    review.append([{"type": "lesson.decided", "id": lid, "decision": "remember"}], H)
    r = cmd("promote", lid)
    assert r.returncode == 0, r.stderr
    doc = (studio / "lessons.md").read_text()
    pic = doc.split("## Picture")[1].split("## Sound")[0]
    assert "- Reveal one thing at a time (" in pic and "<!-- rule p/l-0001 -->" in pic and "an older rule" in pic
    assert "already in lessons.md" in cmd("promote", lid).stderr  # once
    ln = [json.loads(l) for l in open(studio / "feedback.jsonl")][-1]
    assert ln["kind"] == "rule" and ln["action"] == "promoted" and ln["scope"] == "studio" and ln["via"] == "page"
    assert "p/l-0001  every video · pacing.reveal · Picture" in cmd("rules").stdout


def test_ignore_and_this_video_only_never_reach_the_studio(proj, studio):
    before = (studio / "lessons.md").read_text()
    lid = lesson(proj)
    review.append([{"type": "lesson.decided", "id": lid, "decision": "project"}], H)
    r = cmd("promote", lid)
    assert r.returncode and "this video only" in r.stderr and (studio / "lessons.md").read_text() == before
    assert any(x["from"] == lid for x in review.project_rules(review.state()))  # it lives in the project instead
    assert "this video's rules" in cmd("show").stdout


def test_a_note_for_the_whole_video_stays_a_project_rule(proj, studio):
    opened()
    review.append([note(ask="bigger", scope="project", comment="every label this size"), {"type": "round.sent"}], H)
    review.append([{"type": "note.resolved", "id": "n-0001", "said": "all labels bigger", "outcome": "resolved", "tags": ["type.size"]}], A)
    assert review.project_rules(review.state()) == []  # not until it's accepted
    review.append([{"type": "note.accepted", "id": "n-0001"}], H)
    assert [r["from"] for r in review.project_rules(review.state())] == ["n-0001"]
    assert review.candidates() == []  # one note "for this video" is not a pattern for every video
    assert "rule" not in (studio / "lessons.md").read_text().lower().replace("an older rule", "")


def test_a_note_for_every_video_is_put_to_the_human_at_once(proj, studio):
    opened()
    review.append([note(scope="studio", comment="never put words under a moving shape"), {"type": "round.sent"}], H)
    review.append([{"type": "note.resolved", "id": "n-0001", "said": "moved", "outcome": "resolved", "tags": ["layout.overlap"]}], A)
    assert review.candidates() == []  # accepted first
    review.append([{"type": "note.accepted", "id": "n-0001"}], H)
    c = review.candidates()
    assert [x["tag"] for x in c] == ["layout.overlap"] and c[0]["asked"] and c[0]["count"] == 1
    assert (studio / "lessons.md").read_text().count("<!-- rule") == 0  # a candidate, never a rule by itself


def test_a_rule_for_one_kind_and_a_profile_value_can_be_taken_back(proj, studio):
    lid = lesson(proj, "audio.music-level", "Music sits a little lower under the voice")
    review.append([{"type": "lesson.decided", "id": lid, "decision": "kind"}], H)
    assert cmd("promote", lid, "--set", "mix.music_db=-18").returncode == 0
    doc = (studio / "lessons.md").read_text()
    assert "- (reels only) Music sits a little lower under the voice (profile: mix.music_db = -18)" in doc
    assert json.loads((studio / "profile.json").read_text())["mix"]["music_db"] == -18
    lines = [json.loads(l) for l in open(studio / "feedback.jsonl")]
    tags = lambda proj_, kind: [x["tag"] for x in feedback.patterns(lines, proj_, kind)]
    assert "audio.music-level" not in tags("another-reel", "reel")  # a rule for every reel already
    assert "audio.music-level" in tags("an-explainer", "explainer")  # explainers were never asked
    r = cmd("forget", lid)
    assert r.returncode == 0 and "back to -16" in r.stdout
    assert "<!-- rule p/l-0001 -->" not in (studio / "lessons.md").read_text()
    assert json.loads((studio / "profile.json").read_text())["mix"]["music_db"] == -16
    assert cmd("rules").stdout.startswith("no rules promoted")
    lines = [json.loads(l) for l in open(studio / "feedback.jsonl")]
    assert all(x["tag"] != "audio.music-level" for x in feedback.patterns(lines, "p", "reel"))  # forgotten: not asked again


def test_a_decision_made_in_chat_keeps_the_humans_words(proj, studio):
    lid = lesson(proj)
    assert "own words" in cmd("promote", lid, "--chat", " ", "--as", "remember").stderr
    r = cmd("promote", lid, "--chat", "yes, remember that one", "--as", "remember")
    assert r.returncode == 0, r.stderr
    lz = review.state()["lessons"][lid]
    assert lz["decision"] == "remember" and lz["via"] == "chat" and lz["said"] == "yes, remember that one"
    assert lz["recorded_by"] == "agent"  # the human decided; the agent wrote it down, and the record says which
    decided = [x for x in map(json.loads, open(studio / "feedback.jsonl")) if x["kind"] == "lesson"][-1]
    assert (decided["via"], decided["said"], decided["recorded_by"]) == ("chat", "yes, remember that one", "agent")
    assert "(in chat: “yes, remember that one”)" in "".join(s["text"] for s in review.state("human")["steps"])
    # a chat decision with no words of theirs is refused in the diary itself, not only by the command
    lid2 = review.append([{"type": "lesson.proposed", "lesson": {"tag": "type.size", "text": "bigger labels", "dest": "lessons"}}], A)[1][0]["lesson"]["id"]
    with pytest.raises(review.Refused, match="own words"):
        review.append([{"type": "lesson.decided", "id": lid2, "decision": "remember", "via": "chat"}], H)


def test_vs_learn_never_turns_notes_into_rules():
    src = open(os.path.join(ENGINE, "py/learn.py")).read()
    assert "add this video's notes to lessons.md" not in src and "vs review promote" in src
    tmpl = open(os.path.join(KIT, "templates/studio/lessons.md")).read()
    assert "after each round of notes, one line per note" not in tmpl and "vs review promote" in tmpl


# ── one protocol, every skill ──
SKILLS = ["explainer-video", "sizzle-reel"]


def test_every_skill_defers_to_the_one_review_protocol():
    proto = open(os.path.join(ENGINE, "protocol/review.md")).read()
    cmds = set(re.findall(r'sub\.add_parser\("([a-z]+)"', open(os.path.join(ENGINE, "py/review.py")).read())) - {"serve"}
    missing = [c for c in sorted(cmds) if f"vs review {c}" not in proto]
    assert not missing, f"the protocol doesn't say when to use: {missing}"
    for s in SKILLS:
        md = open(os.path.join(KIT, "skills", s, "SKILL.md")).read()
        assert "vs protocol review" in md and "vs review status --ready" in md, s
        # the loop's rules live in the protocol only: a skill that restates them drifts (the reel skill once still told
        # the human to type "sent", after the page learned to wake the agent itself)
        for drift in ('say "sent"', "Approve & send", "No notes · send", "--advice leave|fix", "Remember, This video only"):
            assert drift not in md, f"{s} restates the review loop ({drift!r}): it belongs in engine/protocol/review.md"
        for c in set(re.findall(r"vs review ([a-z]+)", md)):
            assert c in cmds, f"{s} names vs review {c}, which doesn't exist"
        # the file path is the kit's (engine/protocol/files.md): every skill points at it and its four moves, and none
        # files a final or names a render by hand (a reviewer, Oct 8, 2026: a widescreen filed under the vertical's name)
        for must in ("vs protocol files", "vs status", "vs shape", "vs finish", "vs reopen"):
            assert must in md, f"{s} doesn't say {must!r}"
        for drift in ("vs learn --final", "vs review finish --final", "out/", "-16x9"):
            assert drift not in md, f"{s} still names the older layout ({drift!r})"


def test_vs_test_runs_only_the_file_it_is_given():
    """A focused run used to be appended to the whole suite, so one file ran every test (and looked like a hang)."""
    me = os.path.join(KIT, "tests/unit/test_feedback_protocol.py") + "::test_judge_rules_hold_on_their_own"
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "test", me], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and re.search(r"\b1 passed\b", r.stdout), r.stdout[-800:] + r.stderr[-800:]


def test_vs_protocol_prints_the_shared_rules():
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "protocol"], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.startswith("# The review protocol")
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "protocol", "studio"], capture_output=True, text=True)
    assert "Where a new piece of information goes" in r.stdout
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "protocol", "nope"], capture_output=True, text=True)
    assert r.returncode and "review, studio" in r.stderr


def test_the_new_fields_meet_the_review_schema(proj, studio):
    lid = lesson(proj)
    review.append([{"type": "lesson.decided", "id": lid, "decision": "kind"}], H)
    review.append([{**note(1.0, target=dict(TARGET), ask="bigger", scope="studio"), "held": True}, {"type": "round.sent"}], H)
    review.append([{"type": "note.resolved", "id": "n-0004", "said": "bigger", "outcome": "resolved", "expect": "size"},
                   {"type": "note.measured", "id": "n-0004", "measured": {"verdict": "contrary", "flag": "asked bigger; measured the other way",
                                                                          "changes": {"size": -0.3}, "from": 1, "to": 2}}], A)
    r = vs(proj, "check")
    assert "review/state.json" not in r.stdout, r.stdout
