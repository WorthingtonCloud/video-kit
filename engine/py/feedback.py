"""The feedback protocol, with nothing about video in it. Review Studio (review.py) is its first user: the agent makes an
artifact, a page made for that kind of artifact lets the person point at it and say what they want, and the agent does
the work. This module names the life of one piece of feedback and the rules that hold whatever the artifact is. The
artifact's own addressing (for a video: a moment, a scene, an element, a box) and its own measurements come from the
caller; this module only reads the verdict they add up to.

A note waits in a phase; a move by one party takes it to the next. Resolution is a move, not a place to wait:

  phase (where it waits)                                       the move out of it, and whose it is
  observation   the person is pointing: the artifact, its      send (the person)
                version, where (the domain's address), a mark
  intent        what they want: their words, an ask from a     resolve (the agent): what it changed and in which
                short list (bigger, longer, remove…), how far  files, or why not (won't do: straight to acceptance),
                it reaches; a question back waits on them      and the change it expects to show
  verification  answered, waiting for the next version         measure (the tooling): a verdict, never the agent's say-so
  acceptance    the verdict beside the agent's claim           accept, reopen (back to intent), or follow up (the
                                                               person)
  closed        accepted, superseded by a follow-up, or withdrawn
  learning (after, and only on the person's explicit say): this revision, this project, this kind of artifact, or every one

Three things are kept apart on purpose: implemented (the agent says it changed), verified (the measurement saw the
target change the way that was asked), accepted (the person says it's right). A claim the measurement can't confirm is
shown as exactly that, and the person may still accept it: their eyes outrank the instrument, and the record keeps the
verdict they accepted over. Who owns what: the person owns taste, intent, approval and promotion; the agent owns the
implementation and its interpretation of the feedback; the tooling owns the bookkeeping and the measurements."""

# ── intent: what the person can ask for, without saying how. Each ask names the dimension the verification looks at
#    and which way it should go (+1 more, -1 less, 0 any change). The page offers the ones its artifact can show. ──
ASKS = {
    "move": ("place", +1),  # +1: toward where the person pointed (an arrow), or simply moved when they didn't point
    "bigger": ("size", +1),
    "smaller": ("size", -1),
    "longer": ("time", +1),
    "shorter": ("time", -1),
    "simpler": ("busy", -1),  # "less busy": fewer things competing at that moment
    "remove": ("presence", -1),
    "quieter": ("level", -1),
    "louder": ("level", +1),
    "different": ("content", 0),
}
ASK_WORDS = {"move": "move it", "bigger": "bigger", "smaller": "smaller", "longer": "longer", "shorter": "shorter",
             "simpler": "less busy", "remove": "remove it", "quieter": "quieter", "louder": "louder",
             "different": "a different one"}

# the dimensions a measurement can report a change in (the domain decides what counts as a change in each), and the
# words the agent may use for the change it expects (vs review resolve --expect)
DIMS = ("place", "size", "time", "words", "presence", "busy", "pixels", "level", "content", "sound")
EXPECT = {**{d: d for d in DIMS}, "color": "pixels", "elsewhere": "elsewhere"}
# a dimension that stands in for what the person asked rather than measuring it: "less busy" is a judgment, and how
# many things are on screen is only a hint at it (three loud things can be busier than seven quiet ones)
PROXY = {"busy"}

# ── verification: the verdict on a resolved note's target, old version against new ──
VERDICTS = {
    "changed": "the target changed the way it was asked",
    "removed": "the target is gone, and the answer said it was removed",
    "other": "the target changed, but not in the way that was asked",
    "contrary": "the target changed the other way from what was asked",
    "unchanged": "nothing measurable changed in the target",
    "gone": "the target is gone, and the answer didn't say it was removed",
    "unmeasured": "the tooling couldn't measure what was asked",
}
VERDICT_WORDS = {"changed": "changed", "removed": "removed", "other": "changed, not as asked",
                 "contrary": "went the other way", "unchanged": "no change measured", "gone": "gone",
                 "unmeasured": "couldn't be measured"}
VERIFIED = {"changed", "removed"}
# how strong a verdict's evidence is: measured in the dimension asked, through a stand-in for it, or (nothing in
# particular asked) any measured change at all
STRENGTH = {"direct": "measured in what was asked", "proxy": "measured through a stand-in for what was asked",
            "any": "nothing in particular was asked: any measured change counts"}

# ── how far a piece of feedback reaches. A note starts "here" (this revision only); the person can say "project" (the
#    whole artifact: for a video, "all through this video") or "studio" (everything they make, a candidate rule) on
#    the note; "kind" (every artifact of this kind) is offered when a rule is put to them. The page words each in its
#    domain's terms. Nothing is promoted past the scope the person chose. ──
SCOPES = ("here", "project", "kind", "studio")
DECISION_SCOPE = {"ignore": None, "project": "project", "kind": "kind", "remember": "studio"}

WAITING = {"sent", "reopened"}  # the agent owes these an answer
ANSWERED = {"resolved", "wontdo"}


def target_dims(ask, expect):
    """What the verification must see move: the person's ask wins (it's their intent); else the change the agent said it
    expected; else nothing in particular (any measurable change counts)."""
    if ask in ASKS:
        return {ASKS[ask][0]}
    if expect and EXPECT.get(expect) not in (None, "elsewhere"):
        return {EXPECT[expect]}
    return None


def judge(changes, *, ask=None, expect=None, outcome="resolved", removed=False, can=None):
    """The verdict from what a domain measured. changes: {dimension: signed amount (or True for a change with no
    direction)}, holding only the dimensions that really changed (the domain applies its own noise floor). can: the
    dimensions this kind of note can be measured in at all. → (verdict, expected_met, flag): flag is the sentence the
    agent and the person see when something's off; None when the measurement agrees with the answer."""
    changes = {k: v for k, v in (changes or {}).items() if v}
    want = target_dims(ask, expect)
    if changes.get("presence", 0) < 0:  # gone: fine when it was asked to go or said to be removed, else a question
        met = None if not expect else EXPECT.get(expect) == "presence"
        if not removed:  # even when it was asked to go: the answer says so, so a target lost by accident is caught
            return "gone", met, "the target is gone, but the answer didn't say --renamed or --removed"
        if want and "presence" not in want:
            return "other", met, f"asked {ASK_WORDS.get(ask, ask) if ask else next(iter(want))}; the target was removed instead"
        return "removed", met, None
    exp = EXPECT.get(expect) if expect else None
    expected_met = None if not exp or exp == "elsewhere" else exp in changes
    if outcome != "resolved":  # won't do: measured for the record, nothing to verify
        return ("unchanged" if not changes else "other"), expected_met, None
    if want and can is not None and not (want & set(can)):
        # this kind of note can't show what was asked: whatever else changed proves nothing about it (asked longer, the
        # picture changed at that moment), so it is never verified by a stand-in the person didn't choose
        d = next(iter(want))  # what it did see stays in the measurement's evidence, beside this
        return "unmeasured", expected_met, f"not measured: asked {ASK_WORDS.get(ask, d) if ask in ASKS else d}, and this note's measurement can't see {d}"
    if not changes:
        return "unchanged", expected_met, ("nothing measurable changed" + (f" (asked: {ASK_WORDS.get(ask, ask)})" if ask else ""))
    if want:
        d = next(iter(want))
        sign = ASKS[ask][1] if ask in ASKS else 0
        v = changes.get(d)
        if v is None:
            seen = ", ".join(sorted(changes))
            return "other", expected_met, f"asked for {ASK_WORDS.get(ask, d) if ask else d}; measured a change in {seen}, not in {d}"
        if sign and v is not True and (v > 0) != (sign > 0):
            return "contrary", expected_met, f"asked {ASK_WORDS.get(ask, ask)}; measured the other way"
    return "changed", expected_met, None


def strength(ask, expect, v=None):
    """How strong a verdict's evidence is (STRENGTH): direct, proxy (the asked dimension is only a stand-in, PROXY), or
    any (nothing in particular was asked). None when there's no verdict to back (unmeasured, or none yet)."""
    if v in (None, "unmeasured"):
        return None
    want = target_dims(ask, expect)
    if not want:
        return "any"
    return "proxy" if want & PROXY else "direct"


def verdict(m):
    """A measurement's verdict. Older measurements (before verdicts were written) are read from their flag."""
    if not m:
        return None
    if m.get("verdict"):
        return m["verdict"]
    f = m.get("flag") or ""
    if m.get("gone"):
        return "gone" if f else "removed"
    if f.startswith("nothing measurable"):
        return "unchanged"
    if f.startswith("asked"):
        return "contrary" if "louder" in f or "quieter" in f else "other"
    return "changed"


def verified(m):
    """Did the tooling see the target change the way it was asked (or go, when the answer said it was removed)? Only a
    measurement can say yes."""
    return verdict(m) in VERIFIED


def superseded(n, notes):
    """A later note that follows this one carries the matter on: this one is no longer the one to accept. So does one the
    agent linked to it (covered: the person's own words already spoke to it)."""
    return bool(n.get("covered")) or any(x.get("follows") == n["id"] and x["status"] not in ("withdrawn", "draft") for x in notes.values())


def acceptance(n, notes):
    """The person's call on an answered note: pending (theirs to make), accepted, reopened, superseded, lapsed (shown
    through a whole round they sent without acting on it), or n/a (not answered yet)."""
    s = n["status"]
    if s == "accepted":
        return "accepted"
    if s == "reopened":
        return "reopened"
    if s in ANSWERED:
        return "superseded" if superseded(n, notes) else "lapsed" if n.get("lapsed") else "pending"
    return "n/a"


def phase(n, notes):
    """Where a note is in its life, and who moves it next: (phase, waits_on).
    observation  being written (the person)          intent        with the agent, or a question back to the person
    verification answered, waiting for the next      acceptance    measured (or won't do): the person's call
                 version to be measured (tooling)    closed        accepted, superseded or withdrawn"""
    s = n["status"]
    if s == "draft":
        return "observation", "human"
    if s in WAITING:
        return "intent", "agent"
    if s == "question":
        return "intent", "human"
    if s in ANSWERED:
        if superseded(n, notes) or n.get("lapsed"):   # lapsed: shown for a whole round, the person moved on with words
            return "closed", None
        if s == "resolved" and not n.get("measured"):
            return "verification", "tooling"
        return "acceptance", "human"
    return "closed", None


def record(n, notes, artifact, address, ask=None):
    """One note as a feedback record: the protocol's fields, with the domain's address carried as it is (never read
    here). This is what a future artifact type would fill in the same way; only `address` would differ. artifact: what
    the note is about (project, kind, and the rendition it was written on, when the domain has more than one); ask: the
    person's ask, when the domain keeps it somewhere of its own (else the note's)."""
    res, m = n.get("resolution") or None, n.get("measured") or None
    ph, who = phase(n, notes)
    ask = ask or n.get("ask")
    v = verdict(m)
    took = n.get("accepted") if isinstance(n.get("accepted"), dict) else {}
    return {
        "id": n["id"], "status": n["status"], "phase": ph, "waits_on": who,
        "artifact": {**artifact, "version": n["version"]},
        "address": address,
        "intent": {"words": (n.get("comment") or "").strip() or None, "ask": ask, "scope": n.get("scope") or "here",
                   "follows": n.get("follows"), "findings": n.get("findings") or []},
        "resolution": None if not res else {
            "outcome": res.get("outcome"), "said": res.get("said"), "files": res.get("files") or [],
            "expect": res.get("expect") or (ASKS[ask][0] if ask in ASKS else None), "renamed": res.get("renamed"),
            "removed": bool(res.get("removed"))},
        "verification": None if not m else {
            "verdict": v, "strength": m.get("strength") or strength(ask, (res or {}).get("expect"), v),
            "evidence": m.get("summary"), "flag": m.get("flag"), "expected_met": m.get("expected_met"),
            "from": m.get("from"), "to": m.get("to"), "why": m.get("why")},
        "acceptance": acceptance(n, notes),
        # the verdict the person had in front of them when they accepted: "accepted over the measurement" when it
        # wasn't a verification (their call to make, and worth counting)
        "accepted_over": took.get("verdict") if n["status"] == "accepted" and took.get("verdict") not in VERIFIED else None,
        "learning": {"tags": (res or {}).get("tags") or [], "scope": n.get("scope") or "here"},
        "implemented": bool(res) and res.get("outcome") == "resolved",
        "verified": v in VERIFIED,
        "accepted": n["status"] == "accepted",
    }


# ── the hand-off: whose move it is, and whether the review may end. Decided from the snapshot alone. ──
def _owed(S):
    return [i for i, n in S["notes"].items() if n["status"] in WAITING]


def _picked_unapplied(S):
    return [c["id"] for c in S["choices"].values() if c.get("picked") and (c.get("applied") or {}).get("pick") != c["picked"]]


def _asks_of_human(S):
    q = [i for i, n in S["notes"].items() if n["status"] == "question"]
    c = [c["id"] for c in S["choices"].values() if not c.get("picked") and not c.get("covered")]  # covered: their note answered it
    lz = [l["id"] for l in S["lessons"].values() if l.get("decision") is None]
    return q, c, lz


def turn(S, held=0):
    """Whose move it is: (who, why).
      agent     conversation and agent work: nothing in review yet, or intent is in and the agent owes something
      returned  the person sent structured intent the agent hasn't read yet (reading it hands the turn to the agent)
      human     the review page holds the turn: the person is looking, pointing, answering, deciding
      done      the finals are filed and nothing new came back
    held: the person's feedback waiting in the page, not sent yet (the page's view knows it; the agent's doesn't)."""
    R = S["rounds"][-1] if S["rounds"] else None
    if not R:
        return "agent", "nothing is in review yet: make a version, then open a round on it"
    if (R.get("sends") or 0) > (R.get("read_sends") or 0):
        return "returned", f"round {R['n']}: the person sent feedback that hasn't been read (vs review show reads it)"
    owed, picked = _owed(S), _picked_unapplied(S)
    if owed or picked:
        return "agent", "owed: " + ", ".join(owed + [f"apply {c}" for c in picked])
    q, c, lz = _asks_of_human(S)
    fin = S.get("finished")
    if fin and fin.get("round") == R["n"] and not (held or q or c or lz):
        return "done", "the finals are filed; the page offers the downloads and a way back in"
    if held or q or c or lz or R["status"] == "open":
        bits = ([f"reviewing v{R['version']}"] if R["status"] == "open" else []) + ([f"{held} thing(s) not sent yet"] if held else []) + (
            [f"to answer: {', '.join(q)}"] if q else []) + ([f"to pick: {', '.join(c)}"] if c else []) + ([f"to decide: {', '.join(lz)}"] if lz else [])
        return "human", f"round {R['n']}: " + "; ".join(bits)
    return "agent", f"round {R['n']} is read and answered: the next version, or finish"


def exit_checks(S, held=0, renditions=(None,), approved=()):
    """What must be true before the review stage may hand back to the workflow: [(id, ok, words)]. Every check is
    mechanical; the one human judgment in it is the approval itself. renditions: the forms the round shows the same
    version in (the domain's: a video's two shapes), each approved on its own; approved: the (version, rendition) pairs
    the person approved (rendition None = all of them)."""
    R = S["rounds"][-1] if S["rounds"] else None
    if not R:
        return [("round", False, "a round on a rendered version")]
    out = []
    for c in renditions:
        ok = (R["version"], c) in approved or (R["version"], None) in approved
        out.append((f"approved:{c}", ok, f"the person approved v{R['version']}" + (f" ({c})" if len(renditions) > 1 else "")))
    out.append(("read", (R.get("sends") or 0) <= (R.get("read_sends") or 0), "everything they sent has been read"))
    out.append(("held", not held, "nothing waits unsent in the page"))
    owed = _owed(S)
    out.append(("answered", not owed, "every note answered" + (f" (owed: {', '.join(owed)})" if owed else "")))
    q, c, _ = _asks_of_human(S)
    out.append(("questions", not q, "no question waits for the person" + (f" ({', '.join(q)})" if q else "")))
    picked = _picked_unapplied(S)
    out.append(("choices", not c and not picked, "no choice waits to be picked or applied"
                + (f" ({', '.join(c + picked)})" if c or picked else "")))
    return out


def advisories(S, notes_for_round=None):
    """Not gates, but worth saying before the review ends: fixes the measurement couldn't confirm that the person hasn't
    accepted, lessons waiting for the person, lessons decided but not written down yet (promote)."""
    out = []
    for i, n in S["notes"].items():
        v = verdict(n.get("measured"))
        if n["status"] == "resolved" and v and v not in VERIFIED:
            out.append(f"{i}: claimed fixed, but the next version says {VERDICT_WORDS[v]}: the person's eyes decide")
    for l in S["lessons"].values():
        if l.get("decision") is None:
            out.append(f"{l['id']}: a rule waits for the person's answer")
    return out


# ── learning: counting is mechanical, the wording is the agent's, the decision is the person's ──
def patterns(lines, project, kind=None, pending=()):
    """Patterns worth putting to the person, from the studio's feedback lines: a tag on accepted notes in 2 projects, or
    3 times in one; or a single note the person marked for everything they make (scope studio). A tag the person
    ignored is never asked again; one they made a rule (everything, or every one of this kind) is already one; one kept
    for a single project isn't asked again in that project; one already proposed waits for its answer.
    → [{tag, count, projects, notes, comments, asked}] (asked: the person themselves said it should reach further)."""
    seen, by = set(), {}
    for l in lines:
        if l.get("kind") == "note" and (l["project"], l["note"]) not in seen:
            seen.add((l["project"], l["note"]))
            for t in l.get("tags") or []:
                by.setdefault(t, []).append(l)
    done = set()
    for l in lines:
        if l.get("kind") != "lesson":
            continue
        d = l.get("decision")
        if d in ("ignore", "remember", "forgotten"):
            done.add(l["tag"])
        elif d == "kind" and (kind is None or l.get("of_kind") in (None, kind)):
            done.add(l["tag"])
        elif d == "project" and l["project"] == project:
            done.add(l["tag"])
    out = []
    for t, ls in by.items():
        per = {}
        for l in ls:
            per[l["project"]] = per.get(l["project"], 0) + 1
        asked = any(l.get("scope") == "studio" for l in ls)
        if t not in done and t not in pending and (asked or len(per) >= 2 or max(per.values()) >= 3):
            out.append({"tag": t, "count": len(ls), "projects": per, "notes": [f"{l['project']}/{l['note']}" for l in ls],
                        "comments": [l["comment"] for l in ls if l.get("comment")][:4], "asked": asked})
    return sorted(out, key=lambda c: (-c["asked"], -c["count"]))


RULE_MARK = "<!-- rule {} -->"  # a promoted rule's line in a rules file ends with this, so it can be listed and removed


def rule_line(text, when, scope_word=None, why=None, mark=None):
    """A promoted rule as one Markdown bullet: the person's rule, dated, how far it reaches, with its id marker."""
    head = f"({scope_word}) " if scope_word else ""
    return f"- {head}{text.strip()}" + (f" {why.strip()}" if why else "") + f" ({when})" + (f" {RULE_MARK.format(mark)}" if mark else "")


def insert_rule(doc, heading, line):
    """Add a bullet under a heading of a Markdown rules file (made at the end if it isn't there)."""
    lines = doc.rstrip("\n").split("\n") if doc.strip() else []
    h = f"## {heading}"
    if h not in lines:
        return "\n".join(lines + ["", h, "", line]) + "\n"
    i = lines.index(h) + 1
    j = i
    while j < len(lines) and not lines[j].startswith("## "):
        j += 1
    k = j
    while k > i and not lines[k - 1].strip():
        k -= 1
    if k == i:  # an empty section: one blank line after the heading, then the rule
        return "\n".join(lines[:i] + ["", line] + ([""] if j < len(lines) else []) + lines[j:]) + "\n"
    return "\n".join(lines[:k] + [line] + lines[k:]) + "\n"


def remove_rule(doc, mark):
    """Take a promoted rule's line out of a rules file. → (new doc, the line removed or None)."""
    tag = RULE_MARK.format(mark)
    lines = doc.split("\n")
    hit = next((l for l in lines if l.rstrip().endswith(tag)), None)
    return ("\n".join(l for l in lines if l is not hit), hit) if hit else (doc, None)
