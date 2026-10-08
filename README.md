https://github.com/user-attachments/assets/1c6b84dc-20d2-4e21-81ed-616f8b51dc99

<p align="center">
  72 seconds, sound on. This reel was made by the kit, about the kit.
</p>

# video-kit

**Two skills that let your AI agent make videos by itself**: a narrated explainer (2–3 minutes) and a promo reel (30–60
seconds). The agent writes it, voices it, draws every scene in code, checks its own frames, and mixes the sound. You
watch it in a review page, point at what's wrong, and send. You never open a video editor.

The reel above was made this way: one request, music reused from an earlier reel, and every scene drawn in code, the
Review Studio included. The agent lifted the page's own markup while it reviewed this very reel, so the camera can fly
through the real interface and the reel shows up inside itself. Its reviewer gave two notes over three rounds, both on
one transition ("the screen seems to freeze a bit on this fade"); the agent replaced it, and both shapes were approved
on the next version. Nothing in it was paid for.

## How it works

https://github.com/user-attachments/assets/83fe5ddf-b0f1-41be-9d63-7fbf1e3c38a1

<p align="center">
  2:15, sound on. An explainer the kit made about itself. The review round in the middle is this video's own.
</p>

Today's AI models can write a motion graphic in code, in minutes. What they can't do is watch it. They build every
frame without seeing one, so the words land under a chart, a title is gone before anyone can read it, and the logo sits
under a phone's buttons. You end up describing a picture in words ("at about seventeen seconds, the thing in the upper
right…"), the agent guesses, and round six looks a lot like round one.

The kit adds the two missing pieces:

- **Eyes, before you see a frame.** The agent names every element on screen and steps through the video moment by
  moment, catching what a reviewer would otherwise catch by eye. Nothing renders until it's clean.
- **A pointer, when you do.** The Review Studio is a page where you pause, click the thing, and it knows exactly which
  thing. A box if you need one, a few words, send. The next version comes back measured.

## Install it

In Claude Code:

```text
/plugin marketplace add WorthingtonCloud/video-kit
/plugin install video-kit@video-kit
```

Then tell your agent:

```text
Set up video-kit: run its setup, then tell me what's missing.
```

After that, ask in plain words: "make an explainer from this article", "make a sizzle reel for my app".

**Another agent with a skills folder?** Clone this repo and link its two skills into that folder. Link them, don't
copy them: each skill's `vs` command finds the engine beside it.

```bash
git clone https://github.com/WorthingtonCloud/video-kit ~/video-kit
ln -s ~/video-kit/skills/explainer-video ~/video-kit/skills/sizzle-reel <your skills folder>/
```

**You need:** Node 22+, Python 3, a full build of ffmpeg, and curl. Setup installs the rest once: HyperFrames (the
renderer), GSAP (the animation), puppeteer and its Chrome, and a Python with numpy, about 190 MB. It also makes your
studio folder (`~/video-studio`). macOS and Linux run it as is; on Windows, use WSL. After a plugin update, run setup
again: the engine's packages live beside the new version.

## It checks its own work

Before you see anything, `vs inspect` maps every element on screen at every moment (1,058 moments in a 2:56 explainer)
and looks for the notes a reviewer would otherwise have to give: words under a picture, two things to read at once,
words that go by too fast, anything a phone's status bar, buttons or side crop will cover, a word parked half off the
frame, dead air, words that never reach the screen, words a cut takes away before they're read, an animation that
silently never moves. Nothing renders until it finds no errors. After the render, `vs qa` checks the cut itself:
flashes, thin lines that flicker while standing still, blacks that don't match, black holes at the cuts, loudness and peaks, too many sound effects at once.

Every one of those checks started as a note a reviewer once had to give by eye.

## The Review Studio

Every version opens in a review page on your own machine (`vs review`). Play it, pause anywhere, and click the picture:
the page names the exact thing under your cursor (that title, that chart, the third row of that table), so "hold this
a beat longer" lands on the right element at the right frame. Draw a box, an arrow or a keep-clear zone when words
aren't enough.

- **The agent's checks are there too**, each with its advice in plain words and two buttons: leave it, or fix it.
  Answer once and the answer carries to every later version.
- **Nothing reaches the agent until you approve and send.** If it's watching (`vs review wait`), it starts on its own.
  There's nothing to type in chat.
- **Say what you want, not how.** After you point, one click says it: move it, bigger, smaller, longer, shorter,
  less busy, remove it. Another says how far it reaches: just here, all through this video, or every video.
- **The next version comes back measured:** what moved and by how much, how long it now stays on screen, and a plain
  verdict on your note's target: it changed, it changed but not the way you asked, it went the other way, or nothing
  changed at all. The agent's "fixed" and the measurement sit side by side; you decide.
- **Choices come as options you play side by side** (two versions of a scene, two music takes), and the Mix panel
  sets the levels by ear.
- **Both shapes in one round.** Once the first shape is approved, the other one is made from it and joins the same
  page: a Vertical | Widescreen switch at the top puts either one on screen at the same moment, and each gets its own
  notes and approval. One video, one page, one address.
- **When you approve, the page says Done** and hands you the files.

### Why a review page, not a chat

Conversation runs the workflow. A page appears only when pointing says it better than words: which frame, which
element, which of two options. You give judgment there; the agent does the work. The page hands your intent back as
structured notes, the tooling measures whether the agent's change actually landed, and you accept it or reopen it.
The page never becomes an editor: no timeline to drag, no keyframes, no settings the agent could work out itself.

```
  You, in conversation ── "make an explainer about X"
        │
        ▼
  Agent work ─────────── writes, voices, draws, inspects, renders v3
        │  vs review open: the version, plus the map of what's on screen and when
        ▼
  Review Studio ──────── you point at the frame, ask for "bigger" or "longer", pick an option, approve
        │  Approve & send: structured notes (moment · element · mark · ask · reach)
        ▼
  Agent resolution ───── changes the code, renders v4
        │  vs review open measures every answer in v4
        ▼
  Verdict ────────────── changed · not as asked · the other way · no change
        │
        ▼
  You accept, or reopen ── and a note you keep giving becomes a rule only if you say so
```

Both skills follow one review protocol in the engine (`vs protocol review`), so a fix to the loop reaches every kind
of video at once. `vs review status` always answers the same two questions: whose move it is, and whether the review
can end.

## How you'll work with it

One request, then a few stops, and each one waits for you:

1. **The story.** The arc comes first, as acts: one idea per act, its evidence and source, and the picture. It explains
   the ideas, never the article. You OK it.
2. **The voice.** Stage directions steer the read. Every take is transcribed back to catch a changed word, and measured
   for a flat read. You hear it; your ear decides.
3. **The picture.** The voice keeps the time: every animation and title is pinned to a word, not a second, so a
   re-recorded line re-times the whole video. Every scene is drawn in code, checked, rendered, and opened in the Review
   Studio. You point.
4. **The sound.** Music takes and effects pinned to the same words, mixed without re-rendering the picture. You switch
   takes and set the levels by ear.
5. **The other shape.** You start in vertical or widescreen. Once you approve it, the other shape is built from the same
   plan and shown beside it in the same Review Studio.
6. **Done.** Approving both files them: every version you called done in `finals/<video>/`, the newest in
   `latest/<video>/`, each with a web copy beside it: the same picture at about a third of the size, small enough
   for sites that cap uploads.
7. **Later, a change.** `vs reopen <video>` puts the script and scenes back exactly as they made the last final, and
   the next draft picks up from there. When it's done again, it replaces the old one in `latest/`.

A reel works the same way, with a short grill first (what it's for, where it posts, what a viewer should get) and the
music's beat grid setting every cut. Anything that costs money prints its price and waits for a yes.

## Plug in what you have

Drawing, rendering, the checks and the mix cost nothing. Everything else is optional:

- **[ElevenLabs](https://elevenlabs.io)**: the narrator, and any new sound effects (library voices need a paid plan
  over the API).
- **[kie.ai](https://kie.ai)**: music (12 credits for two takes) and a reel's mood stills.
- **[Higgsfield](https://higgsfield.ai)**: AI video clips for a reel.
- **[Blender](https://www.blender.org)** (free): `vs mark3d` builds your end card's mark as a lit 3D tile that swings in
  while its point drops onto the beat. Without it, the end card draws the flat mark.
- **[OpenAI](https://platform.openai.com)**: transcribes each take back to catch a changed word, or times your own
  recording (about a cent).

Or bring your own: screenshots, photos, screen recordings, clips, sound effects, music, your own narration, a logo.
`vs ingest <files> --as image|clip|sfx|music|voice|logo` keeps the original untouched and normalizes a working copy (a
screen recording's uneven frame rate is made steady; iPhone photos converted). Your own voice is timed word by word and
split into the script's acts, and everything after works the same. Every paid call is logged with what it cost.

## The studio learns

The kit is read-only. Your studio is the folder that grows:

- `profile.json`: what you've settled on. The look (colors, fonts, end card), the narrator, the music style that won,
  the mix levels, the spending caps. Every new video starts from it.
- `lessons.md`: your rules. Every note starts as a one-off. When the same kind of note comes back (or you mark one
  "every video"), the agent words it as a rule and asks how far it should reach: every video, every explainer or
  reel, this video only, or not at all. Only then is it written here, marked with where it came from.
  `vs review rules` lists what was learned; `vs review forget` takes one back out. The skills read this file first,
  every time.
- `library/`: sounds, music that won, your logo and fonts, pictures and clips you reuse. The kit's 30 sound effects
  start you off.
- `projects/<video>/`: one folder per video, both shapes, with every draft in `drafts/v1`, `v2` … and `video.json`
  saying where it stands (`vs status` reads it and names the next step).
- `finals/<video>/`: every version you called done, both shapes (`<video>-vertical-v8.mp4`).
  `latest/<video>/`: only the newest, no version in the name (`<video>-vertical.mp4`), and its one web copy
  (`<video>-vertical-web.mp4`: post this one, edit from the full one). `ledger.csv`: every paid call
  with what it cost.

When you approve a video, `vs finish` files it and keeps what you decided: the levels you set, the music take that won.
Your second video asks fewer questions than your first.

## What's in the box

| Folder | What it holds |
|---|---|
| `skills/explainer-video/` | The explainer method: the steps, the gates, the costs, and every mistake that cost a round of notes |
| `skills/sizzle-reel/` | The reel method, the motion vocabulary, and its own list of mistakes |
| `engine/` | One engine under both: `studio.py` (the `vs` command), the build, the scene library, the checks, the Review Studio, and `protocol/` (the review loop and where everything lives, shared by both skills) |
| `library/sfx/` | 30 sound effects with a measured index (where each starts and peaks, a starting level) |
| `templates/` | A new studio, a new explainer, a new reel |
| `examples/meeting-explainer/` | A finished explainer's arc, narration, plan, ten scenes and 95 sound cues, to read |
| `tests/` | The kit's own tests (`vs test`): unit, contract, regression fixtures and browser scenarios |

## The rules that cost a round of notes each

The video explains ideas, never the article. One spoken number per act; the rest sit on screen with a source. Words
need time on screen, and only one place to read at once. Every take is transcribed back before it's trusted. Times
come from the words, never typed in. No render until `vs inspect` finds no errors. The music sits about 20 dB under
the voice and never competes. The picture is never re-rendered for sound. In widescreen, anything that leaves a
vertical frame has to leave the wide one too. The full lists, with the fix for each, are in each skill's
`references/scars.md`.

## New in 3.0

One path for every file, from the first draft to the final and back, held by the kit's own commands instead of by
anyone remembering it (`vs protocol files`). A video is one project with both shapes in it; the kit names every file,
in words (`<video>-widescreen-v8.mp4`, never `16x9`), and reads each file's real width and height before filing it.
Four commands move a video along: `vs status` (where it stands, and the next step), `vs shape` (the other shape, once
the first is approved), `vs finish` (files the finals, makes their web copies, refreshes `latest/`, tells the Review Studio it's done) and
`vs reopen` (a finished video drafts again from exactly its last final). Each refuses the wrong order and names the way
around it for a real change of plan, and the way around is logged. `vs new` now takes the shape a video starts in.

Upgrading a 2.x studio: `vs restructure --dry` shows every move first; then `vs restructure` (with `--merge <video>=<its
-16x9 sibling>` for a reel whose widescreen cut lived in a second project). Nothing is deleted: superseded folders and
byte-identical copies go to `archive/`.

Also: an OpenAI key never appears on a command line while a narration take is checked.

## New in 2.2

Text and thin lines no longer flicker while a scene slowly turns: `vs build` draws two frames for every frame it keeps
and blends them, which takes about twice as long to render (`"blend": 1` in a video's plan turns it off). `vs qa` measures
that flicker (`shimmer`), so it can't come back unnoticed. The review loop is now one written protocol both skills follow
(`vs protocol review`): every answer to a note is measured in the next version and gets a verdict, and a lesson reaches
`lessons.md` only after you decide how far it reaches. Smaller fixes: a first mix can be saved at the levels it starts
with; a note on a video's last frame can be measured; `vs inspect` warns when the first frame is empty (it's the preview a
feed shows) and no longer flags things a window has scrolled out of sight; background specks never count as what's on
screen; a second `vs review wait` refuses instead of quietly reading your send; and filing finals again after a
re-render keeps one history line per video.

## New in 2.1.1

Found while the kit made its own explainer above. An explainer can now show a recorded clip in a floating panel (its
plan's `shots`), and on the widescreen cut that panel sits centered instead of parked on the right. The Review Studio's
top line is calmer: one word a button, with the full words on hover, and when the window gets narrow it folds the
finished stages and the step names away instead of letting them overlap.

## New in 2.1

Review both shapes in one round, each with its own notes and approval. A 3D end card if Blender is installed
(`vs mark3d`). Four new checks, each from a note a reviewer once had to give by eye: words that never reach the screen,
words a cut takes away before they're read, an animation that silently never moves, and a cue word said twice in its
line (`vs plan` says which one it took). The end card now fits its beats into a short card, and the reel's hub scene fits
its labels into its time: both had been timing words past their scene's end.

## New in 2.0

The Review Studio (`vs review`, with the mixer as its Mix panel). `vs inspect` replaces the overlap audit and names
every element it flags. Every paid step goes through one spend gate with a per-video cap. `vs help` lists every step;
`vs check` validates the project files; `vs test` runs the kit's tests. Projects from 1.x keep working (`vs migrate`
marks them). After updating, run setup again.

## Credits

The interview method and the render-then-inspect loop credit Nate Herk and Jay E (RoboNuggets) for the ideas they
build on. Videos render on [HyperFrames](https://github.com/heygen-com/hyperframes) by HeyGen (Apache-2.0) and animate
with [GSAP](https://gsap.com). Voices and effects are ElevenLabs; music is Suno, through kie.ai.

## License

The code is MIT ([LICENSE](LICENSE)). The 30 sound effects in `library/sfx/` are CC0: use them in anything, no credit
needed ([details](library/sfx/LICENSE.md)). No music ships with the kit: make your own takes, or bring a track you own.
