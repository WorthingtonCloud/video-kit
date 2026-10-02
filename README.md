https://github.com/user-attachments/assets/5cdd32b8-3436-4891-95ef-4c7ddf0e8629

<p align="center">
  58 seconds, sound on. This reel was made by the kit, about the kit.
</p>

# video-kit

**Two skills that let your AI agent make videos by itself**: a narrated explainer (2–3 minutes) and a promo reel (30–60
seconds). The agent writes it, voices it, draws every scene in code, checks its own frames, and mixes the sound. You
watch it in a review page, point at what's wrong, and send. You never open a video editor.

The reel above was made this way. One request, music reused from an earlier reel, every scene drawn in code, and the
Review Studio filmed live from a real round. Its reviewer sent one note ("the red dot over the text makes it hard to
read"); the agent traced it to the kit itself, fixed it there for every future reel, and the next version was
approved with no notes. Nothing in it was paid for.

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

**The paid parts, all optional to start:** an [ElevenLabs](https://elevenlabs.io) key for the narrator and any new
sound effects (library voices need a paid plan over the API). An [OpenAI](https://platform.openai.com) key transcribes
each take back to catch a changed word, or times your own recording (about a cent). A [kie.ai](https://kie.ai) key makes
music (12 credits for two takes) and the reel's mood stills; a [Higgsfield](https://higgsfield.ai) key makes the reel's
video clips. Or bring your own voice, music, footage and pictures. Every paid step prints its cost and waits for a yes,
and every call is logged. Drawing, rendering, the checks and the mix cost nothing.

## The Review Studio

Every version opens in a review page on your own machine (`vs review`). Play it, pause anywhere, and click the picture:
the page names the exact thing under your cursor (that title, that chart, the third row of that table), so "hold this
a beat longer" lands on the right element at the right frame. Draw an arrow or a keep-clear box when words aren't
enough.

- **The agent's checks are there too**, each with its advice in plain words and two buttons: leave it, or fix it.
  Answer once and the answer carries to every later version.
- **Nothing reaches the agent until you approve and send.** If it's watching (`vs review wait`), it starts on its own.
  There's nothing to type in chat.
- **The next version comes back measured:** what moved and by how much, and a flag when your note's target didn't
  change at all.
- **Choices come as options you play side by side** (two versions of a scene, two music takes), and the Mix panel
  sets the levels by ear.
- **When you approve, the page says Done** and hands you the files.

## It checks its own work

Before you see anything, `vs inspect` maps every element on screen at every moment and looks for the notes a reviewer
would otherwise have to give: words under a picture, two things to read at once, words that go by too fast, anything
a phone's status bar, buttons or side crop will cover, a word parked half off the frame, dead air. Nothing renders
until it finds no errors. After the render, `vs qa` checks the cut itself: flashes, blacks that don't match, black
holes at the cuts, loudness and peaks, too many sound effects at once.

## The studio learns

The kit is read-only. Your studio is the folder that grows:

- `profile.json`: what you've settled on. The look (colors, fonts, end card), the narrator, the music style that won,
  the mix levels, the spending caps. Every new video starts from it.
- `lessons.md`: your notes, turned into rules. Say "the titles go by too fast" once, and every video after gives the words
  more time without you saying it again. The skills read this file first, every time.
- `library/`: sounds, music that won, your logo and fonts, pictures and clips you reuse. The kit's 30 sound effects
  start you off.
- `finals/` and `ledger.csv`: every approved video, and every paid call with what it cost.

When you approve a video, `vs learn` keeps what you decided: the levels you set, the music take that won, the finals.
Your second video asks fewer questions than your first.

## How an explainer gets made

https://github.com/user-attachments/assets/b84c457f-77d5-42dc-b18d-0e28270cb8e3

A 2:56 explainer made with the kit, for [The Lab](https://lab.worthington.cloud), from one of its notes.

1. **The arc first, as acts:** one idea per act, its evidence and source, and the picture. It explains the ideas, never
   the article: the narrator never says "the author".
2. **The narration, then the voice.** Stage directions steer the read. Every take is transcribed back to catch a changed
   word, and measured for a flat read. Your ear decides.
3. **The voice keeps the time.** Every word gets a timestamp, and every animation and title is pinned to a word, not a
   second. Change a line, record only that act again, and the whole video re-times itself.
4. **Every scene is drawn in code:** literal diagrams of the real thing, one accent color, numbers on screen with their
   source beside them.
5. **It checks its own frames before you see them** (see above), then you review it in the Review Studio.
6. **The sound comes last, without re-rendering.** Music takes, effects pinned to the same words, and a mixer page
   where you switch takes and set the levels live. Press Save and the final is mixed at your levels.
7. **The other shape is one flag:** `vs plan --wide`, and the approved sound drops straight on.

## How a reel gets made

https://github.com/user-attachments/assets/124a13f2-d305-40eb-8b2b-6fa91ce82586

A short grill (what the reel is for, where it posts, what a viewer should get), then the story in a few beats. The
music comes first and its beat grid sets every cut. Scenes are drawn in code, real web pages are recorded scrolling,
your own footage and screenshots drop in, and a few paid mood shots fill what code can't draw. Titles stay up long
enough to read. The agent checks its own render, you review it in the Review Studio, and it exports a cover and makes
the widescreen cut. Above, a 58-second reel the kit made for The Lab.

## Bring your own

Screenshots, photos, screen recordings, clips, sound effects, music, your own narration, a logo:
`vs ingest <files> --as image|clip|sfx|music|voice|logo`. The original stays untouched; the working copy is
normalized (a screen recording's uneven frame rate is made steady; iPhone photos converted). Your own voice is timed
word by word and split into the script's acts, and everything after works the same.

## What's in the box

| Folder | What it holds |
|---|---|
| `skills/explainer-video/` | The explainer method: the steps, the gates, the costs, and every mistake that cost a round of notes |
| `skills/sizzle-reel/` | The reel method, the motion vocabulary, and its own list of mistakes |
| `engine/` | One engine under both: `studio.py` (the `vs` command), the build, the scene library, the checks, the Review Studio |
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
