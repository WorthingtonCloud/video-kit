# Sound: music, effects, the Mix panel

**The voice is mastered to -16 LUFS** (ElevenLabs delivers about -24.6: quiet on a phone) with a -3 dB limiter (AAC
overshoots it: -2 read -0.1 dBTP after encoding; -3 reads about -1.8). Every other level is relative to the voice.

## Music

- A faint bed, about 20 dB under the voice (`music_db -16`, `duck_db 6`): it dips a little more under speech with a slow
  release (it breathes, never pumps), comes up ~5 dB for the logo, and fades to the last frame.
- Where a bed comes from, cheapest first: the studio's `library/music` (beds that won before: free), the human's own
  track (`vs ingest <file> --as music`: the next take), or `vs music` (Suno V6 on kie.ai, 12 credits = 2 takes of ~3
  minutes per direction; the directions come from the profile, `music.json` overrides). Never ominous; no vocals, no
  lead melody. Make sure the take is longer than the video (Suno honors `duration: 180`).
- ⚠️ A take's `audio_url` once served a truncated file twice; `music.py` decodes every download end to end and falls back
  to the `stream_audio_url`.
- Generated music is for the user's own videos; whether it may be redistributed depends on the vendor's terms.

## Effects

`cues.py → cues(T, TT, C, END_T)` returns `(seconds, sound, align, dB vs the voice)`:
- `T[segment]` a segment's start · `TT[title]` when a title lands · `C[scene][cue]` a word-pinned cue · `END_T` the end
  card (the point lands at +1.0, the name at +2.0, the address at +3.0).
- `sound`: a library name (`vs sfx list`) or a path (`media/door.wav`, a clip's own sound).
- `align "peak"` puts the loudest moment on the time (a whoosh into a cut); `"on"` puts the attack there (everything
  else). Files start with different amounts of silence, so never align by the file start: the mixer measures each one.
- `TRIM = {"receipt": (0.0, 0.9)}` plays part of a sound every time; a library sound can carry its own (the "single
  click" came back as three: its index entry keeps the first).

**Starting levels that were approved:** transitions -12…-15 · a number or panel landing -14 · key hits -12…-15 (a bell, a
stamp) · ticks and pops -16…-21 · long textures (a crowd, a shimmer) -16…-21 · the logo sting -9. Each library sound
carries a starting `level` in its index.

**Density: one sound per moment; a busy stretch gets fewer, not quieter.** ~100 effects in three minutes is plenty; a
first draft of 154 (38 of them ticks) was thinned to 138 before anyone heard it.

**Fit the sounds to the story.** The first explainer used interface sounds; a "fight night" story earned boxing bells for
the rounds, a crowd (cheer, ooh, groan) for its big moments, stamps, a receipt printer and coins for the bill.

## The bundled sounds (free, no credit: `library/sfx/LICENSE.md`)

whoosh1/2 (into a cut) · swish1/2 (a whip, something flying by) · land1/2 (a number or panel landing) · tick1/2 (an item,
a stop) · pop (an icon appearing) · counter (a number counting) · click (a button) · powerup (lights on, a boost) ·
shimmer (a field filling in) · paper (a card sliding in) · error (a miss) · chime (a success) · lock · pulse (a ring from a
point) · riser (into a key line) · sting (the logo landing) · bell (a round) · bell3 (the fight starts) · cheer · ooh ·
groan · stamp · receipt · coins · cloth (a robe or cape landing) · punch. Each one's prompt, length, attack and peak are
in `library/sfx/index.json`.

**New sounds:** name them in the project's `sfx.json` (`{"bell": [1.6, "single boxing ring bell, …"]}`); `vs sfx` prints
what's missing and the cost (ElevenLabs text-to-sound, 11 credits a second); with the human's yes, `vs sfx --yes` buys
them into the studio's library, measures them, and flags any that came back nearly silent (two "stamps" once came back
at -55 and -49 dBFS: layer the quiet one over a thud rather than normalizing noise up). The human's own: `vs ingest
<file> --as sfx`.

## The Mix panel (Review Studio)

`vs mix --video out/<name>-vN.mp4 --tag vN` writes every take mixed (`out/<name>-vN-take<N>.mp4`), an effects-only cut,
the stems, and the Mix panel's data: the music un-ducked with its ducking envelope, and every effect once, alone.
`vs mixer` opens Review Studio on its **Mix** panel (`/review/#mix`; a `.claude/launch.json` entry that runs it opens it
in the preview pane). The human plays the picture with every stem in sync (the picture follows the sound), switches
takes live (keys 0–9), sets the music level, the **ducking** (how far the music dips while the voice speaks: it plays
live as the slider moves; every number moves while it plays, and "Music right now" shows the level at the playhead),
and the effects level, and presses **Save**. In a round, the save waits with the rest of their feedback (Undo takes it
back) and lands in the project's `mix.json` when they Approve & send; with no round open, it lands at once.
`vs mix … --final` bakes exactly that (a reel's take 0 too); `vs learn` keeps the levels as the next video's start.

**One sound at a time is a note, never a fader.** A click on a sound in the timeline's Sound row plays it alone (or in
the mix around it); the human answers quieter, louder, a different sound, or remove it. That's a note on the cue
(`sfx/<sound>@<what it's pinned to>`): change its level or sound in `cues.py`, re-mix, and the next round measures it in
that version's cues (and flags an answer that went the other way). A choice between sounds can be offered in Decide.

**`vs qa` on a mixed file** checks the loudness (−16 LUFS ± 1.5), the true peak (−1 dBTP at most) and the sound density
(more than 14 effects in ten seconds; the busiest approved explainer peaked at 13): warnings for the human, thresholds in `profile.json →
checks`. The limiter sits at −3 dB before the encoder, so a kit mix reads about −1.8 dBTP (at −2 it read −0.1).

⚠️ The preview pane's screenshot shows a playing `<video>` as black: check frames by drawing the video to a canvas.
⚠️ `qa.py`'s "audio drops 15 LU" warning fires on narration pauses and a silent end card: expected in an explainer.
