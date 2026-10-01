#!/usr/bin/env python3
"""Music bed for an explainer: Suno V6 on kie.ai, instrumental, one call per direction (12 credits = 2 takes each).
Directions come from the project's music.json ([{"label": "B modern pulse", "style": "..."}, ...]), else the studio
profile's music → directions (the ones this user has settled on), else the two defaults below (the demo explainer's,
Sep 30, 2026: the "modern pulse" won, at -20 dB under the voice). Takes land in the project's music/; the one that wins
moves to the studio's library/music when the video is done (vs learn), so the next video can reuse it for free.
Refuses past --cap credits for this video in the studio ledger. Needs --yes (the human's go, with the number said first).

    vs music                    print the cost and stop (the moment to ask)
    vs music --yes [--duration 180] [--cap 48]
    vs music spent

Every take is downloaded, then decoded end to end: kie.ai's audio_url once served a truncated 458 KB file for a
3-minute take; the stream_audio_url had it all. Raw results (with the audio ids Suno extend needs; kie.ai forgets them
after 14 days) go to music/<task>.json."""
import json, os, subprocess, sys, time, urllib.request
import vslib
from vslib import key as get_key

KIE, PER_CALL, UA = "https://api.kie.ai", 12, "curl/8.7.1"
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
CAP, DUR = int(arg("--cap", vslib.profile().get("spend", {}).get("kie_credits_per_video", 48))), int(arg("--duration", 180))
NEG = ("vocals, rap vocals, singing, lyrics, humming, choir, horror, ominous, eerie, sad, dramatic build, big drops, "
       "loud lead melody, guitar solo")
DEFAULT = [
    {"label": "A lo-fi head-nod", "style": "mellow lo-fi hip-hop instrumental, 85 BPM head-nod groove, dusty boom-bap drums "
        "with a soft kick and brushed snare, warm Rhodes electric piano chords, round bass, vinyl warmth, relaxed but confident, "
        "steady even energy start to finish, sparse, no lead melody, sits under a voiceover"},
    {"label": "B modern pulse", "style": "light modern hip-hop and electronic pulse instrumental, 92 BPM, crisp soft hi-hats, "
        "muted punchy kick, warm sub bass, gentle plucked synth arpeggio, clean, curious and optimistic, smart documentary "
        "explainer bed, steady even energy, minimal melody, leaves room for a narrator"},
]
DIRS = json.load(open("music.json")) if os.path.exists("music.json") else (vslib.profile().get("music", {}).get("directions") or DEFAULT)


def key():
    return get_key("KIE_AI_API_KEY")


def call(path, body=None):
    req = urllib.request.Request(KIE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "User-Agent": UA, "Authorization": f"Bearer {key()}"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def spent():
    return vslib.spent(project=vslib.project_name(), vendor="kie.ai", what_prefix="music")


def log(what, credits, note):
    vslib.log("kie.ai", what, credits=credits, note=note)


def decoded_secs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-f", "null", "-"], capture_output=True, text=True).stderr
    t = [x for x in r.replace("\r", "\n").split() if x.startswith("time=")]
    if not t: return 0
    h, m, s = t[-1][5:].split(":"); return int(h) * 3600 + int(m) * 60 + float(s)


def fetch(urls, out, want):
    for u in urls:
        if not u: continue
        subprocess.run(["curl", "-s", "-m", "400", "--retry", "3", "-A", UA, "-o", out, u])
        got = decoded_secs(out) if os.path.exists(out) else 0
        if got >= want - 2: return got
        print(f"  {out}: {got:.0f}s of {want:.0f}s from {u.split('/')[2]}, trying the next link", flush=True)
    sys.exit(f"{out}: no complete download. The ids are in music/*.json; retry later.")


tracks = lambda res: res.get("data") or (res.get("resultObject") or {}).get("lyricsData") or []

if sys.argv[1:2] == ["spent"]:
    sys.exit(print(f"{spent()} music credits logged"))
cost = PER_CALL * len(DIRS)
if os.path.exists("reel.json"):
    total = vslib.timeline(json.load(open("reel.json")))[2]
    if DUR < total + 3: print(f"⚠️  --duration {DUR}s is shorter than the video ({total:.0f}s): Suno extend, or a longer take")
if "--yes" not in sys.argv:
    sys.exit(f"{len(DIRS)} directions × 2 takes of ~{DUR}s = {cost} kie.ai credits (${cost * 0.005:.2f}). Re-run with --yes once the human has said yes to that number.")
if spent() + cost > CAP:
    sys.exit(f"⛔ would pass the {CAP}-credit cap ({spent()} logged). Ask the human before raising --cap.")

print("balance before:", call("/api/v1/chat/credit").get("data"), flush=True)
tasks = {}
for d in DIRS:
    r = call("/api/v1/jobs/createTask", {"model": "ai-music-api/generate", "input": {  # model NESTED: outer generate, inner V6
        "custom_mode": True, "instrumental": True, "title": f"Explainer bed {d['label'][0]}", "style": d["style"],
        "negative_tags": d.get("negative", NEG), "duration": DUR, "model": "V6"}})
    tid = (r.get("data") or {}).get("taskId") or sys.exit(f"createTask: {json.dumps(r)[:300]}")
    log(f"music {d['label']} (submitted {tid})", PER_CALL, d["style"][:100])  # billed on submit
    tasks[tid] = d["label"]
    print(f"submitted {d['label']}: {tid}", flush=True)

os.makedirs("music", exist_ok=True)
n = len([f for f in os.listdir("music") if f.startswith("take") and f.endswith(".mp3")])
done, t0 = set(), time.time()
while len(done) < len(tasks) and time.time() - t0 < 1200:
    time.sleep(10)
    for tid, label in tasks.items():
        if tid in done: continue
        try:
            d = call(f"/api/v1/jobs/recordInfo?taskId={tid}").get("data") or {}
        except Exception as e:
            print(f"  {label}: poll failed ({e}), status unknown", flush=True); continue  # unknown, never "done"
        st = d.get("state") or d.get("status") or "queued"
        print(f"  {label}: {st} ({int(time.time() - t0)}s)", flush=True)
        if st == "success":
            res = d.get("resultJson"); res = json.loads(res) if isinstance(res, str) else res
            json.dump(res, open(f"music/{tid}.json", "w"), indent=1)
            done.add(tid)
            for t in tracks(res):
                n += 1
                got = fetch([t.get("audio_url"), t.get("stream_audio_url")], f"music/take{n}.mp3", float(t.get("duration") or DUR))
                print(f"music/take{n}.mp3  {label}  {got:.1f}s  id={t.get('id')}", flush=True)
                names = json.load(open("music/takes.json")) if os.path.exists("music/takes.json") else {}
                names[f"take{n}"] = {"label": label, "id": t.get("id"), "secs": round(got, 2)}  # mix.py + the mixer read this
                json.dump(names, open("music/takes.json", "w"), indent=1)
        elif st in ("fail", "failed", "canceled"):
            done.add(tid); print(f"  {label}: FAILED {json.dumps(d)[:300]}", flush=True)
print("balance after:", call("/api/v1/chat/credit").get("data"), flush=True)
