#!/usr/bin/env python3
"""The sound pass: the voice, a faint music bed, and sound effects pinned to the picture. No re-render: the new audio is
muxed onto the finished video. Effect times come from reel.json (the same word-pinned cues the scenes animate on) via
the project's cues.py, so a re-recorded voice re-times the effects too.

    vs mix --video out/<name>-vN.mp4 --tag vN [--takes 1 2 3] [--music_db -16] [--duck_db 6] [--sfx_db 0] [--no_sfx]
      → out/<name>-vN-sfx.mp4 (voice + effects), out/<name>-vN-take<N>.mp4 (voice + music + effects) for every take,
        stems in build/mix/, and the mixer page in build/mixer/ (vs mixer serves it: pick a take, set levels, Save)
    vs mix --video out/<name>-vN.mp4 --tag vN --final
      → only what the mixer saved (mix.json: the take and the levels), as out/<name>-vN-take<N>.mp4

Levels are relative to the voice, which is mastered to -16 LUFS (ElevenLabs delivered -24.6: quiet on a phone). Defaults,
in order: the flags, the project's mix.json (what the human saved in the mixer), the studio profile's "mix" (what they
settled on last time), then music ~20 dB under the voice and the effects as cues.py sets them.
A reel with no narrator (no plan.json): the reel's own track is the reference instead of a voice, and the mixer sets the
effects against it."""
import argparse, importlib.util, json, os, re, shutil, subprocess
import numpy as np
import vslib
from vslib import MIX, MIXER

SR = 48000
saved = vslib.read_json("mix.json")
house = vslib.profile().get("mix", {})
ap = argparse.ArgumentParser()
ap.add_argument("--video", required=True); ap.add_argument("--tag", required=True)
ap.add_argument("--takes", nargs="*", type=int, default=None, help="music takes to mix (default: every music/take*.mp3)")
ap.add_argument("--music_db", type=float, default=None, help="music bed vs the voice, in pauses (LU)")
ap.add_argument("--duck_db", type=float, default=None, help="extra dip under speech")
ap.add_argument("--sfx_db", type=float, default=None, help="shift every effect up or down")
ap.add_argument("--no_sfx", action="store_true")
ap.add_argument("--final", action="store_true", help="mix only what the mixer saved in mix.json")
a = ap.parse_args()
pick = lambda k, d: getattr(a, k) if getattr(a, k) is not None else saved.get(k, house.get(k, d))
MUSIC_DB, DUCK_DB, SFX_DB = pick("music_db", -16), pick("duck_db", 6), pick("sfx_db", 0)
if a.final:
    if not saved.get("take"): raise SystemExit("⛔ no mix.json yet: open the mixer (vs mixer), pick a take, press Save")
    a.takes, a.no_sfx = [saved["take"]], not saved.get("fx_on", True)

R = json.load(open("reel.json"))
END = round(sum(s["secs"] for s in R["segments"]), 3)
T, t = {}, 0.0
for s in R["segments"]:
    T[s["name"]] = t
    t += s["secs"]
TT = {tid: T[s["name"]] + a0 for s in R["segments"] for tid, a0, _ in s.get("titles", [])}
C = {k: v.get("cues", {}) for k, v in R.get("scenes", {}).items()}
END_T = T[R["segments"][-1]["name"]]  # the end card is always the last segment
NARRATED = os.path.exists("plan.json")


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def write(path, x):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", path],
                   input=np.ascontiguousarray(x, np.float32).tobytes(), check=True)


def lufs(x):
    write(f"{MIX}/_lufs.wav", x)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{MIX}/_lufs.wav", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float([l for l in out.splitlines() if l.strip().startswith("I:")][-1].split()[1])


db = lambda d: 10 ** (d / 20)
N = int(round(END * SR))
fit = lambda x: np.pad(x, ((0, max(0, N - len(x))), (0, 0)))[:N]
dbf = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
os.makedirs(MIX, exist_ok=True)

# ── the reference: the voice at -16 LUFS (a reel with no narrator: its own track, at -16 LUFS) ──
voice = fit(load(R["music"]["file"]))
v_lufs = lufs(voice)
voice *= db(-16 - v_lufs)
print(f"{'voice' if NARRATED else 'the reel’s track'} {v_lufs:.1f} → -16 LUFS")

# ── the effects: cues.py → cues(T, TT, C, END_T) returns (time, sound, align, level vs the voice in dB). A sound is a
#    library name ("bell") or a path ("media/door.wav"). align "peak" puts the sound's loudest moment on the time (a
#    whoosh into a cut); "on" puts its attack there (hits, clicks, ticks). ──
# a library sound can carry a trim ("click" came back as three clicks: keep the first); cues.py → TRIM overrides it
CUES, TRIM = [], {n: tuple(e["trim"]) for n, e in vslib.sound_index().items() if e.get("trim")}
if os.path.exists("cues.py"):
    spec = importlib.util.spec_from_file_location("cues", "cues.py"); cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)
    CUES = cm.cues(T, TT, C, END_T)
    TRIM.update(getattr(cm, "TRIM", {}))

ref = 20 * np.log10(np.sqrt(np.mean(voice[np.abs(voice).max(1) > 0.02] ** 2)) + 1e-9)  # the voice's active loudness
sfx = np.zeros((N, 2), np.float32)
cache, missing = {}, set()
for when, name, align, lvl in CUES:
    if name not in cache:
        p = vslib.sound_path(name)
        if not p:
            missing.add(name); cache[name] = None; continue
        x = load(p)
        if name in TRIM:
            a0, a1 = TRIM[name]
            x = x[int(a0 * SR):int(a1 * SR)] * np.linspace(1, 0, int((a1 - a0) * SR))[:, None] ** 0.3
        env = np.sqrt(np.convolve((x ** 2).mean(1), np.ones(240) / 240, "same"))
        act = env > env.max() * 0.1
        rms = 20 * np.log10(np.sqrt(np.mean(x[act] ** 2)) + 1e-9)
        # the peak, and the attack (where it first reaches half its peak): files start with silence of varying length
        cache[name] = (x * db(-rms), int(np.argmax(env)), int(np.argmax(env > env.max() * 0.5)))
    if cache[name] is None: continue
    x, pk, att = cache[name]
    x = x * db(ref + lvl + SFX_DB)
    if np.abs(x).max() > db(-8): x *= db(-8) / np.abs(x).max()  # no single click jumps out of the mix
    s = int(round(when * SR)) - (pk if align == "peak" else att)
    s0, x = max(0, s), x[max(0, -s):]
    x = x[:N - s0]
    sfx[s0:s0 + len(x)] += x
if missing: print(f"⚠️  not in the library, skipped: {', '.join(sorted(missing))} (vs sfx buys them; vs ingest --as sfx brings your own)")
print(f"{len(CUES)} effects placed")
if a.no_sfx: sfx[:] = 0
write(f"{MIX}/stem-voice.wav", voice); write(f"{MIX}/stem-fx.wav", sfx)


def mux(mix, out):
    write(f"{MIX}/_master.wav", mix * db(-16 - lufs(mix)))
    # a limiter at -2 dB (AAC overshoots a -1.5 limit to -0.6), AAC 192k onto the untouched picture
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-i", f"{MIX}/_master.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "alimiter=limit=0.8:attack=3:release=60:level=false", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", "-shortest", out], check=True)
    print(out)


base = re.sub(r"-v\d+$", "", os.path.splitext(os.path.basename(a.video))[0])
if not a.final: mux(voice + sfx, f"out/{base}-{a.tag}-sfx.mp4")
cfg = {"end": END, "narrated": NARRATED, "music_db": MUSIC_DB, "duck_db": DUCK_DB, "sfx_db": SFX_DB, "takes": []}

# ── the music: faint, dipping a little more under speech (slow release, so it breathes, never pumps), up ~5 dB for the
#    end card, faded to the last frame. A reel's own track is already the bed: no takes to choose. ──
names = vslib.read_json("music/takes.json")
takes = []
if NARRATED:
    takes = a.takes or (sorted(int(f[4:-4]) for f in os.listdir("music") if re.fullmatch(r"take\d+\.mp3", f)) if os.path.isdir("music") else [])
venv = np.sqrt(np.convolve((voice ** 2).mean(1), np.ones(2400) / 2400, "same"))
speaking = (venv > db(-45)).astype(np.float32)
held = np.convolve(speaking, np.ones(int(0.35 * SR)), "same") > 0
hann = np.hanning(int(0.5 * SR)); duck = np.convolve(held.astype(np.float32), hann / hann.sum(), "same")
tt = np.arange(N) / SR
gain = db(-DUCK_DB * duck)
gain = np.where(tt >= END_T, np.minimum(1, gain + (tt - END_T) / 0.6) * db(np.clip((tt - END_T) / 0.6, 0, 1) * 5), gain)
gain *= np.clip(tt / 0.4, 0, 1) * np.clip((END - tt) / 1.4, 0, 1)
spk = venv > db(-45)
for n in takes:
    m = load(f"music/take{n}.mp3")
    if len(m) < N: print(f"⚠️  take{n} is {len(m) / SR:.1f}s, shorter than the video ({END:.1f}s): extend it, or pick a longer take")
    m = fit(m) * db(-16 + MUSIC_DB - lufs(fit(m))) * gain[:, None]
    write(f"{MIX}/stem-music{n}.wav", m)
    under = round(dbf(m[spk].mean(1)) - dbf(voice[spk].mean(1)), 1)  # what the mixer shows as "N dB under the voice"
    cfg["takes"].append({"n": n, "label": (names.get(f"take{n}") or {}).get("label", f"take {n}"), "under": under})
    print(f"take{n}: music {under:+.1f} dB vs the voice under speech")
    mux(voice + m + sfx, f"out/{base}-{a.tag}-take{n}.mp4")
if not NARRATED: mux(voice + sfx, f"out/{base}-{a.tag}-mixed.mp4")
if a.final:
    print(f"final: take {saved['take']}, music {MUSIC_DB:g}, effects {SFX_DB:+g} dB" + ("" if saved.get("fx_on", True) else " (off)"))
    raise SystemExit

# ── the mixer page: every stem, compressed, plus the picture, the settings, and the page itself (vs mixer serves it) ──
os.makedirs(f"{MIXER}/media", exist_ok=True)
for s in ["voice", "fx"] + [f"music{n}" for n in takes]:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{MIX}/stem-{s}.wav", "-ar", "44100", "-c:a", "aac", "-b:a", "160k", f"{MIXER}/media/{s}.m4a"], check=True)
vid = f"{MIXER}/media/video.mp4"
if os.path.lexists(vid): os.remove(vid)
os.symlink(os.path.relpath(os.path.abspath(a.video), f"{MIXER}/media"), vid)
shutil.copy(os.path.join(vslib.ENGINE, "mixer/index.html"), f"{MIXER}/index.html")
fonts = os.path.join(vslib.studio_root() or ".", "library/brand/fonts")
if os.path.isdir(fonts):  # the page's own type, if the studio has it (else the system's)
    shutil.copytree(fonts, f"{MIXER}/fonts", dirs_exist_ok=True)
json.dump(cfg, open(f"{MIXER}/config.json", "w"), indent=1)
print(f"mixer: {MIXER}/index.html  (vs mixer serves it; Save writes mix.json, then: vs mix --video {a.video} --tag {a.tag} --final)")
