#!/usr/bin/env python3
"""Music bed for an explainer: Suno V6 on kie.ai, instrumental, one call per direction (12 credits = 2 takes each).
Directions come from the project's music.json ([{"label": "B modern pulse", "style": "..."}, ...]), else the studio
profile's music → directions (the ones this user has settled on), else the two defaults below (the demo explainer's,
Sep 30, 2026: the "modern pulse" won, at -20 dB under the voice). Takes land in the project's music/; the one that wins
moves to the studio's library/music when the video is done (vs learn), so the next video can reuse it for free.
Paid, through the spend gate (vslib.gate): it refuses past --cap credits of music for this video (vs gen music counts
too), past the video's dollar budget, and without --yes (the human's go, with the number said first).

    vs music                    print the cost and stop (the moment to ask)
    vs music --yes [--duration 180] [--cap 48]
    vs music spent
    vs music extend take1 --to 220      free: a take that's shorter than the video grows by whole bars (below)

Every take is downloaded, then decoded end to end: kie.ai's audio_url once served a truncated 458 KB file for a
3-minute take; the stream_audio_url had it all. Raw results (with the audio ids Suno extend needs; kie.ai forgets them
after 14 days) go to music/<task>.json."""
import json, math, os, re, subprocess, sys, time, urllib.request
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

def extend(take, to, start=None):
    """A take that's shorter than the video, made longer for free: one run of whole bars from its middle plays twice,
    back to back, so both joins land on a downbeat inside the same steady section (the intro and the outro stay where
    they are: a replayed intro reads as a repeat). The grid comes from vs beats; the run starts on a phrase (8 bars
    from the first hit) about a third of the way in, unless --from <secs> names a downbeat heard by ear. Writes the
    next free music/take<N>.mp3 and its takes.json entry; the original take is untouched.
    Measured on an explainer (Oct 12, 2026): a 189 s bed, 30.6 s short, grew 12 bars from 1:04 with 20 ms crossfades,
    and the seams matched the original's own downbeats in loudness."""
    src = f"music/{take}.mp3" if not take.endswith(".mp3") else take
    if not os.path.exists(src):
        sys.exit(f"⛔ no {src}: vs music extend <take> --to <secs> (the take names are in music/takes.json)")
    out = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "beats.py"), src],
                         capture_output=True, text=True, check=True).stdout
    grab = lambda k: float(re.search(rf"^{k}\s+([\d.]+)s", out, re.M).group(1))  # "beat  0.6385s (94 BPM)"
    beat, hit, secs = grab("beat"), grab("first hit"), decoded_secs(src)
    bar, need = 4 * beat, to - secs
    if need <= 0:
        return print(f"{src} is already {secs:.1f}s: nothing to extend")
    n = math.ceil(need / bar)
    if start is None:
        k = max(0, math.floor((secs / 3 - hit) / (8 * bar)))  # the phrase just before the one-third mark
        a0 = hit + k * 8 * bar
    else:
        a0 = hit + round((start - hit) / bar) * bar  # snapped to the nearest downbeat
    b0 = a0 + n * bar
    if b0 > secs - min(8 * bar, 0.2 * secs):  # keep the outro (8 bars, or the last fifth of a short take) whole
        sys.exit(f"⛔ {n} bars from {a0:.1f}s run into the outro ({secs:.0f}s take): --from an earlier downbeat, or pick "
                 "a longer take")
    T = json.load(open("music/takes.json")) if os.path.exists("music/takes.json") else {}
    m = 1
    while f"take{m}" in T or os.path.exists(f"music/take{m}.mp3"):
        m += 1
    dst = f"music/take{m}.mp3"
    fc = (f"[0]atrim=0:{b0:.4f},asetpts=PTS-STARTPTS[p1];[0]atrim={a0:.4f}:{b0:.4f},asetpts=PTS-STARTPTS[p2];"
          f"[0]atrim=start={b0:.4f},asetpts=PTS-STARTPTS[p3];[p1][p2]acrossfade=d=0.02:c1=tri:c2=tri[q];"
          "[q][p3]acrossfade=d=0.02:c1=tri:c2=tri[o]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[o]", "-c:a", "libmp3lame",
                    "-b:a", "256k", dst], check=True)
    got = decoded_secs(dst)
    name = os.path.basename(src)[:-4]
    # never "from": that key means "reused from the studio's library" (vs learn files a win on the library item then,
    # and copies nothing): an extended take is a new file of this project's, made from one
    base = T.get(name, {})
    T[f"take{m}"] = {"label": f"{base.get('label', name)} · extended ({n} bars from {a0:.0f}s repeated)",
                     "secs": round(got, 2), "style": base.get("style"), "extended_from": base.get("from") or src}
    json.dump(T, open("music/takes.json", "w"), indent=1)
    print(f"{dst}: {got:.1f}s ({n} bars of {bar:.3f}s from {a0:.2f}s played twice; joins at {b0:.2f}s and "
          f"{b0 + n * bar:.2f}s). Listen to both joins; vs mix mixes it with the others.")


if sys.argv[1:2] == ["extend"]:
    if len(sys.argv) < 3 or "--to" not in sys.argv:
        sys.exit("vs music extend <take> --to <secs> [--from <secs>]")
    sys.exit(extend(sys.argv[2], float(arg("--to", 0)), float(arg("--from", 0)) or None))
if sys.argv[1:2] == ["spent"]:
    sys.exit(print(f"{spent()} music credits logged"))
cost = PER_CALL * len(DIRS)
if os.path.exists("reel.json"):
    total = vslib.timing(quiet=True)[2]
    if DUR < total + 3: print(f"⚠️  --duration {DUR}s is shorter than the video ({total:.0f}s): Suno extend, or a longer take")
vslib.gate("kie.ai", f"{len(DIRS)} music directions × 2 takes of ~{DUR}s (Suno V6)", credits=cost, yes="--yes" in sys.argv,
           cap_key="kie_credits_per_video", cap=CAP, scope="music")

print("balance before:", call("/api/v1/chat/credit").get("data"), flush=True)
tasks, rows = {}, {}
for d in DIRS:
    r = call("/api/v1/jobs/createTask", {"model": "ai-music-api/generate", "input": {  # model NESTED: outer generate, inner V6
        "custom_mode": True, "instrumental": True, "title": f"Explainer bed {d['label'][0]}", "style": d["style"],
        "negative_tags": d.get("negative", NEG), "duration": DUR, "model": "V6"}})
    tid = (r.get("data") or {}).get("taskId") or sys.exit(f"createTask: {json.dumps(r)[:300]}")
    rows[tid] = vslib.log("kie.ai", f"music {d['label']} (submitted {tid})", credits=PER_CALL, note=d["style"][:100])  # billed on submit
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
            vslib.done(rows[tid])
            for t in tracks(res):
                n += 1
                got = fetch([t.get("audio_url"), t.get("stream_audio_url")], f"music/take{n}.mp3", float(t.get("duration") or DUR))
                print(f"music/take{n}.mp3  {label}  {got:.1f}s  id={t.get('id')}", flush=True)
                names = json.load(open("music/takes.json")) if os.path.exists("music/takes.json") else {}
                names[f"take{n}"] = {"label": label, "id": t.get("id"), "secs": round(got, 2)}  # mix.py + the mixer read this
                json.dump(names, open("music/takes.json", "w"), indent=1)
        elif st in ("fail", "failed", "canceled"):
            done.add(tid); vslib.failed(rows[tid]); print(f"  {label}: FAILED {json.dumps(d)[:300]}", flush=True)
print("balance after:", call("/api/v1/chat/credit").get("data"), flush=True)
