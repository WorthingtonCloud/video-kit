#!/usr/bin/env python3
"""vs review: Review Studio. The human points at the video and says what's wrong in the page; the agent reads the
snapshot and answers in the same diary. The page only ever writes feedback: never reel.json, scenes.js or any other
source file (mix.json is the one exception, as in the mixer: a level set by ear is the human's setting).

  vs review [--port 4470]               serve the review page on this machine only: http://localhost:4470/review/
  vs review open [--video out/<name>-vN[-takeK].mp4] [--ask] [--stage picture]
                                        a new round on a rendered version (default: the newest). Refused while vs inspect
                                        has open errors for it (errors never reach a round); --ask puts them in front
                                        of the human to confirm or dismiss instead. Refused while the human has feedback
                                        they haven't sent. --stage: where the video is (contracts.json → stages)
  vs review show [<note>] [--json]      the round as the agent reads it: each note's moment, target, mark and words, and
                                        its still, review/frames/<note>.jpg (LOOK at it: it's what the human saw). Reading
                                        what was sent tells the page Claude has it
  vs review wait [--hours 12]           block until the human sends, then print vs review show. Run it in the background
                                        right after telling them a round is open: the agent is woken by the send, and the
                                        page says "Claude is watching" while it runs (exit 2 = timed out, nothing sent)
  vs review advise <finding>… | --check <check> --advice leave|fix --plain "what it is" [--why "…"]
                                        Claude's advice on a finding, in plain words: the human takes it with one click
                                        (Leave it / Fix it), or doesn't. --check advises every finding of that check
  vs review step "<what the human did>" [--stage <stage>] [--when 2026-10-01T20:20]
                                        a step the human took outside the page (an OK in chat): the page's log of steps
                                        shows it. --stage alone marks where the video got to
  vs review ask <note> "…"              a question back; the note waits for the answer
  vs review resolve <note> --said "…" [--wontdo] [--files scenes.js …] [--tags pacing.reveal …]
                                        [--renamed <new name> | --removed]
                                        what changed (or why not); a target that's gone needs --renamed or --removed
  vs review variant <id> ["what it is"] [--replace] [--anyway]
                                        keep what's built now (inspected, no open errors) as build/variants/<id>/: an
                                        option the human plays live in Decide, with the sources that made it
  vs review offer "<question>" --option a --option b [--option c=take:2 | c=media/x.png] [--label a="…"]
                  [--paid c='gen still --prompt "…" --out media/c.png'] [--t 21 25] [--for <note>]
                                        a choice to pick from (Decide). An option is a variant (its id), a music take, or a
                                        picture/clip/sound; --paid prices one through its step's spend gate (nothing spent
                                        until it's picked). --for answers a note with it (the note waits for the pick)
  vs review apply <choice>              do what was picked: a variant's sources go back into the project, a take into
                                        mix.json, a paid option's step is printed to run (the pick was the yes)
  vs review finish --final out/<name>-vN-takeK.mp4 [out/<name>-16x9-vN-takeK.mp4]
                                        the finals are filed: the page says it's done, with the downloads and a way back in
                                        (opens a round on the final, stage final, if needed); then vs review wait
  vs review report [--md]               the dogfood's numbers: notes pinned, right first time, findings, QA misses,
                                        lessons, time reviewing, cost (--md: the table for DOGFOOD.md)
  vs review learn                       patterns in the studio's accepted notes: a tag in 2 projects, or 3 times in one
  vs review propose <tag> "<the rule>" [--to profile|lessons|check|kit|video]
                                        put one to the human: Remember, This video only, or Ignore (remembered too)

The loop, every round: the human gives feedback (notes, answers to Claude's questions and fixes, finding decisions,
picks, a saved mix, approving the video); each waits in the page, held, with Undo, until they review the list and press
Approve & send; the agent's vs review wait picks it up (no wait running: they tell the agent "sent"). state.json (what the agent reads, and the render gate) holds only what
was sent; the page sees the held ones too. A note added after a send waits for its own send.

A note can be about one sound effect (a click on the timeline's Sound row; it plays alone): its "sound" says which cue
and the human's ask (quieter, louder, a different sound, remove it). The fix goes in cues.py; the next round measures it
in that version's cues (level, sound, moment), and flags an answer that went the other way.

Standing rules vs inspect enforces: every keep-clear zone in a sent note (nothing but what it was drawn over may enter
it, in that note's scene, on its cut), and every scene the human marked done (its frames and length are held to the
version it was approved in: that version's out/<…>-vN.review/comp.html). A finding the human dismisses stays dismissed.

Tags (resolve --tags): pacing.reveal pacing.hold pacing.cut · layout.safe-zone layout.overlap layout.spacing
  layout.keep-clear layout.balance · type.size type.contrast · copy.wording copy.fast-text · motion.style ·
  color.meaning · audio.music-level audio.sfx-level audio.sfx-choice · story.order · kit.bug · qa.miss (a real
  problem the checks should have caught: the report counts the accepted ones)
Accepted notes and the human's decisions go to the studio's feedback.jsonl; taste never goes to the public kit.

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

REVIEW = "review"
LOG, STATE, FRAMES, LOCK = (f"{REVIEW}/log.jsonl", f"{REVIEW}/state.json", f"{REVIEW}/frames", f"{REVIEW}/.lock")
# who may write what: the page writes the human's events, the agent's commands write the agent's. The human's feedback
# can be held (the page marks it "held": true): it waits, undoable, until a round.sent after it covers it
HELD = {"note.added", "note.edited", "note.withdrawn", "note.answered", "note.accepted", "note.reopened",
        "finding.confirmed", "finding.dismissed", "choice.made", "mix.saved", "version.approved", "lesson.decided",
        "scene.done", "scene.reopened", "round.nonotes"}
HUMAN = HELD | {"round.sent", "undo", "friction.noted", "time.spent"}
AGENT = {"round.opened", "note.question", "note.resolved", "note.measured", "choice.offered", "choice.applied",
         "lesson.proposed", "finding.advised", "step.logged", "round.read", "finding.carried", "project.finished"}
MIX_KEYS = {"take", "music_db", "duck_db", "sfx_db", "fx_on", "summary", "saved"}  # what mix.json keeps
STAGES = {k: v for k, v in vslib.CONTRACTS["stages"].items() if not k.startswith("_")}
PLAIN = {k: v for k, v in vslib.CONTRACTS["plain"].items() if not k.startswith("_")}
ALL_STAGES = {s for v in STAGES.values() for s in v}


def check_of(fid):
    """A finding's check from its id (vs inspect's f-<check>-…, qa.py's q-<check>-…): the longest check name that fits."""
    body = re.sub(r"^[fq]-", "", fid or "")
    return max((c for c in PLAIN if body == c or body.startswith(c + "-")), key=len, default=None)
MARKS = {"none", "click", "box", "arrow", "keep-clear"}
# a note's life: draft (in an open round) → sent → question ⇄ (answered: sent) → resolved | wontdo → accepted | reopened
WAITING = {"sent", "reopened"}  # the agent owes these an answer before the next round opens


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
    import atexit, time
    os.makedirs(REVIEW, exist_ok=True)
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
        x = {"version": e.get("version")}
    elif t == "lesson.decided":
        lz = S["lessons"][e["id"]]
        text = f"Lesson “{_q(lz.get('text'), 48)}”: " + {"remember": "remember it", "video": "this video only", "ignore": "ignore it"}[e["decision"]]
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
        S["rounds"].append({"n": len(S["rounds"]) + 1, "version": e["version"], "cut": e.get("cut"), "video": e["video"],
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
        if not (n.get("comment") or "").strip() and not n.get("target") and m["type"] == "none":
            raise Refused("a note needs words, a target or a mark")
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
        for k in ("comment", "mark", "also", "target", "time", "visible", "findings", "segment", "scene", "crumbs"):
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
        n["status"] = "wontdo" if e.get("outcome") == "wontdo" else "resolved"
        n["resolution"] = {k: e.get(k) for k in ("outcome", "said", "files", "tags", "version", "renamed", "removed")}
        n["resolution"]["at"] = at
        thread(n, e["said"], n["status"])
    elif t == "note.measured":
        note_of(S, e)["measured"] = e.get("measured")
    elif t == "note.accepted":
        n = note_of(S, e)
        need(n, {"resolved", "wontdo"}, "accepted")
        n["status"] = "accepted"
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
        if e.get("decision") not in ("remember", "video", "ignore"):
            raise Refused("decide remember, video or ignore")
        lz.update(decision=e["decision"], decided=at)
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
                e["choice"] = {**(e.get("choice") or {}), "id": _next_id(None, "c", S0["choices"])}
            elif t == "lesson.proposed":
                e["lesson"] = {**(e.get("lesson") or {}), "id": _next_id(None, "l", S0["lessons"])}
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


# ── what the studio remembers across projects: accepted notes (tagged) and the human's decisions on lessons ──
def feedback_path():
    s = vslib.studio_root()
    return os.path.join(s, "feedback.jsonl") if s else None


def feedback():
    f = feedback_path()
    return [json.loads(l) for l in open(f) if l.strip()] if f and os.path.exists(f) else []


def _to_studio(S, new):
    """An accepted note and a decided lesson go to the studio's feedback.jsonl (no studio: nothing to remember into)."""
    f = feedback_path()
    if not f:
        return
    lines = []
    for e in new:
        if e["type"] == "note.accepted":
            n = S["notes"][e["id"]]
            lines.append({"kind": "note", "project": vslib.project_name(), "note": n["id"], "tags": (n.get("resolution") or {}).get("tags") or [],
                          "comment": n.get("comment"), "said": (n.get("resolution") or {}).get("said"), "version": n["version"], "at": e["at"]})
        elif e["type"] == "lesson.decided":
            lz = S["lessons"][e["id"]]
            lines.append({"kind": "lesson", "project": vslib.project_name(), "lesson": lz["id"], "tag": lz.get("tag"),
                          "text": lz.get("text"), "dest": lz.get("dest"), "decision": lz["decision"], "at": e["at"]})
    if lines:
        with open(f, "a") as fh:
            for l in lines:
                fh.write(json.dumps(l) + "\n")


def _to_dogfood(S, new):
    """'Report a tool problem' from the page: a line in the kit's DOGFOOD.md friction log, never the fix list."""
    f = os.environ.get("VIDEO_KIT_DOGFOOD") or os.path.join(vslib.KIT, "DOGFOOD.md")  # tests point it elsewhere
    lines = [e for e in new if e["type"] == "friction.noted"]
    if not lines or not os.path.exists(f):
        return
    doc = open(f).read()
    R, day = current(S), datetime.now()
    at = f", round {R['n']}, v{R['version']}" if R else ""
    add = "".join(f"- {day:%b} {day.day} · Review Studio ({e.get('where') or 'the page'}{at}, {vslib.project_name()}): "
                  f"{e['text'].strip()} (from the page's Report a tool problem button)\n" for e in lines)
    i = doc.find("\n## Verdict")  # the friction log is the section before the verdict
    doc = doc.rstrip("\n") + "\n" + add if i < 0 else doc[:i].rstrip("\n") + "\n" + add + doc[i:]
    open(f, "w").write(doc)


def candidates(project=None):
    """Patterns worth asking about: a tag on accepted notes in 2 projects, or 3 times in one. Plain counting: the agent
    only words the question. A tag the human ignored is never asked again; one they remembered is already a rule; one
    kept for a single video isn't asked again in that video; one already proposed here waits for its answer."""
    project = project or vslib.project_name()
    fb, seen = feedback(), set()
    by = {}
    for l in fb:
        if l["kind"] == "note" and (l["project"], l["note"]) not in seen:
            seen.add((l["project"], l["note"]))
            for t in l["tags"]:
                by.setdefault(t, []).append(l)
    done = {l["tag"] for l in fb if l["kind"] == "lesson" and l["decision"] in ("ignore", "remember")}
    done |= {l["tag"] for l in fb if l["kind"] == "lesson" and l["decision"] == "video" and l["project"] == project}
    pending = {lz.get("tag") for lz in state()["lessons"].values() if lz["decision"] is None} if os.path.exists(STATE) else set()
    out = []
    for t, ls in by.items():
        per = {}
        for l in ls:
            per[l["project"]] = per.get(l["project"], 0) + 1
        if t not in done and t not in pending and (len(per) >= 2 or max(per.values()) >= 3):
            out.append({"tag": t, "count": len(ls), "projects": per, "notes": [f"{l['project']}/{l['note']}" for l in ls],
                        "comments": [l["comment"] for l in ls if l.get("comment")][:4]})
    return sorted(out, key=lambda c: -c["count"])


# ── versions: a render is out/<name>[-16x9]-vN.mp4; its mixes add -takeK / -sfx / -mixed ──
def version_of(video):
    b = os.path.splitext(os.path.basename(video))[0]
    m = re.search(r"-v(\d+)(?:-(?:take\d+|sfx|mixed))?$", b)
    if not m:
        raise Refused(f"{video}: not a rendered version (out/<name>-vN.mp4)")
    base = os.path.join(os.path.dirname(video), b[: m.start()] + f"-v{m.group(1)}")
    return int(m.group(1)), base


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


def measure(n, E, size):
    """What the new version did to a note's target, from vs inspect's map: where its box went at the note's moment (in
    pixels of the new frame), whether its words or its time on screen changed, whether it left the keep-clear zones the
    human drew, and how far it now is from where the human's arrow pointed. flag = something the agent has to answer:
    a claimed fix that measures as no change at all, or a target that's gone without --renamed or --removed."""
    tgt, res = n.get("target") or {}, n.get("resolution") or {}
    name = res.get("renamed") or tgt.get("el")
    if not name or not tgt.get("box"):
        return None
    t = n["time"].get("t", n["time"].get("t0"))
    W, H = size
    e = next((x for x in E["items"] if x["id"] == name), None)
    m = {"el": name, "t": t, "flag": None}
    if not e or not e["on"]:
        m["gone"] = True
        if not res.get("removed"):
            m["flag"] = "the target is gone, but the answer didn't say --renamed or --removed"
        return m
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
    if tgt.get("text") is not None and tgt["text"] != e["text"]:
        m["text"] = {"old": tgt["text"], "new": e["text"]}
    if tgt.get("on") and span and [round(v, 2) for v in tgt["on"]] != [round(v, 2) for v in span]:
        m["span"] = {"old": tgt["on"], "new": span}
    zones = [z["box"] for z in n.get("also") or [] if z.get("type") == "keep-clear"]
    if zones:
        m["keep_clear"] = [{"before": _overlaps(ob, z), "after": _overlaps(nb, z)} for z in zones]
    mk = n.get("mark") or {}
    if mk.get("type") == "arrow":
        d = lambda x, y: round(((x - mk["to"][0]) ** 2 * W * W + (y - mk["to"][1]) ** 2 * H * H) ** 0.5)
        m["arrow"] = {"before": d(ox, oy), "after": d(nx, ny)}
    moved = max(abs(m["dx"]), abs(m["dy"]), abs(m["dw"]), abs(m["dh"])) >= 2
    if res.get("outcome") == "resolved" and not (moved or "text" in m or "span" in m or m.get("off_at_t") or res.get("renamed")):
        m["flag"] = "nothing measurable changed (its place, size, words and time on screen are the same): if the fix was a color, a sound or a timing elsewhere, say so"
    return m


def measure_sound(n, cues):
    """What the new version did to a sound the human answered, from vs mix's cues: its level against the voice, its
    sound, its moment, or gone. flag: the answer went the other way from the ask, or a claimed fix measures as nothing."""
    sd, res = n.get("sound") or {}, n.get("resolution") or {}
    name = res.get("renamed") or sd.get("el")
    if not name or cues is None:
        return None
    c = next((x for x in cues if x["el"] == name), None)
    m = {"el": name, "t": sd.get("t"), "flag": None, "sound": True}
    ask = sd.get("ask")
    if not c:
        m["gone"] = True
        if not res.get("removed"):
            m["flag"] = "the sound is gone, but the answer didn't say --renamed or --removed"
        return m
    m.update(db={"old": sd.get("db"), "new": c.get("db")}, name={"old": sd.get("sound"), "new": c.get("sound")},
             dt=round((c["t"] or 0) - (sd.get("t") or 0), 3))
    louder = (c.get("db") or 0) - (sd.get("db") or 0)
    same = abs(louder) < 0.5 and c.get("sound") == sd.get("sound") and abs(m["dt"]) < 0.02
    if res.get("outcome") == "resolved":
        if same and not res.get("renamed"):
            m["flag"] = "nothing measurable changed (its level, its sound and its moment are the same)"
        elif ask == "quieter" and louder > 0 or ask == "louder" and louder < 0:
            m["flag"] = f"asked {ask}, measured {abs(louder):g} dB {'louder' if louder > 0 else 'quieter'}"
        elif ask == "remove":
            m["flag"] = "asked to remove it, and it's still there"
        elif ask == "different" and c.get("sound") == sd.get("sound"):
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


def measure_moment(n, old, new):
    """A note pinned to a moment, not an element (a sound on a dark frame, "it repeats here"): the whole picture and the
    sound around it, old version against new."""
    t = n["time"].get("t", n["time"].get("t0"))
    m = {"el": None, "t": t, "moment": True, "flag": None, "pixels": measure_pixels(old, new, t), "audio": measure_audio(old, new, t)}
    px, au = m["pixels"] or {}, m["audio"] or {}
    if (n.get("resolution") or {}).get("outcome") == "resolved" and not _moved(px) and au.get("changed_secs", 0) < 0.1:
        m["flag"] = "nothing measurable changed at that moment (the picture and the sound around it are the same)"
    return m


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


def describe_measured(m):
    if m.get("moment"):
        parts = [x for x in (_describe_pixels(m.get("pixels")), _describe_audio(m.get("audio"))) if x]
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
        return "gone from this version" + (f" · ⚠ {m['flag']}" if m["flag"] else "")
    parts = []
    if m.get("off_at_t"):
        parts.append(f"no longer on screen at {m['t']:.2f}s (now {m['on'][0]:.2f}–{m['on'][1]:.2f}s)")
    mv = []
    if m["dx"]:
        mv.append(f"{abs(m['dx'])} px {'right' if m['dx'] > 0 else 'left'}")
    if m["dy"]:
        mv.append(f"{abs(m['dy'])} px {'down' if m['dy'] > 0 else 'up'}")
    parts.append("moved " + ", ".join(mv) if mv else "didn't move")
    if m["dw"] or m["dh"]:
        parts.append(f"size {m['dw']:+d} × {m['dh']:+d} px")
    if "text" in m:
        parts.append(f"words \u201c{m['text']['old']}\u201d → \u201c{m['text']['new']}\u201d")
    if "span" in m:
        parts.append(f"on screen {m['span']['old'][0]:.2f}–{m['span']['old'][1]:.2f}s → {m['span']['new'][0]:.2f}–{m['span']['new'][1]:.2f}s")
    for k in m.get("keep_clear", []):
        parts.append({(True, False): "now clear of the keep-clear zone", (False, False): "stayed clear of the keep-clear zone",
                      (True, True): "still in the keep-clear zone", (False, True): "moved INTO the keep-clear zone"}[(k["before"], k["after"])])
    if "arrow" in m:
        parts.append(f"{m['arrow']['after']} px from where the arrow pointed (was {m['arrow']['before']})")
    if m.get("pixels"):
        parts.append(_describe_pixels(m["pixels"]))
    return " · ".join(parts) + (f" · ⚠ {m['flag']}" if m["flag"] else "")


# ── stills: the frame the human pointed at, with the target and the mark drawn on it ──
RED, AMBER = (232, 64, 44), (217, 164, 59)


def _frame(video, t, W, H):
    # a note's moment is a frame's own time (k/fps, rounded to the millisecond): back off under half a frame so the
    # rounding can't push ffmpeg onto the next one
    t = max(0.0, t - 0.4 / fps_of(video))
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
            made.append(make_frame(n, R["video"]))
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
    try:
        base = version_of(R["video"])[1]
    except Refused:
        return []
    tl = vslib.read_json(f"{base}.review/timeline.json") or vslib.read_json(f"{base}.timeline.json")
    F = inspected(base, tl and tl.get("fingerprint")) or {}
    asked = set(R.get("asked") or [])
    out = [f for f in F.get("items", []) if f.get("severity") == "warning" or f["id"] in asked]
    out += (vslib.read_json(f"{base}.review/qa.json") or {}).get("items", [])
    return out


def show(args):
    S = state()
    R = current(S)
    if not R:
        return print("no rounds yet: vs review open starts one on a rendered version")
    if args.json:
        pick = [args.note] if args.note else [i for i, n in S["notes"].items() if n["round"] == R["n"] or n["status"] in WAITING | {"question"}]
        return print(json.dumps({"round": R, "notes": [S["notes"][i] for i in pick]}, indent=1))
    if args.note:
        notes = [S["notes"].get(args.note) or sys.exit(f"⛔ no note {args.note}")]
    else:
        notes = [n for n in S["notes"].values() if (n["round"] == R["n"] or n["status"] in WAITING | {"question", "resolved", "wontdo"}) and n["status"] not in ("withdrawn", "draft")]
        sends = R.get("sends") or 0
        print(f"Round {R['n']} · v{R['version']} ({R['cut']}) · {R['video']} · {R['status']}"
              + (f" {(R['last_sent'] or R['sent'])[:16].replace('T', ' ')}" if R["sent"] else "")
              + (f" ({sends} sends)" if sends > 1 else "") + f" · {len(notes)} note(s)" + (f" · stage: {R['stage']}" if R.get("stage") else ""))
        H = state("human")
        if H["pending"]:
            print(f"(the human has {len(H['pending'])} more thing(s) in the page, not sent yet: you'll see them when they send)")
    for n in notes:
        tgt = (n.get("target") or {}).get("el")
        print(f"\n{n['id']}  {when(n)}  {n.get('segment') or '—'}{' › ' + tgt.split('/', 1)[-1] if tgt else ''}  [{n['status']}]"
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
        if n.get("follows"):
            print(f"  follows {n['follows']}")
        for h in n["thread"]:
            print(f"  {h['by']} ({h['type']}): {h['text']}")
        if n.get("measured"):
            print(f"  measured (v{n['measured']['from']} → v{n['measured']['to']}): {describe_measured(n['measured'])}")
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
                todo = {"remember": f"→ put it in {DEST[lz['dest']]}", "video": "→ this video only: put it in this video's plan",
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
        if S["done"]:
            print("\ndone (vs inspect holds their frames to that version; change one only if the human reopens it): "
                  + ", ".join(f"{k} (v{d['version']})" for k, d in S["done"].items()))
        for a in S["approved"]:
            print(f"\n✓ v{a['version']} ({a.get('cut')}) approved {a['at'][:16].replace('T', ' ')}: vs learn --final <the files> keeps it")
        owed = [i for i, n in S["notes"].items() if n["status"] in WAITING]
        if owed:
            print(f"\nowed an answer: {', '.join(owed)} → vs review resolve <note> --said \"…\" | vs review ask <note> \"…\"")
        unadvised = [f for f in round_findings() if f["id"] not in S["advice"] and f["id"] not in S["findings"]]
        if unadvised:
            checks = sorted({f["check"] for f in unadvised})
            print(f"\nfindings with no advice yet ({len(unadvised)}: {', '.join(checks)}): the human sees them in plain words, "
                  "but your recommendation is what makes them easy → vs review advise --check <check> --advice leave|fix --plain \"…\" --why \"…\"")
    if not args.note and (R.get("sends") or 0) > (R.get("read_sends") or 0):
        append([{"type": "round.read", "round": R["n"]}], "agent")  # the page: "Claude has it"


def open_round(args):
    video = args.video or newest_video()
    if not os.path.exists(video):
        raise Refused(f"{video} doesn't exist")
    version, base = version_of(video)
    W, H, _ = probe(video)
    cut = "16x9" if W > H else "9x16"
    tl = vslib.read_json(f"{base}.review/timeline.json") or vslib.read_json(f"{base}.timeline.json")
    F = inspected(base, tl and tl.get("fingerprint"))
    asked = []
    if F is None:
        print(f"⚠️  no vs inspect findings for v{version}: can't tell whether it has open errors")
    else:
        dismissed = state()["findings"]
        errs = [f for f in F["items"] if f.get("severity") == "error" and dismissed.get(f["id"], {}).get("status") != "dismissed"]
        if errs and not args.ask:
            raise Refused(f"v{version} has {len(errs)} open error(s) from vs inspect (first: {errs[0]['check']} "
                          f"{' × '.join(errs[0]['elements'])} at {errs[0]['t0']:.1f}s): errors never reach a round. "
                          "Fix them, or --ask to put them to the human")
        asked = [f["id"] for f in errs]
    # every answer since the last round, measured in this version's element map: the human sees the claim and the proof
    E = element_map(base, tl and tl.get("fingerprint"))
    cues = vslib.read_json(f"{base}.review/cues.json") or vslib.read_json("build/mix/cues.json")  # vs mix's, for this version
    S0, measured = state(), []
    for n in S0["notes"].values():
        if n["status"] in ("resolved", "wontdo") and n["version"] != version and (n.get("measured") or {}).get("to") != version:
            old, new = bare(S0["rounds"][n["round"] - 1]["video"]), bare(video)
            if n.get("sound"):
                m = measure_sound(n, cues)
            elif (n.get("target") or {}).get("box"):
                m = measure(n, E, [W, H]) if E else None
                # the box didn't move: look at its pixels (a color, a fade, a line's weight change nothing a box can show)
                if m and not m.get("gone") and (m.get("flag") or "").startswith("nothing measurable"):
                    px = _safely(measure_pixels, old, new, m["t"], m.get("new_box"))
                    if px:
                        m["pixels"] = px
                        if _moved(px):
                            m["flag"] = None
            else:
                m = _safely(measure_moment, n, old, new)
            if m:
                m.update({"from": n["version"], "to": version})
                measured.append({"type": "note.measured", "id": n["id"], "measured": {**m, "summary": describe_measured(m)}})
    stage = args.stage or (current(S0) or {}).get("stage") or S0.get("stage")
    kind = "explainer" if os.path.exists("plan.json") else "reel"
    if args.stage and args.stage not in STAGES[kind]:
        raise Refused(f"no stage {args.stage!r} for a {kind}: {', '.join(STAGES[kind])}")
    S, _ = append([{"type": "round.opened", "version": version, "cut": cut, "video": video, "size": [W, H],
                    "asked": asked, **({"stage": stage} if stage else {})}] + measured, "agent")
    R = current(S)
    print(f"round {R['n']} open on v{version} ({cut}): {video}" + (f" · stage: {stage}" if stage else "")
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
    if not E and any(n["status"] == "resolved" and n.get("target") for n in S0["notes"].values()):
        print(f"⚠️  no element map for v{version} (vs inspect): the resolutions can't be measured")


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
         "removed": args.removed}
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
    print(f"{args.note}: {e['outcome']}")


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
    print(f"{new[0]['lesson']['id']}: proposed ({args.tag} → {DEST[dest]}); the human answers Remember, This video only or Ignore")


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
    o.add_argument("--stage", choices=sorted(ALL_STAGES))
    av = sub.add_parser("advise"); av.add_argument("finding", nargs="*"); av.add_argument("--check")
    av.add_argument("--advice", choices=["leave", "fix"], required=True); av.add_argument("--plain", required=True); av.add_argument("--why")
    st = sub.add_parser("step"); st.add_argument("text", nargs="?", default=""); st.add_argument("--stage", choices=sorted(ALL_STAGES))
    st.add_argument("--when"); st.add_argument("--where")
    s = sub.add_parser("show"); s.add_argument("note", nargs="?"); s.add_argument("--json", action="store_true")
    q = sub.add_parser("ask"); q.add_argument("note"); q.add_argument("text")
    r = sub.add_parser("resolve"); r.add_argument("note"); r.add_argument("--said", required=True)
    r.add_argument("--wontdo", action="store_true"); r.add_argument("--files", nargs="*"); r.add_argument("--tags", nargs="*")
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
    w = sub.add_parser("wait"); w.add_argument("--hours", type=float, default=12)
    fi = sub.add_parser("finish"); fi.add_argument("--final", nargs="+", required=True)
    a = ap.parse_args()
    try:
        if a.cmd in (None, "serve"):
            import review_server
            return review_server.serve(a.port)
        {"open": open_round, "show": show, "ask": ask, "resolve": resolve, "offer": offer, "learn": learn,
         "propose": propose, "report": report, "variant": variant, "apply": apply_choice, "advise": advise,
         "step": log_step, "wait": wait, "finish": finish}[a.cmd](a)
    except Refused as x:
        sys.exit(f"⛔ {x}")


if __name__ == "__main__":
    main()
