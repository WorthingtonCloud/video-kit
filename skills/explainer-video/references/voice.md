# The voice: narration, takes, fitting, re-recording

The narration keeps the time: every animation starts on the word it illustrates, so the voice is settled before the
picture.

## Writing `narration.txt`

- One paragraph per act, under `# N title`.
- v4 tags in brackets direct the voice and aren't spoken. CAPS = emphasis. `...` = a beat.
- Never a vocal action ("clears its throat" gets performed out loud).
- At most one spoken number per act; the rest go on screen with a source tag.

## A take, step by step

1. `vs narrate <tag>` prints the cost and stops (about 0.06 ElevenLabs credits a character: the spend gate). Say the
   number, wait for the human's yes, then `vs narrate <tag> --yes`.
2. `vs check-take <tag>` (or the path, `voice/narration-<tag>.mp3`): fix any word that changes the meaning.
3. `vs pitch voice/narration-<tag>.mp3`: a flat read is the failure.
4. Too long for its slot? `vs fit --take voice/narration-<tag>.mp3 --secs N --out <tag>`: shorter pauses first, then a
   faster read, with the word timings moved along. `--pause none` keeps comic timing; `--rush "act:first..last#n"`
   speeds a list alone.
5. `vs listen take.mp3="a label" …` puts the takes on the review page: there's no round yet, so the listening view sits
   where the video goes, on the same address the human will use for every round. You can't hear: say so, and let
   them pick.
6. The approved take: `vs voicebed --take voice/narration-<tag>.mp3 --out <tag>` → the voice bed and its word timings
   for `plan.json`.

## Their own recording instead

`vs ingest <file> --as voice` gets word timings by transcription (about a cent a minute; it asks first) and splits the
recording into the script's acts. Everything after works the same.

## A changed line

- Re-record only those acts: `vs narrate <tag> --acts 9-10` (its cost first), `vs check-take`, then
  `vs voicebed --base <approved> --take <new> --out <tag>`, point `plan.json` at it, `vs plan`. Name a partial run
  with its own tag (`narration-<tag>a5`), or the splice overwrites the run's timings.
- A line that "isn't resonating": offer two wordings (tighter vs fuller) as a choice, with what each costs, and
  recommend one.
