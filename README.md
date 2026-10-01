https://github.com/user-attachments/assets/b84c457f-77d5-42dc-b18d-0e28270cb8e3

<p align="center">
  2 minutes 56 seconds, sound on. The 58-second reel further down came from the same kit.
</p>

# video-kit

**Two skills that let your AI agent make videos by itself**: a narrated explainer (2–3 minutes) and a promo reel (30–60
seconds). The agent writes it, voices it, draws every scene in code, checks its own frames, and mixes the sound. You
bring the source and your notes. You never open a video editor.

The video above was made this way, for [The Lab](https://lab.worthington.cloud), from one of its notes. An agent pulled
the ideas and the evidence out of the note, wrote the narration, recorded the narrator, drew every scene, and
started each move on the word it illustrates. It checked the whole timeline for words and pictures fighting, then laid
a faint music bed and small sound effects under the voice. The levels were set by ear in a mixer page. The widescreen
cut is the same plan with one flag.

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

1. **The arc first, as acts:** one idea per act, its evidence and source, and the picture. It explains the ideas, never
   the article: the narrator never says "the author".
2. **The narration, then the voice.** Stage directions steer the read. Every take is transcribed back to catch a changed
   word, and measured for a flat read. Your ear decides.
3. **The voice keeps the time.** Every word gets a timestamp, and every animation and title is pinned to a word, not a
   second. Change a line, record only that act again, and the whole video re-times itself.
4. **Every scene is drawn in code:** literal diagrams of the real thing, one accent color, numbers on screen with their
   source beside them.
5. **It checks its own frames before you see them.** An audit scrubs the whole timeline for a shape over words, a line
   through a number, a label hanging off its card, or words where a phone's buttons will cover them. Then stills, every
   transition, the black levels.
6. **The sound comes last, without re-rendering.** Music takes, effects pinned to the same words, and a mixer page
   where you switch takes and set the levels live. Press Save and the final is mixed at your levels.
7. **The other shape is one flag:** `vs plan --wide`, and the approved sound drops straight on.

## How a reel gets made

https://github.com/user-attachments/assets/124a13f2-d305-40eb-8b2b-6fa91ce82586

A short grill (what the reel is for, where it posts, what a viewer should get), then the story in a few beats. The
music comes first and its beat grid sets every cut. Scenes are drawn in code, real web pages are recorded scrolling,
your own footage and screenshots drop in, and a few paid mood shots fill what code can't draw. Titles stay up long
enough to read. The agent watches its own render frame by frame, exports a cover, and makes the widescreen cut.

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
| `engine/` | One engine under both: `studio.py` (the `vs` command), the build, the scene library, the audit, the mixer |
| `library/sfx/` | 30 sound effects with a measured index (where each starts and peaks, a starting level) |
| `templates/` | A new studio, a new explainer, a new reel |
| `examples/meeting-explainer/` | A finished explainer's arc, narration, plan, ten scenes and 95 sound cues, to read |

## The rules that cost a round of notes each

The video explains ideas, never the article. One spoken number per act; the rest sit on screen with a source. Words
need time on screen, and only one place to read at once. Every take is transcribed back before it's trusted. Times
come from the words, never typed in. No render until the audit says "no overlaps". The music sits about 20 dB under
the voice and never competes. The picture is never re-rendered for sound. In widescreen, anything that leaves a
vertical frame has to leave the wide one too. The full lists, with the fix for each, are in each skill's
`references/scars.md`.

## Credits

The interview method and the render-then-inspect loop credit Nate Herk and Jay E (RoboNuggets) for the ideas they
build on. Videos render on [HyperFrames](https://github.com/heygen-com/hyperframes) by HeyGen (Apache-2.0) and animate
with [GSAP](https://gsap.com). Voices and effects are ElevenLabs; music is Suno, through kie.ai.

## License

The code is MIT ([LICENSE](LICENSE)). The 30 sound effects in `library/sfx/` are CC0: use them in anything, no credit
needed ([details](library/sfx/LICENSE.md)). No music ships with the kit: make your own takes, or bring a track you own.
