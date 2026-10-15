---
name: video-for-chatgpt
description: "Package a video so a model that can't watch video (ChatGPT, Gemini) can review it: frame strips, a sound map, the soundtrack and a timed PROMPT.md, in one zip. Use on \"show ChatGPT the video\", \"ChatGPT can't watch video\", \"zip up the video for ChatGPT/Gemini\", or to get an outside opinion on a cut."
---

# video-for-chatgpt: let a model that can't watch video "watch" it

Most chat models read images and text but can't play a video. This packs one so they can review it anyway: the picture
as captioned frame strips in order, the sound as a timed script, a sound map and a cue sheet, and the real audio file
for any model that can measure it. Any video works; a video made with this kit packs with less work, because the kit
already knows its sections, its sound effects and when every word is said.

**The command is this skill's `vs`**: `<this skill's folder>/vs pack <move>`, the full path in every call (`vs help
pack` for every option). Run it in the video's project folder (or `vs -p <video> pack …` from anywhere). For a video
from outside the kit, run it anywhere with the file's path; the working files go in `./pack/`.

**Output:** `<out>/<video>-for-review/` and `<video>-for-review.zip` beside it. The out folder is the studio profile's
`pack.out` when it's set (for example `~/Downloads`, where the person uploads from), else the project's `pack/`.

## 1 · Find the video and everything already known about it
Use the latest approved final unless the person names another (`vs status` says which is newest); `vs pack survey`
picks it when no file is named. Note any sibling cut (vertical / widescreen) for one extra strip.

Mine the project before describing anything. **Never invent a detail you can't see or source:**
- the script (`SCRIPT.md`, `narration.txt`): use its spelling and dialect over a transcript's ("lemme", "somethin'")
- the sections and every sound effect: `vs pack survey` writes them into the plan from the render's own timeline
- the mix (`mix.json`, `music.json`, `cues.py`): music in and out, loops, stops, how far under the voice it sits
- the sound library's `index.json` (`library/sfx/`): what each effect sounds like
- the studio's `ledger.csv` (the music's generation prompt) and `profile.json` (the narrator's voice)
- No project (someone else's video)? Say in PROMPT.md which sound details are measured and which are unknown.

## 2 · Survey: look at every second
```
vs pack survey [VIDEO]
```
Writes review sheets (a frame every second, each labeled with its time) to `pack/survey/sheet-NN.jpg`, the soundtrack
(`pack/audio.mp3`), its loudness every 0.1 s, the hard cuts, and, for a kit render, a starter `pack/plan.json` with the
sections and every sound effect. **Read every sheet.** For a fast moment (a shatter, a stamp, a click), grab close-ups
0.2–0.3 s apart (`ffmpeg -ss <t> -i VIDEO -frames:v 1 close-<t>.jpg`) before you caption it. The hard-cut list often
comes back empty on one set or one drawn stage: the sections are the better map.

## 3 · Words: when each line is said
```
vs pack words                                  free: the kit's own word timings, when the video has them
vs pack words --timing <file> [--offset S]     free: a word-timing file the video was built from
vs pack words --yes                            OpenAI whisper-1, about $0.006 a minute: say the cost, get a yes first
```
A timing file the video was built from is exact and costs nothing: a narrated kit video's `voice/*.words.json` (found by
itself), a song's `.words.json` from `vs lyrics`, or any `{"lines": [{"t0", "t1", "text"}]}`. Use the one the FINAL was
built from, not a newer or older take's. `--offset` is where that file's 0:00 falls in the video. Whisper is the fallback:
it flattens dialect and mishears names, so check its lines against the script and keep the script's spelling.

## 4 · Write the plan (`pack/plan.json`), shape in `references/plan-example.json`
- **Strips:** one per section or pair of sections, in order, covering the WHOLE video. 6–12 frames each; 3 columns
  for widescreen (640 px frames), 6 for vertical (300 px), which keeps every image under ~2000 px wide so the model
  doesn't shrink the text away. Each strip gets a title with its time range and a `note`: what moves, how, and what's
  on screen (quote on-screen text exactly). Each frame's caption (`labels`): the line being spoken, in quotes, or the
  visual event.
- Put frames ON the moments that matter: each punchline, each reveal, each stamp, the cut in and out of a section. A
  time read off a survey sheet is the strip's time (both are exact seeks).
- **Sound:** keep the starter's `sections` and `sfx` and rewrite each effect's `what` as what it lands on; add the
  `music` spans (with stops, tape-stops and returns). The voice row comes from step 3 by itself.
- `"videos": {"vertical": "<file>"}` and a strip with `"src": "vertical"` for the other cut (the starter fills it in).

## 5 · Build, look, write the prompt, zip
```
vs pack build
```
The first run draws the strips, `00-sound-map.png` and `soundtrack.mp3`, then stops to ask for PROMPT.md. **Look at
every strip and the sound map**, and fix any caption that doesn't match its frame. Then write `PROMPT.md` into the out
folder from `references/prompt-template.md`: what's in the package, what the video is, the timed script, the voice,
the music, the sound effects, the look and the pacing, the other cut, and a "My question" line with an example
question. No guessed instruments or camera moves. Run `vs pack build` again to zip.

## 6 · Hand it over
Tell the person, in a few sentences: where the zip is, what's in it, and how to use it. They can upload the zip, or
(more reliable, because some models only look closely at images dropped in directly) drag the images in and paste
PROMPT.md, then replace its last line with their question.

## Scars
- 🔑 A described detail you didn't see or source (an instrument, a camera move) is a lie to the reviewer: cut it.
- ⚠️ Some fonts have no arrow glyphs and print a box. `vs pack` swaps → ← ↑ ↓ ▲ ▼ for words or "->"; write "up",
  "down" and "->" in notes and labels yourself and nothing is lost.
- ⚠️ Review sheets made with ffmpeg's fps filter show each frame about 0.5 s after the time printed under it, so a
  moment picked off such a sheet lands half a second late. `vs pack survey` seeks to each exact second instead, the same
  way the strips do; don't make sheets the other way.
- ⚠️ A frame past the end is left out of its strip with a warning (a last frame at the exact length comes back empty).
