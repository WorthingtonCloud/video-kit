"""Review Studio's server and diary (engine/py/review.py, review_server.py): the rules a round follows, one writer at a
time, the stills, and a server that only its own page can write to."""
import json, os, subprocess, sys, threading, urllib.error, urllib.request
import pytest
from conftest import ENGINE, vs

sys.path.insert(0, os.path.join(ENGINE, "py"))
import review  # noqa: E402

H, A = "human", "agent"


def video(path, secs=2.0, size="108x192"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x202020:s={size}:d={secs}:r=30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


@pytest.fixture
def proj(tmp_path, monkeypatch):
    d = tmp_path / "p"
    d.mkdir()
    (d / "reel.json").write_text("{}")
    video(d / "out/p-v1.mp4")
    (d / "out/p-v1.timeline.json").write_text(json.dumps({"fingerprint": "fp1", "end": 2.0}))
    monkeypatch.chdir(d)
    return d


def opened(video="out/p-v1.mp4", version=1):
    return review.append([{"type": "round.opened", "version": version, "cut": "9x16", "video": video}], A)


def note(t=1.0, **kw):
    return {"type": "note.added", "note": {"time": {"t": t}, "comment": "too fast", **kw}}


# ── the rules ──
def test_a_round_from_open_to_accepted(proj):
    opened()
    S, new = review.append([note(), note(0.5)], H)
    assert [e["note"]["id"] for e in new] == ["n-0001", "n-0002"] and S["notes"]["n-0001"]["status"] == "draft"
    S, _ = review.append([{"type": "round.sent"}], H)
    assert S["rounds"][0]["status"] == "sent" and {n["status"] for n in S["notes"].values()} == {"sent"}
    review.append([{"type": "note.question", "id": "n-0001", "text": "which word?"}], A)
    S, _ = review.append([{"type": "note.answered", "id": "n-0001", "text": "the number"}], H)
    assert S["notes"]["n-0001"]["status"] == "sent" and [h["type"] for h in S["notes"]["n-0001"]["thread"]] == ["question", "answer"]
    review.append([{"type": "note.resolved", "id": "n-0001", "said": "slower", "outcome": "resolved"},
                   {"type": "note.resolved", "id": "n-0002", "said": "it's the beat", "outcome": "wontdo"}], A)
    S, _ = review.append([{"type": "note.accepted", "id": "n-0001"}, {"type": "note.reopened", "id": "n-0002", "text": "still"}], H)
    assert S["notes"]["n-0001"]["status"] == "accepted" and S["notes"]["n-0002"]["status"] == "reopened"
    # a reopened note is owed an answer before the next round
    with pytest.raises(review.Refused, match="answer every note first: n-0002"):
        opened("out/p-v2.mp4", 2)


# ── the loop: feedback waits (held, undoable) until the human sends it; the agent sees only what was sent ──
def held(e):
    return {**e, "held": True}


def test_held_feedback_waits_for_the_send_and_the_agent_sees_only_what_was_sent(proj):
    opened()
    H1, new = review.append([held(note())], H)
    assert H1["notes"]["n-0001"]["status"] == "draft" and H1["pending"] == [2]
    assert H1["steps"][-1]["pending"] and H1["steps"][-1]["text"].startswith("Note at 0:01.0")
    assert "n-0001" not in review.state()["notes"]  # the agent's view: nothing until it's sent
    assert json.load(open("review/state.json"))["notes"] == {}
    review.append([{"type": "round.sent"}], H)
    S = review.state()
    assert S["notes"]["n-0001"]["status"] == "sent" and S["rounds"][0]["sends"] == 1 and review.state("human")["pending"] == []
    # after the send, a new note waits for its own send (it used to go straight to the agent)
    review.append([held(note(0.5))], H)
    assert "n-0002" not in review.state()["notes"] and review.state("human")["notes"]["n-0002"]["status"] == "draft"
    S, _ = review.append([{"type": "round.sent"}], H)
    assert S["notes"]["n-0002"]["status"] == "sent" and S["rounds"][0]["sends"] == 2
    assert [s["text"] for s in S["steps"] if s["kind"] == "round.sent"] == ["Sent round 1 (1 thing)", "Sent more to round 1 (1 thing)"]
    with pytest.raises(review.Refused, match="nothing new has been added"):
        review.append([{"type": "round.sent"}], H)
    with pytest.raises(review.Refused, match="only the human's feedback"):
        review.append([held({"type": "note.question", "id": "n-0001", "text": "?"})], A)


def test_undo_takes_back_held_feedback_and_what_depends_on_it(proj):
    opened()
    review.append([held(note())], H)  # line 2
    review.append([held({"type": "note.edited", "id": "n-0001", "comment": "faster"})], H)  # line 3
    Hv, new = review.append([{"type": "undo", "of": 2}], H)
    assert [e["type"] for e in new] == ["undo", "undo"] and new[1]["of"] == 3 and new[1]["cascade"]  # the edit went too
    assert Hv["notes"] == {} and Hv["pending"] == []
    _, new = review.append([held(note(0.5))], H)
    assert new[0]["note"]["id"] == "n-0002"  # an undone note's id is never given again
    with pytest.raises(review.Refused, match="already undone"):
        review.append([{"type": "undo", "of": 2}], H)
    with pytest.raises(review.Refused, match="can't be undone"):
        review.append([{"type": "undo", "of": 1}], H)  # the agent's round.opened
    review.append([{"type": "round.sent"}], H)
    with pytest.raises(review.Refused, match="already sent"):
        review.append([{"type": "undo", "of": 6}], H)


def test_a_round_waits_for_the_humans_unsent_feedback(proj):
    opened()
    review.append([held(note()), {"type": "round.sent"}], H)
    review.append([held({"type": "finding.dismissed", "id": "q-covered-top-1"})], H)
    with pytest.raises(review.Refused, match="haven't sent"):
        opened("out/p-v1.mp4", 2)


def test_a_held_mix_reaches_mix_json_when_its_sent(proj):
    opened()
    mix = {"take": 2, "music_db": -18, "duck_db": 9, "sfx_db": 0, "fx_on": True, "summary": "take 2, 22 dB under"}
    review.append([held({"type": "mix.saved", "mix": mix})], H)
    assert not os.path.exists("mix.json") and review.state()["mix"] is None
    assert review.state("human")["mix"]["duck_db"] == 9
    review.append([{"type": "round.sent"}], H)
    assert json.load(open("mix.json")) == mix and review.state()["mix"]["take"] == 2


def test_findings_get_claudes_advice_and_the_report_counts_it_taken(proj):
    os.makedirs("out/p-v1.review")
    json.dump({"items": [{"id": f"q-covered-top-{t}", "check": "covered", "severity": "warning", "elements": [], "t0": t, "t1": t + .25}
                         for t in (0.5, 1.5)]}, open("out/p-v1.review/qa.json", "w"))
    opened()
    assert "no 'flash' findings" in cmd("advise", "--check", "flash", "--advice", "leave", "--plain", "x").stderr
    r = cmd("advise", "--check", "covered", "--advice", "leave", "--plain", "a phone's clock bar sits there", "--why", "it's decoration")
    assert r.returncode == 0 and "advised leave on 2" in r.stdout
    S = review.state()
    assert S["advice"]["q-covered-top-0.5"]["advice"] == "leave" and S["advice"]["q-covered-top-1.5"]["check"] == "covered"
    review.append([held({"type": "finding.dismissed", "id": "q-covered-top-0.5"}), held({"type": "finding.confirmed", "id": "q-covered-top-1.5"}),
                   {"type": "round.sent"}], H)
    S = review.state()
    assert S["findings"]["q-covered-top-0.5"]["followed"] is True and S["findings"]["q-covered-top-1.5"]["followed"] is False
    assert S["findings"]["q-covered-top-0.5"]["check"] == "covered"
    assert "…decided with Claude's advice taken              1 of 2 advised" in cmd("report").stdout
    assert "leave it dismissed q-covered-top-0.5 (your advice)" in cmd("show").stdout


def test_the_steps_have_stages_and_a_note_can_be_about_one(proj):
    assert cmd("step", "Okayed the outline", "--stage", "story", "--when", "2020-01-01T20:20").returncode == 0
    assert cmd("step", "--stage", "nonsense").returncode != 0
    review.append([{"type": "round.opened", "version": 1, "cut": "9x16", "video": "out/p-v1.mp4", "stage": "picture"}], A)
    S, _ = review.append([held(note(0.2)), held({"type": "version.approved", "version": 1, "cut": "9x16", "video": "out/p-v1.mp4"})], H)
    st = S["steps"]
    assert [(s["text"], s["stage"]) for s in st[:2]] == [("Okayed the outline", "story"), ("Round 1 opened on v1", "picture")]
    assert st[-1]["text"] == "Approved v1: it's done" and st[-1]["pending"] and S["stage"] == "picture"
    first = st[0]["seq"]
    review.append([held(note(0.3, comment="revisit this", step={"seq": first, "text": "Okayed the outline"})), {"type": "round.sent"}], H)
    out = cmd("show").stdout
    assert "about their step: Okayed the outline" in out
    R = review.state()["rounds"][0]
    assert R["read_sends"] == R["sends"] == 1  # reading what was sent tells the page Claude has it
    n = review.state()["events"]
    cmd("show")
    assert review.state()["events"] == n  # read once, not again


@pytest.mark.parametrize("events, by, why", [
    ([note()], H, "no round is open"),
    ([{"type": "round.opened", "version": 1, "video": "x"}], H, "written by the agent"),
    ([{"type": "note.accepted", "id": "n-0001"}], A, "written by the human"),
    ([{"type": "note.zapped"}], H, "unknown event type"),
    ([{"type": "round.nonotes"}], H, "no round is open"),
    ([{"type": "project.finished", "files": []}], H, "written by the agent"),
    ([{"type": "finding.carried", "id": "q-covered-left-1", "status": "dismissed"}], H, "written by the agent"),
    ([{"type": "finding.carried", "id": "q-covered-left-1", "status": "maybe"}], A, "needs its id and the earlier answer"),
])
def test_writes_the_rules_refuse(proj, events, by, why):
    with pytest.raises(review.Refused, match=why):
        review.append(events, by)


def test_what_a_note_must_carry_and_when_it_can_change(proj):
    opened()
    with pytest.raises(review.Refused, match="needs its moment"):
        review.append([{"type": "note.added", "note": {"comment": "x"}}], H)
    with pytest.raises(review.Refused, match="ends after it starts"):
        review.append([{"type": "note.added", "note": {"time": {"t0": 3, "t1": 2}, "comment": "x"}}], H)
    with pytest.raises(review.Refused, match="isn't one of"):
        review.append([note(mark={"type": "circle"})], H)
    with pytest.raises(review.Refused, match="words, a target or a mark"):
        review.append([{"type": "note.added", "note": {"time": {"t": 1}, "comment": "  "}}], H)
    review.append([note()], H)
    with pytest.raises(review.Refused, match="is draft: it can't be accepted"):
        review.append([{"type": "note.accepted", "id": "n-0001"}], H)
    review.append([{"type": "round.sent"}], H)
    with pytest.raises(review.Refused, match="is sent: it can't be edited"):
        review.append([{"type": "note.edited", "id": "n-0001", "comment": "y"}], H)
    S, _ = review.append([note(1.5)], H)  # after Send: straight to the agent
    assert S["notes"]["n-0002"]["status"] == "sent" and S["notes"]["n-0002"]["late"]
    with pytest.raises(review.Refused, match="already open|answer every note"):
        opened()


def test_a_batch_is_all_or_nothing(proj):
    opened()
    with pytest.raises(review.Refused):
        review.append([note(), {"type": "note.accepted", "id": "n-0001"}], H)
    assert len(review.read_log()) == 1 and review.state()["notes"] == {}


def test_the_snapshot_is_always_the_log_folded(proj):
    opened()
    review.append([note(), note(0.2), {"type": "note.withdrawn", "id": "n-0001"}, {"type": "round.sent"}], H)
    review.append([{"type": "finding.dismissed", "id": "f-covers-a-x-b", "reason": "by design"}], H)
    S = json.load(open(review.STATE))
    assert S == review.fold(review.read_log()) and S["events"] == 6
    # the render gate reads exactly this (engine/js/pipeline/gate.mjs)
    assert S["findings"]["f-covers-a-x-b"]["status"] == "dismissed"


def test_two_writers_at_once_lose_nothing(proj):
    opened()
    errs = []

    def add(k):
        try:
            for i in range(10):
                review.append([note(k + i / 100)], H)
        except Exception as e:  # pragma: no cover
            errs.append(e)
    ts = [threading.Thread(target=add, args=(k,)) for k in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    S = review.state()
    assert not errs and len(S["notes"]) == 40 and S["events"] == 41 == len(review.read_log())
    assert sorted(S["notes"]) == [f"n-{i:04d}" for i in range(1, 41)]


def test_a_hand_edited_line_is_named(proj):
    opened()
    with open(review.LOG, "a") as f:
        f.write("{oops\n")
    with pytest.raises(SystemExit, match="line 2 isn't JSON"):
        review.read_log()


# ── stills ──
def test_a_still_shows_the_target_and_the_mark(proj):
    import numpy as np
    opened()
    S, new = review.append([note(1.0, target={"el": "s01/card", "box": [0.2, 0.2, 0.6, 0.4]},
                                 mark={"type": "arrow", "from": [0.4, 0.3], "to": [0.4, 0.8]},
                                 also=[{"type": "keep-clear", "box": [0.1, 0.85, 0.9, 0.95]}])], H)
    review.frames_for(S, new)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "review/frames/n-0001.jpg", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    img = np.frombuffer(raw, np.uint8).reshape(192, 108, 3).astype(int)
    red = lambda p: p[0] > 180 and p[1] < 110 and p[2] < 100
    assert red(img[int(0.2 * 192), int(0.4 * 108)])          # the target's top edge
    assert red(img[int(0.6 * 192), int(0.4 * 108)])          # the arrow's shaft
    assert img[int(0.9 * 192), 54][0] > img[int(0.9 * 192), 54][2] + 30 or img[int(0.9 * 192), 56][0] > 120  # amber stripes
    assert not red(img[int(0.75 * 192), int(0.8 * 108)])     # nothing drawn elsewhere


def test_a_range_gets_its_start_middle_and_end(proj):
    opened()
    S, new = review.append([{"type": "note.added", "note": {"time": {"t0": 0.2, "t1": 1.8}, "comment": "drags"}}], H)
    review.frames_for(S, new)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                          "review/frames/n-0001.jpg"], capture_output=True, text=True).stdout.strip()
    assert out == "162,96"  # three frames, half size, side by side


# ── the agent's commands ──
def test_open_refuses_a_version_with_open_errors(proj):
    os.makedirs("build")
    json.dump({"fingerprint": "fp1", "items": [{"id": "f-covers-a-x-b", "severity": "error", "check": "covers",
                                               "elements": ["s01/a", "s01/b"], "t0": 0.4}]}, open("build/findings.json", "w"))
    r = vs(proj, "review", "open")
    assert r.returncode and "errors never reach a round" in r.stderr and "covers s01/a × s01/b at 0.4s" in r.stderr
    r = vs(proj, "review", "open", "--ask")
    assert r.returncode == 0 and "1 finding(s) put to the human" in r.stdout
    assert review.state()["rounds"][0]["asked"] == ["f-covers-a-x-b"]


def test_a_finding_dismissed_in_review_no_longer_blocks(proj):
    os.makedirs("build")
    json.dump({"fingerprint": "fp1", "items": [{"id": "f-x", "severity": "error", "check": "covers", "elements": ["a"], "t0": 0}]},
              open("build/findings.json", "w"))
    review.append([{"type": "finding.dismissed", "id": "f-x", "reason": "by design"}], H)
    assert vs(proj, "review", "open").returncode == 0


def test_resolve_accounts_for_a_target_that_is_gone(proj):
    opened()
    review.append([note(target={"el": "s01/old-label", "box": [0, 0, .1, .1]}), {"type": "round.sent"}], H)
    os.makedirs("build")
    json.dump({"items": [{"id": "s01/new-label"}]}, open("build/elements.json", "w"))
    r = vs(proj, "review", "resolve", "n-0001", "--said", "moved")
    assert r.returncode and "isn't in the build any more" in r.stderr
    r = vs(proj, "review", "resolve", "n-0001", "--said", "moved", "--renamed", "s01/new-label")
    assert r.returncode == 0 and review.state()["notes"]["n-0001"]["resolution"]["renamed"] == "s01/new-label"
    out = vs(proj, "review", "show").stdout
    assert "n-0001" in out and "agent (resolved): moved" in out and "still: review/frames" not in out


def test_the_snapshot_meets_its_schema(proj):
    opened()
    review.append([note(mark={"type": "box", "box": [0, 0, .5, .5]}), {"type": "round.sent"}], H)
    review.append([{"type": "choice.offered", "choice": {"question": "q", "options": [{"id": "a"}, {"id": "b"}]}}], A)
    r = vs(proj, "check")
    assert "review/state.json" not in r.stdout, r.stdout


# ── carried answers, no notes, the end of the flow (a reviewer's notes, Oct 2: "Once it's been dispositioned, it shouldn't do
#    that"; "I should also be able to just indicate no notes"; "a more obvious ending to the flow") ──
def qa(version, *ids):
    os.makedirs(f"out/p-v{version}.review", exist_ok=True)
    json.dump({"items": [{"id": i, "check": i.split("-")[1], "severity": "warning", "elements": [],
                          "t0": review._fkey(i)[1], "t1": review._fkey(i)[1] + .25} for i in ids]}, open(f"out/p-v{version}.review/qa.json", "w"))


def next_version(version):
    video(f"out/p-v{version}.mp4")
    json.dump({"fingerprint": f"fp{version}", "end": 2.0}, open(f"out/p-v{version}.timeline.json", "w"))


@pytest.mark.parametrize("fid, key, t", [("q-covered-left-55", "q-covered-left", 55.0), ("q-covered-left-9.25", "q-covered-left", 9.25),
                                         ("f-spills-s03_hub-core", "f-spills-s03_hub-core", None)])
def test_a_finding_id_splits_into_what_and_when(fid, key, t):
    assert review._fkey(fid) == (key, t)


def test_an_answer_carries_to_the_same_finding_in_the_next_round(proj):
    qa(1, "q-covered-left-55", "q-covered-right-55")
    assert cmd("open").returncode == 0
    review.append([held({"type": "finding.dismissed", "id": "q-covered-left-55"}),
                   held({"type": "finding.confirmed", "id": "q-covered-right-55"}), {"type": "round.sent"}], H)
    # v2: the voice moved a second (54: the same finding), one moved too far to be the same (60), one is another place
    next_version(2)
    qa(2, "q-covered-left-54", "q-covered-left-60", "q-covered-top-55", "q-covered-right-56.5", "q-flash-55")
    r = cmd("open", "--video", "out/p-v2.mp4")
    assert r.returncode == 0 and "2 finding(s) answered in an earlier round" in r.stdout, r.stdout
    F = review.state()["findings"]
    assert F["q-covered-left-54"]["status"] == "dismissed" and F["q-covered-left-54"]["round"] == 2
    assert F["q-covered-left-54"]["carried"] == {"from": "q-covered-left-55", "round": 1}
    assert F["q-covered-right-56.5"]["status"] == "confirmed" and F["q-covered-right-56.5"]["carried"]["from"] == "q-covered-right-55"
    assert not {"q-covered-left-60", "q-covered-top-55", "q-flash-55"} & set(F)  # too far, another place, another check: asked
    assert "3 finding(s) for the human (covered, flash)" in r.stdout  # and the agent is told to advise those two
    assert "(carried from round 1)" in cmd("show").stdout
    # a carried answer goes on: v3 carries it from round 1 still (through round 2's carry)
    next_version(3)
    qa(3, "q-covered-left-53")
    assert cmd("open", "--video", "out/p-v3.mp4").returncode == 0
    assert review.state()["findings"]["q-covered-left-53"]["carried"]["round"] == 1


def test_the_humans_answer_this_round_wins_over_a_carried_one(proj):
    qa(1, "q-covered-left-55")
    cmd("open")
    review.append([held({"type": "finding.dismissed", "id": "q-covered-left-55"}), {"type": "round.sent"}], H)
    next_version(2)
    qa(2, "q-covered-left-54")
    cmd("open", "--video", "out/p-v2.mp4")
    S, _ = review.append([held({"type": "finding.confirmed", "id": "q-covered-left-54"}), {"type": "round.sent"}], H)
    d = review.state()["findings"]["q-covered-left-54"]
    assert d["status"] == "confirmed" and "carried" not in d
    assert review.carry_findings(review.state(), review.current(review.state())) == []  # nothing left to carry


def test_no_notes_is_a_send_that_says_so(proj):
    opened()
    Hv, _ = review.append([held({"type": "round.nonotes"})], H)
    assert Hv["pending"] and Hv["steps"][-1]["text"] == "No notes this round: nothing to change"
    assert not review.state()["rounds"][0].get("nonotes")  # held: the agent doesn't see it until the send
    S, _ = review.append([{"type": "round.sent"}], H)
    R = S["rounds"][0]
    assert R["status"] == "sent" and R["sends"] == 1 and R["nonotes"]
    assert "the human: no notes this round" in cmd("show").stdout
    assert "review/state.json" not in vs(proj, "check").stdout


def test_finish_records_the_finals_and_opens_a_final_round(proj):
    opened()
    assert "vs review finish --final" in cmd("finish", "--final", "out/nope.mp4").stderr
    for f in ("out/p-v1-take1.mp4", "out/p-16x9-v1-take1.mp4"):
        video(f)
    r = cmd("finish", "--final", "out/p-v1-take1.mp4", "out/p-16x9-v1-take1.mp4")
    assert r.returncode == 0 and "finished: p-v1-take1.mp4, p-16x9-v1-take1.mp4" in r.stdout, r.stderr
    S = review.state()
    R = review.current(S)
    assert R["video"] == "out/p-v1-take1.mp4" and R["stage"] == "final" and R["n"] == 2
    assert S["finished"]["files"] == [{"url": "/out/p-v1-take1.mp4", "name": "p-v1-take1.mp4", "cut": "9x16"},
                                      {"url": "/out/p-16x9-v1-take1.mp4", "name": "p-16x9-v1-take1.mp4", "cut": "16x9"}]
    assert S["finished"]["round"] == 2 and S["steps"][-1]["text"] == "Claude filed the finals: done"
    assert "review/state.json" not in vs(proj, "check").stdout
    # finishing again on the same final doesn't open another round
    assert cmd("finish", "--final", "out/p-v1-take1.mp4").returncode == 0 and len(review.state()["rounds"]) == 2


# ── the server ──
@pytest.fixture
def server(proj):
    import http.server, review_server
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), review_server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def call(url, body=None, headers=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def test_the_page_writes_the_humans_events_only(server, proj):
    opened()
    code, body, _ = call(f"{server}/review/api/events", {"events": [note()]})
    j = json.loads(body)
    assert code == 200 and j["ids"] == ["n-0001"] and j["context"]["round"]["video"] == "/out/p-v1.mp4"
    assert os.path.exists("review/frames/n-0001.jpg")
    code, body, _ = call(f"{server}/review/api/events", {"events": [{"type": "note.resolved", "id": "n-0001", "said": "x"}]})
    assert code == 403 and "can't write note.resolved" in json.loads(body)["error"]
    code, body, _ = call(f"{server}/review/api/events", {"events": [{"type": "note.accepted", "id": "n-0001"}]})
    assert code == 409 and "is draft" in json.loads(body)["error"]


def test_only_its_own_page_can_write(server, proj):
    opened()
    assert call(f"{server}/review/api/events", {"events": [note()]}, {"Content-Type": "text/plain"})[0] == 403
    assert call(f"{server}/review/api/events", {"events": [note()]}, {"Origin": "https://example.com"})[0] == 403
    assert call(f"{server}/review/api/state", headers={"Host": "rebound.example.com"})[0] == 403
    assert review.state()["notes"] == {}


def test_the_video_seeks_and_the_page_is_the_kits(server, proj):
    code, body, hd = call(f"{server}/out/p-v1.mp4", headers={"Range": "bytes=10-29"})
    assert code == 206 and len(body) == 20 and hd["Content-Range"].startswith("bytes 10-29/")
    assert body == open("out/p-v1.mp4", "rb").read()[10:30]
    code, body, _ = call(f"{server}/review/")
    assert code == 200 and b"Review Studio" in body
    # no way out of the page's folder into the engine's code
    assert call(f"{server}/review/%2e%2e/py/review.py")[0] == 404 and call(f"{server}/review/..%2fpy/review.py")[0] == 404


def test_the_mixers_save_still_lands_in_mix_json(server, proj):
    code, _, _ = call(f"{server}/mix.json", {"take": 2, "music_db": -18, "evil": 1})
    assert code == 200 and json.load(open("mix.json"))["take"] == 2 and "evil" not in json.load(open("mix.json"))
    assert review.state()["mix"]["music_db"] == -18


def test_the_page_finds_the_rounds_maps(proj):
    import review_server
    opened()
    os.makedirs("build/mix")
    os.makedirs("voice")
    json.dump({"fingerprint": "fp1", "end": 2.0}, open("build/timeline.json", "w"))
    json.dump({"fingerprint": "old", "items": []}, open("build/elements.json", "w"))
    json.dump([], open("build/mix/cues.json", "w"))
    json.dump([{"w": "Hi", "t0": 0.1, "t1": 0.3, "act": 1}], open("voice/w.words.json", "w"))
    json.dump({"words": "voice/w.words.json"}, open("plan.json", "w"))
    R = review_server.context(review.state())["round"]
    assert R["timeline"] == "/out/p-v1.timeline.json" and R["words"] == "/voice/w.words.json" and R["cues"] == "/build/mix/cues.json"
    # the build moved on since this version: its element map is offered, but not as exact
    assert R["elements"] == "/build/elements.json" and R["exact"] == {"timeline": True, "elements": False, "findings": False, "comp": False}


def test_vs_mixer_opens_review_studio_on_the_mix_panel(proj):
    import socket, time
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    p = subprocess.Popen([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(proj), "mixer", "--port", str(port)],
                         stdout=subprocess.PIPE, text=True)
    try:
        line = p.stdout.readline()
        assert f"http://localhost:{port}/review/#mix" in line
        for _ in range(30):
            try:
                code, body, _ = call(f"http://127.0.0.1:{port}/review/")
                break
            except OSError:
                time.sleep(0.1)
        assert code == 200 and b'id="sec-mix"' in body
    finally:
        p.terminate()
        p.wait()


# ── rounds: the answer's claim, measured ──
def emap(*items, fp="fp2"):
    return {"fingerprint": fp, "step": 0.15, "items": [{"id": i, "text": t, "on": on, "boxes": bx} for i, t, on, bx in items]}


def answered(**kw):
    n = {"id": "n-0001", "version": 1, "time": {"t": 2.0}, "target": {"el": "s01/label", "box": [0.1, 0.1, 0.3, 0.2],
         "text": "OLD", "on": [1.0, 3.0]}, "mark": {"type": "none"}, "also": [],
         "resolution": {"outcome": "resolved", "said": "moved it"}}
    n.update(kw)
    return n


def test_a_move_is_measured_in_pixels_of_the_new_frame():
    E = emap(("s01/label", "OLD", [[1.0, 3.0]], [[1.0, 0.2, 0.15, 0.4, 0.25]]))
    m = review.measure(answered(), E, [1000, 2000])
    assert (m["dx"], m["dy"], m["dw"], m["dh"]) == (100, 100, 0, 0) and m["flag"] is None
    assert review.describe_measured(m).startswith("moved 100 px right, 100 px down")


def test_a_claimed_fix_that_measures_as_nothing_is_flagged():
    E = emap(("s01/label", "OLD", [[1.0, 3.0]], [[1.0, 0.1, 0.1, 0.3, 0.2]]))
    m = review.measure(answered(), E, [1000, 2000])
    assert "nothing measurable changed" in m["flag"]
    assert review.measure(answered(resolution={"outcome": "wontdo", "said": "by design"}), E, [1000, 2000])["flag"] is None


def test_words_time_zones_and_the_arrow_count_as_change():
    E = emap(("s01/label", "NEW", [[1.5, 3.0]], [[1.0, 0.6, 0.6, 0.8, 0.7]]))
    n = answered(also=[{"type": "keep-clear", "box": [0, 0, 0.5, 0.5]}], mark={"type": "arrow", "from": [0.2, 0.15], "to": [0.7, 0.65]})
    m = review.measure(n, E, [1000, 1000])
    assert m["text"] == {"old": "OLD", "new": "NEW"} and m["span"] == {"old": [1.0, 3.0], "new": [1.5, 3.0]}
    assert m["keep_clear"] == [{"before": True, "after": False}] and m["arrow"]["after"] == 0 and m["arrow"]["before"] > 600
    d = review.describe_measured(m)
    assert "now clear of the keep-clear zone" in d and "0 px from where the arrow pointed" in d and m["flag"] is None


def test_a_target_gone_without_a_word_is_flagged_and_a_rename_is_followed():
    E = emap(("s01/new-label", "OLD", [[1.0, 3.0]], [[1.0, 0.1, 0.1, 0.3, 0.2]]))
    assert "--renamed or --removed" in review.measure(answered(), E, [100, 100])["flag"]
    assert review.measure(answered(resolution={"outcome": "resolved", "said": "x", "removed": True}), E, [100, 100])["flag"] is None
    m = review.measure(answered(resolution={"outcome": "resolved", "said": "renamed", "renamed": "s01/new-label"}), E, [100, 100])
    assert m["el"] == "s01/new-label" and m["flag"] is None  # a rename is an answer, even with nothing else changed


def test_opening_the_next_round_measures_every_answer(proj):
    video(proj / "out/p-v2.mp4")
    (proj / "out/p-v2.timeline.json").write_text(json.dumps({"fingerprint": "fp2", "end": 2.0}))
    os.makedirs("build")
    json.dump(emap(("s01/label", "OLD", [[0.0, 2.0]], [[0.0, 0.5, 0.1, 0.7, 0.2]])), open("build/elements.json", "w"))
    opened()
    review.append([note(1.0, target={"el": "s01/label", "box": [0.1, 0.1, 0.3, 0.2], "text": "OLD", "on": [0.0, 2.0]}),
                   {"type": "round.sent"}], H)
    assert vs(proj, "review", "resolve", "n-0001", "--said", "moved right").returncode == 0
    r = vs(proj, "review", "open", "--video", "out/p-v2.mp4")
    assert r.returncode == 0 and "n-0001 label: moved 43 px right" in r.stdout, r.stdout
    S = review.state()
    m = S["notes"]["n-0001"]["measured"]
    assert m["from"] == 1 and m["to"] == 2 and m["summary"].startswith("moved 43 px right") and S["rounds"][1]["video"] == "out/p-v2.mp4"
    assert "measured (v1 → v2): moved 43 px right" in vs(proj, "review", "show", "n-0001").stdout
    review.append([{"type": "version.approved", "version": 2, "cut": "9x16", "video": "out/p-v2.mp4"}], H)
    assert "✓ v2 (9x16) approved" in vs(proj, "review", "show").stdout


def av(path, color, beep):
    """2 s at 108x192: a box drawn in `color`, and a 440 Hz tone (with a 1 kHz beep from 0.8 to 1.2 s when `beep`)."""
    tone = "0.3*sin(2*PI*440*t)" + ("+if(between(t,0.8,1.2),0.6*sin(2*PI*1000*t),0)" if beep else "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x202020:s=108x192:d=2:r=30,drawbox=x=20:y=40:w=60:h=60:color={color}:t=fill",
                    "-f", "lavfi", "-i", f"aevalsrc='{tone}':s=44100:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(path)], check=True)


def test_a_color_change_and_a_change_in_the_sound_are_measured(proj):
    av(proj / "out/p-v1.mp4", "white", True)
    av(proj / "out/p-v2.mp4", "red", False)
    (proj / "out/p-v2.timeline.json").write_text(json.dumps({"fingerprint": "fp2", "end": 2.0}))
    box = [round(20 / 108, 4), round(40 / 192, 4), round(80 / 108, 4), round(100 / 192, 4)]
    os.makedirs("build")
    json.dump(emap(("s01/box", "", [[0.0, 2.0]], [[0.0, *box]])), open("build/elements.json", "w"))
    opened()
    review.append([note(1.0, target={"el": "s01/box", "box": box, "on": [0.0, 2.0]}, comment="red, please"),
                   note(1.0, comment="the beep is too loud"), {"type": "round.sent"}], H)
    for n in ("n-0001", "n-0002"):
        assert vs(proj, "review", "resolve", n, "--said", "done").returncode == 0
    r = vs(proj, "review", "open", "--video", "out/p-v2.mp4")
    assert r.returncode == 0, r.stderr
    S = review.state()
    m1, m2 = S["notes"]["n-0001"]["measured"], S["notes"]["n-0002"]["measured"]
    assert m1["flag"] is None and m1["pixels"]["changed"] > 0.5 and (m1["pixels"]["from"], m1["pixels"]["to"]) == ("white", "red")
    assert "mostly white → red" in m1["summary"]  # the box didn't move: its pixels said what changed
    assert m2["moment"] and m2["audio"]["changed_secs"] >= 0.2 and m2["flag"] is None
    assert "the sound around it changed" in m2["summary"]


def test_a_versions_own_maps_win_after_the_build_moves_on(proj):
    import review_server
    opened()
    os.makedirs("out/p-v1.review")
    os.makedirs("build")
    for f, fp in (("out/p-v1.review/timeline.json", "fp1"), ("build/timeline.json", "fp2")):
        json.dump({"fingerprint": fp, "end": 2.0}, open(f, "w"))
    json.dump({"fingerprint": "fp1", "items": []}, open("out/p-v1.review/elements.json", "w"))
    json.dump({"fingerprint": "fp2", "items": []}, open("build/elements.json", "w"))
    json.dump([], open("out/p-v1.review/cues.json", "w"))
    R = review_server.context(review.state())["round"]
    assert R["timeline"] == "/out/p-v1.review/timeline.json" and R["elements"] == "/out/p-v1.review/elements.json"
    assert R["cues"] == "/out/p-v1.review/cues.json" and R["comp"] is None
    assert R["exact"] == {"timeline": True, "elements": True, "findings": False, "comp": False}


# ── learning: counted by code, worded by the agent, decided by the human ──
@pytest.fixture
def studio(tmp_path, monkeypatch):
    s = tmp_path / "studio"
    s.mkdir()
    (s / "studio.json").write_text("{}")
    monkeypatch.setenv("VIDEO_STUDIO", str(s))
    return s


def accept_tagged(tags, t=1.0):
    S, new = review.append([note(t)], H)
    nid = new[0]["note"]["id"]
    review.append([{"type": "round.sent"}], H) if review.current(S)["status"] == "open" else None
    review.append([{"type": "note.resolved", "id": nid, "said": "done", "outcome": "resolved", "tags": tags}], A)
    review.append([{"type": "note.accepted", "id": nid}], H)
    return nid


def test_a_tag_must_be_on_the_list():
    with pytest.raises(review.Refused, match="did you mean 'pacing.reveal'"):
        review.check_tags(["pacing.reveel"])
    doc = review.__doc__
    assert all(t in doc for t in review.TAGS)  # vs help review lists every tag


def test_accepted_notes_go_to_the_studio_and_three_make_a_pattern(proj, studio):
    opened()
    accept_tagged(["pacing.reveal"])
    accept_tagged(["pacing.reveal", "copy.wording"], 1.2)
    lines = [json.loads(l) for l in open(studio / "feedback.jsonl")]
    assert [l["kind"] for l in lines] == ["note", "note"] and lines[1]["tags"] == ["pacing.reveal", "copy.wording"]
    assert review.candidates() == []  # twice in one video isn't a pattern yet
    accept_tagged(["pacing.reveal"], 1.4)
    c = review.candidates()
    assert [x["tag"] for x in c] == ["pacing.reveal"] and c[0]["count"] == 3 and c[0]["projects"] == {"p": 3}


def test_two_projects_make_a_pattern_and_ignore_is_remembered(proj, studio):
    with open(studio / "feedback.jsonl", "w") as f:
        f.write(json.dumps({"kind": "note", "project": "other", "note": "n-0004", "tags": ["audio.music-level"], "comment": "quieter"}) + "\n")
    opened()
    accept_tagged(["audio.music-level"])
    assert [x["tag"] for x in review.candidates()] == ["audio.music-level"]
    r = vs(proj, "review", "propose", "audio.music-level", "Music sits 22 dB under the voice")
    assert r.returncode == 0 and "profile.json" in r.stdout
    assert review.candidates() == []  # proposed: it waits for the human
    lz = review.state()["lessons"]["l-0001"]
    assert lz["dest"] == "profile" and lz["count"] == 2 and lz["evidence"] == ["other/n-0004", "p/n-0001"]
    review.append([{"type": "lesson.decided", "id": "l-0001", "decision": "ignore"}], H)
    assert json.loads(open(studio / "feedback.jsonl").read().splitlines()[-1])["decision"] == "ignore"
    accept_tagged(["audio.music-level"], 1.3)
    assert review.candidates() == []  # ignored: never asked again, whatever the count
    assert "lesson l-0001 ignore" in vs(proj, "review", "show").stdout


def test_taste_never_goes_to_the_public_kit(proj, studio):
    opened()
    r = vs(proj, "review", "propose", "pacing.reveal", "slower reveals", "--to", "kit")
    assert r.returncode and "stays in the studio, never the public kit" in r.stderr
    assert vs(proj, "review", "propose", "kit.bug", "a $ in scene code", "--to", "kit").returncode == 0


def test_this_video_only_is_asked_again_elsewhere(proj, studio):
    opened()
    for t in (1.0, 1.1, 1.2):
        accept_tagged(["color.meaning"], t)
    assert vs(proj, "review", "propose", "color.meaning", "red means the placebo").returncode == 0
    review.append([{"type": "lesson.decided", "id": "l-0001", "decision": "video"}], H)
    assert review.candidates() == [] and [c["tag"] for c in review.candidates(project="another-video")] == ["color.meaning"]


# ── the dogfood's numbers, and the tool-problem button ──
def test_the_report_counts_what_the_dogfood_asks(proj, studio):
    opened()
    review.append([note(1.0, target={"el": "s01/a", "box": [0, 0, .1, .1]}, mark={"type": "click", "at": [.05, .05]}),
                   note(1.2), note(1.4, target={"el": "s01/b", "box": [0, 0, .1, .1]}), {"type": "round.sent"}], H)
    review.append([{"type": "note.question", "id": "n-0002", "text": "which?"}], A)
    review.append([{"type": "note.answered", "id": "n-0002", "text": "that one"}], H)
    review.append([{"type": "note.resolved", "id": i, "said": "done", "outcome": "resolved", "tags": t}
                   for i, t in (("n-0001", ["qa.miss"]), ("n-0002", []), ("n-0003", []))], A)
    review.append([{"type": "note.accepted", "id": "n-0001"}, {"type": "note.accepted", "id": "n-0002"},
                   {"type": "note.reopened", "id": "n-0003", "text": "no"}, {"type": "finding.dismissed", "id": "q-x"},
                   {"type": "time.spent", "secs": 300, "playing": 120}, {"type": "time.spent", "secs": 60, "playing": 0}], H)
    out = vs(proj, "review", "report").stdout
    for line in ("Notes                                            3 (0 follow-ups)",
                 "…pinned to an element                            2 (67%); 1 with a mark",
                 "…that needed a question back                     1 (33%)",
                 "…right first time (accepted, never reopened)     2 of 2 accepted (100%); 1 reopened",
                 "QA misses (tagged qa.miss, accepted)             1",
                 "Findings shown / fix it / leave it               0 / 0 / 1",
                 "Time reviewing (playing)                         6 min (2 min)"):
        assert line in out, out
    md = vs(proj, "review", "report", "--md").stdout
    assert md.startswith("| Metric | Value |") and "| Rounds | 1 (v1 → v1) |" in md


def test_a_tool_problem_goes_to_the_dogfood_log_not_the_fix_list(proj):
    log = os.environ["VIDEO_KIT_DOGFOOD"]
    open(log, "w").write("# Dogfood\n\n## Friction log\n\n- Oct 1 · an earlier line\n\n## Verdict\n\nlater\n")
    opened()
    with pytest.raises(review.Refused, match="say what's in the way"):
        review.append([{"type": "friction.noted", "text": " "}], H)
    review.append([{"type": "friction.noted", "text": "no handle on the range", "where": "Notes tab at 00:12.43"}], H)
    doc = open(log).read()
    assert "- Oct 1 · an earlier line\n- " in doc and "Review Studio (Notes tab at 00:12.43, round 1, v1, p): no handle on the range" in doc
    assert doc.index("no handle") < doc.index("## Verdict") and doc.endswith("later\n")
    assert review.state()["friction"][0]["text"] == "no handle on the range"


# ── Decide: choices with live variants ──
def built(html="<html>a</html>", end=2.0, errors=(), inspect=True, segs=(("s01", 0.0, 2.0),)):
    """A stand-in for vs build --no-render + vs inspect: a composition, its timeline, its findings."""
    import hashlib
    os.makedirs("build/comp/assets", exist_ok=True)
    open("build/comp/index.html", "w").write(html)
    open("build/comp/assets/bed.wav", "w").write("x")
    fp = hashlib.sha256(html.encode()).hexdigest()[:16]
    json.dump({"fingerprint": fp, "end": end, "size": [108, 192], "fps": 30,
               "segments": [{"name": n, "t0": a, "t1": b} for n, a, b in segs]}, open("build/timeline.json", "w"))
    if inspect:
        json.dump({"fingerprint": fp, "items": [{"id": f"f-{i}", "check": "covers", "severity": "error", "elements": ["s01/x"],
                                                 "t0": 1.0, "t1": 1.2} for i in range(len(errors))]}, open("build/findings.json", "w"))
    return fp


def cmd(*a):
    return vs(".", "review", *a)


def test_a_choice_answers_a_note_and_the_pick_comes_back(proj):
    opened()
    review.append([note(), {"type": "round.sent"}], H)
    S, _ = review.append([{"type": "choice.offered", "choice": {"question": "Which reveal?", "for": "n-0001",
                                                                "options": [{"id": "a", "label": "slow"}, {"id": "b"}]}}], A)
    assert S["notes"]["n-0001"]["status"] == "question" and S["notes"]["n-0001"]["thread"][-1]["type"] == "choice"
    with pytest.raises(review.Refused, match="say what would work instead"):
        review.append([{"type": "choice.made", "id": "c-0001", "pick": "none"}], H)
    with pytest.raises(review.Refused, match="isn't one of c-0001's options"):
        review.append([{"type": "choice.made", "id": "c-0001", "pick": "z"}], H)
    S, _ = review.append([{"type": "choice.made", "id": "c-0001", "pick": "a"}], H)
    n = S["notes"]["n-0001"]
    assert n["status"] == "sent" and n["thread"][-1]["text"] == "picked a (slow)"  # the agent owes the note again
    S, _ = review.append([{"type": "choice.made", "id": "c-0001", "pick": "none", "text": "both too slow"}], H)  # a change of mind
    assert S["choices"]["c-0001"]["picked"] == "none" and len(S["choices"]["c-0001"]["picks"]) == 2
    with pytest.raises(review.Refused, match="pick is 'none', not 'a'"):
        review.append([{"type": "choice.applied", "id": "c-0001", "pick": "a"}], A)
    with pytest.raises(review.Refused, match="each option needs its own id"):
        review.append([{"type": "choice.offered", "choice": {"question": "q", "options": [{"id": "a"}, {"id": "a"}]}}], A)
    with pytest.raises(review.Refused, match="written by the human"):
        review.append([{"type": "choice.made", "id": "c-0001", "pick": "a"}], A)


def test_a_variant_is_kept_only_when_inspected_and_clean(proj):
    assert "nothing built" in cmd("variant", "a").stderr
    built(inspect=False)
    assert "vs inspect hasn't checked this composition" in cmd("variant", "a").stderr
    built(errors=[1])
    assert "1 open error(s)" in cmd("variant", "a").stderr
    built()
    open("scenes.js", "w").write("// variant a's scenes")
    assert "Bad" not in cmd("variant", "a", "slower reveal").stderr
    v = json.load(open("build/variants/a/variant.json"))
    assert v["label"] == "slower reveal" and v["sources"] == ["reel.json", "scenes.js"] and v["inspected"]
    assert open("build/variants/a/index.html").read() == "<html>a</html>" and os.path.exists("build/variants/a/assets/bed.wav")
    assert not os.path.islink("build/variants/a/index.html")  # a later build writes into build/comp: never a link
    assert open("build/variants/a/source/scenes.js").read() == "// variant a's scenes"
    assert "Not a variant" not in cmd("variant", "b", "--anyway").stderr  # unchecked, on the agent's say-so


def test_offer_reads_its_options_and_says_when_timing_differs(proj):
    opened()
    built(segs=(("s01", 0.0, 2.0),))
    os.makedirs("out/p-v1.review", exist_ok=True)
    json.dump({"end": 2.0, "segments": [{"name": "s01", "t0": 0.0}]}, open("out/p-v1.review/timeline.json", "w"))
    cmd("variant", "a", "as it is")
    built(html="<html>b</html>", end=2.5)
    cmd("variant", "b", "longer")
    os.makedirs("media", exist_ok=True)
    open("media/hero.png", "wb").write(b"png")
    r = cmd("offer", "Which ending?", "--option", "a", "--option", "b", "--option", "c=media/hero.png", "--label", "c=a photo", "--t", "1", "2")
    assert r.returncode == 0, r.stderr
    assert "b: its timing differs (ends +0.50s" in r.stdout
    c = review.state()["choices"]["c-0001"]
    assert [(o["id"], o["kind"], o.get("label")) for o in c["options"]] == [("a", "variant", "as it is"), ("b", "variant", "longer"), ("c", "image", "a photo")]
    assert c["options"][0]["preview"] == "build/variants/a/" and "timing" not in c["options"][0] and c["time"] == {"t0": 1.0, "t1": 2.0}
    assert "isn't a variant folder" in cmd("offer", "q", "--option", "a", "--option", "zz").stderr
    # a variant in a choice still waiting for the human isn't swapped under them
    assert "still waiting for the human" in cmd("variant", "a").stderr
    assert cmd("variant", "a", "--replace").returncode == 0


def test_a_paid_option_is_priced_by_its_own_gate_and_nothing_is_spent(proj, studio):
    import csv
    opened()
    built()
    cmd("variant", "a")
    rows = lambda: list(csv.DictReader(open(studio / "ledger.csv"))) if os.path.exists(studio / "ledger.csv") else []
    r = cmd("offer", "Music?", "--option", "a", "--option", "b", "--paid", "b=gen music --style 'warm lo-fi'")
    assert r.returncode == 0, r.stderr
    o = review.state()["choices"]["c-0001"]["options"][1]
    assert o["kind"] == "paid" and o["paid"] and o["run"] == "gen music --style 'warm lo-fi'"
    assert o["cost"] == "about 12 kie.ai credits · $0.06, spent only if you pick it" and rows() == []
    (studio / "profile.json").write_text(json.dumps({"spend": {"kie_credits_per_video": 10}}))
    assert "would pass the 10-credit cap" in cmd("offer", "Music?", "--option", "a", "--option", "b", "--paid", "b=gen music --style x").stderr
    assert "didn't reach its spend gate" in cmd("offer", "q", "--option", "a", "--option", "b", "--paid", "b=gen music").stderr


def test_apply_puts_the_picked_variant_back(proj):
    opened()
    open("scenes.js", "w").write("// b")
    built(html="<html>b</html>")
    cmd("variant", "b")
    open("scenes.js", "w").write("// a")
    built()
    cmd("variant", "a")
    cmd("offer", "Which?", "--option", "a", "--option", "b")
    assert "hasn't been picked yet" in cmd("apply", "c-0001").stderr
    review.append([{"type": "choice.made", "id": "c-0001", "pick": "b"}], H)
    r = cmd("apply", "c-0001")
    assert "restored scenes.js" in r.stdout and open("scenes.js").read() == "// b"
    S = review.state()
    assert S["choices"]["c-0001"]["applied"]["pick"] == "b"
    assert "choice c-0001" not in cmd("show").stdout  # applied: nothing left to do


def test_a_take_choice_lands_in_mix_json(proj):
    opened()
    os.makedirs("build/mixer", exist_ok=True)
    json.dump({"takes": [{"n": 1, "label": "A warm", "under": -20}, {"n": 2, "label": "B bright", "under": -19}]}, open("build/mixer/config.json", "w"))
    json.dump({"take": 1, "music_db": -18}, open("mix.json", "w"))
    assert cmd("offer", "Which bed?", "--option", "1=take:1", "--option", "2=take:2").returncode == 0
    assert "no music take 3" in cmd("offer", "q", "--option", "1=take:1", "--option", "3=take:3").stderr
    review.append([{"type": "choice.made", "id": "c-0001", "pick": "2"}], H)
    cmd("apply", "c-0001")
    assert json.load(open("mix.json")) == {"take": 2, "music_db": -18}  # the levels the human set stay
    assert vs(proj, "check").returncode == 0


# ── one sound, answered: a note, never a fader; measured in the next version's cues ──
def sound_note(ask, db=-13, el="sfx/whoosh1@s02_cage"):
    return note(sound={"el": el, "t": 22.66, "sound": "whoosh1", "db": db, "ask": ask}, target={"el": el})


@pytest.mark.parametrize("ask, new, outcome, says, flag", [
    ("quieter", {"db": -17}, "resolved", "4 dB quieter (-13 → -17 dB)", None),
    ("quieter", {"db": -10}, "resolved", "3 dB louder", "asked quieter, measured 3 dB louder"),
    ("louder", {}, "resolved", "same level", "nothing measurable changed"),
    ("different", {"sound": "swish1", "db": -13}, "resolved", "now “swish1”", None),
    ("remove", {}, "resolved", "same level", "nothing measurable changed"),
])
def test_a_sound_answer_is_measured_against_the_ask(ask, new, outcome, says, flag):
    n = sound_note(ask)["note"]
    n["resolution"] = {"outcome": outcome}
    cues = [{"el": "sfx/whoosh1@s02_cage", "t": 22.66, "sound": "whoosh1", "db": -13, **new}]
    m = review.measure_sound(n, cues)
    assert says in review.describe_measured(m) and (flag in (m["flag"] or "") if flag else m["flag"] is None)


def test_a_removed_sound_needs_the_word(proj):
    n = sound_note("remove")["note"]
    n["resolution"] = {"outcome": "resolved"}
    assert "--renamed or --removed" in review.measure_sound(n, [])["flag"]
    n["resolution"]["removed"] = True
    assert review.measure_sound(n, [])["flag"] is None
    opened()
    review.append([sound_note("remove"), {"type": "round.sent"}], H)
    os.makedirs("build/mix", exist_ok=True)
    json.dump([{"el": "sfx/tick1@s01", "t": 1.0, "sound": "tick1", "db": -12}], open("build/mix/cues.json", "w"))
    assert "isn't in the build any more" in cmd("resolve", "n-0001", "--said", "gone").stderr  # checked in the cues
    assert cmd("resolve", "n-0001", "--said", "gone", "--removed").returncode == 0
    show = cmd("show", "n-0001").stdout
    assert "sound: whoosh1 (sfx/whoosh1@s02_cage) at 00:22.66, -13 dB against the voice → remove it (cues.py)" in show
    r = vs(proj, "check")
    assert "review/state.json" not in r.stdout, r.stdout


def test_a_scene_marked_done_and_reopened(proj):
    with pytest.raises(review.Refused, match="no round"):
        review.append([{"type": "scene.done", "segment": "s02"}], H)
    opened()
    S, _ = review.append([{"type": "scene.done", "segment": "s02"}], H)
    assert S["done"]["s02"]["version"] == 1 and S["done"]["s02"]["video"] == "out/p-v1.mp4"
    with pytest.raises(review.Refused, match="written by the human"):
        review.append([{"type": "scene.done", "segment": "s03"}], A)
    assert "done (vs inspect holds their frames to that version" in cmd("show").stdout and "s02 (v1)" in cmd("show").stdout
    S, _ = review.append([{"type": "scene.reopened", "segment": "s02"}], H)
    assert S["done"] == {}
    with pytest.raises(review.Refused, match="isn't marked done"):
        review.append([{"type": "scene.reopened", "segment": "s02"}], H)
    assert vs(proj, "check").returncode == 0
