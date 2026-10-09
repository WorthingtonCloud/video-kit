"""Review Studio's page, driven in a headless browser against a real server (slow: vs test --fast skips these). Each
scenario in page.mjs is what a person does; the diary is the proof it reached the agent."""
import json, os, socket, subprocess, sys, time
import pytest
from conftest import ENGINE

pytestmark = pytest.mark.slow
HERE = os.path.dirname(os.path.abspath(__file__))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def served(tmp_path):
    yield from _serve(tmp_path)


@pytest.fixture
def served_two(tmp_path):
    """The same, with both shapes rendered: the round shows the Vertical | Wide switch in the top line."""
    yield from _serve(tmp_path, wide=True)


def _serve(tmp_path, wide=False):
    # wide: an explainer at its last stage with a long name and both shapes, the top line as full as it gets in use
    n = "video-kit-explainer" if wide else "p"
    d = tmp_path / n
    os.makedirs(d / "drafts/v1/data/vertical")
    (d / ("plan.json" if wide else "reel.json")).write_text("{}")
    if wide:  # past its first shape: the round shows both
        (d / "video.json").write_text(json.dumps({"schema_version": 1, "video": n, "first": "vertical", "building": "vertical",
                                                  "status": "second"}))
    for size, name in [("216x384", f"{n}-vertical-v1")] + ([("384x216", f"{n}-widescreen-v1")] if wide else []):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s={size}:d=3:r=30", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", str(d / f"drafts/v1/{name}.mp4")], check=True)
    run = lambda *a: subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), *a],
                                    capture_output=True, text=True)
    r = run("review", "open", *(["--stage", "final"] if wide else []))
    assert r.returncode == 0, r.stdout + r.stderr
    port = free_port()
    log = open(d / "server.log", "w")  # a file, not a pipe: a pipe nobody reads fills up and stalls the server mid-test
    srv = subprocess.Popen([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), "review", "--port", str(port)],
                           stdout=log, stderr=subprocess.STDOUT, text=True)
    for _ in range(50):
        with socket.socket() as s:
            if not s.connect_ex(("127.0.0.1", port)):
                break
        time.sleep(0.1)
    yield d, f"http://localhost:{port}/review/", run
    srv.terminate()
    srv.wait()
    log.close()


@pytest.fixture
def reel(tmp_path, font_studio):
    """The beat-reel fixture built and inspected, with a stand-in render (the page plays it; the maps are real)."""
    import shutil
    from conftest import tone
    d = tmp_path / "beat-reel"
    shutil.copytree(os.path.join(os.path.dirname(HERE), "fixtures/beat-reel"), d)
    os.makedirs(d / "music")
    tone(d / "music/take1.mp3", 40, freq=110, db=-12)
    run = lambda *a: subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), *a],
                                    capture_output=True, text=True)
    for step in (("build", "--no-render"), ("inspect",)):
        r = run(*step)  # the rare browser failure names its step only in its own output: keep all of it
        assert r.returncode == 0, f"vs {' '.join(step)} failed:\n{r.stdout[-3000:]}\n{r.stderr[-6000:]}"
    os.makedirs(d / "drafts/v1/data/vertical", exist_ok=True)
    tl = json.load(open(d / "build/timeline.json"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=216x384:d={tl['end']}:r=30", "-c:v",
                    "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(d / "drafts/v1/beat-reel-vertical-v1.mp4")], check=True)
    shutil.copy(d / "build/timeline.json", d / "drafts/v1/data/vertical/timeline.json")
    assert run("review", "open").returncode == 0
    port = free_port()
    log = open(d / "server.log", "w")  # a file, not a pipe: a pipe nobody reads fills up and stalls the server mid-test
    srv = subprocess.Popen([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), "review", "--port", str(port)],
                           stdout=log, stderr=subprocess.STDOUT, text=True)
    for _ in range(50):
        with socket.socket() as s:
            if not s.connect_ex(("127.0.0.1", port)):
                break
        time.sleep(0.1)
    yield d, f"http://localhost:{port}/review/", run
    srv.terminate()
    srv.wait()
    log.close()


@pytest.fixture
def overlay(tmp_path, font_studio):
    """The overlay-reel fixture built and inspected: one still with an arrow and a caption, each on a clear frame-sized
    sheet, the way a footage-first video draws them."""
    import shutil
    from conftest import tone
    d = tmp_path / "overlay-reel"
    shutil.copytree(os.path.join(os.path.dirname(HERE), "fixtures/overlay-reel"), d)
    os.makedirs(d / "media")
    os.makedirs(d / "music")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080", "-frames:v", "1",
                    str(d / "media/shot.jpg")], check=True)
    tone(d / "music/take1.mp3", 4, freq=110, db=-12)
    run = lambda *a: subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), *a],
                                    capture_output=True, text=True)
    for step in (("build", "--no-render"), ("inspect",)):
        r = run(*step)
        assert r.returncode == 0, f"vs {' '.join(step)} failed:\n{r.stdout[-3000:]}\n{r.stderr[-6000:]}"
    os.makedirs(d / "drafts/v1/data/widescreen", exist_ok=True)
    tl = json.load(open(d / "build/timeline.json"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=384x216:d={tl['end']}:r=30", "-c:v",
                    "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(d / "drafts/v1/overlay-reel-widescreen-v1.mp4")], check=True)
    shutil.copy(d / "build/timeline.json", d / "drafts/v1/data/widescreen/timeline.json")
    r = run("review", "open")
    assert r.returncode == 0, r.stdout + r.stderr
    port = free_port()
    log = open(d / "server.log", "w")
    srv = subprocess.Popen([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), "review", "--port", str(port)],
                           stdout=log, stderr=subprocess.STDOUT, text=True)
    for _ in range(50):
        with socket.socket() as s:
            if not s.connect_ex(("127.0.0.1", port)):
                break
        time.sleep(0.1)
    yield d, f"http://localhost:{port}/review/", run
    srv.terminate()
    srv.wait()
    log.close()


def drive(url, scenario):
    r = subprocess.run(["node", os.path.join(HERE, "page.mjs"), url, scenario], capture_output=True, text=True, timeout=90)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert "failed" not in out and not out["errors"], out
    return out


def log(d):
    return [json.loads(l) for l in open(d / "review/log.jsonl")]


def test_the_video_gets_the_room_and_the_top_line_never_overlaps(served):
    d, url, run = served
    out = drive(url, "room")
    assert out["folded"] == [True, True] and out["stage"] > 0.75  # both panels folded: the video takes the height
    assert out["fs"][0] and out["fs"][1] >= 790 and out["back"] is False
    assert out["open"] == [False, False, "1"]
    for w, m in out["widths"].items():
        assert m["h"] <= 52 and not m["over"] and not m["tall"] and not m["scroll"] and not m["clip"], (w, m)


def test_the_top_line_with_both_shapes_folds_instead_of_clipping(served_two):
    # A reviewer, Oct 4, 2026: with the shape switch in, the step strip spilled off both its edges and the current step sat
    # clipped under the stage names ("too crowded and things are overlapping"). Boxes never touched: the clip was inside.
    d, url, run = served_two
    out = drive(url, "room")
    for w, m in out["widths"].items():
        assert m["h"] <= 52 and not m["over"] and not m["tall"] and not m["scroll"] and not m["clip"], (w, m)
        assert int(w) <= 600 or "f4" in m["fold"] or m["now"], (w, m)  # the current step shows while the strip does
    assert out["widths"]["1680"]["fold"] == ""  # a wide window shows everything
    assert sorted(out["shapes"]) == ["Vertical", "Widescreen"]  # one word each


def test_the_loop_undo_review_send_and_claudes_turn(served):
    d, url, run = served
    out = drive(url, "loop")
    assert out["toast"] == "Note at 0:00.5: \u201ctoo fast here\u201d · waits for your send" and out["loop"] == "Feedback"
    assert out["send"] == "Review & send · 1 thing" and out["reviewLoop"] == "Review"
    assert out["list"] == ["Note at 0:00.5: \u201ctoo fast in the first second\u201d"]  # the changed words, on the note's own line
    assert out["word"] == "sent" and out["turn"] == "Waiting for Claude to read it." and out["after"] == "Tell"
    types = [e["type"] for e in log(d)]
    assert types.count("undo") == 2 and types.count("note.added") == 3 and types.count("round.sent") == 1
    S = json.load(open(d / "review/state.json"))
    assert [n["comment"] for n in S["notes"].values()] == ["too fast in the first second"]  # the undone ones never reach Claude
    assert "too fast in the first second" in run("review", "show").stdout  # and that read tells the page
    out = drive(url, "read")
    assert out["loop"] == "Claude" and "Claude has it" in out["sendp"] and out["again"] == "Feedback"
    assert out["sent"]["list"] == ["Note at 0:01.0: \u201cone more thing\u201d"] and out["sent"]["word"] == "sent again"
    assert json.load(open(d / "review/state.json"))["rounds"][0]["sends"] == 2


def test_where_you_are_and_a_comment_on_a_step(served):
    d, url, run = served
    assert run("review", "step", "Okayed the outline", "--stage", "brief", "--when", "2020-01-01T20:00").returncode == 0
    out = drive(url, "steps")
    assert "Brief · round 1" in out["stages"] and out["groups"] == ["Brief"]
    assert out["steps"][0].startswith("Okayed the outline") and "Round 1 opened on v1" in out["steps"][1]
    assert "I want to revisit this" in out["note"] and out["sent"]["list"] == ["About \u201cOkayed the outline\u201d: \u201cI want to revisit this\u201d"]
    assert "about their step: Okayed the outline" in run("review", "show").stdout


def test_a_note_and_a_send_reach_the_agent(served):
    d, url, run = served
    out = drive(url, "notes")
    assert "too fast here" in out["item"] and out["box"] == "" and out["sent"]["word"] == "sent"
    assert out["sent"]["list"] == ["Note at 0:00.5: \u201ctoo fast here\u201d"]
    ev = log(d)
    assert [e["type"] for e in ev] == ["round.opened", "note.added", "round.sent"]
    assert ev[1]["by"] == "human" and ev[1]["held"] and ev[1]["note"]["time"]["t"] == pytest.approx(0.5, abs=0.04)
    assert os.path.exists(d / "review/frames/n-0001.jpg")
    assert "too fast here" in run("review", "show").stdout

def test_the_player_steps_jumps_and_the_timeline_points_at_the_frame(reel):
    d, url, run = reel
    out = drive(url, "player")
    assert out["start"] == "00:13.00" and out["frame"] == "00:13.03" and out["second"] == "00:12.03"
    assert out["scene"] == ["00:17.10", "s05_sources"]  # ] lands on the next scene's first frame
    assert out["back"] == ["00:07.67", "s02_turn"]  # [ at a scene's start goes to the one before (s02 starts at 7.65)
    assert out["rows"][:3] == ["Scenes", "Beats", "Titles"] and out["rows"][3].startswith("s02_turn ▾")
    assert out["rows"][-2:] == ["QA", "Notes"]
    assert out["beats"][1] == 1                      # the first big hit, marked
    assert out["outline"] == 1 and out["lit"] == "title/t_layers" and out["litTitle"]
    assert out["zoom"] == "60 s" and out["watch"] == [True, "none"]  # F: full screen, the panel out of the way


def test_pointing_asks_the_composition_and_the_note_carries_it(reel):
    d, url, run = reel
    out = drive(url, "point")
    assert out["notice"] == ""  # the composition is this version's: no fallback
    assert out["tag"] == "ring-layer-1-label" and out["selRow"] == "s03_hub/ring-layer-1-label"
    # the chip names what the note is pinned to; the breadcrumb above the box shows only when there's a level to go up to
    assert out["chip"].startswith("ring-layer-1-label") and (not out["crumbs"] or out["crumbs"][-1] == "ring-layer-1-label")
    assert out["markline"].startswith("mark: arrow to") and "core" in out["markline"].split("keep-clear over ")[1].split(", ")
    assert out["cleared"] and out["range"] == "00:09.60 → 00:11.00"
    n1, n2 = [e["note"] for e in log(d) if e["type"] == "note.added"]
    assert n1["target"]["el"] == "s03_hub/ring-layer-1-label" and n1["segment"] == "s03_hub"
    assert 0 <= n1["target"]["at"][0] <= 1 and len(n1["target"]["box"]) == 4
    assert n1["mark"]["type"] == "arrow" and n1["mark"]["under_from"][0] == "s03_hub/ring-layer-1-label"
    assert n1["also"][0]["type"] == "keep-clear" and "s03_hub/core" in n1["also"][0]["over"]
    assert "s03_hub/ring-layer-1-label" in n1["visible"] and "title/t_layers" in n1["visible"]
    assert n2["time"] == {"t0": 9.6, "t1": 11.0} and n2["mark"]["type"] == "none" and n2["target"] is None
    assert os.path.exists(d / "review/frames/n-0001.jpg") and os.path.exists(d / "review/frames/n-0002.jpg")
    show = run("review", "show").stdout
    assert "s03_hub › ring-layer-1-label" in show and "arrow (" in show and "keep-clear" in show


def test_the_human_says_what_and_how_far_never_how(reel):
    """The page captures intent, not implementation: an ask and a reach, each one click, carried in the note; a rule's
    reach is the human's pick, never automatic."""
    d, url, run = reel
    assert run("review", "propose", "type.size", "Labels at least 34 px").returncode == 0
    out = drive(url, "intent")
    assert out["asks"] == ["Move it", "Bigger", "Smaller", "Longer", "Shorter", "Less busy", "Remove it"]
    assert out["reach"] == ["Just here", "All through this video", "In every video"]
    assert out["on"] == ["Bigger", "All through this video"] and out["hint"].startswith("Bigger: anything to add")
    item = " ".join(out["item"].split())
    assert item.startswith("● Bigger · hard to read All through this video") and out["cleared"]
    assert out["rangeAsks"] == ["Longer", "Shorter", "Less busy"]  # nothing pointed at: only what a moment can have
    assert out["ruleButtons"] == ["Every video", "Every reel", "This video only", "Ignore"]
    n1, n2 = [e["note"] for e in log(d) if e["type"] == "note.added"]
    assert (n1["ask"], n1["scope"], n1["target"]["el"]) == ("bigger", "project", "s03_hub/ring-layer-1-label")
    assert n2["ask"] == "shorter" and "scope" not in n2 and n2["time"] == {"t0": 9.6, "t1": 11.0}
    S = json.load(open(d / "review/state.json"))
    assert S["lessons"]["l-0001"]["decision"] == "kind"
    show = run("review", "show").stdout
    assert "ask: bigger · everywhere in this video" in show and "ask: shorter" in show


def test_an_older_build_points_from_the_map_and_says_so(reel):
    d, url, run = reel
    f = d / "drafts/v1/data/vertical/timeline.json"
    tl = json.load(open(f))
    tl["fingerprint"] = "an-older-build"
    json.dump(tl, open(f, "w"))
    out = drive(url, "point")
    assert "build has changed since v1" in out["notice"]
    assert out["tag"] == "ring-layer-1-label"  # the map still finds it


def test_findings_in_plain_words_with_claudes_advice(reel):
    d, url, run = reel
    # qa.py's warnings on this render, and one vs inspect error put to the human (a second version, opened with --ask)
    os.makedirs(d / "drafts/v2/data/vertical")
    json.dump({"findings": 1, "source": "qa", "items": [
        {"id": "q-covered-top-15.25", "check": "covered", "severity": "warning", "elements": ["s03_hub/node-files"],
         "t0": 15.25, "t1": 15.5, "at": 15.38, "text": "something bright in the top (status bar)", "hint": "move it"},
        {"id": "q-covered-right-18.25", "check": "covered", "severity": "warning", "elements": ["s05_sources/claim"],
         "t0": 18.25, "t1": 18.5, "at": 18.38, "text": "something bright in the right", "hint": "move it"}]},
        open(d / "drafts/v2/data/vertical/qa.json", "w"))
    F = json.load(open(d / "build/findings.json"))
    F["items"].append({"id": "f-spills-s03_hub-core", "check": "spills", "severity": "error", "elements": ["s03_hub/core"],
                       "text": "", "t0": 12.0, "t1": 13.0, "at": 12.5})
    json.dump(F, open(d / "build/findings.json", "w"))
    import shutil
    shutil.copy(d / "drafts/v1/beat-reel-vertical-v1.mp4", d / "drafts/v2/beat-reel-vertical-v2.mp4")
    shutil.copy(d / "drafts/v1/data/vertical/timeline.json", d / "drafts/v2/data/vertical/timeline.json")
    assert "errors never reach a round" in run("review", "open", "--video", "drafts/v2/beat-reel-vertical-v2.mp4").stderr
    r = run("review", "open", "--video", "drafts/v2/beat-reel-vertical-v2.mp4", "--ask")
    assert r.returncode == 0 and "advise each in plain words" in r.stdout
    assert run("review", "advise", "--check", "covered", "--advice", "leave", "--plain", "two bright edges", "--why", "decoration").returncode == 0
    out = drive(url, "findings")
    cards = {c[0]: c[1:] for c in out["cards"]}
    assert cards["covered"] == ["Something bright near a phone's edges", True] and cards["spills"] == ["Words run past their card's edge", False]
    warn = [f["id"] for f in F["items"] if f["severity"] == "warning"]
    assert warn and "two-zones" in cards  # vs inspect's warnings show too, without being put to the human
    assert out["qaRow"] == 3 + len(warn) and out["todo"].isdigit()
    assert out["toast"].startswith("Something bright near a phone's edges: fix it · waits for your send")
    assert out["comment"]["now"] == "00:18.40" and "claim" in out["comment"]["about"] and "q-covered-right-18.25" in out["comment"]["about"]
    assert out["comment"]["focus"] == "c-text"
    S = json.load(open(d / "review/state.json"))
    assert S["findings"]["q-covered-top-15.25"]["status"] == "confirmed" and S["findings"]["q-covered-top-15.25"]["followed"] is False
    assert S["findings"]["f-spills-s03_hub-core"]["status"] == "dismissed"
    n = S["notes"]["n-0001"]
    assert n["findings"] == ["q-covered-right-18.25"] and n["target"]["el"] == "s05_sources/claim"
    show = run("review", "show").stdout
    assert "confirmed q-covered-top-15.25 (against your advice)" in show and "dismissed f-spills-s03_hub-core" in show

def test_the_mix_panel_plays_the_stems_and_saves_what_a_reel_can_bake(reel):
    d, url, run = reel
    assert run("mix", "--video", "drafts/v1/beat-reel-vertical-v1.mp4", "--tag", "v1").returncode == 0
    out = drive(url, "mix")
    assert out["open"] == "true" and out["music"] == 0 and out["muted"]  # a reel: its own track, no takes to pick
    assert out["playing"][0] > 5.5 and out["playing"][1] == "❚❚"       # the picture followed the stems' clock
    assert out["label"] == "-3 dB" and out["summary"] == "The reel’s own track, effects -3 dB." and out["after"] is False
    assert out["saved"].startswith("Saved: The reel’s own track") and out["sent"]["list"][0].startswith("Saved the mix: The reel’s own track")
    saved = json.load(open(d / "mix.json"))  # written when it was sent
    assert saved["take"] == 0 and saved["sfx_db"] == -3 and json.load(open(d / "review/state.json"))["mix"]["sfx_db"] == -3
    assert run("check").returncode == 0  # take 0 is a reel's mix, not a broken file
    r = run("mix", "--video", "drafts/v1/beat-reel-vertical-v1.mp4", "--tag", "v1", "--final")
    assert r.returncode == 0, r.stdout + r.stderr  # it used to read take 0 as "no mix.json yet"
    assert os.path.exists(d / "drafts/v1/beat-reel-vertical-v1-mixed.mp4") and "final: take 0" in r.stdout

def answered_round(d, run):
    """Round 1 as the page would write it, the agent's answers, and round 2 on the same build (so a claimed fix measures
    as no change)."""
    import shutil
    sys.path.insert(0, os.path.join(ENGINE, "py"))
    import review
    E = {e["id"]: e for e in json.load(open(d / "build/elements.json"))["items"]}
    box = lambda e, t: [b for b in e["boxes"] if b[0] <= t][-1][1:]
    cwd = os.getcwd()
    os.chdir(d)
    try:
        review.append([
            {"type": "note.added", "note": {"time": {"t": 11.5}, "segment": "s03_hub", "comment": "say kinds",
             "target": {"el": "title/t_layers", "box": box(E["title/t_layers"], 11.5), "text": E["title/t_layers"]["text"]}}},
            {"type": "note.added", "note": {"time": {"t0": 9.6, "t1": 11.0}, "segment": "s03_hub", "comment": "too slow"}},
            {"type": "round.sent"}], "human")
    finally:
        os.chdir(cwd)
    assert run("review", "resolve", "n-0001", "--said", "it reads kinds now", "--files", "reel.json").returncode == 0
    assert run("review", "resolve", "n-0002", "--said", "two beats sooner").returncode == 0
    os.makedirs(d / "drafts/v2/data/vertical", exist_ok=True)
    shutil.copy(d / "drafts/v1/beat-reel-vertical-v1.mp4", d / "drafts/v2/beat-reel-vertical-v2.mp4")
    shutil.copy(d / "drafts/v1/data/vertical/timeline.json", d / "drafts/v2/data/vertical/timeline.json")
    return run("review", "open", "--video", "drafts/v2/beat-reel-vertical-v2.mp4")


def test_rounds_measure_compare_looks_right_still_wrong_approve(reel):
    d, url, run = reel
    r = answered_round(d, run)
    assert "n-0001 t_layers: didn't move" in r.stdout and "nothing measurable changed" in r.stdout
    out = drive(url, "rounds")
    # v2 is v1's own bytes: the box didn't move and its pixels didn't change (n-0001), and the stretch's picture and sound
    # are the same (n-0002, a range with no target): both claimed fixes are flagged
    assert out["cards"] == [["n-0001", "Claude says it's fixed in v2", True], ["n-0002", "Claude says it's fixed in v2", True]]
    assert out["compare"] == ["/drafts/v1/beat-reel-vertical-v1.mp4", "/drafts/v2/beat-reel-vertical-v2.mp4"] and out["outlines"] == 2
    assert out["follow"] is None  # looks right: nothing left to follow up from here
    assert "Approved: v2 is done" in out["approve"] and "v2 approved" in out["approved"]  # one click, then sent
    assert out["sent"]["list"] == ["Claude's fix for \u201csay kinds\u201d: looks right",
                                   "Claude's fix for \u201ctoo slow\u201d: still wrong, \u201cstill too slow\u201d", "Approved v2: it's done"]
    S = json.load(open(d / "review/state.json"))
    assert S["notes"]["n-0001"]["status"] == "accepted" and S["notes"]["n-0002"]["status"] == "reopened"
    assert S["approved"][0]["version"] == 2


def test_a_follow_up_points_back_at_the_answer(reel):
    d, url, run = reel
    answered_round(d, run)
    out = drive(url, "follow")
    assert "follows: n-0001" in out["point"] and out["focus"] == "c-text"
    S = json.load(open(d / "review/state.json"))
    assert S["notes"]["n-0003"]["follows"] == "n-0001" and S["notes"]["n-0003"]["target"]["el"] == "title/t_layers"

def test_the_learning_prompt_is_the_humans_click(reel, monkeypatch):
    d, url, run = reel
    studio = os.environ["VIDEO_STUDIO"]  # the fixture's throwaway studio: the server and the commands share it
    with open(os.path.join(studio, "feedback.jsonl"), "w") as f:
        for i in range(3):
            f.write(json.dumps({"kind": "note", "project": "earlier", "note": f"n-000{i}", "tags": ["type.size"], "comment": "bigger"}) + "\n")
    out_learn = run("review", "learn").stdout
    assert "type.size: 3 accepted notes (earlier ×3)" in out_learn
    assert run("review", "propose", "type.size", "Labels at least 34 px").returncode == 0
    out = drive(url, "learn")
    assert "Seen 3×" in out["card"] and "Labels at least 34 px" in out["card"] and "your profile" in out["card"] and int(out["badge"]) >= 1
    assert "ignore it" in out["decided"] and out["sent"]["list"] == ["Lesson \u201cLabels at least 34 px\u201d: ignore it"]
    last = json.loads(open(os.path.join(studio, "feedback.jsonl")).read().splitlines()[-1])
    assert last["kind"] == "lesson" and last["decision"] == "ignore" and last["tag"] == "type.size"
    assert "no patterns yet" in run("review", "learn").stdout


def test_the_review_clock_and_the_tool_problem_button(reel):
    d, url, run = reel
    log = os.environ["VIDEO_KIT_DOGFOOD"]
    open(log, "w").write("## Friction log\n\n## Verdict\n")
    out = drive(url, "usage")
    assert "tool's problem log" in out["toast"]
    ev = [json.loads(l) for l in open(d / "review/log.jsonl")]
    spent = [e for e in ev if e["type"] == "time.spent"]
    assert len(spent) == 1 and spent[0]["secs"] >= 2 and spent[0]["playing"] >= 2
    assert "no handle on the range (from the page's Problem? button)" in open(log).read()
    rep = run("review", "report").stdout
    assert "Tool problems reported                           1" in rep


def test_decide_see_shows_an_option_and_pick_is_its_own_step(reel):
    d, url, run = reel
    assert run("review", "variant", "a", "A · dot, as it is").returncode == 0
    R = json.load(open(d / "reel.json"))
    next(s for s in R["segments"] if s["name"] == "s02_turn")["in"] = "flash"
    json.dump(R, open(d / "reel.json", "w"))
    for step in (("build", "--no-render"), ("inspect",), ("review", "variant", "b", "flash")):
        r = run(*step)
        assert r.returncode == 0, f"vs {' '.join(step)} failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}"
    assert run("review", "offer", "How should the turn arrive?", "--option", "a", "--option", "b", "--t", "7", "9.5").returncode == 0
    out = drive(url, "decide")
    assert [o.split(" ", 4)[:4] for o in out["opts"]] == [["See", "option", "A", "1"], ["See", "option", "B", "2"], ["See", "it", "as", "rendered"]]
    assert out["opts"][0].endswith("1 dot, as it is")  # the label's own "A ·" isn't said twice
    assert "00:07.00" <= out["now"] < "00:09.50" and out["label"].startswith("Showing option B")  # at the choice's moment, playing
    assert out["banner"].startswith("Showing option B · not picked") and out["preview"] == "b"
    assert abs(out["paused"] - 8.5) < 0.04                    # paused: the variant shows the player's own moment
    v, tl, paused = out["playing"]
    assert not paused and v > 7.5 and abs(v - tl) < 0.3       # playing: it follows the player's clock
    assert 9.4 <= out["stopped"] <= 9.9                       # Play the choice stops at its end
    assert out["key"] == "a" and out["notPicked"]             # seeing is never picking
    assert "Your pick: B (flash)" in out["picked"] and int(out["badgeBefore"][0]) == int(out["badge"][0] if out["badge"] else 0) + 1
    assert out["back"] == [True, "", True]                     # Back to the render
    assert out["sent"]["list"] == ["Picked B (flash) for \u201cHow should the turn arrive?\u201d"]
    S = json.load(open(d / "review/state.json"))
    assert S["choices"]["c-0001"]["picked"] == "b"
    assert "choice c-0001 picked: b (flash)" in run("review", "show").stdout
    r = run("review", "apply", "c-0001")
    assert "restored nothing" in r.stdout  # the project already is b (it was built last)

@pytest.fixture
def explainer(tmp_path, font_studio):
    """The tiny explainer with a music take and two effects, mixed against a stand-in render: the Mix panel ducks live."""
    import shutil
    from conftest import tone
    d = tmp_path / "tiny-explainer"
    shutil.copytree(os.path.join(os.path.dirname(HERE), "fixtures/tiny-explainer"), d)
    tone(d / "voice/voice-bed-t1.wav", 13.6, freq=180, db=-20)
    os.makedirs(d / "music")
    tone(d / "music/take1.mp3", 16, freq=220, db=-14)
    (d / "cues.py").write_text("def cues(T, TT, C, END_T):\n    return [(1.0, 'tick1', 'on', -12), (2.5, 'tick1', 'on', -6)]\n")
    run = lambda *a: subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), *a],
                                    capture_output=True, text=True)
    for step in (("plan",), ("build", "--no-render"), ("inspect",)):
        r = run(*step)
        assert r.returncode == 0, f"vs {' '.join(step)} failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}"
    tl = json.load(open(d / "build/timeline.json"))
    os.makedirs(d / "drafts/v1/data/vertical", exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=216x384:d={tl['end']}:r=30", "-c:v",
                    "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(d / "drafts/v1/t-vertical-v1.mp4")], check=True)
    shutil.copy(d / "build/timeline.json", d / "drafts/v1/data/vertical/timeline.json")
    assert run("mix", "--video", "drafts/v1/t-vertical-v1.mp4", "--tag", "v1").returncode == 0
    assert run("review", "open", "--video", "drafts/v1/t-vertical-v1-take1.mp4").returncode == 0
    port = free_port()
    log = open(d / "server.log", "w")  # a file, not a pipe: a pipe nobody reads fills up and stalls the server mid-test
    srv = subprocess.Popen([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), "review", "--port", str(port)],
                           stdout=log, stderr=subprocess.STDOUT, text=True)
    for _ in range(50):
        with socket.socket() as s:
            if not s.connect_ex(("127.0.0.1", port)):
                break
        time.sleep(0.1)
    yield d, f"http://localhost:{port}/review/", run
    srv.terminate()
    srv.wait()
    log.close()


def test_ducking_plays_live_and_the_slider_moves_it(explainer):
    d, url, run = explainer
    out = drive(url, "duck")
    assert out["slider"] == 6 and "(it dips 6 dB while the voice speaks)" in out["summary"]
    assert out["playing"]["running"] and out["playing"]["duck_gain"] == pytest.approx(10 ** (-6 / 20), abs=0.01)
    assert out["deeper"]["duck_gain"] == pytest.approx(10 ** (-12 / 20), abs=0.01)  # moved while it played
    assert "(it dips 12 dB while the voice speaks)" in out["summary2"] and out["label"] == "12 dB" and "dB under" in out["meter"]
    assert json.load(open(d / "mix.json"))["duck_db"] == 12  # sent: vs mix --final bakes it


def test_a_first_mix_can_be_saved_at_the_levels_it_starts_with(explainer):
    """No mix.json yet: Save is open (the take on screen and the starting levels are a choice too), and once saved it
    closes until something changes."""
    d, url, run = explainer
    assert not (d / "mix.json").exists()
    out = drive(url, "firstsave")
    assert out["disabled"] is False, f"Save was gray with nothing saved: {out}"
    assert out["after"] is True
    saved = json.load(open(d / "mix.json"))
    assert saved["take"] == 1 and saved["duck_db"] == 6


def test_one_sound_is_heard_alone_and_answered_with_a_note(explainer):
    d, url, run = explainer
    out = drive(url, "sound")
    assert out["point"].startswith("sound: tick1 · tick1@") and out["now"] == "00:01.00"
    assert out["alone"] > 0 and out["item"] == "Quieter: tick1 · it buries the word"
    n = [e for e in log(d) if e["type"] == "note.added"][0]["note"]
    assert n["sound"]["ask"] == "quieter" and n["sound"]["el"].startswith("sfx/tick1@") and n["target"] == {"el": n["sound"]["el"]}
    assert "→ quieter (cues.py)" in run("review", "show").stdout


def test_a_scene_marked_done_and_a_keep_clear_zone_become_standing_rules(reel):
    d, url, run = reel
    out = drive(url, "rules")
    assert out["line"].startswith("Scene s02_turn") and out["done"][0].startswith("✓ s02_turn is done") and "not sent" in out["done"][0]
    assert out["done"][1] == "✓ s02_turn"
    assert out["draft"] == 0 and out["inScene"] == 1 and out["elsewhere"] == 0
    S = json.load(open(d / "review/state.json"))
    assert list(S["done"]) == ["s02_turn"] and S["done"]["s02_turn"]["version"] == 1
    z = S["notes"]["n-0001"]["also"][0]
    assert "s03_hub/core" in z["keeps"] and set(z["keeps"]) <= set(z["over"])
    types = [e["type"] for e in log(d)]
    assert types.count("scene.done") == 2 and types.count("undo") == 1  # done, taken back before sending, done again


def post_human(url, events):
    import urllib.request
    req = urllib.request.Request(url + "api/events", json.dumps({"events": events}).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        assert r.status == 200


def test_no_notes_is_one_click_and_reaches_the_agent(served):
    d, url, run = served
    out = drive(url, "nonotes")
    assert out["before"] == "No notes · send" and "No notes · send" in out["hint"]
    assert out["list"] == ["No notes this round: nothing to change"] and out["after"] == "Review & send"
    assert [e["type"] for e in log(d)][-2:] == ["round.nonotes", "round.sent"] and log(d)[-2]["held"]
    assert "the human: no notes this round" in run("review", "show").stdout


def test_an_answer_from_an_earlier_round_is_not_asked_again(served):
    import shutil
    d, url, run = served
    for v in (1, 2):
        os.makedirs(d / f"drafts/v{v}/data/vertical", exist_ok=True)
        json.dump({"items": [{"id": f"q-covered-left-{1 + v * 0.25}", "check": "covered", "severity": "warning", "elements": [],
                              "t0": 1 + v * 0.25, "t1": 1.5 + v * 0.25, "at": 1.2, "text": "something bright in the left"}]},
                  open(d / f"drafts/v{v}/data/vertical/qa.json", "w"))
    post_human(url, [{"type": "finding.dismissed", "id": "q-covered-left-1.25", "check": "covered", "held": True}, {"type": "round.sent"}])
    shutil.copy(d / "drafts/v1/p-vertical-v1.mp4", d / "drafts/v2/p-vertical-v2.mp4")
    r = run("review", "open", "--video", "drafts/v2/p-vertical-v2.mp4")
    assert "1 finding(s) answered in an earlier round" in r.stdout, r.stdout + r.stderr
    out = drive(url, "carried")
    assert out["line"].startswith("✓ Leave it") and "your answer from round 1" in out["line"] and out["todo"] == 0
    assert out["buttons"][:2] == ["Leave it", "Fix it"] and "In round 1 you said “leave it”" in out["was"]


def test_the_end_of_the_flow_says_done_with_the_files_and_a_way_back(served):
    import shutil
    d, url, run = served
    shutil.copy(d / "drafts/v1/p-vertical-v1.mp4", d / "drafts/v1/p-vertical-v1-take1.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=384x216:d=3:r=30", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(d / "drafts/v1/p-widescreen-v1-take1.mp4")], check=True)
    assert run("review", "finish", "--final", "drafts/v1/p-vertical-v1-take1.mp4", "drafts/v1/p-widescreen-v1-take1.mp4").returncode == 0
    out = drive(url, "finished")
    assert out["done"] and out["fetched"] == 200
    assert [f[:2] for f in out["files"]] == [["/drafts/v1/p-vertical-v1-take1.mp4", "p-vertical-v1-take1.mp4"], ["/drafts/v1/p-widescreen-v1-take1.mp4", "p-widescreen-v1-take1.mp4"]]
    assert out["files"][0][2].startswith("⤓ Vertical") and out["files"][1][2].startswith("⤓ Widescreen")
    assert out["parts"] == ["the words", "the voice", "the picture", "the sound"]
    assert out["sheetHidden"] and out["note"] == "About the sound: " and out["focus"] == "c-text"
    assert out["againOnReload"] is False and out["reopens"] is True


def test_a_click_on_footage_graphics_finds_the_graphic_not_its_clear_sheet(overlay):
    """A footage-first video (Oct 9, 2026): every overlay sat on a clear sheet the size of the frame, so every click picked the
    whole picture and none of 30 notes carried a target. A click goes through what doesn't paint; the outline is what's
    drawn; and the element map agrees, so a note on the arrow can be measured."""
    d, url, run = overlay
    out = drive(url, "overlay")
    assert out["notice"] == ""  # the composition is this version's own
    assert out["arrow"]["tag"] == "marks-arrow"
    x, y, w, h = out["arrow"]["box"]
    assert 0.65 < x < 0.7 and 0.15 < y < 0.2 and w < 0.15 and h < 0.15  # the arrow, not the frame
    assert out["beside"]["tag"] == "marks-arrow"  # a line a few pixels wide: near it counts
    assert out["caption"]["tag"] == "marks-caption" and out["caption"]["box"][2] < 0.3
    assert out["footage"]["tag"] == "still" and out["corner"]["tag"] == "still"
    E = {e["id"]: e for e in json.load(open(d / "build/elements.json"))["items"]}
    b = E["s01_shot/marks-arrow"]["boxes"][-1]
    assert b[3] - b[1] < 0.15 and b[4] - b[2] < 0.15  # the map's box is the arrow too
