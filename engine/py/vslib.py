"""Shared helpers for the engine's Python scripts: where things live, API keys, the spending ledger, the sound library.

Three places, kept apart on purpose (the same split as engine/js/lib/paths.mjs):
  the kit      this engine, read-only: code, the scene library, the bundled sounds (library/sfx), the templates
  the studio   what the user keeps between videos: profile.json, lessons.md, library/ (sounds, music, brand, media,
               scenes), finals/, ledger.csv
  a project    one video (studio/projects/<slug>); scripts run with it as the working folder. build/ is regenerated.
"""
import csv, datetime, json, os, subprocess, sys

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(ENGINE)
BUILD, QA, MIX, MIXER = "build", "build/qa", "build/mix", "build/mixer"
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


def project_name():
    return os.path.basename(os.getcwd())


def timeline(R):
    """Every segment's start and every title's landing, in seconds, worked out the way the build does
    (engine/js/pipeline/timing.mjs): a segment lasts "secs", or "beats" × the music's beat, or (to_hit) until the
    music's first hit, and its title times count in the segment's own unit. Returns (T, TT, END): T[segment] = start,
    TT[title] = when it lands, END = the video's length. (Summing "secs" alone broke every beat-timed reel.)"""
    B, HIT = float(R["music"]["beat"]), float(R["music"].get("first_hit") or 0)
    T, TT, t = {}, {}, 0.0
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
        T[s["name"]] = t
        for tid, a0, _ in s.get("titles", []):
            TT[tid] = t + a0 * unit
        t += n
    return T, TT, round(t, 3)


def key(name):
    """An API key: the environment, else the nearest .env in this folder or any folder above it, else the studio's .env,
    else ~/.config/video-studio/.env."""
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
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(f"{name} missing: set it in the environment, or in a .env file in this folder, any folder above it, or the studio")


# ── the ledger: every paid call, across every video, in the studio (a project without a studio keeps its own) ──
LEDGER_FIELDS = ["date", "project", "vendor", "what", "credits", "usd", "kept", "note"]


def ledger_path():
    s = studio_root()
    return os.path.join(s, "ledger.csv") if s else "ledger.csv"


def log(vendor, what, credits="", usd="", note="", kept=""):
    """Written the moment a job is submitted: vendors bill on submit, so a crash while waiting still counts. Returns the
    row's index, for amend()."""
    p = ledger_path()
    new = not os.path.exists(p)
    with open(p, "a", newline="") as f:
        w = csv.DictWriter(f, LEDGER_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"date": datetime.date.today().isoformat(), "project": project_name(), "vendor": vendor, "what": what,
                    "credits": credits, "usd": usd, "kept": kept, "note": str(note)[:160]})
    return sum(1 for _ in csv.DictReader(open(p))) - 1


def amend(i, **fields):
    p = ledger_path()
    rs = list(csv.DictReader(open(p)))
    rs[i].update(fields)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, LEDGER_FIELDS)
        w.writeheader()
        w.writerows(rs)


def rows(project=None, vendor=None, what_prefix=None):
    p = ledger_path()
    if not os.path.exists(p):
        return []
    out = []
    for r in csv.DictReader(open(p)):
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


def spent_usd(**kw):
    return sum(float(r["usd"] or 0) for r in rows(**kw))


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
