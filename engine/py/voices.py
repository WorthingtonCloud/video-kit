#!/usr/bin/env python3
"""Pick the narrator: an audition page from ElevenLabs' FREE preview clips (no credits).
    vs voices → build/voice-previews/index.html   (each voice reads its own preview line; some are only 4 s)
The list is twelve narrators from ElevenLabs' voice library (Sep 30, 2026); the demo used #09. Swap it for your own
search. Then have the top three read the SAME line with narrate.py --voice <ID> (a few cents each) before choosing,
and put the winner in the studio's profile.json → "narrator" (every video uses it) or one plan.json. Two library voices can share a name: always record the ID."""
import html, os
VOICES = [("nPczCjzI2devNBz1zQrb", "Brian", "Deep, Resonant and Comforting"), ("gs0tAILXbY5DNrJrsM6F", "Jeff", "Classy, Resonating and Strong"),
          ("DYkrAHD8iwork3YSUBbs", "Tom", "Conversations & Books"), ("8JVbfL6oEdmuxKn5DK2C", "Johnny Kid", "Serious and Calm Narrator"),
          ("6F5Zhi321D3Oq7v1oNT4", "Hank", "Deep and Engaging Narrator"), ("LruHrtVF6PSyGItzMNHS", "Benjamin", "Deep, Warm, Calming"),
          ("hqfrgApggtO1785R4Fsn", "Theodore", "Serene and Grounded"), ("NNl6r8mD7vthiJatiJt1", "Bradford", "Expressive and Articulate"),
          ("UgBBYS2sOqTuMpoF3BR0", "Mark", "Natural Conversations"), ("NOpBlnGInO9m6vDvFkFC", "Spuds Oxley", "Wise and Approachable"),
          ("EkK5I93UQWFDigLMpZcX", "James", "Husky, Engaging and Bold"), ("DTKMou8ccj1ZaWGBiotd", "Jamahal", "Young, Vibrant, and Natural")]
os.makedirs("build/voice-previews", exist_ok=True)
rows = "".join(f'<div class="card"><b>{k:02d} · {html.escape(n)}</b> <span>{html.escape(d)}</span><br><code>{v}</code><audio controls preload="none" src="https://static.aiquickdraw.com/elevenlabs/voice/{v}.mp3"></audio></div>'
               for k, (v, n, d) in enumerate(VOICES, 1))
open("build/voice-previews/index.html", "w").write(f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Voice Auditions</title>
<style>body{{background:#111114;color:#f4f4f2;font:16px/1.5 system-ui;padding:24px 16px;max-width:720px;margin:auto}}.card{{background:#1c1d21;border:1px solid #2a2b30;border-radius:12px;padding:12px 14px;margin:0 0 10px}}span{{color:#9b9da4}}code{{color:#9b9da4;font-size:12px}}audio{{width:100%;margin-top:6px}}</style>
<h1>Voice auditions</h1>{rows}""")
print("build/voice-previews/index.html")
