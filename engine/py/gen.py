#!/usr/bin/env python3
"""Paid generation: music, stills, and short video clips. Every call is gated and logged.

    vs gen music --style "…" [--negative "…"] [--title "…"] [--duration 45]
    vs gen extend --audio-id <id> --at <s> (--lyrics <file> | --instrumental) --style "…" [--negative "…"] [--title "…"] [--out music/x]
                                                   Suno continues an existing song from <s> seconds with new words
                                                   (same singer, tempo and key): a changed lyric, a radio edit
    vs gen stems  --task-id <id> --audio-id <id> --out stems/<name>
                                                   a Suno take split into 12 stems (vocals, backing vocals, drums …)
    vs gen still --prompt "…" --out stills/x.png [--ar 9:16] [--ref stills/y.png] [--engine codex|kie]
    vs gen clip  --image stills/x.png [--end stills/y.png] --prompt "…" --out clips/x_480p.mp4 [--res 480p|720p] [--dur 5] [--via higgsfield|kie]
    vs gen spent                                   total spend so far, from ledger.csv

Every call goes through the spend gate (vslib.gate): without --yes it only prints the estimated cost and this video's
spend so far, and exits: that is the moment to ask the human. It refuses past reel.json → "budget_usd" (else the profile's
usd_per_video, every vendor together) unless you add --over, and music past the video's music credit cap (vs music's
too). With --yes it spends; each job is a ledger row from the moment it's submitted (kept = "pending" until someone
decides; status submitted → done).

Stills default to --engine codex: the Codex CLI's built-in image tool, signed in with a ChatGPT plan, so a still
costs nothing per image (it draws on the plan's usage limit instead). No key and no spend gate; the ledger row says $0.
Codex is found at $CODEX_BIN, then `codex` on PATH, then the copy bundled in ChatGPT.app. --engine kie is the paid
Seedream path and goes through the spend gate as before. If Codex reports a usage limit, stop and ask the human;
never fall back to the paid engine on your own.

Keys, from the environment, a .env in this folder or any folder above it, or the studio's .env:
    KIE_AI_API_KEY       kie.ai  — music (Suno), stills (Seedream), clips (Kling), and hosting for input images
    HIGGSFIELD_API_KEY   Higgsfield — clips (Seedance 2.5), as "<key_id>:<key_secret>"
Costs below are estimates from each vendor's published pricing. Check the vendor's billing page for the truth.
"""
import argparse, base64, json, os, sys, time, urllib.request
import vslib
from vslib import key

KIE, KIE_UP = "https://api.kie.ai", "https://kieai.redpandaai.co/api/file-base64-upload"
HF, HF_STATUS = "https://api.higgsfield.ai/bytedance/seedance-2.5/image-to-video", "https://platform.higgsfield.ai/requests/{}/status"
UA = "curl/8.7.1"  # Higgsfield's firewall rejects Python's default user agent (error 1010) before any job exists


def call(url, body=None, headers=None, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "User-Agent": UA, **(headers or {})})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def fetch(url, out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    open(out, "wb").write(urllib.request.urlopen(req, timeout=300).read())


def fetch_song(t, out):
    """A Suno take, whole. Either of its two links can come back short: audio_url served a truncated file (Sep 2026),
    stream_audio_url an empty one (Oct 11, 2026), and Python's urlopen stalls or returns 0 bytes on them. So: curl
    each link, keep the first whose decoded length is within a second of the take's own duration."""
    import subprocess
    want = float(t.get("duration") or 0)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    for url in [u for u in (t.get("audio_url"), t.get("stream_audio_url")) if u]:
        subprocess.run(["curl", "-sL", "--max-time", "300", "-o", out, url])
        got = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                             capture_output=True, text=True).stdout.strip()
        if got and (not want or abs(float(got) - want) < 1.0):
            return out
        print(f"  {os.path.basename(out)}: {url.split('/')[2]} gave {got or 'no audio'} (want {want:.1f}s), trying the other link")
    sys.exit(f"{out}: no whole copy from either link; the take is still on kie.ai for 14 days")


def host(path):
    """Video models need a public image URL; kie.ai's upload endpoint provides one."""
    print(f"  uploading {path} to kie.ai's file host so the model can read it (it leaves this machine)", flush=True)
    ext = os.path.splitext(path)[1].lstrip(".").lower().replace("jpg", "jpeg")
    r = call(KIE_UP, {"base64Data": f"data:image/{ext};base64," + base64.b64encode(open(path, "rb").read()).decode(),
                      "uploadPath": "reel", "fileName": os.path.basename(path)}, {"Authorization": f"Bearer {key('KIE_AI_API_KEY')}"})
    d = r.get("data") or {}
    url = d.get("downloadUrl") or d.get("fileUrl") or d.get("url")
    if not url:
        sys.exit(f"upload failed: {json.dumps(r)[:300]}")
    return url


def poll(label, fn, timeout=1200):
    """Print on every poll, so a quiet log means something. A failed poll is 'unknown', never 'done'."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(8)
        try:
            state, result = fn()
        except Exception as e:
            print(f"  {label}: poll failed ({e}) — status unknown, still waiting", flush=True)
            continue
        print(f"  {label}: {state} ({int(time.time() - t0)}s)", flush=True)
        if result is not None:
            return result
        if state in ("fail", "failed", "nsfw", "canceled", "cancelled"):
            sys.exit(f"{label}: {state}")
    sys.exit(f"{label}: gave up after {timeout}s. The job may still finish; check the vendor dashboard before re-running.")


def kie_task(model, inp):
    r = call(f"{KIE}/api/v1/jobs/createTask", {"model": model, "input": inp}, {"Authorization": f"Bearer {key('KIE_AI_API_KEY')}"})
    tid = (r.get("data") or {}).get("taskId")
    if not tid:
        sys.exit(f"createTask {model}: {json.dumps(r)[:300]}")
    return tid


def kie_wait(tid, label):
    def fn():
        d = call(f"{KIE}/api/v1/jobs/recordInfo?taskId={tid}", headers={"Authorization": f"Bearer {key('KIE_AI_API_KEY')}"}).get("data") or {}
        st = d.get("state") or d.get("status") or "queued"
        if st == "success":
            out = d.get("resultJson")
            return st, json.loads(out) if isinstance(out, str) else out
        return st, None
    return poll(label, fn)


def codex_bin():
    import shutil
    for c in (os.environ.get("CODEX_BIN"), shutil.which("codex"), "/Applications/ChatGPT.app/Contents/Resources/codex"):
        if c and os.path.exists(c):
            return c
    sys.exit("Codex not found: install the Codex CLI or ChatGPT.app and sign in with a ChatGPT plan, or set CODEX_BIN. "
             "(--engine kie is the paid alternative; ask the human first.)")


def codex_still(prompt, out, ar, ref=None):
    """One image from Codex's built-in image tool. stdin must be closed or `codex exec` waits for input forever,
    and -i takes several files, so `--` ends the list before the prompt."""
    import subprocess, tempfile, shutil
    work = tempfile.mkdtemp(prefix="vs-codex-")
    if ref:
        ask = (f"The attached image is a reference. Use your image generation tool to create exactly one image in a {ar} "
               f"aspect ratio from this prompt, keeping the reference's subject and look where the prompt implies it: "
               f'"{prompt}" Save it as image.png in the current directory and print its pixel dimensions.')
    else:
        ask = (f"Use your image generation tool to create exactly one image in a {ar} aspect ratio, using this prompt "
               f'verbatim and adding nothing to it: "{prompt}" Save it as image.png in the current directory and print its pixel dimensions.')
    cmd = [codex_bin(), "exec", "--skip-git-repo-check", "--sandbox", "workspace-write"]
    if ref:
        cmd += ["-i", os.path.abspath(ref)]
    cmd += ["--", ask]
    try:
        r = subprocess.run(cmd, cwd=work, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=360)
    except subprocess.TimeoutExpired:
        sys.exit(f"codex timed out after 6 min (work dir kept: {work})")
    pngs = [f for f in os.listdir(work) if f.endswith(".png")]
    if not pngs:
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-6:])
        sys.exit(f"codex returned no image (work dir kept: {work}):\n{tail}")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    shutil.copyfile(os.path.join(work, pngs[0]), out)
    shutil.rmtree(work, ignore_errors=True)


def spent():
    return vslib.spent_usd(project=vslib.project_name())


def log(shot, tool, model, resolution, seconds, cost_usd=None, why="", credits=""):
    return vslib.log(tool, shot, credits=credits, usd="" if cost_usd is None else cost_usd, kept="pending",
                     note=f"{model} · {resolution} · {seconds}s · {why}")


def amend(row, shot=None, why=None):
    vslib.amend(row, **({"what": shot} if shot else {}), **({"note": why[:160]} if why else {}))


def gate(vendor, what, a, **cost):
    vslib.gate(vendor, what, yes=a.yes, over=a.over, **({"cap": a.cap} if a.cap is not None else {}), **cost)


ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["music", "extend", "stems", "still", "clip", "spent"])
ap.add_argument("--audio-id"); ap.add_argument("--task-id"); ap.add_argument("--at", type=float); ap.add_argument("--lyrics")
ap.add_argument("--vocal-gender", choices=["m", "f"])
ap.add_argument("--instrumental", action="store_true", help="extend: continue an instrumental take (no --lyrics)")
ap.add_argument("--style"); ap.add_argument("--negative", default="vocals, singing, lyrics, horror, ominous, eerie")
ap.add_argument("--title", default="reel bed"); ap.add_argument("--duration", type=int, default=45)
ap.add_argument("--prompt"); ap.add_argument("--out"); ap.add_argument("--ar", default="9:16"); ap.add_argument("--ref")
ap.add_argument("--image"); ap.add_argument("--end", help="clip (higgsfield): the image the clip must END on"); ap.add_argument("--res", default="480p"); ap.add_argument("--dur", type=int, default=5)
ap.add_argument("--via", default="higgsfield", choices=["higgsfield", "kie"])
ap.add_argument("--engine", default="codex", choices=["codex", "kie"], help="stills only: codex ($0, ChatGPT plan) or kie (paid)")
ap.add_argument("--yes", action="store_true"); ap.add_argument("--over", action="store_true")
ap.add_argument("--cap", type=float, help="lift this video's credit cap for the step's kind of spend; only on the human's say-so")
a = ap.parse_args()

if a.cmd == "spent":
    print(f"${spent():.2f} spent on this video, per {vslib.ledger_path()}")

elif a.cmd == "music":
    if not a.style:
        sys.exit("--style is required: genre, tempo, energy, instruments, and what it should build to")
    gate("kie.ai", "Two ~45s instrumental takes (Suno V6)", a, credits=12, cap_key="kie_credits_per_video", scope="music")
    # the model name is NESTED: outer "ai-music-api/generate", inner "V6". A top-level "V6" returns 422.
    tid = kie_task("ai-music-api/generate", {"custom_mode": True, "instrumental": True, "title": a.title, "style": a.style,
                                             "negative_tags": a.negative, "duration": a.duration, "model": "V6"})
    row = log(shot="music (submitted)", tool="kie.ai", model="suno V6", resolution="n/a", seconds=a.duration, credits=12,
              why=f"task {tid} · {a.style[:120]}")
    res = kie_wait(tid, "music")
    os.makedirs("music", exist_ok=True)
    have = len([f for f in os.listdir("music") if f.startswith("take") and f.endswith(".mp3")])
    for i, t in enumerate(res.get("data", []), have + 1):
        fetch(t["audio_url"], f"music/take{i}.mp3")
        print(f"music/take{i}.mp3")
    # Keep each take's audio id: extending a take later (Suno "extend") needs it, and kie.ai forgets it after 14 days.
    ids = " ".join(f"take{i}={t.get('id', '?')}" for i, t in enumerate(res.get("data", []), have + 1))
    amend(row, shot=f"music takes {have + 1}-{have + len(res.get('data', []))}", why=f"{ids} · {a.style[:120]}")
    vslib.done(row)

elif a.cmd == "extend":
    # Suno "extend": the take is kept up to --at, then continues with these words, conditioned on what came before,
    # so the singer, tempo and key carry over. The fix for a changed lyric: replace-section ignored new words twice
    # (Oct 10, 2026). Audio ids expire 14 days after the take was made.
    if not (a.audio_id and a.at and a.style and (a.lyrics or a.instrumental)):
        sys.exit("--audio-id, --at, --style and --lyrics (a file) or --instrumental are required")
    words = "" if a.instrumental else open(a.lyrics, encoding="utf-8").read().strip()
    if a.negative == ap.get_default("negative") and not a.instrumental:
        sys.exit("--negative is required for extend: pass the source take's own negative tags (the music default bans vocals)")
    gate("kie.ai", "Two takes continuing the " + ("instrumental" if a.instrumental else "song with new words") + " (Suno V6 extend)", a, credits=12,
         cap_key="kie_credits_per_video", scope="music")
    inp = {"audio_id": a.audio_id, "model": "V6", "continue_at": a.at, "lyrics": words, "style": a.style[:1000],
           "title": a.title, "negative_tags": a.negative[:201].rsplit(",", 1)[0] if len(a.negative) > 200 else a.negative,
           "instrumental": bool(a.instrumental)}   # extend refuses negative tags over 200 characters (422, unbilled)
    if a.vocal_gender:
        inp["vocal_gender"] = a.vocal_gender
    tid = kie_task("ai-music-api/extend", inp)
    row = log(shot="music extend (submitted)", tool="kie.ai", model="suno V6 extend", resolution="n/a", seconds=0,
              credits=12, why=f"task {tid} · from {a.audio_id} at {a.at}s")
    res = kie_wait(tid, "extend")
    takes = res.get("data") or (res.get("resultObject") or {}).get("lyricsData") or []
    base = a.out or "music/extend"
    ids = []
    for i, t in enumerate(takes, 1):
        fetch_song(t, f"{base}-take{i}.mp3")
        ids.append(f"take{i}={t.get('id', '?')}")
        print(f"{base}-take{i}.mp3  audio id {t.get('id')}")
    json.dump({"task_id": tid, "takes": takes}, open(f"{base}.json", "w"), indent=1)
    amend(row, shot=f"music extend {os.path.basename(base)}", why=f"task {tid} · {' '.join(ids)} · from {a.audio_id} at {a.at}s")
    vslib.done(row)

elif a.cmd == "stems":
    # 50 credits for 12 stems. They lag Suno's own mix by 19 ms (839 samples at 44.1 kHz) and sum ~3 dB hotter:
    # shift and scale before mixing stems against the mix.
    if not (a.task_id and a.audio_id and a.out):
        sys.exit("--task-id, --audio-id and --out (a folder) are required")
    gate("kie.ai", "One take split into 12 stems (Suno split_stem)", a, credits=50, cap_key="kie_credits_per_video", scope="music")
    tid = kie_task("ai-music-api/separate-vocals", {"task_id": a.task_id, "audio_id": a.audio_id, "type": "split_stem"})
    row = log(shot="music stems (submitted)", tool="kie.ai", model="suno split_stem", resolution="n/a", seconds=0,
              credits=50, why=f"task {tid} · {a.audio_id}")
    res = kie_wait(tid, "stems")
    urls = res.get("resultUrls") or []
    if not urls:
        info = res.get("vocal_removal_info") or res.get("resultObject") or {}
        urls = [v for v in info.values() if isinstance(v, str) and v.startswith("http")]
    os.makedirs(a.out, exist_ok=True)
    for u in urls:
        name = u.split("?")[0].rsplit("/", 1)[-1]
        fetch(u, os.path.join(a.out, name))
        print(os.path.join(a.out, name))
    amend(row, shot=f"music stems {os.path.basename(a.out.rstrip('/'))}", why=f"task {tid} · {a.audio_id} · {len(urls)} stems")
    vslib.done(row)

elif a.cmd == "still":
    if not (a.prompt and a.out):
        sys.exit("--prompt and --out are required")
    if a.engine == "codex":
        print(f"  codex still ({a.ar}) on the ChatGPT plan: $0, about a minute", flush=True)
        row = log(shot=os.path.basename(a.out), tool="codex", model="codex image_gen", resolution=a.ar, seconds=0,
                  cost_usd=0, why=a.prompt[:120])
        codex_still(a.prompt, a.out, a.ar, a.ref)
        vslib.done(row)
        print(a.out)
        sys.exit(0)
    gate("kie.ai", f"One still ({a.ar}, Seedream 5 Pro)", a, credits=28)
    inp = {"prompt": a.prompt, "aspect_ratio": a.ar, "quality": "high", "output_format": "png", "nsfw_checker": False}
    model = "seedream/5-pro-text-to-image"
    if a.ref:
        model, inp["image_urls"] = "seedream/5-pro-image-to-image", [host(a.ref)]
    tid = kie_task(model, inp)
    row = log(shot=os.path.basename(a.out), tool="kie.ai", model=model, resolution=a.ar, seconds=0, credits=28,
              why=f"task {tid} · {a.prompt[:120]}")
    res = kie_wait(tid, os.path.basename(a.out))
    urls = res.get("resultUrls") or res.get("result_urls") or []
    fetch(urls[0], a.out)
    vslib.done(row)
    print(a.out)

elif a.cmd == "clip":
    if not (a.image and a.prompt and a.out):
        sys.exit("--image, --prompt and --out are required")
    if a.via == "higgsfield":
        h = {"480p": 480, "720p": 720}[a.res]
        # Higgsfield bills tokens = h × w × seconds × 24 / 1024 at $0.0214 per 1,000 (5s: ~$1.03 at 480p, ~$2.31 at 720p)
        est = h * round(h * 16 / 9) * a.dur * 24 / 1024 / 1000 * 0.0214
        gate("higgsfield", f"One {a.dur}s {a.res} clip (Seedance 2.5; the shape follows the input image)", a, usd=round(est, 2))
        body = {"image_url": host(a.image), "prompt": a.prompt, "duration": a.dur, "resolution": a.res, "generate_audio": False}
        if a.end:   # Seedance 2.5 lands on this frame (first = last loops cleanly; Oct 7, 2026)
            body["end_image_url"] = host(a.end)
        r = call(HF, body, {"Authorization": f"Key {key('HIGGSFIELD_API_KEY')}"})
        rid = r.get("request_id") or r.get("id")
        print(f"submitted {rid}", flush=True)
        row = log(shot=os.path.basename(a.out), tool=a.via, model="seedance-2.5 image-to-video", resolution=a.res,
                  seconds=a.dur, cost_usd=round(est, 2), why=f"request {rid} · {a.prompt[:120]}")

        def fn():
            s = call(HF_STATUS.format(rid), headers={"Authorization": f"Key {key('HIGGSFIELD_API_KEY')}"})
            st = s.get("status")
            return st, (s.get("video") or {}).get("url") if st == "completed" else None
        fetch(poll(os.path.basename(a.out), fn), a.out)
        vslib.done(row)
    else:
        gate("kie.ai", f"One {a.dur}s clip (Kling 2.1 Pro)", a, credits=160)
        tid = kie_task("kling/v2-1-pro", {"prompt": a.prompt, "image_url": host(a.image), "duration": str(a.dur),
                       "negative_prompt": "blur, distortion, warping, morphing, text, watermark, cut, scene change", "cfg_scale": 0.5})
        row = log(shot=os.path.basename(a.out), tool="kie.ai", model="kling v2.1 pro", resolution=a.res, seconds=a.dur,
                  credits=160, why=f"task {tid} · {a.prompt[:120]}")
        res = kie_wait(tid, os.path.basename(a.out))
        fetch((res.get("resultUrls") or [])[0], a.out)
        vslib.done(row)
    print(a.out, "— now run: vs qa", a.out, "--clip")
