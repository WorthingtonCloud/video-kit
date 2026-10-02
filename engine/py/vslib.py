"""Shared helpers for the engine's Python scripts: where things live, API keys, the spending ledger, the sound library.

Three places, kept apart on purpose (the same split as engine/js/lib/paths.mjs):
  the kit      this engine, read-only: code, the scene library, the bundled sounds (library/sfx), the templates
  the studio   what the user keeps between videos: profile.json, lessons.md, library/ (sounds, music, brand, media,
               scenes), finals/, ledger.csv
  a project    one video (studio/projects/<slug>); scripts run with it as the working folder. build/ is regenerated.
"""
import csv, datetime, hashlib, json, math, os, re, subprocess, sys, uuid

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(ENGINE)
BUILD, QA, MIX, MIXER = "build", "build/qa", "build/mix", "build/mixer"
TIMELINE = "build/timeline.json"
# the numbers both halves of the engine share (engine/contracts.json): safe zones, sizes, frame rates, reading time
CONTRACTS = json.load(open(os.path.join(ENGINE, "contracts.json")))
AUDIO = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".aiff", ".aif", ".ogg")


def studio_root():
    """$VIDEO_STUDIO, else the nearest folder above the working one with a studio.json, else ~/.config/video-studio."""
    if os.environ.get("VIDEO_STUDIO"):
        return os.path.abspath(os.environ["VIDEO_STUDIO"])
    d = os.getcwd()
    while True:
        if os.path.exists(os.path.join(d, "studio.json")):
            return d
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    cfg = os.path.expanduser("~/.config/video-studio/config.json")
    try:
        s = json.load(open(cfg)).get("studio")
        if s and os.path.exists(s):
            return s
    except Exception:
        pass
    return None


def deep_merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = deep_merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


def read_json(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else ({} if default is None else default)


def profile():
    """The kit's defaults overlaid with the studio's profile.json: what this user has settled on."""
    s = studio_root()
    return deep_merge(read_json(os.path.join(KIT, "templates/studio/profile.json")), read_json(os.path.join(s, "profile.json")) if s else {})


def checks():
    """The thresholds of the tunable checks: the kit's (contracts.json → reading, checks), the profile's checks over them."""
    C = {k: v for k, v in {**CONTRACTS.get("reading", {}), **CONTRACTS.get("checks", {})}.items() if k != "_about"}
    return {**C, **(profile().get("checks") or {})}


def project_name():
    return os.path.basename(os.getcwd())


def file_hash(path):
    """The same short sha256 the build stamps into build/timeline.json (engine/js/lib/paths.mjs → hash)."""
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def timing(quiet=False):
    """(T, TT, END, C) as the last build timed them (build/timeline.json): T[segment] = when it starts, TT[title] = when
    it lands, END = the video's length, C[scene][cue] = the scene's word-pinned cues. Read, never re-summed: the build
    worked it out once. With no build yet it's worked out from reel.json the build's way (timeline() below) and says so.
    If reel.json changed after the build, the build's times still win (they're the ones the picture uses), with a warning."""
    tl = read_json(TIMELINE)
    if not tl:
        R = read_json("reel.json")
        T, TT, END = timeline(R)
        if not quiet:
            print(f"(timing worked out from reel.json: no {TIMELINE} yet, vs build --no-render writes it)")
        return T, TT, END, {k: v.get("cues", {}) for k, v in R.get("scenes", {}).items()}
    if not quiet and os.path.exists("reel.json") and tl.get("reel") != file_hash("reel.json"):
        print(f"⚠️  reel.json changed since the last build: using the build's timing ({TIMELINE}); vs build --no-render updates it")
    return ({s["name"]: s["t0"] for s in tl["segments"]}, {t["id"]: t["t0"] for t in tl["titles"]}, tl["end"],
            tl.get("cues", {}))


def timeline(R):
    """The fallback for timing() before there's a build: every segment's start and every title's landing, in seconds,
    worked out the way the build does (engine/js/pipeline/timing.mjs): a segment lasts "secs", or "beats" × the music's
    beat, or (to_hit) until the music's first hit, and its title times count in the segment's own unit. Returns (T, TT,
    END). (Summing "secs" alone broke every beat-timed reel.)"""
    B, HIT = float(R["music"]["beat"]), float(R["music"].get("first_hit") or 0)
    T, TT, t = {}, {}, 0.0
    r3 = lambda x: math.floor(x * 1000 + 0.5) / 1000  # the build's rounding (JS Math.round), not Python's round()
    for s in R["segments"]:
        unit = 1 if s.get("to_hit") or s.get("secs") is not None else B
        if s.get("to_hit"):
            n = HIT - t
        elif s.get("secs") is not None:
            n = float(s["secs"])
        elif s.get("beats") is not None:
            n = float(s["beats"]) * B
        else:
            sys.exit(f"⛔ {s['name']}: no length (give it \"beats\", \"secs\" or \"to_hit\")")
        if not n > 0:
            sys.exit(f"⛔ {s['name']}: length {n:.3f}s (a to_hit segment must come before the hit)")
        T[s["name"]] = r3(t)
        for tid, a0, _ in s.get("titles", []):
            TT[tid] = r3(t + a0 * unit)
        t += n
    return T, TT, r3(t)


def word_at(words, spec, acts):
    """A word spec → (seconds, the word): "word" (first match in the given acts, case and punctuation ignored), "word#2",
    "act:word", plus "+0.3" / "-0.2" to shift. Raises ValueError when it isn't said there. (JS: js/lib/words.mjs;
    tests/contract/cases.json holds both to the same answers.)"""
    norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    m = re.fullmatch(r"(?:(\d+):)?(.+?)(?:#(\d+))?([+-]\d[\d.]*)?", str(spec).strip())
    if not m:
        raise ValueError(f"bad word spec {spec!r}")
    act, word, nth, shift = m.groups()
    pool = [w for w in words if w["act"] in ([int(act)] if act else acts)]
    hits = [w for w in pool if norm(w["w"]) == norm(word)]
    if len(hits) < int(nth or 1):
        raise ValueError(f"{spec!r}: not found in acts {[int(act)] if act else acts}")
    w = hits[int(nth or 1) - 1]
    return math.floor((w["t0"] + float(shift or 0)) * 1000 + 0.5) / 1000, w


def splice_plan(base, new, tail=0.2, lead=0.3, x=0.03, cut_at=None, start2_at=None):
    """Where a re-recorded run of acts joins an approved take (vs voicebed): the base is cut `tail` after the last word of
    the act before the run (never mid-word: the first splice clipped "generously"), the run starts `lead` before its first
    word, and a run from the middle hands back to the base `lead` before the next act. `cut_at` / `start2_at` replace the
    two base points with ones measured in the audio (vs voicebed finds the pause: word timings can run 0.2 s late, and a
    cut 0.2 s after the last word kept the start of the old act's first word, a stutter, jev-explainer, Oct 1, 2026).
    → dict of cuts and the new words."""
    first_act, last_act = min(w["act"] for w in new), max(w["act"] for w in new)
    prev, after = [w for w in base if w["act"] < first_act], [w for w in base if w["act"] > last_act]
    if not prev:
        raise ValueError(f"the base has no acts before act {first_act}")
    end_prev, first_new = max(w["t1"] for w in prev), min(w["t0"] for w in new)
    cut, start = round(cut_at if cut_at is not None else end_prev + tail, 3), round(max(0, first_new - lead), 3)
    off = round(cut - start - x, 3)
    W = prev + [{**w, "t0": round(w["t0"] + off, 3), "t1": round(w["t1"] + off, 3)} for w in new]
    out = {"first_act": first_act, "end_prev": end_prev, "first_new": first_new, "cut": cut, "start": start, "off": off}
    if after:
        cut2 = round(max(w["t1"] for w in new) + tail, 3)
        start2 = round(start2_at if start2_at is not None else min(w["t0"] for w in after) - lead, 3)
        off2 = round(off + cut2 - start2 - x, 3)
        W += [{**w, "t0": round(w["t0"] + off2, 3), "t1": round(w["t1"] + off2, 3)} for w in after]
        out.update(cut2=cut2, start2=start2, off2=off2)
    out["words"] = W
    return out


def name_cues(cues, T, TT, C):
    """Every sound effect's address, sfx/<sound>@<what it's pinned to>: cues.py hands back bare times, so the anchor is
    the nearest word cue, title or segment start (in that order on a tie); a repeat gets #2."""
    anchors = ([(t, f"{sc}.{k}") for sc, cs in C.items() for k, t in cs.items()] + [(t, k) for k, t in TT.items()]
               + [(t, k) for k, t in T.items()])
    named, used = [], {}
    for when, name, align, lvl in cues:
        at = min(anchors, key=lambda a: abs(a[0] - when))[1] if anchors else "start"
        el = f"sfx/{os.path.splitext(os.path.basename(name))[0]}@{at}"
        used[el] = used.get(el, 0) + 1
        named.append({"el": el if used[el] == 1 else f"{el}#{used[el]}", "t": round(when, 3), "sound": name,
                      "align": align, "db": lvl})
    return named


def key(name):
    """An API key (find_key), or a plain sentence and an exit when there's none."""
    return find_key(name) or sys.exit(f"{name} missing: set it in the environment, or in a .env file in this folder, any "
                                      "folder above it, or the studio")


def find_key(name):
    """An API key: the environment, else the nearest .env in this folder or any folder above it, else the studio's .env,
    else ~/.config/video-studio/.env. An empty KEY= line doesn't count. None if there's none. (JS: paths.mjs findKey.)"""
    if os.environ.get(name):
        return os.environ[name].strip()
    places, d = [], os.getcwd()
    while True:
        places.append(os.path.join(d, ".env"))
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    s = studio_root()
    places += ([os.path.join(s, ".env")] if s else []) + [os.path.expanduser("~/.config/video-studio/.env")]
    for f in places:
        if os.path.exists(f):
            for line in open(f):
                if line.startswith(name + "="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        return v
    return None


# ── the ledger: every paid call, across every video, in the studio (a project without a studio keeps its own) ──
# id + status (submitted → done | failed) came with the spend gate; a ledger from before them gains the two columns the
# first time it's written, and its old rows read as before.
LEDGER_FIELDS = ["date", "project", "vendor", "what", "credits", "usd", "kept", "note", "id", "status"]
USD_PER_CREDIT = {"kie.ai": 0.005}  # vendors that sell credits by the dollar; ElevenLabs' depend on the plan


def ledger_path():
    s = studio_root()
    return os.path.join(s, "ledger.csv") if s else "ledger.csv"


def _ledger():
    p = ledger_path()
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


def _write_ledger(rs):
    with open(ledger_path(), "w", newline="") as f:
        w = csv.DictWriter(f, LEDGER_FIELDS, extrasaction="ignore", restval="")
        w.writeheader()
        w.writerows(rs)


def log(vendor, what, credits="", usd="", note="", kept="", status="submitted"):
    """Written the moment a job is submitted: vendors bill on submit, so a crash while waiting still counts. Returns the
    row's id, for amend() / done() when the job ends."""
    p = ledger_path()
    if os.path.exists(p):
        with open(p) as f:
            head = next(csv.reader(f), [])
        if head != LEDGER_FIELDS:
            _write_ledger(_ledger())  # an older ledger gains the id and status columns
    new = not os.path.exists(p)
    rid = uuid.uuid4().hex[:8]
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, LEDGER_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"date": datetime.date.today().isoformat(), "project": project_name(), "vendor": vendor, "what": what,
                    "credits": credits, "usd": usd, "kept": kept, "note": str(note)[:160], "id": rid, "status": status})
    return rid


def amend(rid, **fields):
    """Change a row (by its id; a number is an old row index). done(rid, …) and failed(rid, …) set the status too."""
    rs = _ledger()
    hit = [r for r in rs if r.get("id") == rid] if isinstance(rid, str) else ([rs[rid]] if 0 <= rid < len(rs) else [])
    if not hit:
        return print(f"⚠️  ledger: no row {rid} to update")
    hit[0].update({k: ("" if v is None else v) for k, v in fields.items()})
    _write_ledger(rs)


def done(rid, **fields):
    amend(rid, status="done", **fields)


def failed(rid, **fields):
    amend(rid, status="failed", **fields)


def rows(project=None, vendor=None, what_prefix=None):
    out = []
    for r in _ledger():
        if project and r.get("project") != project:
            continue
        if vendor and r.get("vendor") != vendor:
            continue
        if what_prefix and not (r.get("what") or "").startswith(what_prefix):
            continue
        out.append(r)
    return out


def spent(**kw):
    """Credits logged for the matching rows (vendor credits: ElevenLabs credits, kie.ai credits)."""
    return sum(float(r["credits"] or 0) for r in rows(**kw))


def usd_of(r):
    """A row in dollars: its usd, else its credits at the vendor's price (kie.ai music was logged in credits, and the
    dollar budget never saw it: vs gen and vs music each missed the other's spend)."""
    if r.get("usd"):
        return float(r["usd"])
    return float(r.get("credits") or 0) * USD_PER_CREDIT.get(r.get("vendor"), 0)


def spent_usd(**kw):
    return sum(usd_of(r) for r in rows(**kw))


def estimate(vendor, what, *, credits=0, usd=None, cap_key=None, cap=None, scope=None):
    """What a paid step would cost and whether a cap or the budget stands in its way: the gate's numbers, nothing spent.
    → {vendor, what, credits, usd, cost (in words), so_far, limit, so_usd, budget, over_cap, over_budget}"""
    proj, sp = project_name(), profile().get("spend", {})
    usd = round(credits * USD_PER_CREDIT[vendor], 4) if usd is None and vendor in USD_PER_CREDIT else usd
    limit = cap if cap is not None else sp.get(cap_key) if cap_key else None
    so_far = spent(project=proj, vendor=vendor, what_prefix=scope) if cap_key else 0
    budget = read_json("reel.json").get("budget_usd") if os.path.exists("reel.json") else None
    budget = budget if budget is not None else sp.get("usd_per_video")
    so_usd = spent_usd(project=proj)
    dollars = "" if usd is None else "under a cent" if usd < 0.01 else f"${usd:.2f}"
    cost = " · ".join(x for x in [f"{credits:g} {vendor} credits" if credits else "", dollars] if x) or vendor
    return {"vendor": vendor, "what": what, "credits": credits, "usd": usd, "cost": cost, "cap_key": cap_key,
            "scope": scope, "so_far": so_far, "limit": limit, "so_usd": so_usd, "budget": budget,
            "over_cap": limit is not None and so_far + credits > limit,
            "over_budget": bool(usd) and budget is not None and so_usd + usd > budget}


def gate(vendor, what, *, credits=0, usd=None, yes=False, cap_key=None, cap=None, scope=None, over=False):
    """The one spend gate: every paid step calls it before it spends. It prints the estimate and what this video has
    spent so far, then refuses
      · when VIDEO_KIT_NO_SPEND is set (tests, CI: nothing paid can run)
      · past this video's credit cap for the kind of spend (profile.json → spend.<cap_key>, counted over ledger rows
        whose "what" starts with scope; --cap lifts it, only on the human's say-so)
      · past this video's dollar budget, every vendor together (reel.json → budget_usd, else spend.usd_per_video; --over)
      · without --yes: the human's go, with the number said first.
    Past the gate, the step log()s a row the moment it submits, and done()s or failed()s it when the job ends.
    VIDEO_KIT_ESTIMATE=<file> asks a step for its price only: the gate writes the estimate there and the step stops,
    spending nothing (vs review offer --paid prices a paid option this way, with the step's own numbers)."""
    E = estimate(vendor, what, credits=credits, usd=usd, cap_key=cap_key, cap=cap, scope=scope)
    if os.environ.get("VIDEO_KIT_ESTIMATE"):
        json.dump(E, open(os.environ["VIDEO_KIT_ESTIMATE"], "w"))
        sys.exit(0)
    limit, usd, budget = E["limit"], E["usd"], E["budget"]
    print(f"{what}: about {E['cost']}")
    if cap_key:
        print(f"  this video so far: {E['so_far']:g} credits on {scope or vendor} with {vendor}"
              + (f", of a {limit:g}-credit cap" if limit is not None else ""))
    if usd:
        print(f"  this video so far: ${E['so_usd']:.2f}" + (f" of a ${budget:.2f} budget" if budget is not None else ""))
    if os.environ.get("VIDEO_KIT_NO_SPEND"):
        sys.exit("⛔ VIDEO_KIT_NO_SPEND is set: no paid step runs")
    if E["over_cap"]:
        sys.exit(f"⛔ that would pass the {limit:g}-credit cap for {scope or vendor} on this video. Ask the human before "
                 "raising it (--cap).")
    if E["over_budget"] and not over:
        sys.exit("⛔ that would pass this video's dollar budget. Ask the human; re-run with --over only if they say so.")
    if not yes:
        sys.exit("Not spent. Re-run with --yes once the human has said yes to that number.")


# ── the sound library: the studio's own sounds first (bought or brought), then the kit's bundled ones ──
def sound_dirs():
    s = studio_root()
    return [d for d in ([os.path.join(s, "library/sfx")] if s else []) + [os.path.join(KIT, "library/sfx"), "sfx"] if os.path.isdir(d)]


def sound_path(name):
    """A sound by name ("bell") or by path ("media/door.wav"). None if it isn't anywhere."""
    if os.path.splitext(name)[1].lower() in AUDIO and os.path.exists(name):
        return name
    for d in sound_dirs():
        for ext in AUDIO:
            p = os.path.join(d, name + ext)
            if os.path.exists(p):
                return p
    return None


def sound_index():
    """Every sound the studio can use: {name: entry}, the studio's entries over the kit's."""
    out = {}
    for d in reversed(sound_dirs()):
        out.update(read_json(os.path.join(d, "index.json")).get("sounds", {}))
    return out


def quietest(path, a, b, win=0.04, hop=0.01, prefer="min"):
    """The middle of the quietest `win`-long stretch of a sound between a and b seconds: the pause to cut in. A splice
    trusts the audio, not the word timings, which can run 0.2 s late (jev-explainer, Oct 1, 2026). prefer="last" takes the
    last stretch within 10 dB of the quietest (the end of the pause: cutting there keeps the whole pause before it),
    "first" the first (the start of a pause: what follows keeps it)."""
    import numpy as np
    a = max(0.0, a)
    # decode from 0.1 s earlier and drop it: an mp3 decoder starts a seek with a few ms of digital silence, which would
    # always win as "the quietest"
    s0 = max(0.0, a - 0.1)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{s0:.3f}", "-t", f"{max(0.05, b - s0):.3f}", "-i", path, "-ac", "1",
                          "-ar", "48000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)[int(round((a - s0) * 48000)):]
    n, h = int(48000 * win), int(48000 * hop)
    if len(x) < n:
        return round((a + b) / 2, 3)
    e = np.array([10 * np.log10(float(np.mean(x[i:i + n] ** 2)) + 1e-12) for i in range(0, len(x) - n + 1, h)])
    quiet = np.where(e <= e.min() + 10)[0]
    i = int(quiet[-1] if prefer == "last" else quiet[0] if prefer == "first" else np.argmin(e))
    return round(a + (i * h + n / 2) / 48000, 3)


def decode(path, sr=48000, ch=1):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    return x.reshape(-1, ch).copy() if ch > 1 else x.copy()


def measure(path):
    """What a sound IS, measured: length, where it starts (attack), where it peaks, how loud it is while it sounds, and
    whether it's too quiet to use (ElevenLabs once returned two "stamps" at -55 and -49 dBFS; normalizing them up would
    have made noise as loud as a stamp)."""
    import numpy as np
    sr = 48000
    x = decode(path, sr)
    if not len(x):
        return {"secs": 0, "warning": "empty file"}
    env = np.sqrt(np.convolve(x ** 2, np.ones(480) / 480, "same"))
    m = float(env.max()) + 1e-12
    db = 20 * np.log10(env / m + 1e-9)
    active = np.where(db > -30)[0]
    act = env > m * 0.1
    out = {"secs": round(len(x) / sr, 3), "attack": round(float(np.argmax(env > m * 0.5)) / sr, 3),
           "peak": round(float(np.argmax(env)) / sr, 3),
           "sounding": [round(active[0] / sr, 3), round(active[-1] / sr, 3)] if len(active) else [0, 0],
           "rms_db": round(float(20 * np.log10(np.sqrt(np.mean(x[act] ** 2)) + 1e-9)), 1),
           "peak_dbfs": round(float(20 * np.log10(np.abs(x).max() + 1e-12)), 1)}
    if out["peak_dbfs"] < -35:
        out["warning"] = f"nearly silent (peak {out['peak_dbfs']} dBFS): listen before using it; re-make it or layer it"
    return out
