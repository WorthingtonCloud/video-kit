# Where things live, and the gates every step shares

`vs protocol studio` prints this. Three places, three lifetimes. When a new piece of information turns up, it goes to
exactly one of them, and the table below says which.

## The three places

| | what it is | lifetime | who writes it |
|---|---|---|---|
| **Engine** (the kit: `engine/`, `skills/`, `templates/`, `library/sfx/`) | reusable implementation and the protocols: the steps, the checks, the schemas, Review Studio, this file | every user, every video; read-only while you make a video | kit commits only |
| **Studio** (`vs where`: `profile.json`, `lessons.md`, `library/`, `finals/`, `latest/`, `ledger.csv`, `feedback.jsonl`) | this user's taste and what they keep: settled values, learned rules, reusable media, every spend, every accepted note | across all their videos | `vs learn`, `vs review promote/forget`, `vs ingest --to library`, the spend gate |
| **Project** (`studio/projects/<slug>/`) | one video: its words, plan, scenes, cues, media, versions, renders, and its review | that video | the agent (sources), the steps (`build/`, `out/`), the review page and `vs review` (`review/`) |

## Where a new piece of information goes

| it is… | it goes to | how |
|---|---|---|
| a note, an answer, a pick, an approval, a finding decision | project `review/log.jsonl` | the page, or `vs review …` (never by hand) |
| a rule the human made for this video only | project `review/` (listed every round) | their "This video only" or a note's "everywhere in this video" |
| a rule the human made for every video, or every video of one kind | studio `lessons.md` (marked) | `vs review promote`, after their decision |
| a settled value (a level, a threshold, the narrator, the house look) | studio `profile.json` | `vs learn`, or `vs review promote --set` |
| what this video overrides of the profile | project `plan.json` / `reel.json` | the agent |
| a sound, a music bed, a logo, a picture another video could use | studio `library/` | `vs ingest --to library`, `vs learn` |
| a scene helper another video could use | studio `library/scenes/` | the agent, after `vs learn` lists candidates |
| an approved final | studio `finals/` (then `latest/`) | `vs learn --final` |
| a paid call | studio `ledger.csv` | the spend gate, on every paid step |
| a render, its timeline and its maps | project `out/<name>-vN…` + `out/<name>-vN.review/` | `vs build`, `vs inspect`, `vs qa`, `vs mix` |
| anything regenerated (comp, stills, stems, variants) | project `build/` | the steps; safe to delete |
| a bug anyone using the kit would hit | the engine | a kit change with a regression test (`references/scars.md`) |
| status for the next session | project `NEXT.md` | the agent, at the end of each session |

Taste never goes into the engine. Nothing in a project reaches the studio without a step that says so.

## The gates every step shares

- **Contracts first.** `vs check` validates every file against `engine/schema/` before plan and build.
- **Inspect before render.** `vs build` renders only a composition `vs inspect` passed with no errors (`--anyway` is
  for the kit's own debugging, never a video).
- **Every version is new.** Bump `"version"` before every render. The gate refuses to overwrite a version a round has
  seen.
- **Paid steps ask first, with the number.** Every paid step prints its estimate and this video's spend, refuses past
  the profile's caps and budget, and needs `--yes`. Say the number, wait for the yes, and only then run it. Some
  vendors auto-recharge: a balance is not a budget.
- **Nothing publishes without the human's explicit go, per ship.** Review Studio runs on this machine; it is not a
  publication.
- **Long jobs:** a render takes minutes. Run `vs build` in the background and wait to be woken: it exits on the
  result or a failure (with `vs qa` already run), so there is nothing to check on in between, and silence is not a
  sign of trouble.
- **Review is the protocol's:** `vs protocol review`.
