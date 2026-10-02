#!/usr/bin/env python3
"""Read narration.txt via ElevenLabs with word timings. Paid: it prints the cost and stops; --yes spends (the spend gate).
Usage: vs narrate <tag> [--voice ID] [--model eleven_v4] [--stability 0.3] [--acts 1-2] [--yes] [--cap N]
The narrator is the studio profile's "narrator" ({"voice": "<ElevenLabs voice ID>", "model": "eleven_v4", "stability": 0.3}),
which a plan.json → "narrator" overrides for one video; the flags override both. Always the voice ID, never the name: two library voices can share one.
Writes voice/narration-<tag>.mp3 + .words.json ({w, t0, t1, act}); prints per-act times and credits used."""
import json, math, os, sys, time, base64, urllib.request, urllib.error
from vslib import key, profile, log, gate, done, failed
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
N = {**(profile().get("narrator") or {}), **(((json.load(open("plan.json")).get("narrator") or {}) if os.path.exists("plan.json") else {}))}
tag, VOICE, MODEL = sys.argv[1], arg("--voice", N.get("voice")), arg("--model", N.get("model", "eleven_v4"))
if not VOICE: sys.exit('no narrator: set the studio profile → "narrator": {"voice": "<voice ID>"} (vs voices to audition), or pass --voice')
STAB = float(arg("--stability", N.get("stability", 0.3)))
_a = arg("--acts", "1-99").split("-")  # "5" = act 5 alone, "4-6" a run
lo, hi = int(_a[0]), int(_a[-1])
acts = [" ".join(l for l in b.splitlines() if l.strip() and not l.startswith("#")) for b in open("narration.txt").read().split("\n\n")]
acts = [a for a in acts if a][lo - 1:hi]
v4 = MODEL.startswith("eleven_v3") or MODEL.startswith("eleven_v4")
text = "\n\n".join(acts) if v4 else ' <break time="0.7s" /> '.join(acts)
# about 0.06 credits a character (measured Oct 1, 2026: 2,866 → 173, 408 → 25)
est, what = math.ceil(len(text) * 0.06), f"voice {tag} (acts {lo}-{lo + len(acts) - 1})"
gate("elevenlabs", f"Narration {what}: {len(text)} characters, {MODEL}", credits=est, yes="--yes" in sys.argv,
     cap_key="elevenlabs_voice_credits_per_video", cap=float(arg("--cap", 0)) or None, scope="voice")
KEY = key("ELEVENLABS_API_KEY")
vs = {"stability": STAB, "similarity_boost": 0.75} if v4 else {"stability": STAB, "similarity_boost": 0.75, "style": 0, "speed": 1}
req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128",
                             data=json.dumps({"text": text, "model_id": MODEL, "voice_settings": vs}).encode(),
                             headers={"xi-api-key": KEY, "Content-Type": "application/json"})
sent = time.time()
row = log("elevenlabs", what, credits=est, note=f"{VOICE} · {MODEL} · {len(text)} chars")  # billed on submit
try: d = json.load(urllib.request.urlopen(req, timeout=300))
except urllib.error.HTTPError as e:
    failed(row, note=f"HTTP {e.code}")
    sys.exit(f"HTTP {e.code} {e.read().decode()[:500]}")
os.makedirs("voice", exist_ok=True)
open(f"voice/narration-{tag}.mp3", "wb").write(base64.b64decode(d["audio_base64"]))
a = d.get("alignment") or {}; words, cur, act, skip, t0, last = [], "", lo, None, 0, 0
for ch, s, e in zip(a.get("characters", []), a.get("character_start_times_seconds", []), a.get("character_end_times_seconds", [])):
    if ch in "<[": skip = ">" if ch == "<" else "]"
    if skip:
        if ch == skip: skip = None; act += (ch == ">")
        continue
    if ch == "\n" and cur == "" and words and words[-1]["act"] == act and not v4: pass
    if ch.isspace():
        if cur: words.append({"w": cur, "t0": round(t0, 3), "t1": round(last, 3), "act": act}); cur = ""
        if ch == "\n" and v4 and words and words[-1]["act"] == act: act += 1
        continue
    if not cur: t0 = s
    cur += ch; last = e
if cur: words.append({"w": cur, "t0": round(t0, 3), "t1": round(last, 3), "act": act})
json.dump(words, open(f"voice/narration-{tag}.words.json", "w"), indent=0)
for n in sorted({w["act"] for w in words}):
    ws = [w for w in words if w["act"] == n]; print(f"act {n}: {ws[0]['t0']:6.2f}s – {ws[-1]['t1']:6.2f}s  ({len(ws)} words)")
if not words: print("no alignment returned")
# the history logs a call a few seconds late: reading it at once printed the PREVIOUS call's cost (Oct 1, 2026)
for _ in range(10):
    h = json.load(urllib.request.urlopen(urllib.request.Request("https://api.elevenlabs.io/v1/history?page_size=1", headers={"xi-api-key": KEY})))["history"][0]
    if h["date_unix"] >= sent - 5: break
    time.sleep(2)
else: h = None
cr = (h["character_count_change_to"] - h["character_count_change_from"]) if h else ""
done(row, credits=cr if h else est)  # the measured credits replace the estimate
print(f"{len(text)} chars, credits this call: " + (str(cr) if h else f"not in the history yet (logged the estimate, {est})"))
