#!/usr/bin/env python3
"""The sound pass: the voice, a faint music bed, and sound effects pinned to the picture. No re-render: the new audio is
muxed onto the finished video. Effect times come from reel.json (the same word-pinned cues the scenes animate on) via
the project's cues.py, so a re-recorded voice re-times the effects too. Every whoosh ("peak" cue) then moves to where
its motion peaks in the render being mixed (motion.py, kept in motion-sync.json; --no_sync leaves them on their cues,
--resync measures again).

    vs mix [--video drafts/vN/<video>-<shape>-vN.mp4] [--takes 1 2 3] [--music_db -16] [--duck_db 6] [--sfx_db 0]
      [--no_sfx] [--no_sync] [--resync]          (default video: the newest render of the shape being built)
      → beside the render, in its drafts/vN/: …-vN-sfx.mp4 (voice + effects), …-vN-take<N>.mp4 (voice + music +
        effects) for every take,
        stems in build/mix/, and the Mix panel's data in build/mixer/ (vs mixer opens it: pick a take, set levels, Save):
        the music un-ducked + duck.json (the envelope: the panel ducks live, so the ducking slider plays as it moves),
        and each effect once, alone, at a fixed level (cues.json says each cue's file and gain: a click plays it)
    vs mix [--video drafts/vN/<video>-<shape>-vN.mp4] --final
      → only what the mixer saved (mix.json: the take and the levels), as …-vN-take<N>.mp4 beside the render. The same
        saved mix fits the other shape's render of the same version (same voice, same times): run it on that one too.

Levels are relative to the voice, which is mastered to -16 LUFS (ElevenLabs delivered -24.6: quiet on a phone). Defaults,
in order: the flags, the project's mix.json (what the human saved in the mixer), the studio profile's "mix" (what they
settled on last time), then music ~20 dB under the voice and the effects as cues.py sets them.
A reel with no narrator (no plan.json): the reel's own track is the reference instead of a voice, and the mixer sets the
effects against it."""
import argparse, importlib.util, json, os, re, shutil, subprocess
import numpy as np
import motion, vslib
from vslib import MIX, MIXER

SR = 48000
saved = vslib.read_json("mix.json")
house = vslib.profile().get("mix", {})
ap = argparse.ArgumentParser()
ap.add_argument("--video"); ap.add_argument("--tag", help="(older projects; the version comes from the video's name)")
ap.add_argument("--takes", nargs="*", type=int, default=None, help="music takes to mix (default: every music/take*.mp3)")
ap.add_argument("--music_db", type=float, default=None, help="music bed vs the voice, in pauses (LU)")
ap.add_argument("--duck_db", type=float, default=None, help="extra dip under speech")
ap.add_argument("--sfx_db", type=float, default=None, help="shift every effect up or down")
ap.add_argument("--no_sfx", action="store_true")
ap.add_argument("--no_sync", action="store_true", help="leave every whoosh on its cue (no motion measuring)")
ap.add_argument("--resync", action="store_true", help="measure every whoosh's motion again (motion-sync.json)")
ap.add_argument("--final", action="store_true", help="mix only what the mixer saved in mix.json")
a = ap.parse_args()
if not a.video:  # the newest render of the shape being built
    renders = [p for p, d in vslib.drafts(vslib.active_shape()) if not d["variant"]]
    if not renders: raise SystemExit("⛔ nothing rendered yet: vs build renders a version")
    a.video = renders[-1]
if not vslib.parse_draft(a.video): raise SystemExit(f"⛔ {a.video}: not a draft (drafts/vN/<video>-<shape>-vN.mp4)")
a.video = vslib.render_of(a.video)  # always mixed onto the render, never onto another mix
a.tag = f"v{vslib.parse_draft(a.video)['v']}"
pick = lambda k, d: getattr(a, k) if getattr(a, k) is not None else saved.get(k, house.get(k, d))
MUSIC_DB, DUCK_DB, SFX_DB = pick("music_db", -16), pick("duck_db", 6), pick("sfx_db", 0)
if a.final:
    if "take" not in saved: raise SystemExit("⛔ no mix.json yet: open the mixer (vs mixer), pick a take, press Save")
    # take 0 = no music: a reel's own track, or the voice alone. (It used to read as "no mix.json yet", so a reel's
    # Save could never be baked.)
    a.takes, a.no_sfx = [saved["take"]] if saved["take"] else [], not saved.get("fx_on", True)

R = vslib.reel()
T, TT, END, C = vslib.timing()  # the build's own timing (build/timeline.json): "secs" and "beats" alike
END_T = list(T.values())[-1]  # the end card is always the last segment
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
M = R["music"]
if NARRATED:
    voice = fit(load(M["file"]))
else:  # a reel's own track, cut and faded the way the build cut the picture's bed (pipeline/media.mjs)
    voice = fit(load(M["file"])[int(round(float(M.get("offset") or 0) * SR)):])
    fade = float(M.get("fade", 2.2))
    if fade > 0:
        voice *= np.clip((END - np.arange(N) / SR) / fade, 0, 1)[:, None].astype(np.float32)
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

# every effect gets an address, sfx/<sound>@<the nearest word cue, title or cut> (vslib.name_cues) → build/mix/cues.json
named = vslib.name_cues(CUES, T, TT, C)

# a cue is when a move STARTS, and a move is fastest a beat later: every "peak" sound (a whoosh) moves to where its
# motion peaks in this render (motion.py; kept in motion-sync.json, so a re-mix of the same render is the same mix)
peaks = [k for k, c in enumerate(CUES) if c[2] == "peak"]
if peaks and not a.no_sync:
    shifts, why = motion.sync(a.video, [CUES[k][0] for k in peaks], again=a.resync)
    off = sum(w == "no clear motion" for w in why.values())
    moved = []
    for k in peaks:
        when, name, align, lvl = CUES[k]
        s = shifts[f"{when:.3f}"]
        if s:
            CUES[k] = (when + s, name, align, lvl)
            named[k].update(t=round(when + s, 3), moved=s)  # the address stays the cue's; the time is where it plays
            moved.append(s)
    print(f"whooshes on the motion: {len(moved)} of {len(peaks)} moved later" +
          (f" (median {np.median(moved):.2f} s, up to {max(moved):.2f})" if moved else "") +
          (f", {off} with no clear motion left on their cue" if off else "") + f" → {motion.FILE}")
    for k in peaks:
        if named[k].get("moved", 0) >= 0.2:
            print(f"   {named[k]['el']}  +{named[k]['moved']:.2f} s")

ref = 20 * np.log10(np.sqrt(np.mean(voice[np.abs(voice).max(1) > 0.02] ** 2)) + 1e-9)  # the voice's active loudness
sfx = np.zeros((N, 2), np.float32)
cache, missing = {}, set()
for k, (when, name, align, lvl) in enumerate(CUES):
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
    g = db(ref + lvl + SFX_DB)
    if np.abs(x).max() * g > db(-8): g = db(-8) / np.abs(x).max()  # no single click jumps out of the mix
    x = x * g
    # what the Review page needs to play this one alone: its sound, the gain it was mixed at, how far before its time it starts
    named[k].update(solo=name, gain_db=round(float(20 * np.log10(g)), 2), lead=round((pk if align == "peak" else att) / SR, 3))
    s = int(round(when * SR)) - (pk if align == "peak" else att)
    s0, x = max(0, s), x[max(0, -s):]
    x = x[:N - s0]
    sfx[s0:s0 + len(x)] += x
json.dump(named, open(f"{MIX}/cues.json", "w"), indent=1)
if missing: print(f"⚠️  not in the library, skipped: {', '.join(sorted(missing))} (vs sfx buys them; vs ingest --as sfx brings your own)")
print(f"{len(CUES)} effects placed")
if a.no_sfx: sfx[:] = 0
write(f"{MIX}/stem-voice.wav", voice); write(f"{MIX}/stem-fx.wav", sfx)


def mux(mix, out):
    write(f"{MIX}/_master.wav", mix * db(-16 - lufs(mix)))
    if os.path.islink(out):  # a linked take is replaced, never written through: the link may point at someone's final
        os.remove(out)
    # a limiter at -3 dB, AAC 192k onto the untouched picture: AAC overshoots the limit (-2 read -0.1 dBTP after encoding,
    # -1.5 read -0.6); -3 reads about -1.8, under qa's -1 dBTP, and the loudness moves 0.1 LU (measured on Socrates, Oct 1)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-i", f"{MIX}/_master.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "alimiter=limit=0.708:attack=3:release=60:level=false", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", "-shortest", out], check=True)
    print(out)


variant = lambda v: re.sub(r"\.mp4$", f"-{v}.mp4", a.video)  # beside the render: drafts/vN/<video>-<shape>-vN-<v>.mp4
if not a.final or (NARRATED and not saved.get("take")): mux(voice + sfx, variant("sfx"))
cfg = {"end": END, "narrated": NARRATED, "music_db": MUSIC_DB, "duck_db": DUCK_DB, "sfx_db": SFX_DB, "takes": [],
       "video": a.video, "tag": a.tag}  # which render these stems were mixed against (the Mix panel says so if it differs)

# ── the music: faint, dipping a little more under speech (slow release, so it breathes, never pumps), up ~5 dB for the
#    end card, faded to the last frame. A reel's own track is already the bed: no takes to choose. ──
names = vslib.read_json("music/takes.json")
takes = []
if NARRATED:
    takes = a.takes if a.final else a.takes or (sorted(int(f[4:-4]) for f in os.listdir("music") if re.fullmatch(r"take\d+\.mp3", f)) if os.path.isdir("music") else [])
venv = np.sqrt(np.convolve((voice ** 2).mean(1), np.ones(2400) / 2400, "same"))
speaking = (venv > db(-45)).astype(np.float32)
held = np.convolve(speaking, np.ones(int(0.35 * SR)), "same") > 0
hann = np.hanning(int(0.5 * SR)); duck = np.convolve(held.astype(np.float32), hann / hann.sum(), "same")
tt = np.arange(N) / SR
gain = db(-DUCK_DB * duck)
gain = np.where(tt >= END_T, np.minimum(1, gain + (tt - END_T) / 0.6) * db(np.clip((tt - END_T) / 0.6, 0, 1) * 5), gain)
gain *= np.clip(tt / 0.4, 0, 1) * np.clip((END - tt) / 1.4, 0, 1)
spk = venv > db(-45)
fades = np.clip(tt / 0.4, 0, 1) * np.clip((END - tt) / 1.4, 0, 1)
raw = {}  # each take before the ducking (with its fades): the Mix panel ducks it live, from the envelope
for n in takes:
    m = load(f"music/take{n}.mp3")
    if len(m) < N: print(f"⚠️  take{n} is {len(m) / SR:.1f}s, shorter than the video ({END:.1f}s): extend it, or pick a longer take")
    m = fit(m) * db(-16 + MUSIC_DB - lufs(fit(m)))
    if not a.final:
        raw[n] = m * fades[:, None]
    m = m * gain[:, None]
    write(f"{MIX}/stem-music{n}.wav", m)
    under = round(dbf(m[spk].mean(1)) - dbf(voice[spk].mean(1)), 1)  # what the mixer shows as "N dB under the voice"
    cfg["takes"].append({"n": n, "label": (names.get(f"take{n}") or {}).get("label", f"take {n}"), "under": under})
    print(f"take{n}: music {under:+.1f} dB vs the voice under speech")
    mux(voice + m + sfx, variant(f"take{n}"))
if not NARRATED: mux(voice + sfx, variant("mixed"))
if a.final:
    print(f"final: take {saved['take']}, music {MUSIC_DB:g}, effects {SFX_DB:+g} dB" + ("" if saved.get("fx_on", True) else " (off)"))
    raise SystemExit

# ── the Mix panel's data: every stem, compressed, the picture, and the settings (vs mixer opens Review Studio on it) ──
os.makedirs(f"{MIXER}/media", exist_ok=True)
aac = lambda src, out: subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ar", "44100", "-c:a", "aac", "-b:a", "160k", out], check=True)
for s in ["voice", "fx"]:
    aac(f"{MIX}/stem-{s}.wav", f"{MIXER}/media/{s}.m4a")
for n, m in raw.items():  # the music before the ducking: the panel applies it live (the duck envelope below)
    write(f"{MIX}/_raw.wav", m)
    aac(f"{MIX}/_raw.wav", f"{MIXER}/media/music{n}.m4a")
if takes:  # 100 a second is plenty: the envelope is smoothed over half a second
    json.dump({"rate": 100, "end_t": END_T, "end": END, "db": DUCK_DB,
               "env": [round(float(v), 4) for v in duck[::SR // 100]]}, open(f"{MIXER}/media/duck.json", "w"))
    cfg["duck"] = "duck.json"
# every effect once, alone, at a fixed level (the cue carries the gain it was mixed at): a click on the timeline plays it
os.makedirs(f"{MIXER}/media/sfx", exist_ok=True)
solo = {}
for c in named:
    if c.get("solo") and c["solo"] not in solo and cache.get(c["solo"]):
        f = f"sfx/{len(solo) + 1}.m4a"
        write(f"{MIX}/_solo.wav", cache[c["solo"]][0] * db(-24))  # normalized to 0 dB RMS, so -24 keeps peaks clear
        aac(f"{MIX}/_solo.wav", f"{MIXER}/media/{f}")
        solo[c["solo"]] = f
for c in named:
    if c.get("solo") in solo:
        c.update(file=solo[c["solo"]], gain_db=round(c["gain_db"] + 24, 2))
json.dump(named, open(f"{MIX}/cues.json", "w"), indent=1)
vid = f"{MIXER}/media/video.mp4"
if os.path.lexists(vid): os.remove(vid)
os.symlink(os.path.relpath(os.path.abspath(a.video), f"{MIXER}/media"), vid)
json.dump(cfg, open(f"{MIXER}/config.json", "w"), indent=1)
if os.path.exists(f"{MIX}/cues.json"):  # the version keeps the cues it was mixed with (its timeline's Sound row)
    os.makedirs(vslib.data_dir(a.video), exist_ok=True)
    shutil.copy(f"{MIX}/cues.json", os.path.join(vslib.data_dir(a.video), "cues.json"))
print(f"mixer: vs mixer opens the Mix panel (Save writes mix.json, then: vs mix --video {a.video} --final)")
