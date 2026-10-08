#!/usr/bin/env python3
"""Move a studio from the older flat layout to the folders of engine/protocol/files.md. Nothing is deleted: every file
is moved (or, for a pair of projects merged into one, the left-over folder is retired to archive/).

    vs restructure --dry                       say everything it would do, change nothing (always run this first)
    vs restructure [--merge <video>=<other> …] [--retire <project> …] [--rename <old>=<new> …]

  projects   out/ → drafts/vN/: a render becomes drafts/vN/<video>-<shape>-vN.mp4 (the shape read from its pixels,
             never its old name), its mixes and cover beside it, its .review/ and .timeline.json into data/<shape>/,
             out/watched/ → drafts/watched/. The review diary's paths are rewritten to match (the old diary is kept as
             review/log.pre-restructure.jsonl). video.json is written: the shape it started in, where it stands.
  --merge    a video split across two projects (an older reel kept its other shape in a sibling, <video>-16x9): the
             other's drafts join <video>'s, its reel.json differences become reel.json → "shapes" → <its shape>, a
             media file or scenes.js that differs is kept as media/<shape>/… or scenes.<shape>.js, its review diary goes
             to review/archive/, and its folder is retired to archive/.
  --retire   a project superseded by another: its folder moves to archive/ untouched.
  --rename   a project folder takes the video's name (after --retire freed it).
  finals     finals/<flat files> → finals/<video>/<video>-<shape>-vN.mp4 (+ covers; the shape from the pixels), each
             recorded in its project's video.json; anything that isn't a final goes to archive/finals-strays/.
  latest     rebuilt (vs latest).
Unreadable names are listed and left where they are."""
import argparse, filecmp, hashlib, json, os, re, shutil, subprocess, sys
from datetime import datetime
import vslib
import latest as latest_mod

OLD = re.compile(r"^(?P<base>.+?)(?P<w>-16x9)?-v(?P<v>\d+)(?P<rest>.*)$")
say = print


def probe_shape(p):
    W, H = vslib.probe_size(p)
    return vslib.shape_of(W, H)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Plan:
    """Every move, said first and done only without --dry. moves: [(src, dst)]; paths: {old relative path: new}."""

    def __init__(self, dry, studio):
        self.dry, self.moves, self.notes, self.gone, self.S = dry, [], [], set(), studio

    def move(self, src, dst):
        if os.path.abspath(src) == os.path.abspath(dst):
            return
        if os.path.exists(dst) and os.path.abspath(dst) not in self.gone:  # (a dry run's earlier moves count as done)
            if os.path.isfile(src) and os.path.isfile(dst) and filecmp.cmp(src, dst, shallow=False):
                # the same bytes are already there (an older pair kept copies of each other): this copy is retired
                dst = os.path.join(self.S, "archive", "duplicates", os.path.relpath(src, self.S))
                self.notes.append(f"a copy of a file already in place: {os.path.relpath(src, self.S)} → archive/duplicates/")
            else:
                root, ext = os.path.splitext(dst)
                dst = f"{root}-dup{ext}"
                self.notes.append(f"⚠️  {os.path.relpath(dst, self.S)} kept beside a different file of the same name")
        self.moves.append((src, dst))
        self.gone.add(os.path.abspath(src))
        if not self.dry:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
        return dst


# ── one project's out/ → drafts/ ──
def project_moves(d, video, P, shape_hint=None):
    """out/ of project folder d → its drafts/ (as the video `video`). → {old path relative to d: new path}."""
    out, mp = os.path.join(d, "out"), {}
    if not os.path.isdir(out):
        return mp
    files = sorted(os.listdir(out))
    groups = {}  # (base, w, v) → the files
    for f in files:
        m = OLD.match(f)
        if f == "watched":
            for w in sorted(os.listdir(os.path.join(out, f))):
                mp[f"out/watched/{w}"] = f"drafts/watched/{w}"
            continue
        if not m:
            P.notes.append(f"⚠️  {d}/out/{f}: not a render's name, left in out/")
            continue
        groups.setdefault((m["base"], m["w"] or "", int(m["v"])), []).append((f, m["rest"]))
    for (base, w, v), fs in sorted(groups.items()):
        vids = [f for f, r in fs if f.endswith(".mp4") and not r.endswith(".frames.mp4")]
        shape = probe_shape(os.path.join(out, vids[0])) if vids else (shape_hint or ("widescreen" if w else "vertical"))
        for f, rest in fs:
            dd = f"drafts/v{v}"
            if os.path.isdir(os.path.join(out, f)) and rest == ".review":
                for x in sorted(os.listdir(os.path.join(out, f))):
                    mp[f"out/{f}/{x}"] = f"{dd}/data/{shape}/{x}"
                continue
            if rest == ".timeline.json":
                tgt = f"{dd}/data/{shape}/timeline.json"
                if os.path.exists(os.path.join(out, f"{base}{w}-v{v}.review", "timeline.json")):
                    tgt = f"{dd}/data/{shape}/timeline-copy.json"  # the archive's own wins; this twin is kept beside it
                mp[f"out/{f}"] = tgt
            elif rest == ".cuts.json":
                mp[f"out/{f}"] = f"{dd}/data/{shape}/cuts.json"
            elif rest == ".frames.mp4":
                mp[f"out/{f}"] = f"{dd}/data/{shape}/frames.mp4"
            elif rest == "-cover.jpg" or re.fullmatch(r"-take\d+-cover\.jpg", rest):
                mp[f"out/{f}"] = f"{dd}/{video}-{shape}-v{v}-cover.jpg"
            elif f.endswith(".mp4"):
                mp[f"out/{f}"] = f"{dd}/{video}-{shape}-v{v}{rest}"
            else:
                mp[f"out/{f}"] = f"{dd}/other/{f}"
                P.notes.append(f"⚠️  {d}/out/{f}: kept in {dd}/other/")
    return mp


def walk(x, fn):
    if isinstance(x, dict):
        return {k: walk(v, fn) for k, v in x.items()}
    if isinstance(x, list):
        return [walk(v, fn) for v in x]
    return fn(x) if isinstance(x, str) else x


def rewrite_paths(mp):
    """A function rewriting one diary string: an old path (out/…, /out/…, ../<sibling>/out/…) → its new path."""
    def fn(s):
        if s in mp:
            return mp[s]
        if s.startswith("/") and s[1:] in mp:
            return "/" + mp[s[1:]]
        if s.startswith("/@"):  # an older page's address for a sibling's file
            t = "../" + s[2:]
            if t in mp:
                return "/" + mp[t]
        m = re.match(r"^(/?)(?:\.\./|@)[^/]+/(out/.+)$", s)  # a file a sibling project held under the same name: ours
        if m and m[2] in mp:
            return m[1] + mp[m[2]]
        return s
    return fn


def rewrite_diary(d, mp, P, dest=None):
    """review/log.jsonl and state.json with every moved path rewritten; the old log kept beside it."""
    log = os.path.join(d, "review", "log.jsonl")
    if not os.path.exists(log):
        return
    fn = rewrite_paths(mp)
    lines = [json.loads(l) for l in open(log) if l.strip()]
    new = [walk(e, fn) for e in lines]
    changed = sum(1 for a, b in zip(lines, new) if a != b)
    P.notes.append(f"{os.path.relpath(log, os.path.dirname(d))}: {changed} of {len(lines)} events' paths rewritten")
    if P.dry:
        return
    dst = dest or log
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not dest:
        shutil.copy2(log, os.path.join(d, "review", "log.pre-restructure.jsonl"))
    with open(dst + ".part", "w") as f:
        for e in new:
            f.write(json.dumps(e) + "\n")
    os.replace(dst + ".part", dst)
    st = os.path.join(d, "review", "state.json")
    if os.path.exists(st):
        sdst = os.path.join(os.path.dirname(dst), os.path.basename(dst).replace("log", "state").replace(".jsonl", ".json")) if dest else st
        json.dump(walk(json.load(open(st)), fn), open(sdst, "w"), indent=1)


def apply_moves(d, mp, P):
    for old, new in sorted(mp.items()):
        P.move(os.path.join(d, old), os.path.join(d, new))
    if not P.dry:
        for root, dirs, files in os.walk(os.path.join(d, "out"), topdown=False):
            for x in dirs:
                p = os.path.join(root, x)
                if not os.listdir(p):
                    os.rmdir(p)
        o = os.path.join(d, "out")
        if os.path.isdir(o):
            for junk in (".DS_Store",):
                if os.path.exists(os.path.join(o, junk)):
                    os.remove(os.path.join(o, junk))
            if not os.listdir(o):
                os.rmdir(o)


def renders(d):
    """[(version, shape, path)] of a converted project's renders."""
    out = []
    for v in sorted(os.listdir(os.path.join(d, "drafts"))) if os.path.isdir(os.path.join(d, "drafts")) else []:
        if re.fullmatch(r"v\d+", v):
            for f in os.listdir(os.path.join(d, "drafts", v)):
                x = vslib.parse_draft(f)
                if x and not x["variant"]:
                    out.append((x["v"], x["shape"], os.path.join(d, "drafts", v, f)))
    return sorted(out)


# ── merging a sibling shape project into the video's project ──
SOURCE_SKIP = {"name", "version", "schema_version"}


def merge(S, keep, other, P):
    dk, do = os.path.join(S, "projects", keep), os.path.join(S, "projects", other)
    if not os.path.isdir(do):
        return P.notes.append(f"⚠️  --merge {keep}={other}: no project {other}")
    mp_o = project_moves(do, keep, P)
    for old in [o for o in mp_o if o.startswith("out/watched/")]:  # its rounds' kept copies: apart from the kept project's
        mp_o[old] = f"drafts/watched/{other}/{os.path.basename(old)}"
    shapes = {vslib.parse_draft(os.path.basename(n))["shape"] for n in mp_o.values() if vslib.parse_draft(os.path.basename(n))}
    oshape = shapes.pop() if len(shapes) == 1 else None
    if not oshape:
        return P.notes.append(f"⚠️  --merge {keep}={other}: its renders aren't one shape ({shapes or 'none'}): not merged")
    # the sibling's drafts move straight into the kept project's drafts/ (the path rewrite says where they went)
    full = {}
    for old, new in mp_o.items():
        full[f"../{other}/{old}"] = new  # how the kept project's diary named them
        full[old] = new
        P.move(os.path.join(do, old), os.path.join(dk, new))
    # sources: reel.json / plan.json differences become the shape's block; other differing files are kept per shape
    for src in ("reel.json", "plan.json"):
        a, b = os.path.join(dk, src), os.path.join(do, src)
        if os.path.exists(a) and os.path.exists(b):
            A, B = json.load(open(a)), json.load(open(b))
            block = {k: v for k, v in B.items() if k not in SOURCE_SKIP and k != "shapes" and A.get(k) != v}
            A["version"] = max(int(A.get("version") or 1), int(B.get("version") or 1))
            if block:
                A.setdefault("shapes", {})[oshape] = block
            P.notes.append(f"{keep}/{src}: shapes.{oshape} = {sorted(block)} from {other}; version {A['version']}")
            if not P.dry:
                json.dump(A, open(a, "w"), indent=1)
    media_map = {}
    for root, dirs, files in os.walk(do):
        rel = os.path.relpath(root, do)
        if rel.split(os.sep)[0] in ("out", "build", "review", "drafts", "node_modules"):
            continue
        for f in files:
            r = os.path.normpath(os.path.join(rel, f))
            if r in ("reel.json", "plan.json", ".DS_Store") or f == ".DS_Store":
                continue
            a, b = os.path.join(dk, r), os.path.join(do, r)
            if os.path.islink(b):
                continue  # a link into the kept project (scenes.js -> ../keep/scenes.js): nothing to keep
            if not os.path.exists(a):
                P.move(b, a)
            elif not filecmp.cmp(a, b, shallow=False):
                if r == "scenes.js":
                    P.move(b, os.path.join(dk, f"scenes.{oshape}.js"))
                elif r.startswith("media" + os.sep) or r.startswith("inputs" + os.sep):
                    top, rest = r.split(os.sep, 1)
                    dst = os.path.join(top, oshape, rest)
                    P.move(b, os.path.join(dk, dst))
                    media_map[r] = dst
                else:
                    P.move(b, os.path.join(dk, "review", "archive", other, r))
    if media_map:  # the shape's block names its own copies
        a = os.path.join(dk, "reel.json")
        if os.path.exists(a) and not P.dry:
            A = json.load(open(a))
            fn = lambda s: next((s.replace(o, n) for o, n in media_map.items() if o in s), s)
            if oshape in A.get("shapes", {}):
                A["shapes"][oshape] = walk(A["shapes"][oshape], fn)
                json.dump(A, open(a, "w"), indent=1)
        P.notes.append(f"{keep}: {other}'s own copies of {sorted(media_map)} kept under media/{oshape}/ (its shape block names them)")
    # its diary: archived inside the kept project, paths rewritten
    rewrite_diary(do, full, P, dest=os.path.join(dk, "review", "archive", f"{other}-log.jsonl"))
    if os.path.isdir(os.path.join(do, "review", "frames")):
        P.move(os.path.join(do, "review", "frames"), os.path.join(dk, "review", "archive", f"{other}-frames"))
    retire(S, other, P)
    return full


def retire(S, name, P):
    src = os.path.join(S, "projects", name)
    if os.path.isdir(src):
        P.move(src, os.path.join(S, "archive", name))


# ── video.json for a converted project ──
def write_state(d, video, finals, P):
    vj = os.path.join(d, "video.json")
    if os.path.exists(vj) and not P.dry:
        V = json.load(open(vj))
    else:
        rs = renders(d) if not P.dry else []
        first = min(rs, key=lambda r: os.path.getmtime(r[2]))[1] if rs else vslib.shape_of(*(vslib.read_json(os.path.join(d, "reel.json")).get("size")
                                                      or vslib.read_json(os.path.join(d, "plan.json")).get("size") or [1080, 1920]))
        V = {"schema_version": 1, "video": video, "first": first, "building": rs[-1][1] if rs else first,
             "status": "first", "finals": [], "log": [{"at": datetime.now().astimezone().isoformat(timespec="seconds"),
                                                       "event": "restructured from the older layout (vs restructure)"}]}
    mine = finals.get(video) or {}
    if P.dry:
        return P.notes.append(f"{video}/video.json: written" + (f"; final {', '.join(f'{s} v{v}' for s, (v, _) in sorted(mine.items()))}" if mine else "; no final yet"))
    if mine:
        rs = renders(d) if not P.dry else []
        newest = {}
        for v, s, p in rs:
            newest[s] = max(newest.get(s, 0), v)
        files = {}
        for s, (v, fpath) in mine.items():
            draft = None
            for vv, ss, p in rs:  # the draft it was filed from: the same bytes (a mix of that version, usually)
                if ss == s and vv == v:
                    for f in sorted(os.listdir(os.path.dirname(p))):
                        q = os.path.join(os.path.dirname(p), f)
                        x = vslib.parse_draft(f)
                        if x and x["shape"] == s and os.path.getsize(q) == os.path.getsize(fpath) and sha(q) == sha(fpath):
                            draft = os.path.relpath(q, d)
            files[s] = {"version": v, "draft": draft, "final": os.path.relpath(fpath, os.path.dirname(os.path.dirname(d))),
                        "latest": os.path.join("latest", video, f"{video}-{s}.mp4")}
        V["finals"] = [{"n": 1, "at": datetime.fromtimestamp(max(os.path.getmtime(f) for _, f in mine.values())).astimezone()
                        .isoformat(timespec="seconds"), "imported": True, "files": files}]
        done = all(newest.get(s, 0) <= files[s]["version"] for s in newest if s in files) and set(newest) <= set(files)
        V["status"] = "done" if done else ("second" if len(newest) > 1 else "first")
        if len(files) == 1 and len(newest) <= 1:
            V["one_shape"] = True
    elif not P.dry:
        rs = renders(d)
        V["status"] = "second" if len({s for _, s, _ in rs}) > 1 else "first"
    P.notes.append(f"{video}/video.json: first {V['first']}, status {V['status']}"
                   + (f", final v{', v'.join(str(x['version']) for x in V['finals'][-1]['files'].values())}" if V.get("finals") else ""))
    if not P.dry:
        vslib.save_video_state(V, vj)
    # the reel's / plan's name is the folder's name now
    for src in ("reel.json", "plan.json"):
        f = os.path.join(d, src)
        if os.path.exists(f) and not P.dry:
            j = json.load(open(f))
            if j.get("name") != video:
                j["name"] = video
                json.dump(j, open(f, "w"), indent=1)


# ── finals/ ──
def finals(S, renames, P):
    fin = os.path.join(S, "finals")
    flat = sorted(f for f in os.listdir(fin) if os.path.isfile(os.path.join(fin, f))) if os.path.isdir(fin) else []
    groups, plan, newest = {}, {}, {}
    for f in flat:
        m = re.match(r"^(?P<base>.+?)(?P<w>-16x9)?-v(?P<v>\d+)(?P<take>-take\d+)?(?P<web>-web)?(?P<cover>-cover)?\.(?P<ext>mp4|jpg)$", f)
        if not m or (m["ext"] == "jpg") != bool(m["cover"]):
            if not f.startswith("."):
                plan[f] = os.path.join(S, "archive", "finals-strays", f)
            continue
        groups.setdefault((renames.get(m["base"], m["base"]), m["w"] or "", int(m["v"])), []).append((f, m))
    for (video, w, v), fs in sorted(groups.items()):
        vids = [f for f, m in fs if m["ext"] == "mp4"]
        shape = probe_shape(os.path.join(fin, vids[0])) if vids else ("widescreen" if w else "vertical")
        for f, m in fs:
            name = f"{video}-{shape}-v{v}" + ("-web" if m["web"] else "") + ("-cover.jpg" if m["cover"] else ".mp4")
            plan[f] = os.path.join(fin, video, name)
            if m["ext"] == "mp4" and not m["web"]:
                if shape not in newest.setdefault(video, {}) or v >= newest[video][shape][0]:
                    newest[video][shape] = (v, os.path.join(fin, video, name))
    for f, dst in plan.items():
        P.move(os.path.join(fin, f), dst)
    return newest


def gitignore(S, P):
    p = os.path.join(S, ".gitignore")
    if not os.path.exists(p):
        return
    s = open(p).read()
    add = [x for x in ["projects/*/drafts/", "latest/", "archive/*/build/", "archive/*/drafts/", "archive/*/out/",
                       "archive/*/inputs/", "archive/*/media/", "archive/*/voice/*.mp3", "archive/*/voice/*.wav",
                       "archive/*/music/*.mp3", "archive/finals-strays/"] if x not in s.split("\n")]
    if add:
        P.notes.append(f".gitignore: + {', '.join(add)}")
        if not P.dry:
            open(p, "a").write("\n# vs restructure: drafts, the latest copies, and retired projects' media\n" + "\n".join(add) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--merge", action="append", default=[], help="<video>=<sibling project holding its other shape>")
    ap.add_argument("--retire", action="append", default=[], help="<project> superseded: moved to archive/")
    ap.add_argument("--rename", action="append", default=[], help="<old project>=<new name>")
    a = ap.parse_args()
    S = vslib.studio_root() or sys.exit("⛔ no studio")
    P = Plan(a.dry, S)
    say(f"studio: {S}" + ("   (dry run: nothing moves)" if a.dry else ""))
    renames = dict(x.split("=", 1) for x in a.rename)
    merges = [x.split("=", 1) for x in a.merge]
    for name in a.retire:
        retire(S, name, P)
    for old, new in renames.items():
        if os.path.exists(os.path.join(S, "projects", new)) and not a.dry:
            sys.exit(f"⛔ --rename {old}={new}: projects/{new} still exists (--retire it first)")
        P.move(os.path.join(S, "projects", old), os.path.join(S, "projects", new))
    projects_dir = os.path.join(S, "projects")
    names = sorted(x for x in (os.listdir(projects_dir) if os.path.isdir(projects_dir) else [])
                   if os.path.isdir(os.path.join(projects_dir, x)))
    if a.dry:  # what the retires and renames would have done
        names = sorted((set(names) - set(renames) - set(a.retire)) | set(renames.values()))
    merged_away = {o for _, o in merges}
    for name in names:
        if name in merged_away:
            continue
        d = os.path.join(projects_dir, name if not a.dry else next((o for o, n in renames.items() if n == name), name))
        mp = project_moves(d, name, P)
        extra = {}
        for keep, other in merges:
            if keep == name:
                extra.update(merge(S, keep, other, P) or {})
        if a.dry and not mp and not extra:
            continue
        apply_moves(d, mp, P)
        rewrite_diary(d, {**mp, **extra}, P)
    newest = finals(S, {**renames, **{f"{o}": k for k, o in merges}}, P)
    for name in names:
        if name in merged_away:
            continue
        d = os.path.join(projects_dir, name if not a.dry else next((o for o, n in renames.items() if n == name), name))
        if os.path.isdir(d):
            write_state(d, name, newest, P)
    gitignore(S, P)
    if not a.dry:
        latest_mod.rebuild(S)
    else:
        say("latest/: rebuilt from the new finals/ (vs latest)")
    say(f"{len(P.moves)} file(s) and folder(s) {'would move' if a.dry else 'moved'}")
    for n in P.notes:
        say(f"  {n}")
    if a.dry:
        for s_, d_ in P.moves[:400]:
            say(f"  {os.path.relpath(s_, S)} → {os.path.relpath(d_, S)}")


if __name__ == "__main__":
    main()
