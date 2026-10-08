#!/usr/bin/env python3
"""Where a video stands, and the four moves that carry it from first draft to final and back (engine/protocol/files.md).

    vs status                         where this video stands, and the one next step
    vs shape <vertical|widescreen> [--early "<why>"]
                                      build the other shape: refused until the first shape is approved (--early: a real
                                      pivot, logged). An explainer is re-planned for it on the spot (vs plan).
    vs finish [--final <files>] [--one-shape] [--dry]
                                      the human approved every shape: file the finals into finals/<video>/, refresh
                                      latest/<video>/, make each final's web copy (small enough to upload; it replaces
                                      the one in latest/), close the review (the page says Done) and keep what was
                                      learned (vs learn). The files default to what the approved round showed, each shape's mix
                                      when there is one. --one-shape: a video made in one shape only.
    vs reopen [<video>] [--shape <s>]
                                      a finished video drafts again: the sources go back to exactly what made its last
                                      final (anything changed since is set aside in drafts/reopened-<when>/ first), the
                                      version becomes last + 1, and the shape it started in is the one being built.

video.json holds where it stands: status first (drafting the first shape) → second (the other shape, once the first is
approved) → done (filed). Only these commands and vs build write it. Nothing here deletes anything."""
import argparse, filecmp, hashlib, json, os, shutil, subprocess, sys
from datetime import datetime
import vslib
import latest

PY = os.path.dirname(os.path.abspath(__file__))


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def state():
    V = vslib.video_state()
    if not V:
        sys.exit(f"⛔ {vslib.video_name()} has no video.json yet: vs new makes one (or the first vs build does)")
    return V


def save(V, event, **extra):
    V.setdefault("log", []).append({"at": now(), "event": event, **{k: v for k, v in extra.items() if v}})
    vslib.save_video_state(V)


def review_mod():
    import review
    return review


def approved(shape):
    """The newest approved render of a shape (its file, from the round the human approved it in), or None."""
    if not os.path.exists("review/log.jsonl"):
        return None
    return review_mod().approved_video(vslib.SHAPES[shape])


def newest(shape, renders_only=True):
    d = [(p, x) for p, x in vslib.drafts(shape) if not (renders_only and x["variant"])]
    return d[-1] if d else (None, None)


def sh(*cmd):
    return subprocess.run([sys.executable, *cmd]).returncode


# ── vs status ──
def status(_a):
    V, name = vslib.video_state(), vslib.video_name()
    if not V:
        print(f"{name}: no video.json yet")
        print(f"  next: vs build renders the first draft and starts the video in the {vslib.active_shape()} shape")
        return
    first, other = V["first"], vslib.other_shape(V["first"])
    words = {"first": f"drafting the first shape ({first})", "second": f"the {first} is approved; building the {other}",
             "done": "finished"}
    print(f"{name} · {words[V['status']]}" + (f" · building {V['building']}" if V["status"] != "done" else ""))
    for shape in (first, other) if V["status"] != "done" else ():
        p, x = newest(shape, renders_only=False)
        ap = approved(shape)
        if p:
            print(f"  {shape:10s} newest draft v{x['v']}" + (f" · approved v{vslib.parse_draft(ap)['v']}" if ap else " · not approved yet"))
        elif not V.get("one_shape") or shape == first:
            print(f"  {shape:10s} no drafts yet")
    if V.get("finals"):
        f = V["finals"][-1]
        print(f"  last final #{f['n']} ({f['at'][:10]}): " + ", ".join(f"{s} v{x['version']}" for s, x in sorted(f["files"].items(), key=lambda i: i[0] != first))
              + f" · in latest/{name}/")
    print(f"  next: {next_step(V)}")


def next_step(V):
    first, building = V["first"], V["building"]
    if V["status"] == "done":
        return f"nothing: it's finished. A change starts a new version: vs reopen {V['video']}"
    p, x = newest(building)
    if not p:
        return ("vs plan, then " if os.path.exists("plan.json") else "") + f"vs build (the first {building} draft)"
    ap = approved(building)
    if V["status"] == "first":
        if ap and vslib.parse_draft(ap)["v"] >= x["v"]:
            return f"vs shape {vslib.other_shape(first)} (the {first} is approved), or vs finish --one-shape"
        return f"review v{x['v']}: vs review open, then vs review wait (the human approves or sends notes)"
    ready, checks, _ = review_mod().exit_state() if os.path.exists("review/log.jsonl") else (False, [], 0)
    if ready:
        return "vs finish (every shape in the round is approved)"
    return f"review: vs review open on the {building} v{x['v']}; the page shows both shapes (the switch at the top)"


# ── vs shape ──
def shape(a):
    V, target = state(), a.shape
    if V["status"] == "done":
        sys.exit(f"⛔ {V['video']} is finished: vs reopen {V['video']} first")
    if target == V["building"]:
        return print(f"already building the {target}")
    if V["status"] == "first" and target != V["first"]:
        p, x = newest(V["first"])
        ap = approved(V["first"])
        ok = ap and p and vslib.parse_draft(ap)["v"] >= x["v"]
        if not ok and not a.early:
            sys.exit(f"⛔ the {V['first']} isn't approved yet" + (f" (newest draft v{x['v']})" if p else " (no drafts yet)")
                     + f": the {target} is made from the approved {V['first']}. A real pivot: --early \"<why>\"")
        V["status"] = "second"
    V["building"] = target
    save(V, f"building the {target}", why=a.early)
    print(f"{V['video']}: now building the {target}" + (f" (early: {a.early})" if a.early else ""))
    if os.path.exists("plan.json"):  # an explainer's reel.json is planned per shape
        sh(os.path.join(PY, "plan.py"))
    print(f"  next: {next_step(V)}")


# ── vs finish ──
def pick_final(video):
    """The file to file for a shape: what the human approved when it was a mix; for a bare render, its saved mix
    (mix.json take), else its -mixed, else the render."""
    if vslib.parse_draft(video)["variant"]:
        return video
    render = vslib.render_of(video)
    take = vslib.read_json("mix.json").get("take")
    for v in ([f"take{take}"] if take else []) + ["mixed"]:
        p = render[:-4] + f"-{v}.mp4"
        if os.path.exists(p):
            return p
    return video if os.path.exists(video) else render


def digest(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def file_into(src, dst, dry):
    """Copy src to dst; the same bytes already there is fine, different bytes is refused (finals are never overwritten)."""
    if os.path.exists(dst):
        if os.path.getsize(dst) == os.path.getsize(src) and digest(dst) == digest(src):
            return "already filed"
        sys.exit(f"⛔ {dst} exists with different contents: finals are never overwritten (a kit bug: report it)")
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if subprocess.run(["cp", "-c", "-p", src, dst + ".part"], capture_output=True).returncode != 0:
            shutil.copy2(src, dst + ".part")
        os.replace(dst + ".part", dst)
    return "filed"


def finish(a):
    V, S = state(), vslib.studio_root() or sys.exit("⛔ no studio (vs setup): finals live in one")
    if V["status"] == "done":
        sys.exit(f"⛔ {V['video']} is already finished (final #{V['finals'][-1]['n']}). A change: vs reopen {V['video']}")
    R = review_mod()
    ready, checks, _ = R.exit_state()
    if not ready:
        sys.exit("⛔ not approved yet: " + "; ".join(t for _, ok, t in checks if not ok))
    files = a.final or [pick_final(v) for v in
                        [R.approved_video(vslib.SHAPES[s]) for s in ([V["first"]] if (a.one_shape or V.get("one_shape"))
                                                                    else [V["first"], vslib.other_shape(V["first"])])]
                        if v]
    have = {vslib.parse_draft(f)["shape"]: f for f in files if vslib.parse_draft(f)}
    if len(have) < len(files):
        sys.exit("⛔ every final must be a draft of this video (drafts/vN/<video>-<shape>-vN….mp4)")
    need = [V["first"]] if (a.one_shape or V.get("one_shape")) else ["vertical", "widescreen"]
    missing = [s for s in need if s not in have]
    if missing:
        sys.exit(f"⛔ no approved {' or '.join(missing)} to file: vs shape {missing[0]} makes it; a video made in one "
                 "shape only: vs finish --one-shape")
    rec, said = {}, []
    for s, f in sorted(have.items()):
        d = vslib.parse_draft(f)
        W, H = vslib.probe_size(f)
        if vslib.shape_of(W, H) != s:
            sys.exit(f"⛔ {f} is named {s} but its picture is {W}×{H} ({vslib.shape_of(W, H)}): rebuild it, never rename it")
        if d["video"] != V["video"]:
            sys.exit(f"⛔ {f} is a draft of {d['video']}, not {V['video']}")
        dst = vslib.final_file(S, V["video"], s, d["v"])
        said.append(f"{file_into(f, dst, a.dry)}: {os.path.relpath(dst, S)}")
        cov = vslib.cover_of(f)
        if os.path.exists(cov):
            file_into(cov, vslib.final_file(S, V["video"], s, d["v"], cover=True), a.dry)
        rec[s] = {"version": d["v"], "draft": f, "final": os.path.relpath(dst, S),
                  "latest": os.path.relpath(vslib.latest_file(S, V["video"], s), S),
                  "web": os.path.relpath(vslib.latest_file(S, V["video"], s, web=True), S)}
    print("\n".join(f"  {x}" for x in said))
    if a.dry:
        return print("(dry run: nothing filed)")
    try:  # the page: Done, the downloads, a way back in
        R.finish(argparse.Namespace(final=[have[s] for s in need]))
    except R.Refused as e:
        sys.exit(f"⛔ the finals are filed, but the review couldn't close: {e}. Fix that, then vs finish again")
    V["status"] = "done"
    if a.one_shape:
        V["one_shape"] = True
    V.setdefault("finals", []).append({"n": len(V.get("finals", [])) + 1, "at": now(), "files": rec})
    save(V, f"finished: final #{len(V['finals'])}", why=("one shape only" if a.one_shape else None))
    # the web copy: made here and only here, when the video is called done (latest.py says how)
    latest.make_webs(S, [os.path.relpath(os.path.join(S, r["final"]), os.path.join(S, "finals")) for r in rec.values()])
    latest.rebuild(S)
    sh(os.path.join(PY, "learn.py"), "--final", *have.values())
    print(f"{V['video']}: final #{len(V['finals'])} filed → finals/{V['video']}/ and latest/{V['video']}/")


# ── vs reopen ──
def reopen(a):
    V = state()
    if V["status"] != "done":
        return print(f"{V['video']} isn't finished (status {V['status']}): keep going. vs status says the next step")
    last = V["finals"][-1]
    first = a.shape or V["first"]
    made = last["files"].get(first) or next(iter(last["files"].values()))
    src = os.path.join(vslib.data_dir(made["draft"]), "source")
    if not os.path.isdir(src) and not a.keep_current:
        sys.exit(f"⛔ no sources were kept for {made['draft']} (it predates source snapshots), so the kit can't prove the "
                 "project's files still match that final. Look at them against the final, then: vs reopen --keep-current")
    kept = set(os.listdir(src)) if os.path.isdir(src) else set()
    differ = [] if a.keep_current else [
        f for f in vslib.SOURCE_FILES if (f in kept) != os.path.exists(f) or
        (f in kept and not filecmp.cmp(os.path.join(src, f), f, shallow=False))]
    if differ:
        aside = os.path.join("drafts", "reopened-" + datetime.now().strftime("%Y-%m-%d-%H%M"))
        os.makedirs(aside, exist_ok=True)
        for f in differ:
            if os.path.exists(f):
                shutil.copy2(os.path.realpath(f), os.path.join(aside, f))
                if f not in kept:
                    os.remove(f)
            if f in kept:
                if os.path.islink(f):
                    os.remove(f)  # a linked file gets the final's content, not a write through the link
                shutil.copy2(os.path.join(src, f), f)
        print(f"  changed since the final: {', '.join(differ)} → set aside in {aside}/, the final's put back")
    nxt = vslib.last_version() + 1
    for f in ("plan.json", "reel.json") if os.path.exists("plan.json") else ("reel.json",):
        if os.path.exists(f):
            j = json.load(open(f))
            j["version"] = nxt
            json.dump(j, open(f, "w"), indent=1)
            break
    V.update(status="first", building=first)
    save(V, f"reopened from final #{last['n']}" + (" (kept the current sources)" if a.keep_current else ""), why=a.why)
    if os.path.exists("plan.json"):
        sh(os.path.join(PY, "plan.py"))
    if os.path.exists("review/log.jsonl"):
        review_mod().append([{"type": "project.reopened", "from": made["version"], "next": nxt}], "agent")
    print(f"{V['video']}: reopened from final #{last['n']} (v{made['version']}). The next draft is v{nxt}, in {first}.")
    print(f"  next: {next_step(V)}")


def main():
    ap = argparse.ArgumentParser(prog="vs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("shape")
    p.add_argument("shape", choices=list(vslib.SHAPES))
    p.add_argument("--early")
    p = sub.add_parser("finish")
    p.add_argument("--final", nargs="+")
    p.add_argument("--one-shape", dest="one_shape", action="store_true")
    p.add_argument("--dry", action="store_true")
    p = sub.add_parser("reopen")
    p.add_argument("--shape", choices=list(vslib.SHAPES))
    p.add_argument("--why")
    p.add_argument("--keep-current", dest="keep_current", action="store_true",
                   help="a final with no kept sources: start from the project's files as they are (looked at first)")
    a = ap.parse_args()
    {"status": status, "shape": shape, "finish": finish, "reopen": reopen}[a.cmd](a)


if __name__ == "__main__":
    main()
