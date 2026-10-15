#!/usr/bin/env python3
"""Pack a video for a model that can't watch video (ChatGPT, Gemini, any chat model that reads images): frame strips
with each frame's time and what's happening, a sound map, the soundtrack itself and a PROMPT.md, zipped. The method
(what to caption, what PROMPT.md says) is the video-for-chatgpt skill's; this step does the measuring and the drawing.

    vs pack survey [VIDEO] [--every 1]   a frame every second on time-labeled review sheets (pack/survey/sheet-NN.jpg) to
                                         LOOK at, the soundtrack (pack/audio.mp3), its loudness every 0.1 s, the hard cuts.
                                         VIDEO: this video's newest final when left out. A kit render also starts
                                         pack/plan.json with its sections and every sound effect, from its own timeline.
    vs pack words                        every spoken or sung line and when (pack/transcript.json). Free from the kit's
                                         own word timings when the video has them (plan.json → words), else:
    vs pack words --timing FILE [--offset S]   from a word-timing file: a .words.json ([{w, t0, t1}]) or
                                         {"lines": [{t0, t1, text}]}; S = where the file's 0:00 falls in the video
    vs pack words --yes                  OpenAI whisper-1 on the soundtrack, about $0.006 a minute (OPENAI_API_KEY),
                                         through the spend gate: without --yes it says the cost and stops
    vs pack build [PLAN]                 the strips, 00-sound-map.png and soundtrack.mp3 from pack/plan.json; once
                                         PROMPT.md is in the out folder, the zip beside it

The out folder: plan.json → "out", else profile.json → pack.out (a folder; the pack is <it>/<video>-for-review), else
pack/<video>-for-review. --work DIR keeps the working files somewhere other than pack/ (a video from outside the kit).
Why every frame is an exact seek (ffmpeg -ss t -i VIDEO -frames:v 1), on the sheets and in the strips alike: a sheet
made with the fps filter showed each frame about 0.5 s after the time under it (Oct 2026), so a moment picked off a
sheet landed half a second late in the strips. Frames are cached by the video's size and modified time, so a
re-rendered video is never drawn from an old one's frames. Whisper flattens dialect and mishears names: a timing file
the video was built from is exact, and free."""
import json, os, re, shutil, subprocess, sys
from array import array
from concurrent.futures import ThreadPoolExecutor
from math import log10
import vslib

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("⛔ vs pack draws with Pillow, and the engine's Python hasn't got it: run vs setup again (it adds it)")

A = sys.argv[1:]
opt = lambda name, default=None: A[A.index(name) + 1] if name in A and A.index(name) + 1 < len(A) else default
TAKES = {"--every", "--work", "--timing", "--offset"}
POS = [a for i, a in enumerate(A) if not a.startswith("--") and (i == 0 or A[i - 1] not in TAKES)]
MOVE, ARG = (POS + [None, None])[:2]
WORK = os.path.abspath(os.path.expanduser(opt("--work", "pack")))
ab = lambda p, base=".": os.path.abspath(os.path.join(base, os.path.expanduser(p)))

# ── drawing: the machine's own sans and mono (a Mac's, Linux's, Windows'), else Pillow's built-in ──
FONTS = {"sans": [("/System/Library/Fonts/HelveticaNeue.ttc", 0), ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
                  ("C:/Windows/Fonts/arial.ttf", 0)],
         "bold": [("/System/Library/Fonts/HelveticaNeue.ttc", 1), ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
                  ("C:/Windows/Fonts/arialbd.ttf", 0)],
         "mono": [("/System/Library/Fonts/Menlo.ttc", 0), ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 0),
                  ("C:/Windows/Fonts/consola.ttf", 0)]}
GLYPHS = {"→": "->", "←": "<-", "↑": "up", "↓": "down", "▲": "up", "▼": "down"}  # Helvetica Neue prints these as boxes
_fonts = {}


def font(kind, size):
    if (kind, size) not in _fonts:
        hit = next(((p, i) for p, i in FONTS[kind] if os.path.exists(p)), None)
        _fonts[kind, size] = ImageFont.truetype(hit[0], size, index=hit[1]) if hit else ImageFont.load_default(size)
    return _fonts[kind, size]


def wrap(d, text, f, width):
    lines, cur = [], ""
    for g, r in GLYPHS.items():
        text = text.replace(g, r)
    for word in text.split():
        nxt = (cur + " " + word).strip()
        if d.textlength(nxt, font=f) <= width: cur = nxt
        else: lines.append(cur); cur = word
    return lines + ([cur] if cur else [])


# ── the video ──
def probe(src):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                                   "-of", "json", src], capture_output=True, text=True).stdout or "{}")
    if "format" not in j: sys.exit(f"⛔ {src}: not a video ffprobe can read")
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None) or sys.exit(f"⛔ {src}: no picture in it")
    return {"duration": float(j["format"]["duration"]), "size": [v["width"], v["height"]],
            "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


_durations = {}


def frame(src, t, fw):
    """The frame at t seconds, fw wide: an exact seek, the same call for the sheets and the strips. None past the end."""
    st = os.stat(src)
    f = os.path.join(WORK, "frames", f"{os.path.basename(src)}-{st.st_size}-{int(st.st_mtime)}-{t:.2f}-{fw}.jpg")
    if t >= _durations.setdefault(src, probe(src)["duration"]) - 0.02:
        return None  # ffmpeg fails outright on a seek past the end, and comes back empty in the last frame's sliver
    if not os.path.exists(f):
        os.makedirs(os.path.dirname(f), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
                        "-vf", f"scale={fw}:-2:flags=lanczos", "-q:v", "2", f], check=True)
    return f if os.path.exists(f) else None


def newest_final():
    """This video's newest final (the shape being built first), from the studio's finals/<video>/."""
    s, video = vslib.studio_root(), vslib.video_name()
    d = s and os.path.join(s, "finals", video)
    have = [(p["v"], p["shape"], os.path.join(d, f)) for f in (os.listdir(d) if d and os.path.isdir(d) else [])
            if (p := vslib.parse_draft(f)) and p["video"] == video and not p["variant"]]
    shape = vslib.active_shape()
    have.sort(key=lambda x: (x[1] == shape, x[0]))
    return have[-1][2] if have else sys.exit("⛔ which video? vs pack survey <file> (this video has no final yet)")


def kit_data(src):
    """A kit render's own files (drafts/vN/data/<shape>/, in this project), or None for any other video."""
    p = vslib.parse_draft(src)
    d = p and os.path.join("drafts", f"v{p['v']}", "data", p["shape"])
    return d if d and os.path.isdir(d) else None


# ── vs pack survey ──
def survey():
    V = ab(ARG) if ARG else newest_final()
    if not os.path.isfile(V): sys.exit(f"⛔ no video at {V}")
    P, every = probe(V), float(opt("--every", 1.0))
    tall = P["size"][1] > P["size"][0]
    S = os.path.join(WORK, "survey"); os.makedirs(S, exist_ok=True)
    for f in os.listdir(S):
        if re.fullmatch(r"sheet-\d+\.jpg", f): os.remove(os.path.join(S, f))  # a shorter re-survey leaves no stale sheet
    fw, cols, rows = (240, 8, 3) if tall else (300, 6, 5)  # a sheet stays under ~2000 px wide: 1974 tall, 1842 wide
    times = [round(k * every, 3) for k in range(int(P["duration"] / every) + 1) if k * every < P["duration"] - 0.02]
    with ThreadPoolExecutor(8) as pool:
        frames = [(t, f) for t, f in zip(times, pool.map(lambda t: frame(V, t, fw), times)) if f]
    per, lab = cols * rows, font("bold", 18)
    for k in range(0, len(frames), per):
        batch = frames[k:k + per]
        cw, ch = Image.open(batch[0][1]).size
        sheet = Image.new("RGB", (cols * (cw + 6) + 6, rows * (ch + 30) + 6), "white"); d = ImageDraw.Draw(sheet)
        for i, (t, f) in enumerate(batch):
            x, y = 6 + (i % cols) * (cw + 6), 6 + (i // cols) * (ch + 30)
            sheet.paste(Image.open(f), (x, y)); d.text((x, y + ch + 4), f"{t:.1f}s", fill="black", font=lab)
        sheet.save(os.path.join(S, f"sheet-{k // per + 1:02d}.jpg"), quality=85)
    # hard cuts: often none on footage from one set or one drawn stage; the timeline's sections are the better map
    o = subprocess.run(["ffmpeg", "-hide_banner", "-i", V, "-vf", "select='gt(scene,0.3)',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    cuts = [round(float(l.split("pts_time:")[1].split()[0]), 2) for l in o.splitlines() if "pts_time:" in l]
    json.dump(cuts, open(os.path.join(S, "cuts.json"), "w"))
    if P["audio"]:  # the soundtrack, and its loudness every 0.1 s: RMS of the whole mix in dBFS, floor -90
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", V, "-vn", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k",
                        os.path.join(WORK, "audio.mp3")], check=True)
        pcm = array("h", subprocess.run(["ffmpeg", "-v", "error", "-i", V, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                                        capture_output=True, check=True).stdout)
        db = []
        for k in range(0, len(pcm), 800):  # 800 samples at 8 kHz = 0.1 s
            win = pcm[k:k + 800]
            rms = (sum(v * v for v in win) / len(win)) ** 0.5 / 32768
            db.append(round(max(20 * log10(rms), -90.0), 1) if rms > 0 else -90.0)
        json.dump({"step": 0.1, "db": db}, open(os.path.join(WORK, "loudness.json"), "w"))
    info = {"video": V, **P, "tall": tall, "every": every, "frames": len(frames), "sheets": -(-len(frames) // per), "cuts": cuts}
    json.dump(info, open(os.path.join(WORK, "survey.json"), "w"), indent=1)
    started = starter_plan(V)
    print(f"{info['sheets']} sheets, a frame every {every:g} s ({len(frames)}): {S}/sheet-NN.jpg  ← look at every one")
    print(f"  soundtrack {'pack/audio.mp3 + loudness.json' if P['audio'] else 'none (no audio in the video)'} · "
          f"{len(cuts)} hard cuts · {P['duration']:.1f} s, {P['size'][0]}x{P['size'][1]}")
    print(f"  {started}" if started else f"  plan: {os.path.join(WORK, 'plan.json')} is yours (kept as it is)")


def starter_plan(V):
    """pack/plan.json with what the kit already knows, if there's no plan yet: the render's sections (its timeline's
    segments) and every sound effect (its mix cues). The agent adds the strips, the music and every effect's meaning."""
    f = os.path.join(WORK, "plan.json")
    if os.path.exists(f): return None
    plan = {"video": V, "strips": [], "sound": {"sections": [], "music": [], "sfx": []}}
    d, note = kit_data(V), ""
    if d:
        tl = vslib.read_json(os.path.join(d, "timeline.json"), {})
        plan["sound"]["sections"] = [{"name": re.sub(r"^s\d+_", "", s["name"]), "t0": s["t0"], "t1": s["t1"]}
                                     for s in tl.get("segments", [])]
        p, s = vslib.parse_draft(V), vslib.studio_root()
        # a render keeps the cues it was mixed with (vs mix, since 3.4); an older one's are the project's latest mix,
        # and only when nothing newer has been rendered since
        cf = os.path.join(d, "cues.json")
        if not os.path.exists(cf) and p["v"] == vslib.last_version() and os.path.exists("build/mix/cues.json"):
            cf, note = "build/mix/cues.json", " (from the project's latest mix: this render kept no cues of its own, check them)"
        cues = vslib.read_json(cf, [])
        plan["sound"]["sfx"] = [{"t": c["t"], "name": c["sound"], "what": "at " + re.sub(r"^s\d+_", "", c["el"].split("@")[-1])}
                                for c in cues if isinstance(c, dict) and "t" in c and "sound" in c]
        other = os.path.join(s or "", "finals", p["video"])
        sib = sorted((q["v"], os.path.join(other, g)) for g in (os.listdir(other) if s and os.path.isdir(other) else [])
                     if (q := vslib.parse_draft(g)) and q["shape"] != p["shape"] and not q["variant"])
        if sib: plan["videos"] = {vslib.other_shape(p["shape"]): sib[-1][1]}
    json.dump(plan, open(f, "w"), indent=1)
    got = f"{len(plan['sound']['sections'])} sections and {len(plan['sound']['sfx'])} sound effects from the render's timeline{note}"
    known = d and (plan["sound"]["sections"] or plan["sound"]["sfx"])
    return f"plan: {f} started ({got if known else 'no kit timeline for this video: sections and effects are yours to add'})"


# ── vs pack words ──
def lines_of(words):
    """A flat word list ([{w, t0, t1, act?}]) → lines: a new one after . ? or !, a 0.7 s gap, a new act, or 14 words."""
    out, cur = [], []
    for x in words:
        if cur and (re.search(r"[.?!][\"')\]”’]*$", cur[-1]["w"]) or x["t0"] - cur[-1]["t1"] > 0.7
                    or x.get("act") != cur[-1].get("act") or len(cur) >= 14):
            out.append(cur); cur = []
        cur.append(x)
    return [{"t0": c[0]["t0"], "t1": c[-1]["t1"], "text": " ".join(w["w"] for w in c)} for c in out + ([cur] if cur else [])]


def from_timing(path, off):
    j = json.load(open(path))
    flat = j if isinstance(j, list) else j.get("words") if isinstance(j.get("words"), list) else None
    lines = lines_of(flat) if flat is not None else j.get("lines") or sys.exit(f"⛔ {path}: no words or lines in it")
    words = flat if flat is not None else [x for l in lines for x in l.get("words", [])]
    segs = [{"start": round(l["t0"] + off, 2), "end": round(l["t1"] + off, 2), "text": l["text"].strip()} for l in lines]
    return segs, [{"w": x["w"], "t": round(x["t0"] + off, 2)} for x in words]


def kit_words():
    """The word timings this video was built from: its render's plan.json → words (the snapshot), else the project's."""
    sv = vslib.read_json(os.path.join(WORK, "survey.json"), {})
    d = sv.get("video") and kit_data(sv["video"])
    for plan in ([os.path.join(d, "source", "plan.json")] if d else []) + ["plan.json"]:
        w = vslib.read_json(plan, {}).get("words")
        if w and os.path.isfile(w): return w
    return None


def words():
    out = os.path.join(WORK, "transcript.json")
    src = opt("--timing") or (None if "--yes" in A else kit_words())
    if src:
        segs, ws = from_timing(ab(src), float(opt("--offset", 0)))
        how = f"from {src} (free)"
    else:
        audio = os.path.join(WORK, "audio.mp3")
        if not os.path.exists(audio): sys.exit("⛔ no pack/audio.mp3: vs pack survey first")
        mono = os.path.join(WORK, ".speech.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", audio, "-ac", "1", "-ar", "16000", "-b:a", "48k", mono], check=True)
        secs = probe_secs(mono)
        usd = round(secs / 60 * 0.006, 4)
        vslib.gate("openai", f"Transcribing {secs:.0f} s of soundtrack (whisper-1)", usd=usd, yes="--yes" in A)
        row = vslib.log("openai", "pack words", usd=usd, note=f"whisper-1, word times, {secs:.0f} s")
        d = json.loads(vslib.transcribe(mono, ["model=whisper-1", "response_format=verbose_json",
                                               "timestamp_granularities[]=segment", "timestamp_granularities[]=word"], row))
        vslib.done(row); os.remove(mono)
        segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
                for s in d.get("segments", []) if s["text"].strip()]  # whisper pads a cut-off ending with empty segments
        ws = [{"w": x["word"], "t": round(x["start"], 2)} for x in d.get("words", [])]
        for s in segs:  # whisper often stretches a line's start back over the music: snap it to its first word
            first = next((x for x in ws if s["start"] - 0.05 <= x["t"] < s["end"]), None)
            if first: s["start"] = first["t"]
        how = "by whisper-1: check it against the script and keep the script's spelling"
    os.makedirs(WORK, exist_ok=True)
    json.dump({"segments": segs, "words": ws}, open(out, "w"), indent=1)
    for s in segs: print(f"{s['start']:7.2f}–{s['end']:7.2f}  {s['text']}")
    print(f"{len(segs)} lines {how} → {out}")


def probe_secs(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True).stdout)


# ── vs pack build ──
def build():
    global WORK
    pf = ab(ARG) if ARG else os.path.join(WORK, "plan.json")
    if not os.path.exists(pf): sys.exit(f"⛔ no plan at {pf}: vs pack survey starts one")
    P, base = json.load(open(pf)), os.path.dirname(pf)
    work = WORK = ab(P["work"], base) if P.get("work") else base
    sv = vslib.read_json(os.path.join(work, "survey.json"), {})
    V = ab(P["video"], base) if P.get("video") else sv.get("video") or sys.exit("⛔ the plan names no video (\"video\")")
    name = P.get("name") or (vslib.parse_draft(V) or {}).get("video") or os.path.splitext(os.path.basename(V))[0]
    pack_dir = (vslib.profile().get("pack") or {}).get("out")
    OUT = ab(P["out"], base) if P.get("out") else os.path.join(ab(pack_dir) if pack_dir else work, f"{name}-for-review")
    VIDS = {"main": V, **{k: ab(v, base) for k, v in P.get("videos", {}).items()}}
    os.makedirs(OUT, exist_ok=True)
    scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    dur = probe_secs(V)
    # 1 · the strips: a title, what happens and how it moves, then the frames with time + caption under each
    for i, s in enumerate(P.get("strips", []), 1):
        src = VIDS[s.get("src", "main")]
        sz = probe(src)["size"]
        fw = s.get("frame_w", 300 if sz[1] > sz[0] else P.get("frame_w", 640)); cols, gap, pad = s["cols"], 14, 22
        W = cols * fw + (cols - 1) * gap + 2 * pad
        head = wrap(scratch, f"{i:02d} · {s['title']}", font("bold", 26), W - 2 * pad)
        note = wrap(scratch, s.get("note", ""), font("sans", 18), W - 2 * pad)
        cells, labels = [], s.get("labels", {})
        for t in s["t"]:
            f = frame(src, t, fw)
            if not f: print(f"⚠️  {s['slug']}: {t} s is past the end of {os.path.basename(src)}, left out"); continue
            lab = labels.get(f"{t}") or labels.get(f"{t:.1f}")
            cells.append((Image.open(f).convert("RGB"), wrap(scratch, f"{t:.2f}s" + (f" · {lab}" if lab else ""), font("sans", 16), fw)))
        rows = [cells[k:k + cols] for k in range(0, len(cells), cols)]
        rh = [max(c[0].height for c in r) + 8 + 20 * max(len(c[1]) for c in r) + gap for r in rows]
        img = Image.new("RGB", (W, pad + 34 * len(head) + 24 * len(note) + 14 + sum(rh) + pad), "white")
        d, y = ImageDraw.Draw(img), pad
        for l in head: d.text((pad, y), l, fill="#111", font=font("bold", 26)); y += 34
        for l in note: d.text((pad, y), l, fill="#333", font=font("sans", 18)); y += 24
        y += 14
        for r, h in zip(rows, rh):
            for k, (im, cap) in enumerate(r):
                x = pad + k * (fw + gap); img.paste(im, (x, y)); d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline="#bbb")
                for j, l in enumerate(cap):
                    d.text((x, y + im.height + 6 + 20 * j), l, fill="#111" if j == 0 else "#333", font=font("bold" if j == 0 else "sans", 16))
            y += h
        fn = f"{i:02d}-{s['slug']}.jpg"; img.save(os.path.join(OUT, fn), quality=88); print(fn, img.size)
    # 2 · the sound map: the whole soundtrack against the clock: sections, every spoken line, the music, every effect,
    #     and how loud the mix is moment to moment
    S = P.get("sound")
    if S:
        tf, lf = os.path.join(work, "transcript.json"), os.path.join(work, "loudness.json")
        tx = json.load(open(tf))["segments"] if os.path.exists(tf) else []
        ld = json.load(open(lf)) if os.path.exists(lf) else None
        W, L, R = 2000, 150, 30; X = lambda t: L + (W - L - R) * t / dur
        sfx = sorted(S.get("sfx", []), key=lambda e: e["t"])
        lanes = [("Sections", 46), ("Voice", 118), ("Music", 46), ("Effects", 40 + 22 * 4), ("Loudness", 120)]
        img = Image.new("RGB", (W, 90 + sum(h + 18 for _, h in lanes) + 40), "white"); d = ImageDraw.Draw(img)
        d.text((24, 22), "Sound map: the whole soundtrack against the clock (left to right = 0 to the end)", fill="#111", font=font("bold", 26))
        y = top = 80
        for lane, h in lanes:
            d.text((24, y + 4), lane, fill="#111", font=font("bold", 18)); d.line([L, y + h + 8, W - R, y + h + 8], fill="#ddd")
            if lane == "Sections":
                for k, s in enumerate(S.get("sections", [])):
                    d.rectangle([X(s["t0"]), y, X(s["t1"]) - 2, y + h], fill=["#e8e8e8", "#d4d4d4"][k % 2])
                    for j, l in enumerate(wrap(d, s["name"], font("sans", 14), X(s["t1"]) - X(s["t0"]) - 6)[:2]):
                        d.text((X(s["t0"]) + 3, y + 4 + 17 * j), l, fill="#111", font=font("sans", 14))
            if lane == "Voice":
                for k, s in enumerate(tx):
                    d.rectangle([X(s["start"]), y + 4 + 38 * (k % 3), max(X(s["end"]), X(s["start"]) + 3), y + 30 + 38 * (k % 3)], fill="#3b6fd8")
                    d.text((X(s["start"]) + 2, y + 30 + 38 * (k % 3)), " ".join(s["text"].split()[:3]), fill="#3b6fd8", font=font("sans", 11))
            if lane == "Music":
                for m in S.get("music", []):
                    d.rectangle([X(m["t0"]), y + 6, X(m["t1"]), y + h - 6], fill="#e7a33c")
                    d.text((X(m["t0"]) + 6, y + 14), m["label"], fill="#111", font=font("bold", 15))
            if lane == "Effects":
                for k, e in enumerate(sfx):
                    x, row = X(e["t"]), k % 4
                    d.line([x, y, x, y + 26 + 22 * row], fill="#d23b3b", width=2)
                    d.text((x + 3, y + 12 + 22 * row), e["name"], fill="#d23b3b", font=font("bold", 13))
            if lane == "Loudness" and ld:
                pts = [(X(k * ld["step"]), y + h - (max(v, -60) + 60) / 60 * h) for k, v in enumerate(ld["db"]) if k * ld["step"] <= dur]
                d.line(pts, fill="#222", width=1)
                for db in (-10, -30, -50): d.text((L - 46, y + h - (db + 60) / 60 * h - 8), f"{db}dB", fill="#999", font=font("sans", 11))
            y += h + 18
        for t in range(0, int(dur) + 1, 10):
            d.line([X(t), top - 6, X(t), y - 10], fill="#eee"); d.text((X(t) - 10, y), f"{t // 60}:{t % 60:02d}", fill="#555", font=font("mono", 15))
        img.save(os.path.join(OUT, "00-sound-map.png")); print("00-sound-map.png", img.size)
    # 3 · the soundtrack itself, then (once PROMPT.md is written) the zip
    if os.path.exists(os.path.join(work, "audio.mp3")): shutil.copy(os.path.join(work, "audio.mp3"), os.path.join(OUT, "soundtrack.mp3"))
    if not os.path.exists(os.path.join(OUT, "PROMPT.md")):
        sys.exit(f"→ {OUT}\nLook at every strip and the sound map, then write PROMPT.md there and run vs pack build again to zip.")
    z = shutil.make_archive(OUT, "zip", os.path.dirname(OUT), os.path.basename(OUT))
    print(z, round(os.path.getsize(z) / 1e6, 1), "MB")


if __name__ == "__main__":
    {"survey": survey, "words": words, "build": build}.get(MOVE, lambda: sys.exit(
        "vs pack survey [VIDEO] · vs pack words [--timing FILE | --yes] · vs pack build   (vs help pack)"))()
