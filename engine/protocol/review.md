# The review protocol

The one source of truth for how a skill hands an artifact to the human for review and takes their intent back. Every
skill that renders something follows it as written; a skill adds only what is reviewed, the context its kind needs,
and what comes after. `vs protocol review` prints this. `vs help review` lists every command and option.

## The idea in one paragraph

Conversation runs the workflow. When pointing beats describing (a moment, an element, a region, a pick between
options), the agent opens Review Studio: a page that already knows the version, the moment, the scene, the element
and its box. The human gives judgment there, not a description of what they are looking at. They send it, and the
page hands structured intent back. The agent does the work, and the tooling measures whether the target actually
changed. The human accepts or reopens. The page is a tool for saying what they want. It is never an editor: no
keyframes, no timelines to drag, no parameters the agent could infer.

## Who owns what

| | owns |
|---|---|
| **Human** | taste, intent, judgment, approval, how far a rule reaches, final acceptance |
| **Agent** | the implementation (code, animation, rendering), interpreting each note, proposing alternatives, wording rules |
| **Tooling** | schemas, versions and bookkeeping, render correctness, the checks, measuring what changed |

Don't ask a model what code can check cheaply. Don't turn taste into a threshold the human didn't choose.

## The hand-off: conversation → review page → conversation

```
AGENT WORK         build, inspect (no errors), render a NEW version, vs qa
   ↓
UI REQUIRED        a version is ready for human judgment
   ↓
CONTEXT PACKAGE    vs review open: the round names the version (both shapes if both are rendered), the
                   version's own maps ride along (out/<name>-vN.review/: timeline, element map, findings,
                   qa, cues, composition), every earlier answer is measured in it
   ↓
REVIEW UI          the human points, writes, answers, picks, approves; everything waits, held, with Undo
   ↓
STRUCTURED INTENT  they press Approve & send; vs review wait wakes the agent; vs review show reads it
   ↓
AGENT WORK         resolve every note, the next version … until the exit criteria hold
```

`vs review status` tells you where you are, the same way every time: whose turn it is (`agent`, `returned`, `human`,
`done`), and whether the review may end. Read it whenever you're unsure, never guess.

## The loop, every round

1. **Serve it once per video.** One `.claude/launch.json` entry per project: `<vs> -p <slug> review --port <its own
   port>`, started at the first thing the human reviews (the narration, or the first cut). Its address,
   `http://localhost:<port>/review/`, is the only link the human ever gets. Every round and every stage use it: the
   open tab follows the project live. Never a second server, a `#hash` link or a file path.
2. **Open the round.** `vs review open --stage <stage>` on the newest render. It's refused while `vs inspect` has open
   errors (`--ask` puts them to the human instead). It's also refused while the human has feedback they haven't sent.
   Both shapes at the same version show as one round with a Vertical | Wide switch. Every note, finding and approval
   then belongs to the shape on screen.
3. **Advise every finding** before you tell them: `vs review advise --check <check> --advice leave|fix --plain "…"
   --why "…"`. A warning they answered in an earlier round carries over (same check, same place, within 3 s). Never
   ask twice.
4. **Tell them in one line per change** (and the spend so far, if anything was paid). Then **run `vs review wait` in
   the background** right away. It exits the moment they send and prints what they sent, which wakes you. While it
   runs, the page tells them Claude picks it up, so they never come back to type "sent". (No wait running: the page
   asks them to tell you.) One watcher per project: a second `vs review wait` refuses while one runs (`--replace` stops
   it and takes over), so a send is never read by a watcher nobody is listening to.
5. **Read what was sent:** `vs review show` (reading it tells the page you have it). LOOK at every note's still,
   `review/frames/<note>.jpg`: it is what they saw, with the target and the mark drawn on it. Each note carries its
   moment, its target element, its mark, its words, and maybe an **ask** (move it, bigger, smaller, longer, shorter,
   less busy, remove it; for a sound: quieter, louder, a different one, remove it) and a **reach** (`here`;
   `project`, everywhere in this video; `studio`, every video). Unsure what they mean? `vs review ask <note> "…"`. Never guess.
6. **Resolve every note.** Fix it in code. An element with a derived `~name` that got a note gets a real name. Run the
   build loop, then answer: `vs review resolve <note> --said "what changed" --files … --tags …` with
   `[--expect <the change it should show>]`, or `--wontdo` with the reason. A target that's gone needs
   `--renamed <new>` or `--removed`. A note that reaches "everywhere in this video" is fixed everywhere it applies.
7. **More than one good way? Offer a choice, don't guess.** Build each, `vs review variant <id> "what it is"`, then
   `vs review offer "<question>" --option a --option b [--for <note>]`. They play each live in Decide and pick. Then
   `vs review apply <choice>`. A music take (`--option 2=take:2`) or a picture works the same way; a paid option
   (`--paid c='<step>'`) shows its price, and picking it is the yes.
8. **The next version.** Bump the version, render, then `vs review open` again. It measures every answer (below).

Steps the human decides in chat (an OK on the outline, a yes to a price) go in the page's log:
`vs review step "<what they did>" [--stage <stage>]`.

## Feedback, as a lifecycle

Every note is a structured record (`vs review show --json` → `records`, the shape `engine/py/feedback.py` defines).
A note waits in a phase; one party's move takes it to the next:

| phase (where it waits) | what it holds | the move out, and whose |
|---|---|---|
| observation | the artifact, version and shape; where (moment, scene, element, box, mark) | send (the human) |
| intent | their words, ask and reach; a question back waits on them | resolve (the agent); won't do skips to acceptance |
| verification | the agent's answer (said, files, expected change), waiting for the next version | measure (the tooling, `vs review open`) |
| acceptance | the measurement's verdict, beside the agent's claim | Looks right / Still wrong (back to intent) / Follow up (the human) |
| closed | accepted, superseded by a follow-up, or withdrawn | — |

Resolution is a move, not a phase: nothing waits "in resolution". The agent's `vs review resolve` takes a note from
intent to verification in one step.

**Measured, never just claimed.** When the next version opens, each answered note's target is measured against the
version it was written on. The target's box, words, time on screen, keep-clear zones, the arrow's point, how much is
on screen, its pixels, the sound around it, a sound's level. The measurement gets one verdict:

| verdict | meaning |
|---|---|
| `changed` | the target changed the way that was asked (or, with no ask, measurably at all) |
| `removed` | the target is gone, and the answer said `--removed` (asked to remove it, or no ask) |
| `other` | it changed, but not in the way that was asked (asked bigger, it moved) |
| `contrary` | it changed the other way (asked quieter, it got louder) |
| `unchanged` | nothing measurable changed: a rename alone is not a change |
| `gone` | the target is gone and the answer didn't say `--renamed` or `--removed` |
| `unmeasured` | the tooling can't see what was asked, and says why: no element map, no cues, or the note's measurement can't see that dimension (asked longer on a moment with no element: a changed picture there proves nothing about time) |

A change in some other dimension never stands in for the one that was asked. With an ask, only that dimension
verifies; with no ask, the agent's `--expect` names the one to check; with neither, any measured change counts, and
the record says so. Each verdict carries its **strength**: `direct` (measured in what was asked), `proxy` (a stand-in:
"less busy" is measured as how many things are on screen, which hints at busy but isn't it) or `any` (nothing in
particular was asked). The page shows a proxy as "measured by a stand-in", never as proof.

**Implemented** (the agent said so), **verified** (the verdict is `changed` or `removed`) and **accepted** (the human
said so) are three different facts, shown separately in the page and in `vs review show`. A flagged answer is never
argued away in chat. Fix it, or say what kind of change it was with `--expect` on the next answer. The human sees the
claim and the proof side by side and makes the call. They may accept over the measurement: their eyes outrank the
instrument. The note keeps the verdict they accepted over (`accepted.verdict`), the page says so beside the
acceptance, and `vs review report` counts them.

## Standing rules and findings

- A keep-clear zone in a sent note, and a scene the human marks done, are rules `vs inspect` enforces from then on.
  Change a done scene only after they reopen it in the page.
- Warnings are theirs to call, with your advice. Fix it = real (treat it as a note). Leave it = fine as it is.
  Thresholds live in `profile.json → checks`.
- Errors never reach a round (`vs review open` refuses), unless you `--ask`.

## Exit criteria: when the review stage may hand back

`vs review status --ready` exits 0 only when all of these hold:

- the human **approved** the round's version, every shape in it (their one click)
- everything they sent has been **read**, and nothing waits **unsent** in the page
- every note is **answered**; no question and no choice waits on anyone

Don't advance past a review stage until it says ready. Its heads-ups aren't gates, but say them out loud: a fix the
measurement couldn't confirm that the human hasn't accepted, or a rule waiting for their answer.

## Learning: only with the human's explicit say

Every note is one-off by default (reach: here). From there:

1. **Counted by code.** `vs review learn` lists patterns: a tag on accepted notes in 2 projects, or 3 times in one,
   or any note the human themselves marked "every video".
2. **Worded by the agent:** `vs review propose <tag> "<one rule, in their terms>"`.
3. **Decided by the human** in the page: Every video · Every <kind> · This video only · Ignore. Ignore is remembered
   too, and a pattern they ignored or ruled on isn't asked again. If they decide in chat instead, record their words:
   `vs review promote <lesson> --chat "<their exact words>" --as remember|kind`. Quote them; never paraphrase, and
   never record a decision they didn't state (a "sure" to something else is not one). The decision keeps `via: chat`,
   their words and `recorded_by: agent`, so a chat decision is never mistaken for a click.
4. **Written by the tooling:** `vs review promote <lesson>` puts the rule into the studio's `lessons.md` under its
   heading, dated, with a marker. A value goes into `profile.json` with `--set path=value`. It's refused until the
   human decided, and refused for "this video only". That stays in the project's review and is listed every round
   as *this video's rules*.
5. **Inspectable and removable:** `vs review rules` lists every rule learned this way, where it lives and where it
   came from. `vs review forget <lesson>` takes one back out, and restores a profile value it set if nobody changed
   it since.

Never write a rule into `lessons.md` or `profile.json` any other way. Taste never goes into the kit. A kit bug
(`kit.bug`, `qa.miss`) is a kit change with a regression test.

## Finish: the end of the flow is visible

1. The last version approved (`vs review status --ready`) → the finals: `vs review finish --final <files>`. The page
   shows Done with the downloads and a way back in (pick the part, leave a note, send). Run `vs review wait` again.
2. `vs learn --final <files>` files the finals and keeps the settled values (levels, the winning music, the house
   look). It lists any lesson the human decided that isn't written down yet. Promote those, nothing else.
3. `vs review report` gives the review's numbers. Update the project's `NEXT.md` so the next session starts from the
   file.

## What not to build into the page

Every control answers "is the human saying what they want, or doing the agent's job?" Keep the first:

- **yes:** point at an element, drag a box or an arrow, a keep-clear zone, a range on the ruler, an ask (bigger,
  longer, remove…), a reach (here / this video / every video), pick an option, mark a scene done, approve
- **no:** keyframes, curves, frame-by-frame edits, dragging things into place as the final layout, any setting the
  agent can infer

The one deliberate exception is the Mix panel: music level, ducking and the effects' level are set by ear, live,
because hearing it is the judgment. They stay three sliders and a take switch, and the agent still bakes the mix.
