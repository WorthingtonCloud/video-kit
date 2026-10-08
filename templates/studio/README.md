# The studio

Everything the video skills keep between videos. The kit (the skills and their engine) is read-only; this folder is
yours, and it grows a little with every video.

- `profile.json`: what you've settled on: the look (palette, fonts, finish, end card), the narrator, the music style
  that won, the mix levels, the spending caps. Every new video starts from it. `vs finish` updates it after each one.
- `lessons.md`: your notes, turned into rules. The skills read it first, every time.
- `library/`: things bought or brought once and reused: `sfx/` (sound effects; the kit's 30 come free), `music/` (beds
  that won, and tracks you brought), `brand/` (fonts, logo), `media/` (pictures and clips you reuse, named
  `lib:media/<file>` in a project), `scenes/` (scene pieces promoted from a finished video), `originals/` (untouched
  copies of what you handed over).
- `projects/<video>/`: one video each, both shapes: its script, plan, scenes and cues (yours), `video.json` (where it
  stands: `vs status`), `inputs/` and `media/` (its pictures and clips), `voice/` and `music/` (its takes), `drafts/v1`,
  `v2` … (every render you haven't called done), `build/` (regenerated, safe to delete).
- `finals/<video>/`: every version you called done, both shapes, with covers (`<video>-vertical-v8.mp4`).
- `latest/<video>/`: only the newest final of each shape, no version in the name (`<video>-vertical.mp4`).
  `VERSIONS.md` says which version each one is.
- `archive/`: project folders a restructure retired; nothing reads them.
- `ledger.csv`: every paid call, for every video: what, from whom, what it cost, kept or not.

How a video moves from first draft to final, and back when you want a change: `vs protocol files`.
