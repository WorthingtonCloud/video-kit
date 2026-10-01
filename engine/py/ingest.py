#!/usr/bin/env python3
"""Bring your own media: screenshots, photos, screen recordings, video clips, audio clips, sound effects, a music track,
your own narration, a logo. Not everything in a video is generated; what the human hands over goes in here.

    vs ingest <file or folder>… [--as KIND] [--to project|library] [--name NAME] [--note "what it is"] [--yes]

KIND: image · clip · sfx · music · voice · logo. Pictures and video are known by their format. AUDIO must say what it
is (--as sfx, music or voice): only the human knows whether a 6-second file is a door slam or a jingle, so ask.
Where it goes (the default follows what gets reused):
  sfx, music, logo        → the studio's library (every later video can use them)
  image, clip, voice      → this project (they belong to this video); --to library keeps a reusable one (a headshot,
                            product b-roll) in library/media, and a project names it as "lib:media/<name>.jpg"
What happens:
  the original is kept untouched (project: inputs/ · library: library/originals/), and a working copy is made:
  image  → media/<name>.jpg or .png (alpha kept), longest side ≤ 3000 px; HEIC converted
  clip   → media/<name>.mp4: H.264, constant frame rate, longest side ≤ 1920 (screen recordings are often variable
           frame rate, which stutters in a render); its sound, if any → media/<name>.wav; a poster frame → media/<name>.jpg
  sfx    → library/sfx/<name>.<ext>, measured (attack, peak, loudness) and checked for near-silence; cue it by name
  music  → library/music/<name>.mp3, and the project's next music take (the mixer offers it beside generated ones)
  voice  → voice/narration-<name>.mp3 + word timings from a transcription (OpenAI whisper-1, about a cent a minute:
           it asks first, --yes to spend), split into acts by matching narration.txt, so plan.py pins scenes to YOUR words
Everything lands in an index (media.json in the project; index.json in each library folder) with its size, length and
your note, so the agent can find it again without guessing."""
import argparse, difflib, json, os, re, shutil, subprocess, sys
from fractions import Fraction
import vslib

IMG = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif", ".tif", ".tiff", ".bmp", ".svg"}
VID = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
ap = argparse.ArgumentParser()
ap.add_argument("paths", nargs="+"); ap.add_argument("--as", dest="kind", choices=["image", "clip", "sfx", "music", "voice", "logo"])
ap.add_argument("--to", choices=["project", "library"]); ap.add_argument("--name"); ap.add_argument("--note", default="")
ap.add_argument("--yes", action="store_true")
a = ap.parse_args()
S = vslib.studio_root()
fps = (vslib.read_json("plan.json").get("fps") or vslib.read_json("reel.json").get("fps") or vslib.profile().get("render", {}).get("fps") or 30)


def sh(*cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, check=True, **kw).stdout


def probe(p):
    j = json.loads(sh("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", p))
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    au = any(s["codec_type"] == "audio" for s in j["streams"])
    rate = lambda r: round(float(Fraction(r)), 3) if r and r != "0/0" else None
    return {"w": v and v.get("width"), "h": v and v.get("height"), "fps": v and rate(v.get("avg_frame_rate")),
            "vfr": bool(v and v.get("avg_frame_rate") != v.get("r_frame_rate")), "secs": round(float(j["format"].get("duration", 0)), 3), "audio": au}


def clean(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "item"


def index_add(path, name, entry):
    idx = vslib.read_json(path, {"items": {}})
    idx.setdefault("items", {})[name] = entry
    json.dump(idx, open(path, "w"), indent=1)


def keep_original(src, where):
    os.makedirs(where, exist_ok=True)
    dst = os.path.join(where, os.path.basename(src))
    if os.path.abspath(src) != os.path.abspath(dst): shutil.copy2(src, dst)
    return dst


def kind_of(p):
    ext = os.path.splitext(p)[1].lower()
    if a.kind: return a.kind
    if ext in IMG: return "image"
    if ext in VID: return "clip"
    if ext in vslib.AUDIO: sys.exit(f"⛔ {p} is audio: say what it is with --as sfx, --as music or --as voice (ask the human)")
    sys.exit(f"⛔ {p}: not a picture, video or audio file this knows")


def ingest(p):
    kind, ext = kind_of(p), os.path.splitext(p)[1].lower()
    name = clean(a.name or os.path.splitext(os.path.basename(p))[0])
    to = a.to or ("library" if kind in ("sfx", "music", "logo") else "project")
    if to == "library" and not S: sys.exit("⛔ no studio yet (vs setup): the library lives in the studio")
    lib = lambda *x: os.path.join(S, "library", *x)
    orig = keep_original(p, lib("originals") if to == "library" else "inputs")
    note = {"note": a.note, "original": os.path.relpath(orig, S if to == "library" else "."), "source": "yours"}

    if kind in ("image", "logo"):
        out_dir = lib("brand") if kind == "logo" else (lib("media") if to == "library" else "media")
        os.makedirs(out_dir, exist_ok=True)
        if ext == ".svg":
            out = os.path.join(out_dir, name + ".svg"); shutil.copy(p, out); info = {}
        else:
            src = p
            if ext in (".heic", ".heif"):  # ffmpeg often can't read HEIC; macOS can
                src = os.path.join(out_dir, f".{name}-tmp.jpg"); sh("sips", "-s", "format", "jpeg", p, "--out", src)
            alpha = "a" in sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", src)
            out = os.path.join(out_dir, name + (".png" if alpha else ".jpg"))
            sh("ffmpeg", "-v", "error", "-y", "-i", src, "-frames:v", "1", "-vf",
               "scale='if(gt(iw,ih),min(3000,iw),-2)':'if(gt(iw,ih),-2,min(3000,ih))'", *([] if alpha else ["-q:v", "2"]), out)
            if src != p: os.remove(src)
            info = probe(out)
        entry = {"kind": kind, "file": os.path.basename(out), "w": info.get("w"), "h": info.get("h"), **note}
    elif kind == "clip":
        out_dir = lib("media") if to == "library" else "media"
        os.makedirs(out_dir, exist_ok=True)
        info, out = probe(p), os.path.join(out_dir, name + ".mp4")
        sh("ffmpeg", "-v", "error", "-y", "-i", p, "-vf",
           f"fps={fps},scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))',format=yuv420p",
           "-an", "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart", out)
        sh("ffmpeg", "-v", "error", "-y", "-ss", str(min(1.0, info["secs"] / 2)), "-i", out, "-frames:v", "1", "-q:v", "2", os.path.join(out_dir, name + ".jpg"))
        if info["audio"]:
            sh("ffmpeg", "-v", "error", "-y", "-i", p, "-vn", "-ar", "48000", "-ac", "2", os.path.join(out_dir, name + ".wav"))
        entry = {"kind": "clip", "file": name + ".mp4", "poster": name + ".jpg", "sound": name + ".wav" if info["audio"] else None,
                 "w": info["w"], "h": info["h"], "secs": info["secs"], "fps_in": info["fps"], "was_vfr": info["vfr"], **note}
    elif kind == "sfx":
        os.makedirs(lib("sfx") if to == "library" else "sfx", exist_ok=True)
        out = os.path.join(lib("sfx") if to == "library" else "sfx", name + ext)
        shutil.copy(p, out)
        m = vslib.measure(out)
        idx = os.path.join(os.path.dirname(out), "index.json")
        d = vslib.read_json(idx, {"sounds": {}}); d.setdefault("sounds", {})[name] = {"file": name + ext, **note, **m}
        json.dump(d, open(idx, "w"), indent=1)
        if m["secs"] > 8: print(f"  ⚠️  {name} is {m['secs']}s: long for an effect (music? --as music)")
        if m.get("warning"): print(f"  ⚠️  {name}: {m['warning']}")
        print(f"{out}  cue it as \"{name}\" in cues.py (attack at {m['attack']}s, peak at {m['peak']}s)")
        return
    elif kind == "music":
        os.makedirs(lib("music"), exist_ok=True)
        out = lib("music", name + ".mp3")
        sh("ffmpeg", "-v", "error", "-y", "-i", p, "-vn", "-c:a", "libmp3lame", "-b:a", "320k", out)
        secs = probe(out)["secs"]
        index_add(lib("music", "index.json"), name, {"kind": "music", "file": name + ".mp3", "secs": secs, "label": a.note or name, **note})
        if os.path.exists("reel.json") or os.path.exists("plan.json"):  # also this video's next take, for the mixer
            os.makedirs("music", exist_ok=True)
            n = 1 + max([int(f[4:-4]) for f in os.listdir("music") if re.fullmatch(r"take\d+\.mp3", f)] or [0])
            shutil.copy(out, f"music/take{n}.mp3")
            t = vslib.read_json("music/takes.json"); t[f"take{n}"] = {"label": f"B yours · {name}", "secs": secs, "from": f"library/music/{name}.mp3"}
            json.dump(t, open("music/takes.json", "w"), indent=1)
            print(f"music/take{n}.mp3 (the mixer's take {n})")
        print(out); return
    elif kind == "voice":
        return voice(p, name, note)
    if to == "library":
        index_add(lib("media", "index.json") if kind != "logo" else lib("brand", "index.json"), name, entry)
        print(f"{os.path.join(os.path.relpath(out_dir, S), entry['file'])}  (a project names it \"lib:{os.path.relpath(out_dir, lib())}/{entry['file']}\")")
    else:
        index_add("media.json", name, entry)
        print(f"{os.path.join(out_dir, entry['file'])}  {entry.get('w')}×{entry.get('h')}" + (f"  {entry['secs']}s" if entry.get("secs") else "")
              + ("  (was variable frame rate: now steady)" if entry.get("was_vfr") else ""))


def voice(p, name, note):
    """Your own narration: the voice is still the clock, so it needs word timings, split into the script's acts."""
    secs = probe(p)["secs"]
    cost = round(secs / 60 * 0.006, 3)
    if not a.yes:
        sys.exit(f"Word timings for {secs:.0f}s of narration: OpenAI whisper-1, about ${cost:.3f}. Re-run with --yes once the human says yes.")
    os.makedirs("voice", exist_ok=True)
    mp3 = f"voice/narration-{name}.mp3"
    sh("ffmpeg", "-v", "error", "-y", "-i", p, "-vn", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", mp3)
    key = vslib.key("OPENAI_API_KEY")
    raw = sh("curl", "-s", "https://api.openai.com/v1/audio/transcriptions", "-H", f"Authorization: Bearer {key}", "-F", f"file=@{mp3}",
             "-F", "model=whisper-1", "-F", "response_format=verbose_json", "-F", "timestamp_granularities[]=word")
    vslib.log("openai", f"voice timings {name}", usd=cost, note="whisper-1 word timestamps")
    heard = json.loads(raw).get("words") or sys.exit(f"no word timings came back: {raw[:300]}")
    # acts: match the heard words to narration.txt (one paragraph per act); without a script, it's all act 1
    acts = [" ".join(l for l in b.splitlines() if l.strip() and not l.startswith("#")) for b in open("narration.txt").read().split("\n\n")] if os.path.exists("narration.txt") else []
    acts = [x for x in acts if x]
    norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
    script = [(norm(w), k + 1) for k, act in enumerate(acts) for w in re.sub(r"\[[^\]]*\]", " ", act).replace("...", " ").split() if norm(w)]
    act_of = [1] * len(heard)
    if script:
        sm = difflib.SequenceMatcher(None, [s for s, _ in script], [norm(w["word"]) for w in heard], autojunk=False)
        for blk in sm.get_matching_blocks():
            for i in range(blk.size): act_of[blk.b + i] = script[blk.a + i][1]
        for i in range(1, len(act_of)):  # a word the script didn't match takes the act of the word before it
            if act_of[i] < act_of[i - 1]: act_of[i] = act_of[i - 1]
    words = [{"w": w["word"], "t0": round(w["start"], 3), "t1": round(w["end"], 3), "act": act_of[i]} for i, w in enumerate(heard)]
    json.dump(words, open(f"voice/narration-{name}.words.json", "w"), indent=0)
    open(f"voice/narration-{name}.heard.txt", "w").write(" ".join(w["word"] for w in heard) + "\n")
    for n in sorted({w["act"] for w in words}):
        ws = [w for w in words if w["act"] == n]; print(f"act {n}: {ws[0]['t0']:6.2f}s – {ws[-1]['t1']:6.2f}s  ({len(ws)} words)")
    if not script: print("⚠️  no narration.txt: every word is act 1. Write the script as paragraphs (one per act) and run this again to split it.")
    print(f"{mp3} + voice/narration-{name}.words.json → vs voicebed --take {mp3} --out {name}")


for p in a.paths:
    if os.path.isdir(p):
        for f in sorted(os.listdir(p)):
            if not f.startswith("."): ingest(os.path.join(p, f))
    elif os.path.exists(p):
        ingest(p)
    else:
        print(f"⚠️  {p}: not found")
