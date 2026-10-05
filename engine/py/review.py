#!/usr/bin/env python3
"""vs review: Review Studio. The human points at the video and says what's wrong in the page; the agent reads the
snapshot and answers in the same diary. The page only ever writes feedback: never reel.json, scenes.js or any other
source file (mix.json is the one exception, as in the mixer: a level set by ear is the human's setting).

  vs review [--port 4470]               serve the review page on this machine only: http://localhost:4470/review/
  vs review open [--video out/<name>-vN[-takeK].mp4] [--ask] [--stage picture] [--also <the other shape> | --only]
                                        a new round on a rendered version (default: the newest). Both shapes when both
                                        are rendered at that version (an explainer's out/<name>-16x9-vN…, a reel's
                                        ../<slug>-16x9/out/…; --also names it, --only shows one): the page switches
                                        between them, and every note, finding and approval is about the one on screen,
                                        so each gets its own feedback (vs review show labels them). Refused while vs inspect
                                        has open errors for it (errors never reach a round); --ask puts them in front
                                        of the human to confirm or dismiss instead. Refused while the human has feedback
                                        they haven't sent. --stage: where the video is (contracts.json → stages)
  vs review show [<note>] [--json]      the round as the agent reads it: each note's moment, target, mark and words, and
                                        its still, review/frames/<note>.jpg (LOOK at it: it's what the human saw). Reading
                                        what was sent tells the page Claude has it
  vs review launch                      the review page's server for THIS project, ready for the preview pane: picks
                                        a free port once (and keeps it), writes the "<project>-review" entry into the
                                        nearest .claude/launch.json, then says in one line whether the server and the
                                        watcher are running. vs review open prints the same line. Never hunt for a port
                                        or check the watcher by hand
  vs review wait [--hours 12]           block until the human sends, then print vs review show. Run it in the background
                                        right after telling them a round is open: the agent is woken by the send, and the
                                        page says "Claude is watching" while it runs (exit 2 = timed out, nothing sent)
  vs review advise <finding>… | --check <check> --advice leave|fix --plain "what it is" [--why "…"]
                                        Claude's advice on a finding, in plain words: the human takes it with one click
                                        (Leave it / Fix it), or doesn't. --check advises every finding of that check
  vs review step "<what the human did>" [--stage <stage>] [--when 2026-10-01T20:20]
                                        a step the human took outside the page (an OK in chat): the page's log of steps
                                        shows it. --stage alone marks where the video got to
  vs review status [--json | --ready]   whose move it is (agent / returned / human / done) and whether the review may
                                        end: every shape approved, everything sent read, nothing held unsent, every
                                        note answered, no question or choice waiting. --ready exits 1 until it may
  vs review ask <note> "…"              a question back; the note waits for the answer
  vs review resolve <note> --said "…" [--wontdo] [--files scenes.js …] [--tags pacing.reveal …]
                                        [--renamed <new name> | --removed] [--expect place|size|time|words|color|…|elsewhere]
                                        what changed (or why not); a target that's gone needs --renamed or --removed.
                                        --expect: the change it should show (the human's ask, if they gave one, is
                                        measured whatever this says; elsewhere = the fix was to something else, so the
                                        whole moment is measured)
  vs review variant <id> ["what it is"] [--replace] [--anyway]
                                        keep what's built now (inspected, no open errors) as build/variants/<id>/: an
                                        option the human plays live in Decide, with the sources that made it
  vs review offer "<question>" --option a --option b [--option c=take:2 | c=media/x.png] [--label a="…"]
                  [--paid c='gen still --prompt "…" --out media/c.png'] [--t 21 25] [--for <note>]
                                        a choice to pick from (Decide). An option is a variant (its id), a music take, or a
                                        picture/clip/sound; --paid prices one through its step's spend gate (nothing spent
                                        until it's picked). --for answers a note with it (the note waits for the pick)
  vs review cover <card> --by <note> [--as fix|leave] [--pick <option>] [--why "…"]
                                        the person's note already speaks to a card still open in the inbox (an answer
                                        waiting to be accepted, a choice, a finding): the card closes with their words
                                        and never comes back. A finding takes --as (fix: the note asks for a change;
                                        leave: it says it's fine); a choice takes --pick when the note named an option
                                        (then vs review apply), none when it didn't. vs review show lists the open cards
                                        beside a round's notes: make the link there, or the card comes back next round
  vs review apply <choice>              do what was picked: a variant's sources go back into the project, a take into
                                        mix.json, a paid option's step is printed to run (the pick was the yes)
  vs review finish --final out/<name>-vN-takeK.mp4 [out/<name>-16x9-vN-takeK.mp4]
                                        the finals are filed: the page says it's done, with the downloads and a way back in
                                        (opens a round on the final, stage final, if needed); then vs review wait
  vs review report [--md]               the dogfood's numbers: notes pinned, right first time, findings, QA misses,
                                        lessons, time reviewing, cost (--md: the table for DOGFOOD.md)
  vs review learn                       patterns in the studio's accepted notes: a tag in 2 projects, or 3 times in one
  vs review propose <tag> "<the rule>" [--to profile|lessons|check|kit|video]
                                        put one to the human: Every video, Every <kind>, This video only, or Ignore
  vs review promote <lesson> [--heading "Picture"] [--set mix.music_db=-18] [--chat "<their words>" --as remember|kind]
                                        write a rule the human decided into the studio (lessons.md, marked; a value into
                                        profile.json). Refused until they decided it; this-video-only stays in the project
  vs review rules [--json]              every rule promoted through review, where it lives, where it came from
  vs review forget <lesson>             take a promoted rule back out (and a profile value it set, if unchanged since)

The loop, every round: the human gives feedback (notes, answers to Claude's questions and fixes, finding decisions,
picks, a saved mix, approving the video); each waits in the page, held, with Undo, until they review the list and press
Approve & send; the agent's vs review wait picks it up (no wait running: they tell the agent "sent"). state.json (what the agent reads, and the render gate) holds only what
was sent; the page sees the held ones too. A note added after a send waits for its own send.

A note can be about one sound effect (a click on the timeline's Sound row; it plays alone): its "sound" says which cue
and the human's ask (quieter, louder, a different sound, remove it). The fix goes in cues.py; the next round measures it
in that version's cues (level, sound, moment), and flags an answer that went the other way. A visual note can carry an
ask too (the note box's buttons: move it, bigger, smaller, longer, shorter, less busy, remove it) and how far it reaches
(scope: here, project = everywhere in this video, studio = every video, which makes it a candidate rule).

Every answer is measured when the next round opens (a new version, or the same picture re-mixed: then the two mixes
are compared, the round's kept copy being the "before"), and gets a verdict (feedback.py): changed (the way it was asked),
removed (gone, as the answer said), other (changed, not as asked), contrary (the other way), unchanged, gone (and the
answer didn't say so), or unmeasured (with why: no map, or the note's measurement can't see what was asked). Implemented
(the agent says so), verified (the measurement saw it) and accepted (the human says so) are three different things: the
page and vs review show say which, and the human may accept over the measurement (it's recorded). A rename alone is not
a change.

Standing rules vs inspect enforces: every keep-clear zone in a sent note (nothing but what it was drawn over may enter
it, in that note's scene, on its cut), and every scene the human marked done (its frames and length are held to the
version it was approved in: that version's out/<…>-vN.review/comp.html). A finding the human dismisses stays dismissed.

Tags (resolve --tags): pacing.reveal pacing.hold pacing.cut · layout.safe-zone layout.overlap layout.spacing
  layout.keep-clear layout.balance · type.size type.contrast · copy.wording copy.fast-text · motion.style ·
  color.meaning · audio.music-level audio.sfx-level audio.sfx-choice · story.order · kit.bug · qa.miss (a real
  problem the checks should have caught: the report counts the accepted ones)
Accepted notes, the human's decisions and the rules promoted from them go to the studio's feedback.jsonl; taste never
goes to the public kit. The protocol these commands follow, for any skill: vs protocol review.

review/
  log.jsonl    every event, one per line, appended and never edited. The page and the agent both write it, through here,
               one writer at a time (two writers on one JSON file is how one silently overwrites the other)
  state.json   the current picture, folded from the log after every write: what the agent reads, and where the render
               gate reads findings.<id>.status
  frames/      a still per note: the frame, the target outlined in red, the mark drawn (a range: its start, middle, end)
"""
import argparse, fcntl, glob, json, os, re, subprocess, sys
from datetime import datetime, timezone

import vslib
import feedback  # the protocol, with nothing about video in it: phases, asks, verdicts, the hand-off, learning

REVIEW = "review"
LOG, STATE, FRAMES, LOCK = (f"{REVIEW}/log.jsonl", f"{REVIEW}/state.json", f"{REVIEW}/frames", f"{REVIEW}/.lock")
# who may write what: the page writes the human's events, the agent's commands write the agent's. The human's feedback
# can be held (the page marks it "held": true): it waits, undoable, until a round.sent after it covers it
HELD = {"note.added", "note.edited", "note.withdrawn", "note.answered", "note.accepted", "note.reopened",
        "finding.confirmed", "finding.dismissed", "choice.made", "mix.saved", "version.approved", "lesson.decided",
        "scene.done", "scene.reopened", "round.nonotes"}
HUMAN = HELD | {"round.sent", "undo", "friction.noted", "time.spent"}
AGENT = {"round.opened", "note.question", "note.resolved", "note.measured", "choice.offered", "choice.applied",
         "lesson.proposed", "finding.advised", "step.logged", "round.read", "finding.carried", "project.finished",
         "card.covered"}
# the human's ask on a visual note (the note box's buttons: what they want, never how) and on a sound (the timeline's
# Sound row); how far a note reaches (just here, this whole video = "project", every video = "studio": a candidate rule)
NOTE_ASKS = {"move", "bigger", "smaller", "longer", "shorter", "simpler", "remove"}
NOTE_SCOPES = {"here", "project", "studio"}
MIX_KEYS = {"take", "music_db", "duck_db", "sfx_db", "fx_on", "summary", "saved"}  # what mix.json keeps
STAGES = {k: v for k, v in vslib.CONTRACTS["stages"].items() if not k.startswith("_")}
PLAIN = {k: v for k, v in vslib.CONTRACTS["plain"].items() if not k.startswith("_")}
ALL_STAGES = {s for v in STAGES.values() for s in v}


def check_of(fid):
    """A finding's check from its id (vs inspect's f-<check>-…, qa.py's q-<check>-…): the longest check name that fits."""
    body = re.sub(r"^[fq]-", "", re.sub(r"^(9x16|16x9):", "", fid or ""))  # the other shape's carry its name first
    return max((c for c in PLAIN if body == c or body.startswith(c + "-")), key=len, default=None)
MARKS = {"none", "click", "box", "arrow", "keep-clear"}
# a note's life: draft (in an open round) → sent → question ⇄ (answered: sent) → resolved | wontdo → accepted | reopened
# (feedback.phase names the same life in the protocol's words: observation → intent → verification → acceptance)
WAITING = feedback.WAITING  # the agent owes these an answer before the next round opens


def ask_of(n):
    """The human's ask on a note: its own, or the one they gave a sound (a sound's ask lives on its cue address)."""
    return n.get("ask") or (n.get("sound") or {}).get("ask")


# The short list an answer is tagged from (vs review resolve --tags), and where a pattern of each would go once the
# human says so. Taste (preference, procedure, this video) stays in the studio, never in the public kit.
TAGS = {
    "pacing.reveal": ("preference", "how fast things arrive"),
    "pacing.hold": ("preference", "how long a thing stays"),
    "pacing.cut": ("preference", "where a cut lands"),
    "layout.safe-zone": ("check", "something a phone covers"),
    "layout.overlap": ("check", "two things fighting"),
    "layout.spacing": ("preference", "room around things"),
    "layout.keep-clear": ("check", "a zone that should stay empty"),
    "layout.balance": ("procedure", "how a frame is laid out"),
    "type.size": ("preference", "how big the words are"),
    "type.contrast": ("check", "words hard to read on their ground"),
    "copy.wording": ("procedure", "what the words say"),
    "copy.fast-text": ("check", "words gone before they can be read"),
    "motion.style": ("preference", "how things move"),
    "color.meaning": ("video", "what a color stands for in this video"),
    "audio.music-level": ("preference", "the music under the voice"),
    "audio.sfx-level": ("preference", "how loud the effects sit"),
    "audio.sfx-choice": ("procedure", "which sound"),
    "story.order": ("procedure", "what comes first"),
    "kit.bug": ("kit", "anyone using the kit would hit it"),
    "qa.miss": ("check", "a real problem the checks should have caught"),
}
DEST = {  # where a remembered pattern goes
    "profile": "profile.json (a value: checks, mix or brand)",
    "lessons": "lessons.md (a rule in the human's words)",
    "check": "a kit check, the threshold in profile.json checks",
    "kit": "the kit's scars.md + a regression test (a kit commit)",
    "video": "this video's plan, as a constraint",
}
KIND_DEST = {"preference": "profile", "procedure": "lessons", "check": "check", "kit": "kit", "video": "video"}


# the human's answer to one sound effect (the timeline's Sound row): a note the agent applies in cues.py, never a fader
SOUND_ASKS = {"quieter": "quieter", "louder": "louder", "different": "a different sound", "remove": "remove it"}


class Refused(Exception):
    """A write the rules don't allow, in a sentence a person can act on. seq: the event (its line in the log) that broke
    a rule, when folding found it."""

    def __init__(self, msg, seq=None):
        super().__init__(msg)
        self.seq = seq


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ── the snapshot: the log folded, event by event. Every rule lives here, so a write that breaks one is never appended ──
def empty():
    return {"review": 1, "events": 0, "round": None, "rounds": [], "notes": {}, "findings": {}, "choices": {},
            "mix": None, "approved": [], "lessons": {}, "friction": [], "time": {"secs": 0, "playing": 0}, "done": {},
            "advice": {}, "steps": [], "stage": None, "pending": [], "finished": None}


def fold(events, view="agent"):
    """The log, folded event by event. view="agent" is what the agent may act on (state.json): a held event, the human's
    feedback waiting in the page, counts only once a round.sent after it covers it. view="human" is the page's picture:
    the held ones too, listed in "pending" by their line in the log (for Undo). An undone event never happened."""
    undone = {e.get("of") for e in events if e.get("type") == "undo"}
    last_send = max((i for i, e in enumerate(events) if e.get("type") == "round.sent"), default=-1)
    S = empty()
    S["_since"], S["_marks"] = 0, []
    for i, e in enumerate(events):
        seq = i + 1
        if e.get("type") == "undo" or seq in undone:
            continue
        pending = bool(e.get("held")) and i > last_send
        if pending and view == "agent":
            continue
        try:
            apply(S, e)
        except Refused as x:
            raise Refused(f"event {seq} ({e.get('type')}): {x}", seq)
        if e.get("held"):
            S["_since"] += 1
        _step(S, e, seq, pending)
        if pending:
            S["pending"].append(seq)
    _stages(S)
    del S["_since"], S["_marks"]
    S["events"] = len(events)
    return S


def current(S):
    return S["rounds"][-1] if S["rounds"] else None


WAITING_FILE = f"{REVIEW}/waiting.json"


def agent_waiting():
    """True while a vs review wait is alive (its pid answers): the page then says Claude picks a send up on its own."""
    w = vslib.read_json(WAITING_FILE)
    try:
        os.kill(int(w["pid"]), 0)
        return True
    except (TypeError, KeyError, ValueError, ProcessLookupError, PermissionError):
        return False


def wait(args):
    """Block until the human sends, then print what they sent (vs review show, which tells the page Claude has it).
    The signal is positive: a send in the log that the agent hasn't read (sends > read_sends), checked every 2 s, so a
    send that landed before the wait started counts at once. The agent runs this in the background and is woken when it
    exits; the page shows "Claude is watching" while it runs. Exit 0 = sent, 2 = timed out (nothing was sent)."""
    import atexit, signal, time
    os.makedirs(REVIEW, exist_ok=True)
    # one watcher per project: a second one never hears the send the first one reads (an explainer, Oct 4, 2026: a
    # leftover watcher read the human's send and exited into a log nobody watched; the agent sat on the other one)
    if agent_waiting():
        old = vslib.read_json(WAITING_FILE)
        if not args.replace:
            print(f"⛔ another vs review wait is already watching this project (pid {old['pid']}, since {old.get('since')}): "
                  "it will read the send. Watch that one, or take over with vs review wait --replace", file=sys.stderr)
            sys.exit(3)
        os.kill(int(old["pid"]), signal.SIGTERM)
        for _ in range(50):
            if not agent_waiting():
                break
            time.sleep(0.1)
        print(f"replaced the watcher that was running (pid {old['pid']})", flush=True)
    json.dump({"pid": os.getpid(), "since": datetime.now().isoformat(timespec="seconds")}, open(WAITING_FILE, "w"))
    atexit.register(lambda: os.path.exists(WAITING_FILE) and vslib.read_json(WAITING_FILE).get("pid") == os.getpid()
                    and os.remove(WAITING_FILE))
    start, beat = time.time(), time.time()
    R = current(state())
    print(f"waiting for the human to send" + (f" round {R['n']} (v{R['version']})" if R else " (no round open yet)")
          + f": checking every 2 s, for up to {args.hours:g} h", flush=True)
    mixed = lambda: os.path.exists("mix.json") and os.path.getmtime("mix.json")
    mix0 = mixed()
    while True:
        R = current(state())
        if R and (R.get("sends") or 0) > (R.get("read_sends") or 0):
            print(f"sent: round {R['n']}, send {R['sends']}\n", flush=True)
            return show(argparse.Namespace(note=None, json=False))
        if mixed() != mix0:  # a Save in the Mix panel with no round open goes straight to mix.json
            print(f"mix saved: {(vslib.read_json('mix.json') or {}).get('summary', '')}", flush=True)
            return
        if time.time() - start > args.hours * 3600:
            print("timed out: nothing was sent", flush=True)
            sys.exit(2)
        if time.time() - beat > 900:
            beat = time.time()
            print(f"still waiting ({int((beat - start) // 60)} min)", flush=True)
        time.sleep(2)


def _mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def _q(x, n=60):
    x = " ".join((x or "").split())
    return x if len(x) <= n else x[: n - 1].rstrip() + "…"


ASKED = {"quieter": "quieter", "louder": "louder", "different": "a different sound", "remove": "remove it"}


def _step(S, e, seq, pending):
    """The human's steps (and the ones the agent logged for them), in plain words: the page's "How we got here", and
    its Review list (the pending ones). Findings decided one after another merge into one step."""
    t, R, at = e["type"], current(S), e.get("at")
    x = {}
    if t == "round.opened":
        text = f"Round {R['n']} opened on v{R['version']}" + (" (widescreen)" if R.get("cut") == "16x9" else "")
        x = {"version": R["version"]}
    elif t == "note.added":
        n = S["notes"][e["note"]["id"]]
        tm = n["time"].get("t", n["time"].get("t0"))
        words = f"“{_q(n['comment'])}”" if (n.get("comment") or "").strip() else "a mark, no words"
        if n.get("ask"):
            words = feedback.ASK_WORDS[n["ask"]] + (f", {words}" if (n.get("comment") or "").strip() else "")
        head = None
        if n.get("step"):
            head = f"About \u201c{_q(n['step'].get('text'), 48)}\u201d"
            text = f"{head}: {words}"
        elif n.get("sound"):
            sd = n["sound"]
            text = f"Sound {sd.get('sound')} at {_mmss(sd.get('t') or tm)}: " + (ASKED.get(sd.get("ask")) or "") + (
                f", {words}" if (n.get("comment") or "").strip() and sd.get("ask") else words if not sd.get("ask") else "")
        else:
            tg = (n.get("target") or {}).get("el")
            head = f"Note at {_mmss(tm)}" + (f" on {tg.split('/', 1)[-1].lstrip('~')}" if tg else "")
            text = f"{head}: {words}"
        x = {"t": tm, "version": n["version"], "note": n["id"], "head": head}
    elif t == "note.edited":  # the note's own line in the log says the new words; Undo on it takes both back
        added = next((st for st in reversed(S["steps"]) if st["kind"] == "note.added" and st.get("note") == e["id"]), None)
        if added:
            n = S["notes"][e["id"]]
            words = f"\u201c{_q(n['comment'])}\u201d" if (n.get("comment") or "").strip() else "a mark, no words"
            if added.get("head"):
                added["text"] = f"{added['head']}: {words}"
            added["seqs"].append(seq)
            return
        text, x = f"Changed note {e['id']}", {"note": e["id"]}
    elif t == "note.withdrawn":
        text, x = f"Took back note {e['id']}", {"note": e["id"]}
    elif t == "round.sent":
        k = 0
        for st in reversed(S["steps"]):
            if st["kind"] == "round.sent":
                break
            if st["by"] == "human" and st["kind"] != "round.opened":
                k += len(st["seqs"])
        text = (f"Sent round {R['n']}" if R["sends"] == 1 else f"Sent more to round {R['n']}") + (f" ({k} thing{'s' if k != 1 else ''})" if k else "")
    elif t in ("note.answered", "note.accepted", "note.reopened"):
        n = S["notes"][e["id"]]
        about = f"“{_q(n.get('comment'), 40)}”" if (n.get("comment") or "").strip() else n["id"]
        text = {"note.answered": f"Answered Claude's question on {about}: “{_q(e.get('text'))}”",
                "note.accepted": f"Claude's fix for {about}: looks right",
                "note.reopened": f"Claude's fix for {about}: still wrong, “{_q(e.get('text'))}”"}[t]
        x = {"note": n["id"], "t": n["time"].get("t", n["time"].get("t0"))}
    elif t in ("finding.confirmed", "finding.dismissed"):
        d = S["findings"][e["id"]]
        name = (PLAIN.get(d["check"]) or {}).get("name") or e["id"]
        verdict = "fix it" if t == "finding.confirmed" else "leave it"
        last = S["steps"][-1] if S["steps"] else None
        if last and last["kind"] == t and last.get("check") == d["check"] and last["pending"] == pending:
            last["seqs"].append(seq)
            last["findings"].append(e["id"])
            last["text"] = f"{name} ({len(last['seqs'])}×): {verdict.replace('it', 'them')}"
            return
        text, x = f"{name}: {verdict}", {"check": d["check"], "findings": [e["id"]]}
    elif t == "choice.made":
        c = S["choices"][e["id"]]
        lab = next((o.get("label") for o in c["options"] if o["id"] == e.get("pick")), None)
        text = (f"None of these, for “{_q(c.get('question'), 48)}”: “{_q(e.get('text'))}”" if e.get("pick") == "none"
                else f"Picked {e.get('pick', '').upper()}" + (f" ({_q(_unlettered(lab, e.get('pick')), 48)})" if lab else "")
                + f" for “{_q(c.get('question'), 48)}”")
        x = {"choice": c["id"]}
    elif t == "mix.saved":
        text = f"Saved the mix: {_q((e.get('mix') or {}).get('summary') or 'your levels', 110)}"
        last = S["steps"][-1] if S["steps"] else None
        if last and last["kind"] == t and last["pending"] == pending:  # saved again: one line, the latest levels
            last.update(text=text, at=e.get("when") or at or last["at"])
            last["seqs"].append(seq)
            return
    elif t == "version.approved":
        text = f"Approved v{e.get('version')}" + (" (widescreen)" if e.get("cut") == "16x9" else "") + ": it's done"
        x = {"version": e.get("version"), "cut": e.get("cut")}
    elif t == "lesson.decided":
        lz = S["lessons"][e["id"]]
        text = f"Lesson “{_q(lz.get('text'), 48)}”: " + {"remember": "every video", "kind": "every video like this", "project": "this video only",
                                                          "ignore": "ignore it"}[e["decision"]] + (f" (in chat: “{_q(e.get('said'), 40)}”)" if e.get("via") == "chat" else "")
        x = {"lesson": lz["id"]}
    elif t == "scene.done":
        text, x = f"Scene {e.get('segment')} is done", {"segment": e.get("segment")}
    elif t == "scene.reopened":
        text, x = f"Reopened scene {e.get('segment')}", {"segment": e.get("segment")}
    elif t == "round.nonotes":
        text = "No notes this round: nothing to change"
    elif t == "project.finished":
        text = "Claude filed the finals: done"
    elif t == "step.logged" and (e.get("text") or "").strip():
        text, x = e["text"].strip(), {"where": e.get("where")}
    else:
        return
    S["steps"].append({"seq": seq, "seqs": [seq], "at": e.get("when") or at or "", "kind": t, "by": e.get("by"), "text": text,
                       "pending": pending, "stage": None, **{k: v for k, v in x.items() if v is not None}})


def _unlettered(label, pick):
    """An option's label without the letter it already carries ("A · Red from the start" → "Red from the start")."""
    return re.sub(rf"^{re.escape((pick or '').upper())}\s*[·:.)-]\s*", "", label or "")


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _when(x):
    try:
        d = datetime.fromisoformat(x)
        return d if d.tzinfo else d.astimezone()
    except (TypeError, ValueError):
        return _EPOCH


def _stages(S):
    """Each step's stage: the latest mark at or before it (a round opened with --stage, a step logged with one); a round
    opened without one inherits the stage it was opened in. The video's stage is the latest mark."""
    marks = sorted(((_when(a), st) for a, st in S["_marks"]), key=lambda m: m[0])
    at = lambda x: next((st for w, st in reversed(marks) if w <= _when(x)), None)
    S["steps"].sort(key=lambda st: _when(st["at"]))
    for st in S["steps"]:
        st["stage"] = at(st["at"])
    for R in S["rounds"]:
        R["stage"] = R.get("stage") or at(R["opened"])
    S["stage"] = marks[-1][1] if marks else (current(S) or {}).get("stage")


def found(pool, e, what):
    x = pool.get(e.get("id"))
    if not x:
        raise Refused(f"no {what} {e.get('id')!r}")
    return x


def note_of(S, e):
    return found(S["notes"], e, "note")


def need(n, states, doing):
    if n["status"] not in states:
        raise Refused(f"{n['id']} is {n['status']}: it can't be {doing} (only when {' or '.join(sorted(states))})")


def apply(S, e):
    t, at, by = e.get("type"), e.get("at"), e.get("by")
    if t not in HUMAN | AGENT:
        raise Refused(f"unknown event type {t!r}")
    if by not in ("human", "agent") or (t in HUMAN) != (by == "human"):
        raise Refused(f"{t} is written by the {'human' if t in HUMAN else 'agent'}, not {by!r}")
    R = current(S)
    thread = lambda n, text, kind: n["thread"].append({"by": by, "type": kind, "text": text, "at": at})

    if t == "round.opened":
        if e.get("stage") and e["stage"] not in ALL_STAGES:
            raise Refused(f"no stage {e['stage']!r}: one of {', '.join(sorted(ALL_STAGES))}")
        if R and R["status"] == "open" and any(S["notes"][i]["status"] == "draft" for i in R["notes"]):
            raise Refused(f"round {R['n']} is still open with notes the human hasn't sent")
        if R and R["status"] == "open" and R["video"] == e.get("video"):
            raise Refused(f"round {R['n']} is already open on {R['video']}")
        owed = [i for i, n in S["notes"].items() if n["status"] in WAITING]
        if owed:
            raise Refused(f"answer every note first: {', '.join(owed)} (vs review resolve or ask)")
        for k in ("version", "video"):
            if e.get(k) in (None, ""):
                raise Refused(f"a round needs its {k}")
        if R:
            R["status"] = "closed"
            # only the latest round's cards wait in the inbox (a reviewer, Oct 5, 2026): an answer the person already had in
            # front of them, through a round they sent without accepting or reopening it, has lapsed. They moved on
            # with words instead, and it never comes back as a card
            for n in S["notes"].values():
                if n["status"] in feedback.ANSWERED and n.get("shown_in") == R["n"]:
                    n["lapsed"] = R["n"]
        S["rounds"].append({"n": len(S["rounds"]) + 1, "version": e["version"], "cut": e.get("cut"), "video": e["video"],
                            **({"cuts": e["cuts"]} if e.get("cuts") else {}), **({"kept": e["kept"]} if e.get("kept") else {}),
                            "size": e.get("size"), "status": "open", "opened": at, "sent": None, "notes": [],
                            "asked": e.get("asked", []), "stage": e.get("stage"), "sends": 0, "last_sent": None,
                            "read": None, "read_sends": 0})
        if e.get("stage"):
            S["_marks"].append((at, e["stage"]))
    elif t == "note.added":
        if not R or R["status"] == "closed":
            raise Refused("no round is open: the agent opens one on a rendered version (vs review open)")
        n = dict(e.get("note") or {})
        if not n.get("id"):
            raise Refused("a note needs an id")
        if n["id"] in S["notes"]:
            raise Refused(f"{n['id']} exists")
        tm = n.get("time") or {}
        if not ("t" in tm or ("t0" in tm and "t1" in tm and tm["t1"] > tm["t0"])):
            raise Refused("a note needs its moment: {t} or a range {t0, t1} that ends after it starts")
        m = n.get("mark") or {"type": "none"}
        if m.get("type") not in MARKS:
            raise Refused(f"mark {m.get('type')!r} isn't one of: {', '.join(sorted(MARKS))}")
        if not (n.get("comment") or "").strip() and not n.get("target") and m["type"] == "none" and not n.get("ask"):
            raise Refused("a note needs words, a target, a mark or an ask")
        if n.get("cut") and R.get("cuts") and n["cut"] not in [c["cut"] for c in R["cuts"]]:
            raise Refused(f"round {R['n']} has no {n['cut']} cut")
        if n.get("ask") is not None and n["ask"] not in NOTE_ASKS:
            raise Refused(f"ask {n['ask']!r} isn't one of: {', '.join(sorted(NOTE_ASKS))}")
        if n.get("scope") is not None and n["scope"] not in NOTE_SCOPES:
            raise Refused(f"scope {n['scope']!r} isn't one of: {', '.join(sorted(NOTE_SCOPES))}")
        # added after Send: held, it waits for its own send; from an older page, it went straight to the agent
        late = R["status"] == "sent"
        n.update({"round": R["n"], "version": R["version"], "cut": n.get("cut") or R["cut"], "mark": m,
                  "status": "sent" if late and not e.get("held") else "draft", "late": late, "added": at, "thread": [],
                  "resolution": None, "measured": None})
        S["notes"][n["id"]] = n
        R["notes"].append(n["id"])
    elif t == "note.edited":
        n = note_of(S, e)
        need(n, {"draft"}, "edited")
        if e.get("ask") is not None and e["ask"] not in NOTE_ASKS or e.get("scope") is not None and e["scope"] not in NOTE_SCOPES:
            raise Refused("an ask or a scope that isn't on the list")
        for k in ("comment", "mark", "also", "target", "time", "visible", "findings", "segment", "scene", "crumbs", "ask", "scope"):
            if k in e:
                n[k] = e[k]
    elif t == "note.withdrawn":
        n = note_of(S, e)
        need(n, {"draft"}, "withdrawn")
        n["status"] = "withdrawn"
    elif t == "round.sent":
        if not R or R["status"] == "closed":
            raise Refused("there's no open round to send")
        if R["status"] == "sent" and not S["_since"]:
            raise Refused(f"round {R['n']} is sent, and nothing new has been added since")
        R.update(status="sent", sent=R["sent"] or at, last_sent=at, sends=R.get("sends", 0) + 1)
        S["_since"] = 0
        # every answer waiting on the person's call was in front of them for this send (by event order, not the clock):
        # if the next round opens and it still waits, it lapses
        for n in S["notes"].values():
            if n["status"] in feedback.ANSWERED and not n.get("lapsed"):
                n["shown_in"] = R["n"]
        for i in R["notes"]:
            if S["notes"][i]["status"] == "draft":
                S["notes"][i]["status"] = "sent"
    elif t == "round.read":  # the agent read what was sent: the page shows "Claude has it"
        if R:
            R.update(read=at, read_sends=R.get("sends", 0))
    elif t == "note.question":
        n = note_of(S, e)
        need(n, WAITING, "asked about")
        n["status"] = "question"
        thread(n, e.get("text", ""), "question")
    elif t == "note.answered":
        n = note_of(S, e)
        need(n, {"question"}, "answered")
        n["status"] = "sent"
        thread(n, e.get("text", ""), "answer")
    elif t == "note.resolved":
        n = note_of(S, e)
        need(n, WAITING | {"question"}, "resolved")
        if not (e.get("said") or "").strip():
            raise Refused("say what changed, or why not (--said)")
        if e.get("expect") is not None and e["expect"] not in feedback.EXPECT:
            raise Refused(f"expect {e['expect']!r} isn't one of: {', '.join(sorted(feedback.EXPECT))}")
        n["status"] = "wontdo" if e.get("outcome") == "wontdo" else "resolved"
        n["resolution"] = {k: e.get(k) for k in ("outcome", "said", "files", "tags", "version", "renamed", "removed", "expect")}
        n["resolution"]["at"] = at
        n["measured"] = None  # a new answer is measured afresh: an earlier answer's measurement isn't this one's
        thread(n, e["said"], n["status"])
    elif t == "note.measured":
        note_of(S, e)["measured"] = e.get("measured")
    elif t == "note.accepted":
        n = note_of(S, e)
        need(n, {"resolved", "wontdo"}, "accepted")
        n["status"] = "accepted"
        n["accepted"] = {"at": at, "verdict": feedback.verdict(n.get("measured"))}  # what the measurement said when they did
    elif t == "note.reopened":
        n = note_of(S, e)
        need(n, {"resolved", "wontdo"}, "reopened")
        n["status"] = "reopened"
        thread(n, e.get("text", ""), "reopened")
    elif t in ("finding.confirmed", "finding.dismissed"):  # the page's Fix it / Leave it
        if not e.get("id"):
            raise Refused("which finding?")
        adv = S["advice"].get(e["id"])
        S["findings"][e["id"]] = {"status": t.split(".")[1], "reason": e.get("reason"), "at": at,
                                  "round": R and R["n"], "check": e.get("check") or check_of(e["id"]),
                                  "followed": None if not adv else adv["advice"] == ("fix" if t == "finding.confirmed" else "leave")}
    elif t == "finding.carried":  # an answer the human gave this same finding in an earlier round stands (vs review open)
        if e.get("status") not in ("confirmed", "dismissed") or not e.get("id"):
            raise Refused("a carried finding needs its id and the earlier answer")
        S["findings"][e["id"]] = {"status": e["status"], "reason": e.get("reason"), "at": at, "round": R and R["n"],
                                  "check": e.get("check") or check_of(e["id"]), "followed": e.get("followed"),
                                  "carried": {"from": e.get("from"), "round": e.get("from_round")}}
    elif t == "card.covered":
        # the person's own note already speaks to a card in the inbox (a fix card, a finding, a choice): the card is
        # closed by those words, says so, and never comes back (a reviewer, Oct 5, 2026: "each round should only contain the
        # things that need reviewing in that round and haven't been addressed through any means"). The agent makes the
        # link, since reading what a note is about is judgment; the note's words are the decision
        by = found(S["notes"], {"id": e.get("note")}, "note")  # the note whose words answer it ("by" is who wrote the event)
        if by["status"] in ("draft", "withdrawn"):
            raise Refused(f"{by['id']} is {by['status']}: only a note the person sent can answer a card")
        words = (by.get("comment") or "").strip() or None
        cov = {"by": by["id"], "at": at, "said": words, "why": e.get("why")}
        card = e.get("card") or ""
        if card in S["notes"]:
            n = S["notes"][card]
            if card == by["id"]:
                raise Refused("a note can't cover itself")
            need(n, feedback.ANSWERED, "covered by a later note")
            n["covered"] = cov
        elif card in S["choices"]:
            c = S["choices"][card]
            if c.get("picked"):
                raise Refused(f"{card} is already picked ({c['picked']})")
            pick = e.get("pick")
            if pick is not None and pick != "none" and pick not in [o["id"] for o in c["options"]]:
                raise Refused(f"{pick!r} isn't one of {card}'s options")
            c["covered"] = cov
            if pick is not None:  # the note named an option: it's their pick, in their words, and it gets applied
                c.update(picked=pick, picked_at=at, said=words, via="note")
                c.setdefault("picks", []).append({"pick": pick, "said": words, "at": at, "via": by["id"]})
        elif check_of(card):
            if e.get("as") not in ("fix", "leave"):
                raise Refused("a finding covered by a note is fix (the note asks for a change) or leave (it says it's fine)")
            adv = S["advice"].get(card)
            S["findings"][card] = {"status": "confirmed" if e["as"] == "fix" else "dismissed", "reason": words, "at": at,
                                   "round": R and R["n"], "check": check_of(card), "covered": cov,
                                   "followed": None if not adv else adv["advice"] == e["as"]}
        else:
            raise Refused(f"no card {card!r}: a note (n-…), a choice (c-…) or a finding (f-… / q-…)")
    elif t == "round.nonotes":  # the human looked and has nothing to change: a send with no notes still says so
        if not R or R["status"] == "closed":
            raise Refused("no round is open")
        R["nonotes"] = at
    elif t == "project.finished":  # the agent filed the finals: the page shows the downloads and the way back in
        S["finished"] = {"files": e.get("files") or [], "at": at, "round": R and R["n"]}
    elif t == "finding.advised":
        ids = e.get("ids") or []
        if not ids or e.get("advice") not in ("leave", "fix"):
            raise Refused("advice is leave or fix, on at least one finding")
        if not (e.get("plain") or "").strip():
            raise Refused("say what it is in plain words")
        for i in ids:
            S["advice"][i] = {"advice": e["advice"], "plain": e["plain"], "why": e.get("why"), "check": e.get("check") or check_of(i),
                              "ids": ids, "at": at}
    elif t == "step.logged":  # a step the human took outside the page; a stage alone marks where the video got to
        if not (e.get("text") or "").strip() and not e.get("stage"):
            raise Refused("a step needs its words, or a stage")
        if e.get("stage"):
            if e["stage"] not in ALL_STAGES:
                raise Refused(f"no stage {e['stage']!r}: one of {', '.join(sorted(ALL_STAGES))}")
            S["_marks"].append((e.get("when") or at, e["stage"]))
    elif t == "choice.offered":
        c = dict(e.get("choice") or {})
        ids = [o.get("id") for o in c.get("options") or []]
        if not c.get("id") or len(ids) < 2:
            raise Refused("a choice needs an id and at least two options")
        if not all(ids) or len(set(ids)) != len(ids) or "none" in ids:
            raise Refused("each option needs its own id (and \"none\" is the human's answer, not an option)")
        if c.get("for"):  # the choice is the agent's question back on a note: the note waits for the pick
            n = found(S["notes"], {"id": c["for"]}, "note")
            need(n, WAITING | {"question"}, "answered with a choice")
            n["status"] = "question"
            thread(n, f"{c['id']}: {c.get('question')}", "choice")
        c.update(picked=None, offered=at, round=R and R["n"], picks=[], applied=None)
        S["choices"][c["id"]] = c
    elif t == "choice.made":
        c = found(S["choices"], e, "choice")
        pick, said = e.get("pick"), (e.get("text") or "").strip() or None
        if pick == "none" and not said:
            raise Refused("none of these: say what would work instead")
        if pick != "none" and pick not in [o["id"] for o in c["options"]]:
            raise Refused(f"{pick!r} isn't one of {c['id']}'s options")
        c.update(picked=pick, picked_at=at, said=said)
        c.setdefault("picks", []).append({"pick": pick, "said": said, "at": at})
        n = S["notes"].get(c.get("for") or "")
        if n:  # the pick answers the note's question: it's the agent's again
            if n["status"] == "question":
                n["status"] = "sent"
            lab = next((o.get("label") for o in c["options"] if o["id"] == pick), None)
            thread(n, ("none of these" if pick == "none" else f"picked {pick}" + (f" ({lab})" if lab else ""))
                   + (f": {said}" if said else ""), "answer")
    elif t == "choice.applied":
        c = found(S["choices"], e, "choice")
        if not c.get("picked") or c["picked"] != e.get("pick"):
            raise Refused(f"{c['id']}'s pick is {c.get('picked')!r}, not {e.get('pick')!r}")
        c["applied"] = {"pick": e["pick"], "said": e.get("said"), "at": at}
    elif t == "mix.saved":
        S["mix"] = {**(e.get("mix") or {}), "at": at}
    elif t == "version.approved":
        S["approved"].append({"version": e.get("version"), "cut": e.get("cut"), "video": e.get("video"), "at": at})
    elif t == "lesson.proposed":
        lz = dict(e.get("lesson") or {})
        if not lz.get("id"):
            raise Refused("a lesson needs an id")
        lz.update(decision=None, proposed=at)
        S["lessons"][lz["id"]] = lz
    elif t == "lesson.decided":
        lz = found(S["lessons"], e, "lesson")
        if e.get("decision") not in feedback.DECISION_SCOPE:
            raise Refused("decide remember (every video), kind (every video of this kind), video (this one only) or ignore")
        if e.get("via") == "chat" and not (e.get("said") or "").strip():
            raise Refused("a decision made in chat keeps the human's own words (said): the agent records it, never makes it")
        lz.update(decision=e["decision"], decided=at, **({"via": e["via"], "said": e["said"].strip(), "recorded_by": e.get("recorded_by") or "agent"}
                                                         if e.get("via") else {}))
    elif t == "friction.noted":
        if not (e.get("text") or "").strip():
            raise Refused("say what's in the way")
        S["friction"].append({"text": e["text"].strip(), "where": e.get("where"), "at": at, "round": R and R["n"]})
    elif t == "scene.done":  # "this scene is done": vs inspect locks its frames to the version it was approved in
        seg = e.get("segment")
        if not seg:
            raise Refused("which scene?")
        if not R:
            raise Refused("no round: a scene is done in a version the human is reviewing")
        S["done"][seg] = {"version": R["version"], "cut": R["cut"], "video": R["video"], "at": at}
    elif t == "scene.reopened":
        if e.get("segment") not in S["done"]:
            raise Refused(f"{e.get('segment')} isn't marked done")
        del S["done"][e["segment"]]
    elif t == "time.spent":  # the page's own clock: seconds reviewing (visible and in use), and of those, playing
        S["time"] = {"secs": S["time"]["secs"] + float(e.get("secs") or 0), "playing": S["time"]["playing"] + float(e.get("playing") or 0)}
    S["round"] = current(S) and current(S)["n"]


# ── the diary: read, and append through the one lock ──
def read_log():
    if not os.path.exists(LOG):
        return []
    out = []
    for i, line in enumerate(open(LOG), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                raise SystemExit(f"⛔ {LOG} line {i} isn't JSON (was it edited by hand?): fix that line, the rest is fine")
    return out


def state(view="agent"):
    """The snapshot, folded fresh from the diary (state.json on disk can be from an older engine; the log is the truth).
    view="human": the page's picture, with the human's held feedback in."""
    return fold(read_log(), view)


def _next_id(_S, prefix, pool):
    k = 1 + max([int(x.split("-")[1]) for x in pool if re.fullmatch(rf"{prefix}-\d+", x)] or [0])
    return f"{prefix}-{k:04d}"


def append(events, by):
    """Append events (dicts with a type) as `by`, fold, write state.json (the agent's view). All or nothing: if any event
    breaks a rule, nothing is written and Refused says why. An undo takes along the held events that depend on what it
    undoes. → (the writer's view of the state: the page's for the human, state.json's for the agent; the events as
    written)."""
    os.makedirs(REVIEW, exist_ok=True)
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        old = read_log()
        S0 = fold(old, "human")
        new = []
        for e in events:
            e = {**e, "at": now(), "by": by}
            t = e.get("type")
            if t == "note.added":  # an id is never reused, an undone note's included
                e["note"] = {**(e.get("note") or {}), "id": _next_id(None, "n", _ids(old + new, "note.added", "note"))}
            elif t == "choice.offered":
                e["choice"] = {**(e.get("choice") or {}), "id": _next_id(None, "c", [*S0["choices"], *_ids(new, "choice.offered", "choice")])}
            elif t == "lesson.proposed":
                e["lesson"] = {**(e.get("lesson") or {}), "id": _next_id(None, "l", [*S0["lessons"], *_ids(new, "lesson.proposed", "lesson")])}
            elif t == "undo":
                _undoable(old + new, e)
            elif t == "round.opened" and S0["pending"]:
                k = len(S0["pending"])
                raise Refused(f"round.opened: the human has {k} thing{'s' if k > 1 else ''} in the page they haven't sent: "
                              "ask them to Approve & send (or undo it) first")
            if e.get("held") and (by != "human" or t not in HELD):
                raise Refused(f"{t}: only the human's feedback can wait to be sent")
            new.append(e)
        new = _cascade(old, new)
        try:
            H, S = fold(old + new, "human"), fold(old + new, "agent")
        except Refused as x:
            if x.seq and x.seq > len(old):
                raise Refused(f"{(old + new)[x.seq - 1].get('type')}: {str(x).split(': ', 1)[-1]}")
            raise
        with open(LOG, "a") as f:
            for e in new:
                f.write(json.dumps(e, separators=(",", ":")) + "\n")
        tmp = STATE + ".tmp"
        json.dump(S, open(tmp, "w"), indent=1)
        os.replace(tmp, STATE)
    sent = _sent_now(old, new)
    _to_studio(S, sent)
    _to_dogfood(S, new)
    _mix_on_send(S, sent)
    _forget_stills(old + new, new)
    return (H if by == "human" else S), new


def _ids(events, kind, key):
    return {(e.get(key) or {}).get("id") for e in events if e.get("type") == kind}


def _undoable(events, e):
    """Undo is for the human's held feedback that hasn't been sent: once sent, Claude may have acted on it."""
    k = e.get("of")
    if not isinstance(k, int) or not 1 <= k <= len(events):
        raise Refused("undo: which event? (its line in the log)")
    x = events[k - 1]
    if x.get("by") != "human" or not x.get("held") or x.get("type") not in HELD:
        raise Refused(f"undo: {x.get('type')} can't be undone")
    if any(y.get("type") == "undo" and y.get("of") == k for y in events):
        raise Refused("undo: that's already undone")
    if any(y.get("type") == "round.sent" for y in events[k:]):
        raise Refused("undo: that was already sent, and Claude may have acted on it: add a note instead")


def _cascade(old, new):
    """An undo takes along the held, unsent events that need what it undoes (an edit of an undone note): undoing them
    one by one would be refused, so they go with it."""
    if not any(e.get("type") == "undo" for e in new):
        return new
    for _ in range(200):
        try:
            fold(old + new, "human")
            return new
        except Refused as x:
            evs = old + new
            j = x.seq
            ok = j and evs[j - 1].get("held") and evs[j - 1].get("by") == "human" and not any(y.get("type") == "round.sent" for y in evs[j:])
            if not ok:
                raise
            new = new + [{"type": "undo", "of": j, "cascade": True, "at": now(), "by": "human"}]
    raise Refused("undo: too much depends on it")


def _sent_now(old, new):
    """The events these writes made real for the agent: the held ones a send in them covered (undone ones never count),
    and anything written unheld."""
    evs = old + new
    undone = {e.get("of") for e in evs if e.get("type") == "undo"}
    sends = [i for i, e in enumerate(evs) if e.get("type") == "round.sent" and i >= len(old)]
    out = []
    if sends:
        prev = max((i for i, e in enumerate(old) if e.get("type") == "round.sent"), default=-1)
        out = [evs[i] for i in range(prev + 1, sends[-1]) if evs[i].get("held") and (i + 1) not in undone]
    return out + [e for e in new if not e.get("held") and e.get("type") not in ("undo", "round.sent")]


def _mix_on_send(S, sent):
    """A mix saved in the page reaches mix.json when it's sent (vs mix --final reads it); held, it's still the human's."""
    if any(e["type"] == "mix.saved" and e.get("held") for e in sent) and S.get("mix"):
        json.dump({k: S["mix"][k] for k in MIX_KEYS if k in S["mix"]}, open("mix.json", "w"), indent=1)


def _forget_stills(evs, new):
    """An undone note's still goes with it."""
    for e in new:
        if e.get("type") == "undo":
            x = evs[e["of"] - 1]
            if x.get("type") == "note.added":
                f = f"{FRAMES}/{(x.get('note') or {}).get('id')}.jpg"
                if os.path.exists(f):
                    os.remove(f)


# ── what the studio remembers across projects: accepted notes (tagged), the human's decisions on lessons, the rules
#    promoted from them (and taken back), and the page's tool-problem reports. Project state stays in review/; this file
#    is the studio's, so a pattern can be counted across videos. ──
def feedback_path():
    s = vslib.studio_root()
    return os.path.join(s, "feedback.jsonl") if s else None


def studio_feedback():
    f = feedback_path()
    return [json.loads(l) for l in open(f) if l.strip()] if f and os.path.exists(f) else []


def kind_of():
    """What kind of video this project is (a lesson can reach every video of one kind)."""
    return "explainer" if os.path.exists("plan.json") else "reel"


def _studio_write(lines):
    f = feedback_path()
    if not f or not lines:
        return
    with open(f, "a") as fh:
        for l in lines:
            fh.write(json.dumps(l) + "\n")


def _to_studio(S, new):
    """An accepted note, a decided lesson and a tool problem go to the studio's feedback.jsonl (no studio: nothing to
    remember into)."""
    lines = []
    for e in new:
        if e["type"] == "note.accepted":
            n = S["notes"][e["id"]]
            lines.append({"kind": "note", "project": vslib.project_name(), "of_kind": kind_of(), "note": n["id"],
                          "tags": (n.get("resolution") or {}).get("tags") or [], "comment": n.get("comment"),
                          "said": (n.get("resolution") or {}).get("said"), "version": n["version"], "at": e["at"],
                          **({"ask": ask_of(n)} if ask_of(n) else {}), **({"scope": n["scope"]} if n.get("scope") else {}),
                          **({"verdict": n["accepted"]["verdict"]} if (n.get("accepted") or {}).get("verdict") else {})})
        elif e["type"] == "lesson.decided":
            lz = S["lessons"][e["id"]]
            lines.append({"kind": "lesson", "project": vslib.project_name(), "of_kind": kind_of(), "lesson": lz["id"], "tag": lz.get("tag"),
                          "text": lz.get("text"), "dest": lz.get("dest"), "decision": lz["decision"], "at": e["at"],
                          "via": lz.get("via") or "page", **({"said": lz["said"], "recorded_by": lz.get("recorded_by")} if lz.get("via") == "chat" else {})})
        elif e["type"] == "friction.noted":
            lines.append({"kind": "friction", "project": vslib.project_name(), "text": e.get("text"), "where": e.get("where"), "at": e["at"]})
    _studio_write(lines)


def _to_dogfood(S, new):
    """The page's Problem? button (report a tool problem): a line in the kit's DOGFOOD.md friction log when the kit has
    one (a development checkout; the published kit doesn't), never the fix list. The studio keeps every report anyway."""
    f = os.environ.get("VIDEO_KIT_DOGFOOD") or os.path.join(vslib.KIT, "DOGFOOD.md")  # tests point it elsewhere
    lines = [e for e in new if e["type"] == "friction.noted"]
    if not lines or not os.path.exists(f):
        return
    doc = open(f).read()
    R, day = current(S), datetime.now()
    at = f", round {R['n']}, v{R['version']}" if R else ""
    add = "".join(f"- {day:%b} {day.day} · Review Studio ({e.get('where') or 'the page'}{at}, {vslib.project_name()}): "
                  f"{e['text'].strip()} (from the page's Problem? button)\n" for e in lines)
    i = doc.find("\n## Verdict")  # the friction log is the section before the verdict
    doc = doc.rstrip("\n") + "\n" + add if i < 0 else doc[:i].rstrip("\n") + "\n" + add + doc[i:]
    open(f, "w").write(doc)


def candidates(project=None):
    """Patterns worth asking about (feedback.patterns: plain counting; the agent only words the question)."""
    project = project or vslib.project_name()
    pending = {lz.get("tag") for lz in state()["lessons"].values() if lz["decision"] is None} if os.path.exists(LOG) else set()
    return feedback.patterns(studio_feedback(), project, kind_of(), pending)


# ── versions: a render is out/<name>[-16x9]-vN.mp4; its mixes add -takeK / -sfx / -mixed ──
def version_of(video):
    b = os.path.splitext(os.path.basename(video))[0]
    m = re.search(r"-v(\d+)(?:-(?:take\d+|sfx|mixed))?$", b)
    if not m:
        raise Refused(f"{video}: not a rendered version (out/<name>-vN.mp4)")
    base = os.path.join(os.path.dirname(video), b[: m.start()] + f"-v{m.group(1)}")
    return int(m.group(1)), base


def partner(video):
    """The same version in the other shape, when it's rendered: an explainer keeps both in out/ (<name>-vN… and
    <name>-16x9-vN…); a reel's widescreen cut is its own project beside this one (<slug>-16x9/out/<slug>-16x9-vN.mp4),
    and the vertical's is <slug> beside a -16x9 project. The same take when there is one, else the bare render."""
    d, b = os.path.split(video)
    m = re.search(r"-v(\d+)((?:-(?:take\d+|sfx|mixed))?)\.mp4$", b)
    if not m:
        return None
    name, v, tail = b[: m.start()], m.group(1), m.group(2)
    proj = os.path.basename(os.getcwd())
    if name.endswith("-16x9"):
        other = name[:-5]
        cands = [os.path.join(d, f"{other}-v{v}{{}}.mp4")]
        if proj.endswith("-16x9"):
            cands.append(os.path.join("..", proj[:-5], "out", f"{other}-v{v}{{}}.mp4"))
    else:
        cands = [os.path.join(d, f"{name}-16x9-v{v}{{}}.mp4"), os.path.join("..", f"{proj}-16x9", "out", f"{name}-16x9-v{v}{{}}.mp4")]
    for t in ([tail, ""] if tail else [""]):
        for c in cands:
            if os.path.exists(c.format(t)):
                return c.format(t)
    return None


def cut_of(video):
    W, H, _ = probe(video)
    return "16x9" if W > H else "9x16"


def keep(video, rnd, cut):
    """A copy of the render a round shows, so the next round has a "before" even when the file is written over in place
    (a sound fix re-mixes out/<name>-vN-takeK.mp4 under the same name: on Oct 5, 2026 the render three sound answers
    were made on was gone by the time they could be measured). A clone where the disk can make one (APFS, Btrfs, XFS)
    costs no space; elsewhere it's a copy. out/ is the project's renders, never committed. → its path, or None."""
    dst = f"out/watched/round{rnd}-{cut}.mp4"
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            os.remove(dst)
        clone = ["cp", "-c"] if sys.platform == "darwin" else ["cp", "--reflink=auto"]
        if subprocess.run(clone + [video, dst], capture_output=True).returncode != 0:
            import shutil
            shutil.copyfile(video, dst)
        return dst
    except OSError as x:
        print(f"⚠️  couldn't keep a copy of {video} ({x}): a fix answered on it can't be measured if it's written over")
        return None


def watched(R, cut):
    """What the person actually watched in round R: its kept copy (the file itself may have been written over since)."""
    k = (R.get("kept") or {}).get(cut)
    return k if k and os.path.exists(k) else cut_video(R, cut)


def cut_video(R, cut):
    """The round's render of one shape (its own video when the round shows one shape)."""
    for c in (R or {}).get("cuts") or []:
        if c["cut"] == cut:
            return c["video"]
    return (R or {}).get("video")


_probes = {}


def probe(video):
    if video not in _probes:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height,r_frame_rate:format=duration", "-of", "json", video],
                             capture_output=True, text=True, check=True).stdout
        j = json.loads(out)
        s = j["streams"][0]
        n, d = (s.get("r_frame_rate") or "30/1").split("/")
        _probes[video] = (int(s["width"]), int(s["height"]), float(j["format"]["duration"]), float(n) / float(d or 1))
    return _probes[video][:3]


def fps_of(video):
    probe(video)
    return _probes[video][3]


def newest_video():
    vids = [v for v in glob.glob("out/*.mp4") if re.search(r"-v\d+(-take\d+|-mixed)?\.mp4$", v)]
    if not vids:
        raise Refused("nothing rendered yet in out/: vs build renders a version")
    # the newest version, and of its files the mixed one (with the sound) over the bare render
    key = lambda v: (version_of(v)[0], os.path.getmtime(v), "-take" in v or "-mixed" in v)
    return max(vids, key=key)


def inspected(base, fingerprint):
    """The findings vs inspect wrote for this version: its archive (out/<…>-vN.review/), else the build's own if it's
    the same composition. None when nobody can tell."""
    for f in (f"{base}.review/findings.json", "build/findings.json"):
        F = vslib.read_json(f)
        if F and (not fingerprint or F.get("fingerprint") == fingerprint):
            return F
    return None


def element_map(base, fingerprint):
    """The element map vs inspect made for this version: its archive, else the build's own if it's the same
    composition. None when there's none to trust."""
    for f in (f"{base}.review/elements.json", "build/elements.json"):
        E = vslib.read_json(f)
        if E and (not fingerprint or E.get("fingerprint") == fingerprint):
            return E
    return None


# ── proof of what changed: a resolved note's target, measured in the new version's element map ──
def _box_at(e, t):
    b = None
    for x in e["boxes"]:
        if x[0] > t + 1e-3:
            break
        b = x
    return (b or e["boxes"][0])[1:] if e["boxes"] else None


def _overlaps(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def _area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


BACKDROP = re.compile(r"^frame/|/~ex-(spot|mote|glow|dust)(#\d+)?$")  # the ground every frame stands on, never "busy" (= maps.js)


def visible_at(E, t):
    """What the element map says is on screen at a moment (as the page counts it for a note's "visible"), minus the
    backdrop."""
    h = E.get("step", 0.15) / 2 + 1e-3
    return {x["id"] for x in E["items"] if not BACKDROP.search(x["id"]) and any(a - h <= t <= b + h for a, b in x.get("on") or [])}


def _busy(n, E, t):
    """How many more (or fewer) things are on screen at the note's moment than when the human wrote it."""
    if not E or n.get("visible") is None:
        return None
    old = {v for v in n["visible"] if not BACKDROP.search(v)}
    return len(visible_at(E, t)) - len(old)


def _judge(m, n, can):
    """The protocol's verdict on a measurement (feedback.judge), written into it with the flag it implies."""
    res = n.get("resolution") or {}
    m["verdict"], m["expected_met"], m["flag"] = feedback.judge(
        m.get("changes"), ask=ask_of(n), expect=res.get("expect"), outcome=res.get("outcome") or "resolved",
        removed=bool(res.get("removed")), can=can)
    m["strength"] = feedback.strength(ask_of(n), res.get("expect"), m["verdict"])
    if m["verdict"] == "unmeasured":  # what was asked is out of this measurement's sight: say which, beside what it saw
        m["why"] = m["flag"].removeprefix("not measured: ")
    else:
        m.pop("why", None)
    return m


ELEMENT_DIMS = ("place", "size", "time", "words", "presence", "busy", "pixels")


def measure(n, E, size):
    """What the new version did to a note's target, from vs inspect's map: where its box went at the note's moment (in
    pixels of the new frame), whether its words or its time on screen changed, whether it left the keep-clear zones the
    human drew, how far it now is from where the human's arrow pointed, and how much is on screen around it. Each real
    change becomes a dimension in m["changes"]; feedback.judge turns them into the verdict (changed, other, contrary,
    unchanged, gone). A rename alone is not a change: the renamed target is measured like any other."""
    tgt, res = n.get("target") or {}, n.get("resolution") or {}
    name = res.get("renamed") or tgt.get("el")
    if not name or not tgt.get("box"):
        return None
    t = n["time"].get("t", n["time"].get("t0"))
    W, H = size
    e = next((x for x in E["items"] if x["id"] == name), None)
    m = {"el": name, "t": t, "flag": None, "changes": {}}
    if not e or not e["on"]:
        m["gone"] = True
        m["changes"]["presence"] = -1
        return _judge(m, n, ELEMENT_DIMS)
    h = E.get("step", 0.15) / 2 + 1e-3
    span = next(([a, b] for a, b in e["on"] if a - h <= t <= b + h), None)
    if not span:  # not on screen at the note's moment any more: report where it is in time
        m["off_at_t"] = True
        m["on"] = min(e["on"], key=lambda s: min(abs(s[0] - t), abs(s[1] - t)))
    ob, nb = tgt["box"], _box_at(e, t if span else m["on"][0])
    c = lambda b: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    (ox, oy), (nx, ny) = c(ob), c(nb)
    m.update(old_box=ob, new_box=nb, dx=round((nx - ox) * W), dy=round((ny - oy) * H),
             dw=round(((nb[2] - nb[0]) - (ob[2] - ob[0])) * W), dh=round(((nb[3] - nb[1]) - (ob[3] - ob[1])) * H))
    ch = m["changes"]
    if tgt.get("text") is not None and tgt["text"] != e["text"]:
        m["text"] = {"old": tgt["text"], "new": e["text"]}
        ch["words"] = True
    if tgt.get("on") and span and [round(v, 2) for v in tgt["on"]] != [round(v, 2) for v in span]:
        m["span"] = {"old": tgt["on"], "new": span}
        d = (span[1] - span[0]) - (tgt["on"][1] - tgt["on"][0])
        ch["time"] = d if abs(d) >= 0.05 else True  # longer or shorter on screen, or the same length moved
    if m.get("off_at_t"):
        ch["time"] = ch.get("time") or True
    zones = [z["box"] for z in n.get("also") or [] if z.get("type") == "keep-clear"]
    if zones:
        m["keep_clear"] = [{"before": _overlaps(ob, z), "after": _overlaps(nb, z)} for z in zones]
    mk = n.get("mark") or {}
    moved = max(abs(m["dx"]), abs(m["dy"])) >= 2
    if mk.get("type") == "arrow":
        d = lambda x, y: round(((x - mk["to"][0]) ** 2 * W * W + (y - mk["to"][1]) ** 2 * H * H) ** 0.5)
        m["arrow"] = {"before": d(ox, oy), "after": d(nx, ny)}
        if moved:  # toward where the arrow pointed, or away from it
            ch["place"] = 1 if m["arrow"]["after"] < m["arrow"]["before"] else -1
    elif moved:
        ch["place"] = 1
    if max(abs(m["dw"]), abs(m["dh"])) >= 2:
        ratio = _area(nb) / (_area(ob) or 1e-9)
        ch["size"] = (ratio - 1) if abs(ratio - 1) >= 0.02 else True
    busy = _busy(n, E, t)
    if busy:
        m["busy"] = busy
        ch["busy"] = busy
    _judge(m, n, ELEMENT_DIMS)
    if m["verdict"] == "unchanged" and m["flag"]:
        m["flag"] = ("nothing measurable changed (its place, size, words and time on screen are the same): if the fix was a "
                     "color, a sound or something elsewhere, say so (vs review resolve --expect)")
    return m


def measure_sound(n, cues):
    """What the new version did to a sound the human answered, from vs mix's cues: its level against the voice, its
    sound, its moment, or gone; judged against their ask (quieter, louder, a different sound, remove it)."""
    sd, res = n.get("sound") or {}, n.get("resolution") or {}
    name = res.get("renamed") or sd.get("el")
    if not name or not isinstance(cues, list):  # no cues for this version (vs mix hasn't run: read_json's {}) ≠ the sound is gone
        return None
    c = next((x for x in cues if x["el"] == name), None)
    m = {"el": name, "t": sd.get("t"), "flag": None, "sound": True, "changes": {}}
    if not c:
        m["gone"] = True
        m["changes"]["presence"] = -1
        return _judge(m, n, ("level", "content", "time", "presence"))
    m.update(db={"old": sd.get("db"), "new": c.get("db")}, name={"old": sd.get("sound"), "new": c.get("sound")},
             dt=round((c["t"] or 0) - (sd.get("t") or 0), 3))
    louder = (c.get("db") or 0) - (sd.get("db") or 0)
    ch = m["changes"]
    if abs(louder) >= 0.5:
        ch["level"] = louder
    if c.get("sound") != sd.get("sound"):
        ch["content"] = True
    if abs(m["dt"]) >= 0.02:
        ch["time"] = True
    _judge(m, n, ("level", "content", "time", "presence"))
    if m["verdict"] == "contrary" and "level" in ch:  # say it in dB, the way the Mix panel does
        m["flag"] = f"asked {sd.get('ask')}, measured {abs(louder):g} dB {'louder' if louder > 0 else 'quieter'}"
    elif m["verdict"] == "other" and sd.get("ask") == "remove":
        m["flag"] = "asked to remove it, and it's still there"
    elif m["verdict"] == "other" and sd.get("ask") == "different":
        m["flag"] = "asked for a different sound, and it's the same one"
    return m


# ── what the box can't show: the pixels and the sound themselves, from the two renders (the bare ones, no music) ──
def bare(video):
    """A version's render without the mix (the music would make every moment's sound differ): out/<name>-vN.mp4."""
    try:
        b = version_of(video)[1] + ".mp4"
    except Refused:
        return video
    return b if os.path.exists(b) else video


def _color(rgb):
    import colorsys
    h, s_, v = colorsys.rgb_to_hsv(*[x / 255 for x in rgb])
    if s_ < 0.25 or v < 0.15:
        return "black" if v < 0.15 else "white" if v > 0.8 else "gray"
    h *= 360
    return ("red" if h < 15 or h >= 345 else "orange" if h < 45 else "yellow" if h < 70 else "green" if h < 170
            else "blue" if h < 260 else "purple")


def measure_pixels(old, new, t, box=None):
    """The share of pixels (inside the box, or the whole frame) that changed by more than a render's grain (48 of 255 on
    any channel), and the color they mostly went from and to. Measured on the Jev explainer: the coal line made red =
    1.5% of the chart, white → red; the same moment's untouched corner and an unchanged moment: 0–0.06%."""
    import numpy as np
    W, H, _ = probe(old)
    if probe(new)[:2] != (W, H):
        return None  # another shape: nothing to lay over
    a, b = _frame(old, t, W, H), _frame(new, t, W, H)
    if box:
        x0, y0, x1, y1 = [int(round(v * k)) for v, k in zip(box, (W, H, W, H))]
        a, b = a[max(0, y0):y1, max(0, x0):x1], b[max(0, y0):y1, max(0, x0):x1]
    if not a.size:
        return None
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    ch = d > 48
    # "faint": dim shapes on a dark ground move only 10-25 levels, under the grain line above, and a human sees them go
    # (the video-kit reel's background shapes behind a card, Oct 2, 2026: 4.4% of the frame past 6 levels; unchanged
    # moments of the same two renders, 0-0.5%)
    out = {"changed": round(float(ch.mean()), 4), "faint": round(float((d > 6).mean()), 4)}
    if ch.sum() >= 20:
        out.update({"from": _color(a[ch].mean(0)), "to": _color(b[ch].mean(0))})
    return out


def _audio(video, t0, t1, rate=8000):
    import numpy as np
    pre = min(0.2, max(0.0, t0))  # a decoder starts a seek with a little silence: decode from earlier and drop it
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0 - pre:.3f}", "-t", f"{t1 - t0 + pre:.3f}", "-i", video, "-vn",
                          "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32)[int(pre * rate):] / 32768


def measure_audio(old, new, t, span=1.5, slack=0.3):
    """How the sound around a moment changed: 20 ms loudness envelopes of the two renders, the new one slid up to 0.3 s
    to line up (an edit earlier in the voice moves everything after it), then the time where they differ by more than
    6 dB while either is audible. Measured on the Jev explainer: the act 5 repeat taken out = 1.1 s changed, and what
    follows 0.24 s earlier; unchanged moments before and after it: 0.0 s."""
    import numpy as np
    f = int(8000 * 0.02)
    env = lambda x: 20 * np.log10(np.sqrt((x[: (len(x) // f) * f].reshape(-1, f) ** 2).mean(1)) + 1e-5)
    ea, eb = env(_audio(old, max(0, t - span), t + span)), env(_audio(new, max(0, t - span - slack), t + span + slack))
    if not len(ea) or not len(eb):
        return None
    S, best = int(slack / 0.02), None
    for k in range(0, 2 * S + 1):
        seg = eb[k: k + len(ea)]
        if len(seg) < len(ea):
            break
        d = int(((np.abs(ea - seg) > 6) & ((ea > -45) | (seg > -45))).sum())
        if best is None or d < best[0]:
            best = (d, k - S)
    if best is None:
        return None
    return {"changed_secs": round(best[0] * 0.02, 2), "shift": round(best[1] * 0.02, 2), "window": round(2 * span, 1)}


def _safely(fn, *a):
    """A measurement that can't be made (a render deleted, a file that won't decode) is no measurement, never a stop."""
    try:
        return fn(*a)
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as x:
        print(f"⚠️  couldn't measure ({fn.__name__}): {x}")
        return None


def _moved(px):
    """A real change in the picture: past the grain line, or a faint change over enough of it (see measure_pixels)."""
    return bool(px) and (px.get("changed", 0) >= 0.005 or px.get("faint", 0) >= 0.02)


def measure_moment(n, old, new, E=None):
    """A note pinned to a moment, not an element (a sound on a dark frame, "it repeats here"), or one the agent answered
    by changing something else (--expect elsewhere): the whole picture and the sound around it, old version against new,
    and how much is on screen."""
    t = n["time"].get("t", n["time"].get("t0"))
    m = {"el": None, "t": t, "moment": True, "flag": None, "pixels": measure_pixels(old, new, t), "audio": measure_audio(old, new, t),
         "changes": {}}
    px, au = m["pixels"] or {}, m["audio"] or {}
    if _moved(px):
        m["changes"]["pixels"] = True
    if au.get("changed_secs", 0) >= 0.1:
        m["changes"]["sound"] = True
    busy = _busy(n, E, t)
    if busy:
        m["busy"] = busy
        m["changes"]["busy"] = busy
    if m["pixels"] is None and m["audio"] is None:
        return unmeasured(n, "neither render could be read at that moment")
    _judge(m, n, ("pixels", "sound", "busy"))
    if m["verdict"] == "unchanged" and m["flag"]:
        m["flag"] = "nothing measurable changed at that moment (the picture and the sound around it are the same)"
    return m


def unmeasured(n, why):
    """A resolved note the tooling couldn't measure, said out loud (it used to be silence, which read like no news)."""
    return {"el": (n.get("target") or {}).get("el") or (n.get("sound") or {}).get("el"), "t": n["time"].get("t", n["time"].get("t0")),
            "verdict": "unmeasured", "why": why, "flag": f"not measured: {why}", "changes": {}}


def _describe_pixels(px):
    if not px:
        return None
    if px["changed"] < 0.005:
        if px.get("faint", 0) >= 0.02:
            return f"its pixels changed faintly ({100 * px['faint']:.1f}% of it, by a few shades)".replace(".0%", "%")
        return "its pixels didn't change"
    pct = f"{100 * px['changed']:.1f}".rstrip("0").rstrip(".")
    return f"its pixels changed ({pct}% of it)" + (f", mostly {px['from']} → {px['to']}" if px.get("from") and px["from"] != px["to"] else "")


def _describe_audio(au):
    if not au:
        return None
    moved = f"; what follows is {abs(au['shift']):g}s {'earlier' if au['shift'] < 0 else 'later'}" if abs(au["shift"]) >= 0.04 else ""
    if au["changed_secs"] < 0.1:
        return "the sound around it is the same" + moved
    return f"the sound around it changed ({au['changed_secs']:g}s of the {au['window']:g}s around it){moved}"


def _describe_busy(m):
    b = m.get("busy")
    return f"{abs(b)} {'more' if b > 0 else 'fewer'} thing{'s' if abs(b) != 1 else ''} on screen" if b else None


def describe_measured(m):
    """A measurement in plain words, for the agent (vs review show) and the human (the page's "Measured:" line)."""
    if m.get("verdict") == "unmeasured" and not m.get("changes"):
        return f"not measured: {m.get('why') or 'the tooling had nothing to compare'}"
    if m.get("basis") == "pixels":  # no element map: only the pixels where the target was
        return (_describe_pixels(m.get("pixels")) or "not measured") + " (no element map: pixels only)" + (f" · ⚠ {m['flag']}" if m["flag"] else "")
    if m.get("moment"):
        parts = [x for x in (_describe_pixels(m.get("pixels")), _describe_audio(m.get("audio")), _describe_busy(m)) if x]
        return (" · ".join(parts) or "not measured") + (f" · ⚠ {m['flag']}" if m["flag"] else "")
    if m.get("sound") and not m.get("gone"):
        parts = []
        d = (m["db"]["new"] or 0) - (m["db"]["old"] or 0)
        parts.append(f"{abs(d):g} dB {'louder' if d > 0 else 'quieter'} ({m['db']['old']} → {m['db']['new']} dB)" if abs(d) >= 0.5 else "same level")
        if m["name"]["new"] != m["name"]["old"]:
            parts.append(f"now \u201c{m['name']['new']}\u201d (was \u201c{m['name']['old']}\u201d)")
        if abs(m["dt"]) >= 0.02:
            parts.append(f"{abs(m['dt']):.2f}s {'later' if m['dt'] > 0 else 'earlier'}")
        return " · ".join(parts) + (f" · ⚠ {m['flag']}" if m["flag"] else "")
    if m.get("gone"):
        return ("removed in this version, as the answer said" if m.get("verdict") == "removed" else "gone from this version") + (
            f" · ⚠ {m['flag']}" if m["flag"] else "")
    parts = []
    if m.get("off_at_t"):
        parts.append(f"no longer on screen at {m['t']:.2f}s (now {m['on'][0]:.2f}–{m['on'][1]:.2f}s)")
    mv = []
    if m.get("dx"):
        mv.append(f"{abs(m['dx'])} px {'right' if m['dx'] > 0 else 'left'}")
    if m.get("dy"):
        mv.append(f"{abs(m['dy'])} px {'down' if m['dy'] > 0 else 'up'}")
    parts.append("moved " + ", ".join(mv) if mv else "didn't move")
    if m.get("dw") or m.get("dh"):
        parts.append(f"size {m.get('dw', 0):+d} × {m.get('dh', 0):+d} px")
    if "text" in m:
        parts.append(f"words \u201c{m['text']['old']}\u201d → \u201c{m['text']['new']}\u201d")
    if "span" in m:
        parts.append(f"on screen {m['span']['old'][0]:.2f}–{m['span']['old'][1]:.2f}s → {m['span']['new'][0]:.2f}–{m['span']['new'][1]:.2f}s")
    for k in m.get("keep_clear", []):
        parts.append({(True, False): "now clear of the keep-clear zone", (False, False): "stayed clear of the keep-clear zone",
                      (True, True): "still in the keep-clear zone", (False, True): "moved INTO the keep-clear zone"}[(k["before"], k["after"])])
    if "arrow" in m:
        parts.append(f"{m['arrow']['after']} px from where the arrow pointed (was {m['arrow']['before']})")
    if m.get("busy"):
        parts.append(_describe_busy(m))
    if m.get("pixels"):
        parts.append(_describe_pixels(m["pixels"]))
    return " · ".join(parts) + (f" · ⚠ {m['flag']}" if m["flag"] else "")


# ── stills: the frame the human pointed at, with the target and the mark drawn on it ──
RED, AMBER = (232, 64, 44), (217, 164, 59)


def _frame(video, t, W, H):
    # a note's moment is a frame's own time (k/fps, rounded to the millisecond): back off under half a frame so the
    # rounding can't push ffmpeg onto the next one. A moment at (or past) the end is the last frame: a note on the end
    # card's final frame read "no frame at 159.99s" (corporate-job, Oct 2; an explainer, Oct 4, 2026)
    fps = fps_of(video)
    t = max(0.0, min(t, probe(video)[2] - 1 / fps) - 0.4 / fps)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", video, "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    import numpy as np
    if len(raw) < W * H * 3:
        raise RuntimeError(f"no frame at {t:.2f}s")
    return np.frombuffer(raw[: W * H * 3], np.uint8).reshape(H, W, 3).copy()


def _draw(img, note):
    import numpy as np
    H, W = img.shape[:2]
    s = max(2, round(min(W, H) / 270))  # line width: 4 px on a 1080-wide frame
    px = lambda p: (p[0] * W, p[1] * H)

    def rect(b, color, fill=None):
        x0, y0, x1, y1 = [int(round(v)) for v in (b[0] * W, b[1] * H, b[2] * W, b[3] * H)]
        x0, x1, y0, y1 = max(0, min(x0, x1)), min(W, max(x0, x1)), max(0, min(y0, y1)), min(H, max(y0, y1))
        if fill is not None:  # keep-clear: amber stripes over the zone
            yy, xx = np.mgrid[y0:y1, x0:x1]
            on = ((xx + yy) // (4 * s)) % 2 == 0
            reg = img[y0:y1, x0:x1].astype(np.float32)
            reg[on] = reg[on] * (1 - fill) + np.array(color) * fill
            img[y0:y1, x0:x1] = reg.astype(np.uint8)
        for (a, b2, c, d) in ((y0, y0 + s, x0, x1), (y1 - s, y1, x0, x1), (y0, y1, x0, x0 + s), (y0, y1, x1 - s, x1)):
            img[max(0, a):max(0, b2), max(0, c):max(0, d)] = color

    def dot(x, y, r, color):
        yy, xx = np.ogrid[:H, :W]
        x0, x1, y0, y1 = int(max(0, x - r)), int(min(W, x + r + 1)), int(max(0, y - r)), int(min(H, y + r + 1))
        m = (xx[:, x0:x1] - x) ** 2 + (yy[y0:y1] - y) ** 2 <= r * r
        img[y0:y1, x0:x1][m] = color

    def line(a, b, color):
        (x0, y0), (x1, y1) = a, b
        n = int(max(abs(x1 - x0), abs(y1 - y0)) / max(1, s / 2)) + 1
        for k in range(n + 1):
            dot(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, s, color)

    def arrow(a, b, color):
        line(a, b, color)
        import math
        ang, L = math.atan2(b[1] - a[1], b[0] - a[0]), 9 * s
        for d in (2.6, -2.6):
            line(b, (b[0] + L * math.cos(ang + d), b[1] + L * math.sin(ang + d)), color)

    tg = (note.get("target") or {}).get("box")
    if tg:
        rect(tg, RED)
    for m in [note.get("mark") or {}] + list(note.get("also") or []):
        k = m.get("type")
        if k == "box":
            rect(m["box"], AMBER)
        elif k == "keep-clear":
            rect(m["box"], AMBER, fill=0.45)
        elif k == "arrow":
            arrow(px(m["from"]), px(m["to"]), RED)
            dot(*px(m["from"]), 2 * s, RED)
        elif k == "click":
            x, y = px(m["at"])
            dot(x, y, 3 * s, RED)
            dot(x, y, 1.5 * s, (255, 255, 255))
    return img


def make_frame(note, video):
    """review/frames/<note>.jpg: the frame at the note's moment (a range: start, middle and end side by side, half
    size), the target outlined in red, the mark in red (arrow, click) or amber (box, keep-clear)."""
    import numpy as np
    W, H, dur = probe(video)
    tm = note["time"]
    ts = [tm["t"]] if "t" in tm else [tm["t0"], (tm["t0"] + tm["t1"]) / 2, tm["t1"]]
    imgs = [_draw(_frame(video, min(t, dur - 0.05), W, H), note) for t in ts]
    img = imgs[0] if len(imgs) == 1 else np.concatenate([x[::2, ::2] for x in imgs], axis=1)
    os.makedirs(FRAMES, exist_ok=True)
    out = f"{FRAMES}/{note['id']}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                    f"{img.shape[1]}x{img.shape[0]}", "-i", "-", "-q:v", "3", out],
                   input=np.ascontiguousarray(img).tobytes(), check=True)
    return out


def frames_for(S, events):
    """Stills for the notes these events added or re-pointed. A still that can't be made says why; the note stands."""
    made = []
    for e in events:
        nid = (e.get("note") or {}).get("id") if e["type"] == "note.added" else e.get("id") if e["type"] == "note.edited" else None
        if not nid:
            continue
        n = S["notes"][nid]
        R = S["rounds"][n["round"] - 1]
        try:
            made.append(make_frame(n, cut_video(R, n.get("cut") or R["cut"])))
        except Exception as x:
            print(f"⚠️  no still for {nid}: {x}", flush=True)
    return made


# ── the agent's commands ──
def fmt_t(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def when(n):
    tm = n["time"]
    return fmt_t(tm["t"]) if "t" in tm else f"{fmt_t(tm['t0'])} → {fmt_t(tm['t1'])}"


def describe_mark(m):
    k = m.get("type")
    f = lambda p: f"({p[0]:.2f}, {p[1]:.2f})"
    if k == "arrow":
        under = ", ".join(m.get("under_to") or []) or "nothing"
        return f"arrow {f(m['from'])} → {f(m['to'])}, over {under}"
    if k in ("box", "keep-clear"):
        b = m["box"]
        over = ", ".join(m.get("over") or [])
        return f"{k} {f(b[:2])}–{f(b[2:])}" + (f" over {over}" if over else "")
    if k == "click":
        return f"click at {f(m['at'])}"
    return None


def _fkey(fid):
    """A finding id → (what and where, when): q-covered-left-55 → ("q-covered-left", 55.0). No time → (the id, None)."""
    m = re.match(r"^(.*)-(\d+(?:\.\d+)?)$", fid or "")
    return (m.group(1), float(m.group(2))) if m else (fid, None)


def carry_findings(S, R):
    """The same finding seen again in a new round (the same check, the same place, within 3 s, since a re-timed voice
    moves it a little) keeps the human's earlier answer: they were asked once (a reviewer, Oct 2: "Once it's been
    dispositioned, it shouldn't do that"). → finding.carried events. Changing it is still one click in the page."""
    out, prior = [], {i: d for i, d in S["findings"].items() if d.get("round") != R["n"]}
    for f in round_findings(S):
        mine = S["findings"].get(f["id"])
        if mine and mine.get("round") == R["n"]:
            continue
        k, t = _fkey(f["id"])
        best = None
        for i, d in prior.items():
            k2, t2 = _fkey(i)
            if k2 != k or (t is None and i != f["id"]) or (t is not None and (t2 is None or abs(t - t2) > 3)):
                continue
            if not best or (d.get("round") or 0) > (best[1].get("round") or 0):
                best = (i, d)
        if best:
            d = best[1]
            out.append({"type": "finding.carried", "id": f["id"], "status": d["status"], "reason": d.get("reason"),
                        "check": f.get("check"), "followed": d.get("followed"), "from": best[0],
                        "from_round": (d.get("carried") or {}).get("round") or d.get("round")})
    return out


def finish(args):
    """The finals are filed: a round on the final (stage final) if one isn't open on it, and project.finished, so the page
    says it's done, offers the downloads and a way back in (a note on any part reaches the agent like any other)."""
    files = [f for f in args.final if os.path.exists(f)]
    if not files:
        raise Refused("vs review finish --final <the final files in out/>")
    S = state()
    R = current(S)
    if not R or R["video"] != files[0] or R["status"] == "closed":
        open_round(argparse.Namespace(video=files[0], ask=False, stage="final"))
    append([{"type": "project.finished", "files": [{"url": "/" + f.replace(os.sep, "/"), "name": os.path.basename(f),
                                                     "cut": "16x9" if "-16x9-" in f else "9x16"} for f in files]}], "agent")
    print(f"finished: {', '.join(os.path.basename(f) for f in files)} → the page shows the downloads; run vs review wait")


def round_findings(S=None):
    """The findings the current round puts to the human: qa.py's on its render, vs inspect's warnings, and the errors
    open --ask asked about (what the page lists)."""
    S = S or state()
    R = current(S)
    if not R:
        return []
    asked, out = set(R.get("asked") or []), []
    for c in R.get("cuts") or [{"cut": R.get("cut"), "video": R["video"]}]:
        try:
            base = version_of(c["video"])[1]
        except Refused:
            continue
        pre = "" if c["cut"] == R.get("cut") else f"{c['cut']}:"  # the other shape's carry its name (open_round)
        tl = vslib.read_json(f"{base}.review/timeline.json") or vslib.read_json(f"{base}.timeline.json")
        F = inspected(base, tl and tl.get("fingerprint")) or {}
        mine = [f for f in F.get("items", []) if f.get("severity") == "warning" or pre + f["id"] in asked]
        mine += (vslib.read_json(f"{base}.review/qa.json") or {}).get("items", [])
        out += [{**f, "id": pre + f["id"], "cut": c["cut"]} if pre else f for f in mine]
    return out


def show(args):
    S = state()
    R = current(S)
    if not R:
        return print("no rounds yet: vs review open starts one on a rendered version")
    if args.json:
        pick = [args.note] if args.note else [i for i, n in S["notes"].items() if n["round"] == R["n"] or n["status"] in WAITING | {"question"}]
        art = {"project": vslib.project_name(), "kind": kind_of()}
        print(json.dumps({"round": R, "notes": [S["notes"][i] for i in pick],
                          "records": [as_record(S["notes"][i], S, art) for i in pick],
                          "rules": project_rules(S)}, indent=1))
        if not args.note and (R.get("sends") or 0) > (R.get("read_sends") or 0):
            append([{"type": "round.read", "round": R["n"]}], "agent")  # read as JSON is read all the same
        return
    if args.note:
        notes = [S["notes"].get(args.note) or sys.exit(f"⛔ no note {args.note}")]
    else:
        notes = [n for n in S["notes"].values() if (n["round"] == R["n"] or n["status"] in WAITING | {"question", "resolved", "wontdo"}) and n["status"] not in ("withdrawn", "draft")]
        sends = R.get("sends") or 0
        both = " + ".join(f"{c['cut']} {c['video']}" for c in R["cuts"]) if R.get("cuts") else f"({R['cut']}) · {R['video']}"
        print(f"Round {R['n']} · v{R['version']} {both} · {R['status']}"
              + (f" {(R['last_sent'] or R['sent'])[:16].replace('T', ' ')}" if R["sent"] else "")
              + (f" ({sends} sends)" if sends > 1 else "") + f" · {len(notes)} note(s)" + (f" · stage: {R['stage']}" if R.get("stage") else ""))
        H = state("human")
        if H["pending"]:
            print(f"(the human has {len(H['pending'])} more thing(s) in the page, not sent yet: you'll see them when they send)")
    for n in notes:
        tgt = (n.get("target") or {}).get("el")
        shape = f"  ({'WIDESCREEN' if n.get('cut') == '16x9' else 'VERTICAL'})" if (S["rounds"][n["round"] - 1].get("cuts")) else ""
        print(f"\n{n['id']}{shape}  {when(n)}  {n.get('segment') or '—'}{' › ' + tgt.split('/', 1)[-1] if tgt else ''}  [{n['status']}]"
              + (" (added after Send)" if n.get("late") else ""))
        if n.get("sound"):
            sd = n["sound"]
            print(f"  sound: {sd.get('sound')} ({sd.get('el')}) at {fmt_t(sd.get('t') or 0)}"
                  + (f", {sd['db']} dB against the voice" if sd.get("db") is not None else "")
                  + (f" → {SOUND_ASKS.get(sd.get('ask'), sd.get('ask'))}" if sd.get("ask") else "") + " (cues.py)")
        mk = [x for x in [describe_mark(n["mark"])] + [describe_mark(a) for a in n.get("also") or []] if x]
        if mk:
            print(f"  mark: {' · '.join(mk)}")
        if n.get("step"):
            print(f"  about their step: {n['step'].get('text')}" + (f" ({n['step']['at'][:16].replace('T', ' ')})" if n["step"].get("at") else ""))
        if (n.get("comment") or "").strip():
            print(f"  “{n['comment'].strip()}”")
        if n.get("ask") or (n.get("scope") or "here") != "here":
            print("  ask: " + " · ".join(x for x in [feedback.ASK_WORDS.get(n.get("ask")) if n.get("ask") else None,
                                                     {"project": "everywhere in this video", "studio": "in every video (they want it to be a rule)"}.get(n.get("scope"))] if x))
        if n.get("follows"):
            print(f"  follows {n['follows']}")
        for h in n["thread"]:
            print(f"  {h['by']} ({h['type']}): {h['text']}")
        if n.get("measured"):
            v = feedback.verdict(n["measured"])
            st = n["measured"].get("strength") or feedback.strength(ask_of(n), (n.get("resolution") or {}).get("expect"), v)
            mm = n["measured"]
            span = (f"v{mm.get('from')}, round {mm['from_round']} → {mm['to_round']}" if mm.get("from") == mm.get("to") and mm.get("to_round")
                    else f"v{mm.get('from')} → v{mm.get('to')}")
            print(f"  measured ({span}): {describe_measured(mm)}"
                  f"  [{feedback.VERDICT_WORDS.get(v, v)}{', by a stand-in' if st == 'proxy' else ''}]")
        if n["status"] == "accepted" and (n.get("accepted") or {}).get("verdict") not in (None, *feedback.VERIFIED):
            print(f"  accepted over the measurement ({feedback.VERDICT_WORDS[n['accepted']['verdict']]}): the human's eyes decided")
        if n.get("visible"):
            print(f"  on screen: {', '.join(v.split('/', 1)[-1] for v in n['visible'][:12])}{' …' if len(n['visible']) > 12 else ''}")
        if n.get("findings"):
            print(f"  findings: {', '.join(n['findings'])}")
        fr = f"{FRAMES}/{n['id']}.jpg"
        if os.path.exists(fr):
            print(f"  still: {fr}")
    if not args.note:
        if R.get("asked"):
            print(f"\nfindings put to the human: " + ", ".join(f"{i} ({S['findings'].get(i, {}).get('status', 'open')})" for i in R["asked"]))
        decided = [(i, d) for i, d in S["findings"].items() if d.get("round") == R["n"]]
        if decided:
            print("\nfindings the human decided this round (fix it = confirmed, it's real; leave it = dismissed):")
            for i, d in sorted(decided, key=lambda x: x[1]["status"]):
                fol = {True: " (your advice)", False: " (against your advice)"}.get(d.get("followed"), "")
                print(f"  {'fix it' if d['status'] == 'confirmed' else 'leave it':8s} {d['status']:9s} {i}{fol}" + (f"  \u201c{d['reason']}\u201d" if d.get("reason") else "")
                      + (f" (carried from round {d['carried']['round']})" if d.get("carried") else ""))
        if R.get("nonotes"):
            print("\nthe human: no notes this round (nothing to change)")
        if S["mix"]:
            print(f"\nmix saved: {S['mix'].get('summary') or S['mix']}")
        for lz in S["lessons"].values():
            if lz["decision"] is None:
                print(f"\nlesson {lz['id']} waits for the human: {lz['tag']} \u201c{lz['text']}\u201d")
            elif (lz.get("decided") or "") >= (R["opened"] or ""):
                todo = {"remember": f"→ every video: vs review promote {lz['id']} (writes it to {DEST[lz['dest']]})",
                        "kind": f"→ every {kind_of()}: vs review promote {lz['id']}",
                        "project": "→ this video only: it stays in this project (listed under this video's rules)",
                        "ignore": "→ ignored (never asked again)"}[lz["decision"]]
                print(f"\nlesson {lz['id']} {lz['decision']}: {lz['tag']} \u201c{lz['text']}\u201d {todo}")
        for c in S["choices"].values():
            if c.get("applied") and c["applied"]["pick"] == c.get("picked"):
                continue
            opts = " · ".join(f"{o['id']} {o.get('label') or o['kind']}" for o in c["options"])
            if not c.get("picked"):
                print(f"\nchoice {c['id']} waits for the human: {c['question']} ({opts})")
            else:
                lab = "none of these" if c["picked"] == "none" else next(f"{o['id']} ({o.get('label') or o['kind']})" for o in c["options"] if o["id"] == c["picked"])
                print(f"\nchoice {c['id']} picked: {lab}" + (f" \u201c{c['said']}\u201d" if c.get("said") else "")
                      + f" → vs review apply {c['id']}")
        rules = project_rules(S)
        if rules:
            print("\nthis video's rules (the human's, for this video only: apply them in every version):")
            for r in rules:
                print(f"  {r['from']}: {r['text']}")
        if S["done"]:
            print("\ndone (vs inspect holds their frames to that version; change one only if the human reopens it): "
                  + ", ".join(f"{k} (v{d['version']})" for k, d in S["done"].items()))
        for a in S["approved"]:
            print(f"\n✓ v{a['version']} ({a.get('cut')}) approved {a['at'][:16].replace('T', ' ')}: vs learn --final <the files> keeps it")
        owed = [i for i, n in S["notes"].items() if n["status"] in WAITING]
        if owed:
            print(f"\nowed an answer: {', '.join(owed)} → vs review resolve <note> --said \"…\" | vs review ask <note> \"…\"")
        cards = open_cards(S)
        if cards and any(S["notes"][i]["status"] not in ("draft", "withdrawn") for i in R["notes"]):
            print("\nstill open in the inbox: if a note this round already speaks to one, close it with that note, or it comes"
                  " back next round → vs review cover <card> --by <note> [--as fix|leave, a finding] [--pick <option>, a choice]")
            for i, what in cards:
                print(f"  {i}: {what}")
        unadvised = [f for f in round_findings() if f["id"] not in S["advice"] and f["id"] not in S["findings"]]
        if unadvised:
            checks = sorted({f["check"] for f in unadvised})
            print(f"\nfindings with no advice yet ({len(unadvised)}: {', '.join(checks)}): the human sees them in plain words, "
                  "but your recommendation is what makes them easy → vs review advise --check <check> --advice leave|fix --plain \"…\" --why \"…\"")
    if not args.note and (R.get("sends") or 0) > (R.get("read_sends") or 0):
        append([{"type": "round.read", "round": R["n"]}], "agent")  # the page: "Claude has it"


def open_cards(S):
    """The inbox cards still waiting on the person, with what each is about: fix cards (an answer to accept or reopen),
    choices not picked, findings not decided. → [(id, words)]"""
    out = []
    for i, n in S["notes"].items():
        if n["status"] in feedback.ANSWERED and feedback.acceptance(n, S["notes"]) == "pending" and not n.get("covered"):
            out.append((i, f"your answer to “{_q((n.get('comment') or '').strip(), 50)}”: {_q((n.get('resolution') or {}).get('said') or '', 70)}"))
    for c in S["choices"].values():
        if not c.get("picked") and not c.get("covered"):
            out.append((c["id"], f"choice: {c['question']} ({' · '.join(o['id'] for o in c['options'])})"))
    for f in round_findings(S):
        if f["id"] not in S["findings"]:
            out.append((f["id"], f"finding: {(S['advice'].get(f['id']) or {}).get('plain') or f.get('text') or f.get('check')}"))
    return out


def cover(args):
    """The person's note already speaks to a card in the inbox: close the card with it (card.covered)."""
    e = {"type": "card.covered", "card": args.card, "note": args.by, **({"why": args.why} if args.why else {})}
    if args.as_:
        e["as"] = args.as_
    if args.pick:
        e["pick"] = args.pick
    S, _ = append([e], "agent")
    what = ("their pick: " + args.pick + " → vs review apply " + args.card) if args.pick else (f"as {args.as_}" if args.as_ else "closed")
    print(f"{args.card} covered by {args.by} ({what}): the page shows it answered by their note, and it doesn't come back")


def measure_note(n, old, new, E, size, cues):
    """One answered note, measured in the new version: its sound in vs mix's cues, its target in vs inspect's map (then
    its pixels, when the box didn't show the change), or the whole moment when it pointed at no one thing or the agent
    said the change was elsewhere. A resolved note always gets a verdict, "unmeasured" (with why) included; a won't-do
    is measured when it can be, for the record."""
    res = n.get("resolution") or {}
    claimed = res.get("outcome") == "resolved"
    tgt = n.get("target") or {}
    if n.get("sound"):
        m = measure_sound(n, cues)
        return m or (unmeasured(n, "no sound cues for this version (vs mix makes them)") if claimed else None)
    if res.get("expect") in ("elsewhere", "sound") or not tgt.get("box"):
        m = _safely(measure_moment, n, old, new, E)
        return m or (unmeasured(n, "the renders couldn't be read at that moment") if claimed else None)
    t = n["time"].get("t", n["time"].get("t0"))
    if not E:  # no element map for this version: what's in the target's old place is the evidence
        px = _safely(measure_pixels, old, new, t, tgt["box"])
        if px is None:
            return unmeasured(n, "no element map for this version (vs inspect makes one), and its pixels couldn't be compared") if claimed else None
        m = {"el": tgt.get("el"), "t": t, "flag": None, "basis": "pixels", "pixels": px, "changes": {"pixels": True} if _moved(px) else {}}
        return _judge(m, n, ("pixels",))
    m = measure(n, E, size)
    want = feedback.target_dims(ask_of(n), res.get("expect"))
    if m and not m.get("gone") and (m["verdict"] == "unchanged" or want == {"pixels"}):
        # the box didn't show it: look at its pixels (a color, a fade, a line's weight change nothing a box can show)
        px = _safely(measure_pixels, old, new, m["t"], m.get("new_box"))
        if px:
            m["pixels"] = px
            if _moved(px):
                m["changes"]["pixels"] = True
                _judge(m, n, ELEMENT_DIMS)
    return m


def open_round(args):
    video = args.video or newest_video()
    if not os.path.exists(video):
        raise Refused(f"{video} doesn't exist")
    version, base = version_of(video)
    W, H, _ = probe(video)
    cut = "16x9" if W > H else "9x16"
    # both shapes in one round when both are rendered at this version: the human watches either, and each note, finding
    # and approval belongs to the one on screen (a reviewer, Oct 4, 2026: "view both … and give feedback on each independently")
    named = getattr(args, "also", None)
    other = None if getattr(args, "only", False) else (named or partner(video))
    if named:
        if not os.path.exists(named):
            raise Refused(f"{named} doesn't exist")
        if version_of(named)[0] != version:
            raise Refused(f"{named} is v{version_of(named)[0]}, the round is v{version}: render both shapes at one version")
        if cut_of(named) == cut:
            raise Refused(f"{named} is the same shape as {video}: --also takes the other one")
    elif other and cut_of(other) == cut:
        other = None  # found by its name, but it isn't the other shape after all
    shapes = [(video, base, cut)] + ([(other, version_of(other)[1], cut_of(other))] if other else [])
    S0 = state()
    n_new = len(S0["rounds"]) + 1
    kept = {c: keep(v, n_new, c) for v, _, c in shapes}
    asked, maps = [], {}
    dismissed = state()["findings"]
    for v, b, c in shapes:
        tl = vslib.read_json(f"{b}.review/timeline.json") or vslib.read_json(f"{b}.timeline.json")
        F = inspected(b, tl and tl.get("fingerprint"))
        pre = "" if c == cut else f"{c}:"  # the other shape's findings carry its name: the same check on both is two answers
        maps[c] = (v, element_map(b, tl and tl.get("fingerprint")), list(probe(v)[:2]))
        if F is None:
            print(f"⚠️  no vs inspect findings for v{version} ({c}): can't tell whether it has open errors")
            continue
        errs = [f for f in F["items"] if f.get("severity") == "error" and dismissed.get(pre + f["id"], {}).get("status") != "dismissed"]
        if errs and not args.ask:
            raise Refused(f"v{version} ({c}) has {len(errs)} open error(s) from vs inspect (first: {errs[0]['check']} "
                          f"{' × '.join(errs[0]['elements'])} at {errs[0]['t0']:.1f}s): errors never reach a round. "
                          "Fix them, or --ask to put them to the human")
        asked += [pre + f["id"] for f in errs]
    # every answer since the last round, measured in this version's element map (of the note's own shape): the human
    # sees the claim and the proof
    cues = vslib.read_json(f"{base}.review/cues.json") or vslib.read_json("build/mix/cues.json")  # vs mix's, for this version
    # every answer not measured yet, in any later round: a sound fix re-mixes the same picture version, so "a new
    # version" was the wrong test (Oct 5, 2026: three sound answers in a row were never measured)
    measured = []
    for n in S0["notes"].values():
        if n["status"] in ("resolved", "wontdo") and not n.get("measured") and feedback.phase(n, S0["notes"])[0] != "closed":
            nc = n.get("cut") or cut
            if nc not in maps:
                print(f"⚠️  {n['id']} is about the {'widescreen' if nc == '16x9' else 'vertical'} cut, not in this round: not measured")
                continue
            nv, E, size = maps[nc]
            was = S0["rounds"][n["round"] - 1]
            if n["version"] == version:  # the same picture, re-mixed: the mix is what changed, so compare the mixes
                old, new = watched(was, nc), nv
            else:  # a new picture: without the music (a different take would make every moment's sound differ)
                old, new = bare(cut_video(was, nc)), bare(nv)
            m = measure_note(n, old, new, E, size, cues)
            if m:
                m.update({"from": n["version"], "to": version, "from_round": n["round"], "to_round": n_new})
                measured.append({"type": "note.measured", "id": n["id"], "measured": {**m, "summary": describe_measured(m)}})
    stage = args.stage or (current(S0) or {}).get("stage") or S0.get("stage")
    kind = "explainer" if os.path.exists("plan.json") else "reel"
    if args.stage and args.stage not in STAGES[kind]:
        raise Refused(f"no stage {args.stage!r} for a {kind}: {', '.join(STAGES[kind])}")
    cuts = [{"cut": c, "video": v, "size": maps[c][2]} for v, _, c in shapes] if other else None
    S, _ = append([{"type": "round.opened", "version": version, "cut": cut, "video": video, "size": [W, H],
                    "asked": asked, **({"kept": {c: k for c, k in kept.items() if k}} if any(kept.values()) else {}), **({"cuts": cuts} if cuts else {}), **({"stage": stage} if stage else {})}] + measured, "agent")
    R = current(S)
    print(f"round {R['n']} open on v{version} ({cut}): {video}" + (f" + the {cut_of(other)} cut: {other}" if other else "")
          + (f" · stage: {stage}" if stage else "")
          + (f" · {len(asked)} finding(s) put to the human" if asked else ""))
    carried = carry_findings(S, R)
    if carried:
        S, _ = append(carried, "agent")
        print(f"  {len(carried)} finding(s) answered in an earlier round: the answer stands (the page shows it, no click needed)")
    todo = [f for f in round_findings(S) if f["id"] not in S["advice"] and f["id"] not in S["findings"]]
    if todo:
        print(f"  {len(todo)} finding(s) for the human ({', '.join(sorted({f['check'] for f in todo}))}): advise each in plain "
              "words → vs review advise --check <check> --advice leave|fix --plain \"…\" --why \"…\"")
    for e in measured:
        m = e["measured"]
        print(f"  {e['id']} {(m['el'] or 'the moment').split('/', 1)[-1]}: {describe_measured(m)}")
    if not maps[cut][1] and any(n["status"] == "resolved" and n.get("target") for n in S0["notes"].values()):
        print(f"⚠️  no element map for v{version} (vs inspect): the answers were measured by their pixels only")
    print(server_line())


# ── the server and the watcher, in one line: sessions used to spend 15-25 steps finding a free port, writing the
#    preview entry by hand and confirming exactly one watcher ──
PORTS = range(4470, 4500)


def launch_file():
    """The nearest .claude/launch.json above this project (the preview pane reads the session's own); none: the studio's."""
    d = os.getcwd()
    while True:
        f = os.path.join(d, ".claude", "launch.json")
        if os.path.exists(f):
            return f
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    return os.path.join(vslib.studio_root() or os.getcwd(), ".claude", "launch.json")


def _listening(port):
    import socket
    with socket.socket() as k:
        k.settimeout(0.3)
        return k.connect_ex(("127.0.0.1", port)) == 0


def launch_entry():
    """This project's entry in launch.json, made or repaired: (name, port, file, what changed or None)."""
    f = launch_file()
    L = vslib.read_json(f) if os.path.exists(f) else {}
    L.setdefault("version", "0.0.1")
    confs = L.setdefault("configurations", [])
    name = f"{vslib.project_name()}-review"
    skill = "explainer-video" if kind_of() == "explainer" else "sizzle-reel"
    vs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "skills", skill, "vs")
    have = next((c for c in confs if c.get("name") == name), None)
    port = have and have.get("port")
    if not port:
        used = {c.get("port") for c in confs}
        port = next((p for p in PORTS if p not in used and not _listening(p)), None)
        if port is None:
            raise Refused(f"no free port in {PORTS.start}-{PORTS.stop - 1}: remove an old *-review entry from {f}")
    want = {"name": name, "runtimeExecutable": "/bin/sh",
            "runtimeArgs": ["-c", f"cd {shlex_quote(os.getcwd())} && {shlex_quote(vs)} review --port {port}"], "port": port}
    if have == want:
        return name, port, f, None
    if have:
        confs[confs.index(have)] = want
    else:
        confs.append(want)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w") as o:
        json.dump(L, o, indent=2)
        o.write("\n")
    return name, port, f, "updated" if have else "added"


def shlex_quote(x):
    import shlex
    return shlex.quote(x)


def server_line():
    """One line: the server (running, or how to start it) and the watcher."""
    name, port, f, changed = launch_entry()
    up = _listening(port)
    w = vslib.read_json(WAITING_FILE) if agent_waiting() else None
    return (f"server: {'running' if up else 'not running'} · http://localhost:{port}/review/"
            + ("" if up else f' → start it in the preview pane: preview_start {{name: "{name}"}}')
            + (f" ({changed} in {f})" if changed else "")
            + f"\nwatcher: " + (f"running (pid {w['pid']}, since {w.get('since', '?')[11:16]}): it will read the send; don't start another"
                                if w else "none → run vs review wait in the background once the human has the round"))


def launch(args):
    print(server_line())


def advise(args):
    """Claude's advice on findings the human will see: what it is in plain words, and leave it or fix it (with why)."""
    S = state()
    F = {f["id"]: f for f in round_findings(S)}
    if args.check:
        ids = [i for i, f in F.items() if f.get("check") == args.check]
        if not ids:
            known = sorted({f.get("check") for f in F.values()})
            raise Refused(f"no {args.check!r} findings in round {(current(S) or {}).get('n')}: {', '.join(known) or 'none at all'}")
    else:
        ids = args.finding or []
        miss = [i for i in ids if i not in F]
        if not ids or miss:
            import difflib
            near = difflib.get_close_matches(miss[0], list(F), n=1) if miss else []
            raise Refused(f"no finding {miss[0] if miss else '(none named)'} in this round" + (f" (did you mean {near[0]}?)" if near else "")
                          + ": vs review show lists them")
    check = args.check or (F[ids[0]].get("check") if len({F[i].get("check") for i in ids}) == 1 else None)
    append([{"type": "finding.advised", "ids": ids, "check": check, "advice": args.advice, "plain": args.plain, "why": args.why}], "agent")
    print(f"advised {args.advice} on {len(ids)} finding(s): {', '.join(ids[:6])}{' …' if len(ids) > 6 else ''}")


def log_step(args):
    """A step the human took outside the page (an OK in chat, a listen on the listening page): it joins the page's log."""
    when = None
    if args.when:
        try:
            when = datetime.fromisoformat(args.when).astimezone().isoformat(timespec="seconds")
        except ValueError:
            raise Refused(f"--when {args.when!r}: a time like 2026-10-01T20:20")
    append([{"type": "step.logged", "text": args.text, **({"stage": args.stage} if args.stage else {}),
             **({"when": when} if when else {}), **({"where": args.where} if args.where else {})}], "agent")
    print(f"logged: {args.text or '(stage mark)'}" + (f" · stage {args.stage}" if args.stage else "") + (f" · {when[:16]}" if when else ""))


def ask(args):
    append([{"type": "note.question", "id": args.note, "text": args.text}], "agent")
    print(f"{args.note}: asked; it waits for the human's answer")


def check_tags(tags):
    import difflib
    for t in tags or []:
        if t not in TAGS:
            near = difflib.get_close_matches(t, TAGS, n=1)
            raise Refused(f"no tag {t!r}{f' (did you mean {near[0]!r}?)' if near else ''}: the list is in vs help review")


def resolve(args):
    check_tags(args.tags)
    S = state()
    n = S["notes"].get(args.note) or sys.exit(f"⛔ no note {args.note}")
    tgt = (n.get("target") or {}).get("el")
    e = {"type": "note.resolved", "id": args.note, "outcome": "wontdo" if args.wontdo else "resolved",
         "said": args.said, "files": args.files or [], "tags": args.tags or [], "renamed": args.renamed,
         "removed": args.removed, **({"expect": args.expect} if getattr(args, "expect", None) else {})}
    if tgt and not args.wontdo and not (args.renamed or args.removed):
        # a target that's no longer in the build has to be accounted for: renamed, or removed on purpose (a sound's
        # address lives in vs mix's cues, an element's in vs inspect's map)
        if tgt.startswith("sfx/"):
            ids = {c["el"] for c in vslib.read_json("build/mix/cues.json") or []}
        else:
            ids = {x["id"] for x in (vslib.read_json("build/elements.json") or {}).get("items", [])}
        if ids and tgt not in ids:
            raise Refused(f"{tgt} isn't in the build any more: say --renamed <new name> or --removed")
    append([e], "agent")
    want = feedback.target_dims(ask_of(n), e.get("expect"))
    print(f"{args.note}: {e['outcome']}" + (f" (the next version is measured for a change in {', '.join(sorted(want))})" if want and not args.wontdo
                                             else " (the next version is measured at that moment, the whole frame)" if e.get("expect") == "elsewhere" else ""))


def learn(args):
    cs = candidates()
    if not cs:
        return print("no patterns yet: a tag counts once it's on accepted notes in 2 projects, or 3 times in one")
    for c in cs:
        dest = KIND_DEST[TAGS.get(c["tag"], ("procedure",))[0]]
        where = ", ".join(f"{p} ×{n}" for p, n in c["projects"].items())
        print(f"{c['tag']}: {c['count']} accepted notes ({where}) → would go to {DEST[dest]}")
        for cm in c["comments"]:
            print(f"    \u201c{cm}\u201d")
        print(f"  vs review propose {c['tag']} \"<one rule, in the human's terms>\"")


def propose(args):
    check_tags([args.tag])
    kind = TAGS[args.tag][0]
    dest = args.to or KIND_DEST[kind]
    if dest == "kit" and kind != "kit":
        raise Refused(f"{args.tag} is taste ({kind}): it stays in the studio, never the public kit")
    c = next((x for x in candidates() if x["tag"] == args.tag), None)
    S, new = append([{"type": "lesson.proposed", "lesson": {"tag": args.tag, "text": args.text, "dest": dest,
                                                            "evidence": c["notes"] if c else [], "count": c["count"] if c else 0}}], "agent")
    print(f"{new[0]['lesson']['id']}: proposed ({args.tag} → {DEST[dest]}); the human answers Every video, Every {kind_of()}, "
          f"This video only or Ignore; then vs review promote {new[0]['lesson']['id']} writes a kept one down")


def report(args):
    """The dogfood's numbers, from the diary (and the ledger for cost): how pointed the notes were, how often Claude got
    them right the first time, what the checks showed and missed, what was learned, how long reviewing took."""
    S = state()
    notes = [n for n in S["notes"].values() if n["status"] != "withdrawn"]
    pct = lambda a, b: f"{round(100 * a / b)}%" if b else "—"
    pinned = sum(1 for n in notes if (n.get("target") or {}).get("el"))
    marked = sum(1 for n in notes if (n.get("mark") or {}).get("type") not in (None, "none") or n.get("also"))
    asked = sum(1 for n in notes if any(h["type"] in ("question", "choice") for h in n["thread"]))  # a choice offered --for it asks back too
    accepted = [n for n in notes if n["status"] == "accepted"]
    first = sum(1 for n in accepted if not any(h["type"] == "reopened" for h in n["thread"]))
    reopened = sum(1 for n in notes if any(h["type"] == "reopened" for h in n["thread"]))
    follow = sum(1 for n in notes if n.get("follows"))
    flagged = sum(1 for n in notes if (n.get("measured") or {}).get("flag"))
    over = sum(1 for n in accepted if (n.get("accepted") or {}).get("verdict") not in (None, *feedback.VERIFIED))
    shown = set()
    for R in S["rounds"]:
        shown |= set(R.get("asked") or [])
        try:
            home = f"{version_of(R['video'])[1]}.review"
        except Refused:
            continue
        shown |= {f["id"] for f in (vslib.read_json(f"{home}/qa.json") or {}).get("items", [])}
        shown |= {f["id"] for f in (vslib.read_json(f"{home}/findings.json") or {}).get("items", []) if f.get("severity") == "warning"}
    decided = S["findings"]
    conf = sum(1 for d in decided.values() if d["status"] == "confirmed")
    dism = sum(1 for d in decided.values() if d["status"] == "dismissed")
    advised = [d for d in decided.values() if d.get("followed") is not None]
    log = read_log()
    undos = sum(1 for e in log if e.get("type") == "undo" and not e.get("cascade"))
    sends = sum(R.get("sends") or (1 if R.get("sent") else 0) for R in S["rounds"])
    misses = sum(1 for n in accepted if "qa.miss" in ((n.get("resolution") or {}).get("tags") or []))
    L = list(S["lessons"].values())
    kept = [l for l in L if l["decision"] == "remember"]
    rows = vslib.rows(project=vslib.project_name())
    usd = sum(vslib.usd_of(r) for r in rows)
    by = {}
    for r in rows:
        by[r.get("vendor")] = by.get(r.get("vendor"), 0) + float(r.get("credits") or 0)
    T = S["time"]
    vs_ = [R["version"] for R in S["rounds"]]
    M = [("Rounds", f"{len(S['rounds'])}" + (f" (v{min(vs_)} → v{max(vs_)})" if vs_ else "")),
         ("Notes", f"{len(notes)} ({follow} follow-ups)"),
         ("…pinned to an element", f"{pinned} ({pct(pinned, len(notes))}); {marked} with a mark"),
         ("…that needed a question back", f"{asked} ({pct(asked, len(notes))})"),
         ("…right first time (accepted, never reopened)", f"{first} of {len(accepted)} accepted ({pct(first, len(accepted))}); {reopened} reopened"),
         ("…answers the measurement flagged", f"{flagged}"),
         ("…accepted over the measurement", f"{over}"),
         ("Choices offered / picked (none of these)", f"{len(S['choices'])} / {sum(1 for c in S['choices'].values() if c.get('picked'))}"
          f" ({sum(1 for c in S['choices'].values() if c.get('picked') == 'none')})"),
         ("Findings shown / fix it / leave it", f"{len(shown)} / {conf} / {dism}"),
         ("…decided with Claude's advice taken", f"{sum(1 for d in advised if d['followed'])} of {len(advised)} advised"),
         ("Feedback sends (Approve & send)", f"{sends}"),
         ("Taken back before sending (Undo)", f"{undos}"),
         ("QA misses (tagged qa.miss, accepted)", f"{misses}"),
         ("Lessons proposed / kept / turned into checks", f"{len(L)} / {len(kept)} / {sum(1 for l in kept if l.get('dest') == 'check')}"),
         ("Time reviewing (playing)", f"{T['secs'] / 60:.0f} min ({T['playing'] / 60:.0f} min)"),
         ("Cost (the ledger)", f"${usd:.2f}" + (" · " + ", ".join(f"{v} {c:.0f} credits" for v, c in by.items() if c) if any(by.values()) else "")),
         ("Scenes marked done", f"{len(S['done'])}"),
         ("Tool problems reported", f"{len(S['friction'])}")]
    if args.md:
        print("| Metric | Value |\n|---|---|")
        for k, v in M:
            print(f"| {k} | {v} |")
    else:
        print(f"Review report · {vslib.project_name()}")
        for k, v in M:
            print(f"  {k:48s} {v}")


# ── the protocol's view: one note as a feedback record, whose move it is, whether the review may end, and the rules
#    the human made. The video's own addressing lives here; everything else is feedback.py's. ──
def video_address(n):
    """Where a note points, in a video's terms (the protocol carries this, never reads it): the moment or range, the
    scene, the element and its box, the mark, the keep-clear zones, the sound, the step it's about."""
    tm = n["time"]
    a = {"domain": "video", **({"t": tm["t"]} if "t" in tm else {"t0": tm["t0"], "t1": tm["t1"]}),
         "segment": n.get("segment"), "scene": n.get("scene")}
    tg = n.get("target") or {}
    for k, v in (("element", tg.get("el")), ("box", tg.get("box")), ("text", tg.get("text")), ("on", tg.get("on"))):
        if v is not None:
            a[k] = v
    mk = n.get("mark") or {}
    if mk.get("type") not in (None, "none"):
        a["mark"] = mk
    for k in ("also", "sound", "step", "visible"):
        if n.get(k):
            a[k] = n[k]
    return a


def as_record(n, S, art):
    """A note as the protocol's feedback record: the video's address, the shape it was written on, and its ask (a sound's
    ask lives on the sound)."""
    return feedback.record(n, S["notes"], {**art, "rendition": n.get("cut")}, video_address(n), ask=ask_of(n))


def project_rules(S):
    """The human's rules for this video only: notes they said reach the whole video (once accepted), and lessons they
    kept for this video. Project state: they never leave the project's review/ (a rule for every video needs its own yes)."""
    out = [{"from": n["id"], "text": ((n.get("comment") or "").strip() or feedback.ASK_WORDS.get(n.get("ask"), "")),
            "ask": n.get("ask")} for n in S["notes"].values() if n["status"] == "accepted" and n.get("scope") == "project"]
    out += [{"from": l["id"], "text": l.get("text"), "tag": l.get("tag")} for l in S["lessons"].values() if l.get("decision") == "project"]
    return out


def context_package(S):
    """What the review page is handed for the round, per shape: the render, and its version's own maps (the archive vs
    build keeps beside every render). Missing pieces aren't fatal; they make the page point from less."""
    R = current(S)
    out = []
    for c in (R.get("cuts") or [{"cut": R.get("cut"), "video": R["video"]}]) if R else []:
        try:
            base = version_of(c["video"])[1]
        except Refused:
            continue
        tl = vslib.read_json(f"{base}.review/timeline.json") or vslib.read_json(f"{base}.timeline.json")
        fp = tl and tl.get("fingerprint")
        have = {"video": os.path.exists(c["video"]), "timeline": bool(tl), "elements": bool(element_map(base, fp)),
                "findings": inspected(base, fp) is not None, "qa": os.path.exists(f"{base}.review/qa.json"),
                "cues": os.path.exists(f"{base}.review/cues.json"), "composition": os.path.exists(f"{base}.review/comp.html")}
        out.append({"rendition": c["cut"], "video": c["video"], "archive": f"{base}.review/", "has": have})
    return out


def status(args):
    """Whose move it is, and whether the review may end: decided from the diary alone, the same answer every time."""
    S, Hv = state(), state("human")
    held = len(Hv["pending"])
    who, why = feedback.turn(S, held)
    R = current(S)
    shapes = [c["cut"] for c in (R or {}).get("cuts") or []] or [(R or {}).get("cut")]  # a round shows one version in each shape
    checks = feedback.exit_checks(S, held, shapes, {(a.get("version"), a.get("cut")) for a in S["approved"]})
    ready = all(ok for _, ok, _ in checks)
    art = {"project": vslib.project_name(), "kind": kind_of()}
    recs = [as_record(n, S, art) for n in S["notes"].values() if n["status"] != "withdrawn"]
    out = {"turn": who, "why": why, "waiting": agent_waiting(), "stage": S.get("stage"),
           "round": R and {k: R.get(k) for k in ("n", "version", "cut", "status", "sends", "read_sends")},
           "exit": {"ready": ready, "checks": [{"id": i, "ok": ok, "text": t} for i, ok, t in checks]},
           "advisories": feedback.advisories(S), "rules": project_rules(S), "context": context_package(S),
           "records": recs, "finished": S.get("finished")}
    if args.ready:
        if not ready:
            sys.exit("not yet: " + "; ".join(t for _, ok, t in checks if not ok))
        return print("ready: the review may hand back to the workflow")
    if args.json:
        return print(json.dumps(out, indent=1))
    print(f"Review · {art['project']} ({art['kind']})" + (f" · round {R['n']} on v{R['version']} · {R['status']}" if R else "")
          + (f" · stage {S['stage']}" if S.get("stage") else ""))
    print(f"turn: {who} · {why}" + (" · vs review wait is running" if out["waiting"] else ""))
    print(f"exit: {'ready' if ready else 'not yet'}")
    for i, ok, t in checks:
        print(f"  {'✓' if ok else '✗'} {t}")
    live = [r for r in recs if r["phase"] != "closed"]
    if live:
        print("notes: " + " · ".join(f"{r['id']} {r['phase']}" + (f" ({feedback.VERDICT_WORDS[r['verification']['verdict']]})" if r["verification"] else "")
                                     for r in live))
    for a in out["advisories"]:
        print(f"  heads-up: {a}")
    for c in out["context"]:
        print(f"context ({c['rendition']}): {c['archive']} " + " ".join(f"{k} {'✓' if v else '✗'}" for k, v in c["has"].items()))


# ── learning, the last step: a rule is written into the studio only after the human said how far it reaches ──
HEADINGS = {"pacing": "Picture", "layout": "Picture", "type": "Picture", "motion": "Picture", "color": "Picture",
            "copy": "Story and words", "story": "Story and words", "audio": "Sound", "qa": "Spend and process"}


def lessons_path():
    s = vslib.studio_root()
    return os.path.join(s, "lessons.md") if s else None


def _dotted(d, path):
    for k in path.split(".")[:-1]:
        d = d.setdefault(k, {}) if isinstance(d, dict) else None
    return d


def promote(args):
    """vs review promote <lesson> [--heading …] [--set path=value] [--chat "<their words>" --as remember|kind]
    Write a lesson the human decided (Every video / Every <kind>) into the studio: a line in lessons.md (dated, with a
    marker so vs review rules lists it and vs review forget takes it out) and, for a value, the profile. Refused for a
    lesson the human hasn't decided, ignored, or kept for this video only. --chat: they decided it in chat; their words
    are kept as the decision (the page's buttons are the usual way)."""
    S = state()
    lz = S["lessons"].get(args.lesson) or sys.exit(f"⛔ no lesson {args.lesson} in this project (vs review show lists them)")
    if args.chat is not None:
        if not args.chat.strip() or args.as_ not in ("remember", "kind"):
            raise Refused("--chat needs the human's own words and --as remember|kind (what they said it reaches)")
        if lz.get("decision") is None:
            append([{"type": "lesson.decided", "id": lz["id"], "decision": args.as_, "via": "chat", "said": args.chat.strip(),
                     "recorded_by": "agent"}], "human")
            lz = state()["lessons"][lz["id"]]
    d = lz.get("decision")
    if d is None:
        raise Refused(f"{lz['id']} waits for the human: they answer it in the page (or, if they said it in chat, --chat \"<their words>\" --as remember|kind)")
    if d == "ignore":
        raise Refused(f"{lz['id']}: the human said ignore it, so it isn't a rule")
    if d == "project":
        raise Refused(f"{lz['id']}: this video only. It stays in this project (vs review show lists it under this video's rules); nothing goes into the studio")
    if lz.get("dest") == "kit":
        raise Refused(f"{lz['id']}: a kit rule is a kit change (scars.md and a regression test), not a studio file")
    f = lessons_path() or sys.exit("⛔ no studio: a rule needs somewhere to be kept (vs setup)")
    mark = f"{vslib.project_name()}/{lz['id']}"
    doc = open(f).read() if os.path.exists(f) else "# Lessons\n"
    if feedback.RULE_MARK.format(mark) in doc:
        raise Refused(f"{mark} is already in lessons.md (vs review rules lists it)")
    kind = kind_of()
    heading = args.heading or HEADINGS.get((lz.get("tag") or "").split(".")[0], "Learned in review")
    day = datetime.now()
    setv = None
    if args.set:
        path, _, raw = args.set.partition("=")
        if not path or not raw:
            raise Refused("--set <path>=<value>, e.g. --set mix.music_db=-18 (a JSON value)")
        try:
            val = json.loads(raw)
        except ValueError:
            val = raw
        pp = os.path.join(vslib.studio_root(), "profile.json")
        prof = vslib.read_json(pp) or {}
        parent = _dotted(prof, path)
        if not isinstance(parent, dict):
            raise Refused(f"--set {path}: there's a value (not a section) on the way to it in profile.json")
        key = path.split(".")[-1]
        setv = {"path": path, "old": parent.get(key), "new": val}
        parent[key] = val
        json.dump(prof, open(pp, "w"), indent=1)
    scope_word = {"kind": f"{kind}s only"}.get(d)
    extra = f"(profile: {setv['path']} = {json.dumps(setv['new'])})" if setv else None
    line = feedback.rule_line(lz["text"], f"{day:%b} {day.day}", scope_word, extra, mark)
    open(f, "w").write(feedback.insert_rule(doc, heading, line))
    _studio_write([{"kind": "rule", "action": "promoted", "project": vslib.project_name(), "lesson": lz["id"], "tag": lz.get("tag"),
                    "text": lz.get("text"), "scope": feedback.DECISION_SCOPE[d], "of_kind": kind, "file": "lessons.md",
                    "heading": heading, "line": line, **({"set": setv} if setv else {}), "via": lz.get("via") or "page",
                    "at": now()}])
    print(f"{mark}: written to lessons.md under “{heading}”" + (f" and profile.json {setv['path']} = {json.dumps(setv['new'])}" if setv else "")
          + f" ({'every ' + kind if d == 'kind' else 'every video'}). vs review forget {lz['id']} takes it out.")
    if lz.get("dest") in ("profile", "check") and not setv:
        print(f"  (it's a {lz['dest']} kind of lesson: if a value should change too, vs review promote can't guess it; set it with --set next time)")


def promoted():
    """Every rule promoted in this studio and not taken back: [{…the promote line…, "present": still in lessons.md}]."""
    live = {}
    for l in studio_feedback():
        if l.get("kind") != "rule":
            continue
        k = f"{l['project']}/{l['lesson']}"
        if l.get("action") == "promoted":
            live[k] = l
        elif l.get("action") == "forgotten":
            live.pop(k, None)
    f = lessons_path()
    doc = open(f).read() if f and os.path.exists(f) else ""
    return [{**l, "mark": k, "present": feedback.RULE_MARK.format(k) in doc} for k, l in live.items()]


def rules(args):
    """vs review rules: what the studio has learned through review, where each rule lives, and where it came from."""
    rs = promoted()
    S = state() if os.path.exists(LOG) else None
    waiting = [l for l in (S or {}).get("lessons", {}).values() if l.get("decision") in ("remember", "kind")
               and not any(r["mark"] == f"{vslib.project_name()}/{l['id']}" for r in rs)]
    if args.json:
        return print(json.dumps({"studio": rs, "decided_not_written": waiting, "this_video": project_rules(S) if S else []}, indent=1))
    if not rs:
        print("no rules promoted through review yet (lessons.md may hold older ones written by hand)")
    for r in rs:
        reach = {"studio": "every video", "kind": f"every {r.get('of_kind')}"}.get(r.get("scope"), r.get("scope"))
        print(f"{r['mark']}  {reach} · {r.get('tag')} · {r.get('heading')}{'' if r['present'] else ' · ⚠ not in lessons.md any more (edited by hand?)'}")
        print(f"    {r.get('text')}" + (f"  [profile {r['set']['path']}: {json.dumps(r['set']['old'])} → {json.dumps(r['set']['new'])}]" if r.get("set") else ""))
    for l in waiting:
        print(f"decided, not written yet: {l['id']} ({l['decision']}) “{l.get('text')}” → vs review promote {l['id']}")
    if S and project_rules(S):
        print("this video only: " + " · ".join(f"{r['from']} {r['text']}" for r in project_rules(S)))


def forget(args):
    """vs review forget <lesson | project/lesson>: take a promoted rule back out of lessons.md (and put a value it set in
    the profile back, if nobody has changed it since). The tag isn't asked about again unless the human brings it up."""
    mark = args.lesson if "/" in args.lesson else f"{vslib.project_name()}/{args.lesson}"
    r = next((x for x in promoted() if x["mark"] == mark), None)
    if not r:
        raise Refused(f"no promoted rule {mark} (vs review rules lists them)")
    f = lessons_path()
    doc, hit = feedback.remove_rule(open(f).read(), mark) if f and os.path.exists(f) else ("", None)
    if hit:
        open(f, "w").write(doc)
    restored = ""
    if r.get("set"):
        pp = os.path.join(vslib.studio_root(), "profile.json")
        prof = vslib.read_json(pp) or {}
        parent, key = _dotted(prof, r["set"]["path"]), r["set"]["path"].split(".")[-1]
        if isinstance(parent, dict) and parent.get(key) == r["set"]["new"]:
            if r["set"]["old"] is None:
                parent.pop(key, None)
            else:
                parent[key] = r["set"]["old"]
            json.dump(prof, open(pp, "w"), indent=1)
            restored = f"; profile {r['set']['path']} back to {json.dumps(r['set']['old'])}"
        else:
            restored = f"; profile {r['set']['path']} changed since it was promoted, so it's left as it is"
    proj, lid = mark.split("/", 1)
    _studio_write([{"kind": "rule", "action": "forgotten", "project": proj, "lesson": lid, "tag": r.get("tag"), "at": now()},
                   {"kind": "lesson", "decision": "forgotten", "project": proj, "lesson": lid, "tag": r.get("tag"), "at": now()}])
    print(f"{mark}: forgotten" + (" (its line is out of lessons.md)" if hit else " (its line wasn't in lessons.md)") + restored)


# ── Decide: choices with live variants. A variant is a built composition kept aside (build/variants/<id>/): the page
#    plays it live over the round's sound, so a motion or timing choice costs no render. A music take plays through the
#    Mix panel's stems. A picture or clip is shown as it is. A paid option is priced by its own step's spend gate (run in
#    estimate mode: nothing spent) and only made once the human picks it. ──
VARIANTS = "build/variants"
SOURCES = ("reel.json", "plan.json", "scenes.js", "cues.py")  # what made a variant: apply puts them back
MEDIA = {".mp4": "video", ".mov": "video", ".webm": "video", ".jpg": "image", ".jpeg": "image", ".png": "image",
         ".webp": "image", ".mp3": "audio", ".wav": "audio", ".m4a": "audio"}


def _fingerprint(html):
    import hashlib
    return hashlib.sha256(open(html, "rb").read()).hexdigest()[:16]


def _clone(src, dst):
    """A copy that costs no space where the disk can share blocks (APFS clones), else a plain copy. Never a link: a
    later build writes into build/comp, and a link would carry that write into the variant."""
    import shutil
    if sys.platform == "darwin" and subprocess.run(["cp", "-cR", src, dst], capture_output=True).returncode == 0:
        return
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)


def _offered(vid):
    """The open choices (not yet picked) that show variant `vid`."""
    return [c["id"] for c in state()["choices"].values() if not c.get("picked")
            and any(o.get("kind") == "variant" and o.get("preview", "").rstrip("/") == f"{VARIANTS}/{vid}" for o in c["options"])]


def variant(args):
    """vs review variant <id> ["what it is"]: keep what's built now (build/comp, its timeline, its element map and
    findings, and the sources that made it) as build/variants/<id>/, an option the human plays live in Decide."""
    import shutil
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", args.id) or args.id == "none":
        raise Refused(f"{args.id!r}: a variant id is short, lower-case letters, digits, - or _ (and not \"none\")")
    html, tl = "build/comp/index.html", vslib.read_json("build/timeline.json")
    if not os.path.exists(html) or not tl:
        raise Refused("nothing built: vs build --no-render first")
    fp = _fingerprint(html)
    if tl.get("fingerprint") != fp:
        raise Refused("build/timeline.json isn't this composition's: vs build --no-render again")
    F = vslib.read_json("build/findings.json")
    if not args.anyway:  # errors never reach the human, as in a round
        if not F or F.get("fingerprint") != fp:
            raise Refused("vs inspect hasn't checked this composition: vs inspect first (--anyway to keep it unchecked)")
        errs = [f for f in F["items"] if f.get("severity") == "error"]
        if errs:
            raise Refused(f"{len(errs)} open error(s) from vs inspect (first: {errs[0]['check']} {' × '.join(errs[0]['elements'])} "
                          f"at {errs[0]['t0']:.1f}s): fix them before the human sees it (--anyway to keep it)")
    d = f"{VARIANTS}/{args.id}"
    if os.path.exists(d):
        busy = _offered(args.id)
        if busy and not args.replace:
            raise Refused(f"{d} is an option in {', '.join(busy)}, still waiting for the human: --replace to change what they see")
        shutil.rmtree(d)
    os.makedirs(VARIANTS, exist_ok=True)
    _clone("build/comp", d)
    shutil.copy("build/timeline.json", f"{d}/timeline.json")
    for f in ("elements.json", "findings.json"):
        J = vslib.read_json(f"build/{f}")
        if J and J.get("fingerprint") == fp:
            shutil.copy(f"build/{f}", f"{d}/{f}")
    os.makedirs(f"{d}/source", exist_ok=True)
    kept = [f for f in SOURCES if os.path.exists(f)]
    for f in kept:
        shutil.copy(f, f"{d}/source/{f}")
    json.dump({"id": args.id, "label": args.label, "fingerprint": fp, "end": tl.get("end"), "size": tl.get("size"),
               "fps": tl.get("fps"), "sources": kept, "inspected": bool(F and F.get("fingerprint") == fp), "made": now()},
              open(f"{d}/variant.json", "w"), indent=1)
    print(f"{d}/ ({args.label or 'no label'}): {tl.get('end', 0):.2f}s, sources kept: {', '.join(kept)}")
    print(f"  offer it: vs review offer \"<the question>\" --option {args.id} --option <another> [--t <from> <to>]")


def _timing_vs(vtl, rtl):
    """How a variant's timing differs from the round's (the page plays it over the round's sound)."""
    if not vtl or not rtl:
        return None
    if abs((vtl.get("end") or 0) - (rtl.get("end") or 0)) > 1e-3:
        return f"ends {vtl['end'] - rtl['end']:+.2f}s from the round's version"
    a = [(x["name"], round(x["t0"], 3)) for x in vtl.get("segments", [])]
    b = [(x["name"], round(x["t0"], 3)) for x in rtl.get("segments", [])]
    if a != b:
        moved = [n for (n, t), m in zip(a, b) if (n, t) != m]
        return f"scenes move ({', '.join(moved[:3]) or 'the list changed'})"
    return None


def _priced(cmd):
    """A paid option's price, from its own step's spend gate in estimate mode (VIDEO_KIT_ESTIMATE): nothing is spent."""
    import shlex, tempfile
    words = shlex.split(cmd)
    if words and words[0] == "vs":
        words = words[1:]
    if not words:
        raise Refused("--paid needs the step that makes it, e.g. --paid c='gen still --prompt \"…\" --out media/c.png'")
    out = os.path.join(tempfile.gettempdir(), f"vk-estimate-{os.getpid()}-{len(words)}.json")
    if os.path.exists(out):
        os.remove(out)
    r = subprocess.run([sys.executable, os.path.join(vslib.ENGINE, "studio.py"), *words], capture_output=True, text=True,
                       env={**os.environ, "VIDEO_KIT_ESTIMATE": out})
    E = vslib.read_json(out) if os.path.exists(out) and os.path.getsize(out) else None
    if os.path.exists(out):
        os.remove(out)
    if not E:
        raise Refused(f"vs {' '.join(words)} didn't reach its spend gate (so there's no price): {(r.stderr or r.stdout).strip()[-300:]}")
    if E["over_cap"]:
        raise Refused(f"{E['what']}: about {E['cost']} would pass the {E['limit']:g}-credit cap on this video: ask the human first")
    if E["over_budget"]:
        raise Refused(f"{E['what']}: about {E['cost']} would pass this video's dollar budget: ask the human first")
    return E, shlex.join(words)


def _spent_on(path):
    """What the ledger says a picture or clip already cost (vs gen logs it by file name)."""
    rows = [r for r in vslib.rows(project=vslib.project_name()) if r.get("what") == os.path.basename(path)]
    if not rows:
        return None
    cr, usd = sum(float(r.get("credits") or 0) for r in rows), sum(vslib.usd_of(r) for r in rows)
    return " · ".join(x for x in [f"{cr:g} {rows[0]['vendor']} credits" if cr else "", f"${usd:.2f}" if usd else ""] if x) + ", spent"


def offer(args):
    """A choice: the human plays each option and picks one (or none, with words)."""
    S = state()
    R = current(S)
    rtl = None
    if R:
        try:
            base = version_of(R["video"])[1]
            rtl = vslib.read_json(f"{base}.review/timeline.json") or vslib.read_json(f"{base}.timeline.json")
        except Refused:
            pass
    labels = dict(x.partition("=")[::2] for x in args.label or [])
    paid = dict(x.partition("=")[::2] for x in args.paid or [])
    opts = []
    for o in args.option:
        k, _, v = o.partition("=")
        if not v and k in paid:  # nothing to see until it's made: the price is the preview
            v = "paid:"
        v = v or f"{VARIANTS}/{k}/"
        opt = {"id": k}
        if v.startswith("take:"):
            cfg = vslib.read_json("build/mixer/config.json") or {}
            n = int(v[5:])
            tk = next((x for x in cfg.get("takes", []) if x["n"] == n), None)
            if not tk:
                raise Refused(f"option {k}: no music take {n} in the Mix panel's stems (vs mix makes them)")
            opt.update(kind="take", take=n, label=tk.get("label"))
        elif v == "paid:":
            opt.update(kind="paid")
        elif os.path.isdir(v):
            if not os.path.exists(os.path.join(v, "index.html")):
                raise Refused(f"option {k}: {v} has no composition (vs review variant {k} keeps one)")
            vj = vslib.read_json(os.path.join(v, "variant.json")) or {}
            vtl = vslib.read_json(os.path.join(v, "timeline.json"))
            opt.update(kind="variant", preview=v.rstrip("/") + "/", label=vj.get("label"), end=(vtl or {}).get("end"))
            diff = _timing_vs(vtl, rtl)
            if diff:
                opt["timing"] = diff
        elif os.path.isfile(v) and os.path.splitext(v)[1].lower() in MEDIA:
            opt.update(kind=MEDIA[os.path.splitext(v)[1].lower()], preview=v)
            sp = _spent_on(v)
            if sp:
                opt["cost"] = sp
        else:
            raise Refused(f"option {k}: {v!r} isn't a variant folder, take:N, or a picture, clip or sound in this project")
        if k in labels:
            opt["label"] = labels[k]
        if k in paid:
            E, run = _priced(paid[k])
            opt.update(paid=True, run=run, cost=f"about {E['cost']}, spent only if you pick it", estimate=E)
        opts.append(opt)
    c = {"question": args.question, "options": opts,
         "cost": "free: drawn variants, played live" if all(o["kind"] == "variant" for o in opts)
         else "paid: " + ", ".join(f"{o['id']} {o['cost']}" for o in opts if o.get("cost")) if any(o.get("cost") for o in opts)
         else "free"}
    if args.t:
        c["time"] = {"t0": args.t[0], "t1": args.t[1]} if len(args.t) > 1 else {"t": args.t[0]}
    if getattr(args, "for_", None):
        c["for"] = args.for_
    S, new = append([{"type": "choice.offered", "choice": c}], "agent")
    print(f"{new[0]['choice']['id']}: offered ({len(opts)} options: "
          + ", ".join(f"{o['id']} {o['kind']}" + (f" ({o['label']})" if o.get("label") else "") for o in opts) + ")")
    for o in opts:
        if o.get("timing"):
            print(f"  ⚠️  {o['id']}: its timing differs ({o['timing']}): it plays over the round's sound, which may not line up")
        if o.get("paid"):
            print(f"  {o['id']}: {o['cost']} (picked → vs {o['run']} --yes)")
    print("  the human plays them in Review Studio's Decide panel and picks; then vs review apply " + new[0]["choice"]["id"])


def apply_choice(args):
    """vs review apply <choice>: do what the human picked. A variant's sources go back into the project (then build,
    inspect, render); a take goes into mix.json; a paid option prints the step to run (the pick was the yes to its
    price). Logged as choice.applied."""
    import filecmp, shutil
    S = state()
    c = S["choices"].get(args.choice) or sys.exit(f"⛔ no choice {args.choice}")
    pick = c.get("picked")
    if not pick:
        raise Refused(f"{c['id']} hasn't been picked yet: it waits for the human in the Decide panel")
    if pick == "none":
        said = c.get("said")
        print(f"{c['id']}: none of these — \u201c{said}\u201d. Make new options (or answer the note) from that.")
        return append([{"type": "choice.applied", "id": c["id"], "pick": pick, "said": "none: back to the human's words"}], "agent")
    o = next(x for x in c["options"] if x["id"] == pick)
    said = None
    if o["kind"] == "variant":
        src = os.path.join(o["preview"], "source")
        changed = []
        for f in sorted(os.listdir(src)) if os.path.isdir(src) else []:
            if not os.path.exists(f) or not filecmp.cmp(f"{src}/{f}", f, shallow=False):
                shutil.copy(f"{src}/{f}", f)
                changed.append(f)
        said = f"restored {', '.join(changed) or 'nothing (the project already matches)'} from {o['preview']}"
        print(f"{c['id']}: {pick} ({o.get('label') or 'variant'}) → {said}")
        print("  next: vs build --no-render → vs inspect → bump \"version\" → vs build")
    elif o["kind"] == "take":
        m = vslib.read_json("mix.json") or {}
        m["take"] = o["take"]
        json.dump(m, open("mix.json", "w"), indent=1)
        said = f"mix.json take → {o['take']}"
        print(f"{c['id']}: {pick} → {said}; next: vs mix --video <the round's video> --tag vN --final")
    elif o.get("paid"):
        said = f"to run: vs {o['run']} --yes ({o['cost']})"
        print(f"{c['id']}: {pick} → the human said yes to {o['cost'].split(',')[0]}: vs {o['run']} --yes")
    else:
        said = f"use {o['preview']}"
        print(f"{c['id']}: {pick} → {said}")
    append([{"type": "choice.applied", "id": c["id"], "pick": pick, "said": said}], "agent")


def main():
    ap = argparse.ArgumentParser(prog="vs review", description="Review Studio (vs help review)")
    ap.add_argument("--port", type=int, default=4470)
    sub = ap.add_subparsers(dest="cmd")
    o = sub.add_parser("open"); o.add_argument("--video"); o.add_argument("--ask", action="store_true")
    o.add_argument("--also"); o.add_argument("--only", action="store_true")
    o.add_argument("--stage", choices=sorted(ALL_STAGES))
    av = sub.add_parser("advise"); av.add_argument("finding", nargs="*"); av.add_argument("--check")
    av.add_argument("--advice", choices=["leave", "fix"], required=True); av.add_argument("--plain", required=True); av.add_argument("--why")
    st = sub.add_parser("step"); st.add_argument("text", nargs="?", default=""); st.add_argument("--stage", choices=sorted(ALL_STAGES))
    st.add_argument("--when"); st.add_argument("--where")
    s = sub.add_parser("show"); s.add_argument("note", nargs="?"); s.add_argument("--json", action="store_true")
    q = sub.add_parser("ask"); q.add_argument("note"); q.add_argument("text")
    r = sub.add_parser("resolve"); r.add_argument("note"); r.add_argument("--said", required=True)
    r.add_argument("--wontdo", action="store_true"); r.add_argument("--files", nargs="*"); r.add_argument("--tags", nargs="*")
    r.add_argument("--expect", choices=sorted(feedback.EXPECT))
    g = r.add_mutually_exclusive_group(); g.add_argument("--renamed"); g.add_argument("--removed", action="store_true")
    sub.add_parser("learn")
    rp = sub.add_parser("report"); rp.add_argument("--md", action="store_true")
    p = sub.add_parser("propose"); p.add_argument("tag"); p.add_argument("text"); p.add_argument("--to", choices=list(DEST))
    f = sub.add_parser("offer"); f.add_argument("question"); f.add_argument("--option", action="append", required=True)
    f.add_argument("--t", nargs="+", type=float); f.add_argument("--label", action="append")
    f.add_argument("--paid", action="append"); f.add_argument("--for", dest="for_")
    v = sub.add_parser("variant"); v.add_argument("id"); v.add_argument("label", nargs="?")
    v.add_argument("--anyway", action="store_true"); v.add_argument("--replace", action="store_true")
    ap_ = sub.add_parser("apply"); ap_.add_argument("choice")
    sub.add_parser("serve")
    w = sub.add_parser("wait"); w.add_argument("--hours", type=float, default=12); w.add_argument("--replace", action="store_true", help="stop a watcher already running here and take over")
    sub.add_parser("launch")
    stt = sub.add_parser("status"); stt.add_argument("--json", action="store_true"); stt.add_argument("--ready", action="store_true")
    pr = sub.add_parser("promote"); pr.add_argument("lesson"); pr.add_argument("--heading"); pr.add_argument("--set")
    pr.add_argument("--chat"); pr.add_argument("--as", dest="as_", choices=["remember", "kind"])
    ru = sub.add_parser("rules"); ru.add_argument("--json", action="store_true")
    fg = sub.add_parser("forget"); fg.add_argument("lesson")
    fi = sub.add_parser("finish"); fi.add_argument("--final", nargs="+", required=True)
    cv = sub.add_parser("cover"); cv.add_argument("card"); cv.add_argument("--by", required=True)
    cv.add_argument("--as", dest="as_", choices=["fix", "leave"]); cv.add_argument("--pick"); cv.add_argument("--why")
    a = ap.parse_args()
    try:
        if a.cmd in (None, "serve"):
            import review_server
            return review_server.serve(a.port)
        {"open": open_round, "show": show, "ask": ask, "resolve": resolve, "offer": offer, "learn": learn,
         "propose": propose, "report": report, "variant": variant, "apply": apply_choice, "advise": advise,
         "step": log_step, "wait": wait, "finish": finish, "status": status, "promote": promote, "rules": rules,
         "forget": forget, "launch": launch, "cover": cover}[a.cmd](a)
    except Refused as x:
        sys.exit(f"⛔ {x}")


if __name__ == "__main__":
    main()
