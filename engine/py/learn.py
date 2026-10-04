#!/usr/bin/env python3
"""After the human approves a video: keep what was decided, so the next video starts there and asks less.

    vs learn --final out/<name>-vN-take<N>.mp4 [out/<name>-16x9-vN-take<N>.mp4 …] [--dry]

  finals      the approved files (and their covers) are copied to the studio's finals/, and latest/ is refreshed
              (vs latest: the newest version of every video under its plain name)
  mix         the levels saved in the mixer (mix.json) become the profile's "mix": the next video starts at them
  music       the winning take is kept in library/music (free to reuse), and its direction moves to the front of the
              profile's music → directions, so the next bed is made in the style that won
  narrator    the voice, model and stability this video used become the profile's narrator, if it had none
  brand       a first video seeds the profile's brand (palette, fonts, finish, end card); after that, a video that broke
              from the house look is reported, never written over: the human decides whether the house look changes
  history     one line per video: what was made, what won, what it cost
What a script can't judge is the agent's job, and this prints the reminder: turn this video's notes into rules in
lessons.md, and move any scene helper that would serve another video into library/scenes/."""
import argparse, json, os, re, shutil, sys
from datetime import date
import vslib

ap = argparse.ArgumentParser()
ap.add_argument("--final", nargs="+", required=True); ap.add_argument("--dry", action="store_true")
a = ap.parse_args()
S = vslib.studio_root() or sys.exit("⛔ no studio (vs setup): learning needs somewhere to keep it")
P_PATH = os.path.join(S, "profile.json")
prof = vslib.read_json(P_PATH)
plan, reel, mix = vslib.read_json("plan.json"), vslib.read_json("reel.json"), vslib.read_json("mix.json")
proj, said = vslib.project_name(), []
src = plan or reel

# finals
os.makedirs(os.path.join(S, "finals"), exist_ok=True)
for f in a.final:
    if not os.path.exists(f): sys.exit(f"⛔ {f} not found")
    for g in [f, re.sub(r"(-take\d+)?\.mp4$", "-cover.jpg", f)]:
        if os.path.exists(g) and not a.dry: shutil.copy2(g, os.path.join(S, "finals", os.path.basename(g)))
    said.append(f"finals/{os.path.basename(f)}")
if a.final and not a.dry:  # latest/ follows finals/ the moment a final is filed
    import subprocess
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest.py")])

# mix levels
if mix:
    m = {k: mix[k] for k in ("music_db", "duck_db", "sfx_db") if k in mix}
    if m != {k: prof.get("mix", {}).get(k) for k in m}:
        prof.setdefault("mix", {}).update(m); said.append(f"mix levels → {m}")

# the winning music take: into the library, and its direction to the front
take = mix.get("take")
takes = vslib.read_json("music/takes.json")
if take and os.path.exists(f"music/take{take}.mp3"):
    t = takes.get(f"take{take}", {})
    label = re.sub(r"^[A-Z] ", "", t.get("label", f"take {take}"))
    dirs = vslib.read_json("music.json", []) or prof.get("music", {}).get("directions", [])
    style = next((d.get("style") for d in dirs if d.get("label") and label.startswith(re.sub(r"^[A-Z] ", "", d["label"]))), t.get("style"))
    lib = os.path.join(S, "library/music")
    name = f"{proj}-take{take}"
    if not a.dry:
        os.makedirs(lib, exist_ok=True)
        if not t.get("from"): shutil.copy2(f"music/take{take}.mp3", os.path.join(lib, name + ".mp3"))
        idx = vslib.read_json(os.path.join(lib, "index.json"), {"items": {}})
        idx.setdefault("items", {})[t.get("from", name).split("/")[-1].replace(".mp3", "")] = {
            "kind": "music", "file": (t.get("from") or name + ".mp3").split("/")[-1], "label": label, "style": style, "won": proj,
            "id": t.get("id"), "secs": t.get("secs"), "date": date.today().isoformat()}
        json.dump(idx, open(os.path.join(lib, "index.json"), "w"), indent=1)
    said.append(f"music: take {take} ({label}) won → library/music")
    if style:
        md = prof.setdefault("music", {}).setdefault("directions", [])
        md[:] = [{"label": label, "style": style, "won": proj}] + [d for d in md if d.get("style") != style]

# narrator
nar = plan.get("narrator")
if nar and not prof.get("narrator", {}).get("voice"):
    prof["narrator"] = dict(nar); said.append(f"narrator → {nar.get('voice')}")

# brand: seed it from a first video; afterwards only report a departure
brand = {k: src[k] for k in ("palette", "finish") if k in src}
for k in ("font", "mono"):
    if src.get(k, {}).get("family"): brand[k] = {"family": src[k]["family"]}
end = (src.get("scene_data") or src.get("scenes") or {}).get("endcard")
if end: brand["endcard"] = {k: v for k, v in end.items() if k != "cues"}
if not prof.get("brand", {}).get("settled", True):  # the template's placeholder look: a first video sets the house look
    prof["brand"] = {**prof.get("brand", {}), **brand, "settled": True}
    said.append("the house look is settled" + (f" (from this video: {', '.join(brand)})" if brand else " (the defaults this video used)"))
else:
    diffs = [f"{k}.{kk}" for k in ("palette",) for kk in brand.get(k, {}) if brand[k][kk] != prof["brand"].get(k, {}).get(kk)]
    diffs += [k for k in ("font", "mono") if k in brand and brand[k] != {"family": prof["brand"].get(k, {}).get("family")}]
    if diffs: print(f"  this video broke from the house look in: {', '.join(diffs)} (left as is; change profile.json → brand if it should stick)")

# history
spend = {}
for r in vslib.rows(project=proj):
    v = r.get("vendor") or "?"
    spend[v] = round(spend.get(v, 0) + float(r.get("credits") or 0), 2) if r.get("credits") else spend.get(v, 0)
    if r.get("usd"): spend[v + " $"] = round(spend.get(v + " $", 0) + float(r["usd"]), 3)
prof.setdefault("history", []).append({"project": proj, "date": date.today().isoformat(), "finals": [os.path.basename(f) for f in a.final],
                                        "music_take": take, "mix": {k: mix.get(k) for k in ("music_db", "sfx_db")} if mix else None, "spend": spend})
if not a.dry:
    json.dump(prof, open(P_PATH, "w"), indent=1)
print("\n".join(f"  {x}" for x in said) or "  nothing new to keep")
print(f"{'(dry run) ' if a.dry else ''}profile: {P_PATH}")
helpers = sorted(set(re.findall(r"^(?:function|const)\s+(ex[A-Z]\w*)", open("scenes.js").read(), re.M))) if os.path.exists("scenes.js") else []
print("Now the agent's part: add this video's notes to lessons.md as rules (one line each, dated, with why)"
      + (f"; and move any of these helpers another video could use into library/scenes/: {', '.join(helpers)}" if helpers else "") + ".")
