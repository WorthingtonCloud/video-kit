#!/usr/bin/env python3
"""Sound effects: what a video needs that the library doesn't have yet, bought once from ElevenLabs text-to-sound
(eleven_text_to_sound_v2) and kept in the studio's library/sfx, so every later video gets it for free.

The kit bundles a palette of 30 sounds (library/sfx/index.json: whooshes, hits, ticks, a logo sting, boxing bells, a
crowd, stamps, coins…; free to use, no credit needed). A project asks for more in its sfx.json:
    {"bell": [1.6, "single boxing ring bell, one strike of a brass ringside bell, …"], …}
and only the ones the library doesn't already have are bought. Duration set = 11 credits a second (min 0.5 s).
Every new sound is measured (length, attack, peak, loudness) and anything that came back nearly silent is flagged: two
"rubber stamps" once came back at -55 and -49 dBFS, and the mixer would have turned the noise up to a stamp's level.

    vs sfx                 list what's missing and what it costs, then stop (the moment to ask)
    vs sfx --yes [--cap 1000]
    vs sfx list            every sound the studio can use, with what it's for"""
import json, math, os, sys, urllib.request, urllib.error
import vslib

URL = "https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_192"
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
CAP = int(arg("--cap", vslib.profile().get("spend", {}).get("elevenlabs_sfx_credits_per_video", 1000)))

if sys.argv[1:2] == ["list"]:
    for name, e in sorted(vslib.sound_index().items()):
        print(f"  {name:10s} {e.get('use', ''):22s} {e.get('secs', '')}s  {e.get('source', '')}")
    sys.exit()

want = vslib.read_json("sfx.json")
todo = {n: v for n, v in want.items() if not vslib.sound_path(n)}
cost = lambda n: math.ceil(11 * todo[n][0])
if not todo:
    sys.exit(f"Nothing to buy: the library already has all {len(want)} sounds sfx.json asks for." if want else
             "No sfx.json in this project: the library's sounds are all available (vs sfx list).")
for n in todo:
    print(f"  {n:10s} {todo[n][0]:.1f}s  ~{cost(n)} credits  {todo[n][1][:70]}")
vslib.gate("elevenlabs", f"{len(todo)} new sounds", credits=sum(cost(n) for n in todo), yes="--yes" in sys.argv,
           cap_key="elevenlabs_sfx_credits_per_video", cap=CAP, scope="sfx")

s = vslib.studio_root()
lib = os.path.join(s, "library/sfx") if s else "sfx"
os.makedirs(lib, exist_ok=True)
index_path = os.path.join(lib, "index.json")
index = vslib.read_json(index_path, {"sounds": {}})
key = vslib.key("ELEVENLABS_API_KEY")
spent = lambda: vslib.spent(project=vslib.project_name(), vendor="elevenlabs", what_prefix="sfx")
for name, (secs, prompt) in todo.items():
    req = urllib.request.Request(URL, method="POST", headers={"xi-api-key": key, "Content-Type": "application/json"},
                                 data=json.dumps({"text": prompt, "duration_seconds": secs, "prompt_influence": 0.6,
                                                  "model_id": "eleven_text_to_sound_v2"}).encode())
    row = vslib.log("elevenlabs", f"sfx {name}", credits=cost(name), note=prompt)  # billed on the call
    try:
        audio = urllib.request.urlopen(req, timeout=120).read()
    except urllib.error.HTTPError as e:
        vslib.failed(row, note=f"HTTP {e.code}")
        sys.exit(f"{name}: HTTP {e.code} {e.read()[:300]}")
    out = os.path.join(lib, name + ".mp3")
    open(out, "wb").write(audio)
    vslib.done(row)
    m = vslib.measure(out)
    index["sounds"][name] = {"file": name + ".mp3", "source": "elevenlabs eleven_text_to_sound_v2", "prompt": prompt,
                             "project": vslib.project_name(), **m}
    json.dump(index, open(index_path, "w"), indent=1)
    print(f"{out}  {secs}s  ~{cost(name)} credits (this video: {spent():.0f})" + (f"  ⚠️  {m['warning']}" if m.get("warning") else ""), flush=True)
