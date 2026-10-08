#!/usr/bin/env python3
"""After the human approves a video: keep what was decided, so the next video starts there and asks less.

    vs learn --final <the final files> [--dry]      (vs finish runs it: files the finals, then this)

  finals      named in the history line; filing them is vs finish's job (finals/<video>/, then latest/<video>/)
  mix         the levels saved in the mixer (mix.json) become the profile's "mix": the next video starts at them
  music       the winning take is kept in library/music (free to reuse), and its direction moves to the front of the
              profile's music → directions, so the next bed is made in the style that won
  narrator    the voice, model and stability this video used become the profile's narrator, if it had none
  brand       a first video seeds the profile's brand (palette, fonts, finish, end card); after that, a video that broke
              from the house look is reported, never written over: the human decides whether the house look changes
  history     one line per video: what was made, what won, what it cost
  rules       never from the notes themselves: a note becomes a rule only when the human said how far it reaches
              (Review Studio's lesson cards, vs protocol review → Learning). This lists the lessons they decided that
              aren't written down yet, for vs review promote; nothing else goes into lessons.md
What a script can't judge is the agent's job, and this prints the reminder: promote those lessons, and move any scene
helper that would serve another video into library/scenes/."""
import argparse, json, os, re, shutil, sys
from datetime import date
import vslib

ap = argparse.ArgumentParser()
ap.add_argument("--final", nargs="+", required=True); ap.add_argument("--dry", action="store_true")
a = ap.parse_args()
S = vslib.studio_root() or sys.exit("⛔ no studio (vs setup): learning needs somewhere to keep it")
P_PATH = os.path.join(S, "profile.json")
prof = vslib.read_json(P_PATH)
plan, reel, mix = vslib.read_json("plan.json"), vslib.reel(), vslib.read_json("mix.json")
proj, said = vslib.project_name(), []
src = plan or reel

# the finals: vs finish filed them (finals/<video>/) before running this; learn only names them in the history
for f in a.final:
    if not os.path.exists(f): sys.exit(f"⛔ {f} not found")

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
        key = t.get("from", name).split("/")[-1].replace(".mp3", "")
        prev = idx.setdefault("items", {}).get(key) or {}
        entry = {"kind": "music", "file": (t.get("from") or name + ".mp3").split("/")[-1], "label": label, "style": style, "won": proj,
                 "id": t.get("id"), "secs": t.get("secs"), "date": date.today().isoformat()}
        # a bed another video won first keeps its first win; this video joins also_won. Re-filing a video's finals
        # keeps its date (an explainer, Oct 4, 2026: three times the bed's "won" moved to the latest video, date reset)
        if prev.get("won"):
            entry.update(won=prev["won"], date=prev.get("date", entry["date"]))
            also = list(prev.get("also_won", []))
            if prev["won"] != proj and not any(x.split(" (")[0] == proj for x in also):
                also.append(f"{proj} ({date.today().isoformat()})")
            if also:
                entry["also_won"] = also
        idx["items"][key] = entry
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
line = {"project": proj, "date": date.today().isoformat(), "finals": [os.path.basename(f) for f in a.final],
        "music_take": take, "mix": {k: mix.get(k) for k in ("music_db", "sfx_db")} if mix else None, "spend": spend}
# one line per video: re-filing its finals (a re-render) replaces its line, keeping the first date and the finals it
# replaced, so its spend is never counted twice (an explainer, Oct 4, 2026)
hist = prof.setdefault("history", [])
old = next((h for h in hist if h.get("project") == proj), None)
if old:
    line["first_date"] = old.get("first_date", old.get("date"))
    line["replaced_finals"] = old.get("replaced_finals", []) + old.get("finals", [])
    hist[hist.index(old)] = line
else:
    hist.append(line)
if not a.dry:
    json.dump(prof, open(P_PATH, "w"), indent=1)
print("\n".join(f"  {x}" for x in said) or "  nothing new to keep")
print(f"{'(dry run) ' if a.dry else ''}profile: {P_PATH}")
helpers = sorted(set(re.findall(r"^(?:function|const)\s+(ex[A-Z]\w*)", open("scenes.js").read(), re.M))) if os.path.exists("scenes.js") else []
# the rules: only the lessons the human decided (Every video / Every <kind>) and that aren't written down yet
decided = []
if os.path.exists("review/log.jsonl"):
    import review
    written = {r["mark"] for r in review.promoted()}
    decided = [l for l in review.state()["lessons"].values() if l.get("decision") in ("remember", "kind")
               and f"{proj}/{l['id']}" not in written]
for l in decided:
    print(f"  decided, not written yet: {l['id']} “{l.get('text')}” → vs review promote {l['id']}")
print("Now the agent's part: "
      + ("promote the lessons above (nothing else goes into lessons.md without the human's say)" if decided
         else "no lesson waits to be written (a note becomes a rule only through vs review propose and the human's answer)")
      + (f"; and move any of these helpers another video could use into library/scenes/: {', '.join(helpers)}" if helpers else "") + ".")
