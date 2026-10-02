# The kit's own tests

`vs test` runs them all (about ten seconds); `vs test --fast` skips the ones that build in a browser. Nothing paid can
run: `VIDEO_KIT_NO_SPEND` is set, every test gets its own HOME, and no media is checked in (tones and clips are made
with ffmpeg as needed).

- `contract/` — one `cases.json`, answered by BOTH halves of the engine (`test_contract.py`, `contract.test.mjs`): where
  the studio is, how the profile merges, where an API key comes from, segment and title timing, word specs, hashes.
  A rule both languages implement is pinned here, so they can't drift apart.
- `unit/` — the ledger and the spend gate, voice splices, sound-effect names, sound measuring, the beat grid, the command
  table (every paid step calls the gate), `vs check` and every schema against the templates the kit ships.
- `fixtures/` — two tiny projects: the reel template's beat reel and a three-act explainer with its own scene.
- `integration/` — those fixtures planned, built (`--no-render`), inspected and mixed for real.
- `regression/` — one deliberately broken mini-project per scar a check can catch, with what it must find.
