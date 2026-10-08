#!/usr/bin/env python3
"""vs: the one command. It finds the engine (here), the studio (what you keep) and the project (this video), then runs
the step. Each skill folder has a `vs` launcher that lands here, wherever the kit is installed.

  vs help                         every step, by what it's for (paid ones say so)
  vs help <step>                  that step's own notes: what it does, its options, its scars
  vs help scenes                  every helper a scenes.js can call, with its arguments and notes (from the code)
  vs help --md                    the command reference, as Markdown
  vs [-p <slug>] <step> …         run a step in a project (default: the folder you're in)
"""
import json, os, shutil, subprocess, sys

ENGINE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(ENGINE)
sys.path.insert(0, os.path.join(ENGINE, "py"))
import vslib  # noqa: E402

# Every step, once: name · runs (self: in studio.py) · script · needs a project · paid (who bills it) · group · what
COMMANDS = [
    ("setup", "self", None, False, None, "setup", "make the studio, install the engine, fetch the fonts, check it all"),
    ("new", "self", None, False, None, "setup", "a new video: new <video> --kind explainer|reel --shape vertical|widescreen"),
    ("where", "self", None, False, None, "setup", "the kit, the studio, this project, what's settled"),
    ("doctor", "node", "js/doctor.mjs", False, None, "setup", "is everything installed and set up"),
    ("fonts", "node", "js/fonts.mjs", False, None, "setup", "download a Google Font into the studio once"),
    ("spent", "self", None, False, None, "setup", "what this video (--all: every video) has cost"),
    ("check", "node", "js/check.mjs", True, None, "checks", "the files against their contracts"),
    ("migrate", "node", "js/migrate.mjs", True, None, "checks", "mark older files as schema_version 2"),
    ("inspect", "node", "js/inspect.mjs", True, None, "checks", "map every element; find words and pictures fighting"),
    ("qa", "py", "qa.py", True, None, "checks", "a rendered cut: sheets, safe zone, cuts, sound"),
    ("crops", "py", "crops.py", True, None, "checks", "close-ups of inspect's findings"),
    ("compare", "py", "compare.py", False, None, "checks", "did a change move any pixels (two folders of stills)"),
    ("test", "self", None, False, None, "checks", "the kit's own tests (--fast skips the browser)"),
    ("voices", "py", "voices.py", False, None, "voice", "audition narrators from free preview clips"),
    ("narrate", "py", "narrate.py", True, "elevenlabs", "voice", "read narration.txt with word timings"),
    ("check-take", "py", "check_take.py", True, "openai", "voice", "transcribe a take, list words that differ"),
    ("listen", "py", "listen.py", True, None, "voice", "a listening page for the takes"),
    ("pitch", "py", "pitch.py", True, None, "voice", "is a take monotone"),
    ("fit", "py", "fit.py", True, None, "voice", "fit a take to a length: shorter pauses, then faster"),
    ("voicebed", "py", "voicebed.py", True, None, "voice", "the voice bed + word timings"),
    ("plan", "py", "plan.py", True, None, "picture", "plan.json + words → reel.json (--wide)"),
    ("build", "node", "js/pipeline/index.mjs", True, None, "picture", "reel.json → composition → render"),
    ("snap", "node", "js/snap.mjs", True, None, "picture", "stills at any moment, no render"),
    ("record", "node", "js/record.mjs", True, None, "picture", "record a real page as scroll frames"),
    ("collage", "node", "js/collage.mjs", True, None, "picture", "the collage wall's tiles"),
    ("gen", "py", "gen.py", True, "kie.ai, higgsfield", "picture", "generated music, stills and clips"),
    ("beats", "py", "beats.py", True, None, "sound", "a track's beat grid and first big hit"),
    ("music", "py", "music.py", True, "kie.ai", "sound", "music beds for an explainer"),
    ("sfx", "py", "sfx.py", True, "elevenlabs", "sound", "buy sounds the library lacks"),
    ("mix", "py", "mix.py", True, None, "sound", "voice + music + effects onto the picture"),
    ("mixer", "py", "serve.py", True, None, "sound", "Review Studio's Mix panel: take, levels, ducking, Save"),
    ("review", "py", "review.py", True, None, "review", "Review Studio: point at the video, say what's wrong; rounds, choices, rules"),
    ("protocol", "self", None, False, None, "review", "the rules every skill shares: review (default), studio (where things live), files (names, folders, the path to final)"),
    ("status", "video", "video.py", True, None, "lifecycle", "where this video stands, and the one next step"),
    ("shape", "video", "video.py", True, None, "lifecycle", "build the other shape, once the first is approved"),
    ("finish", "video", "video.py", True, None, "lifecycle", "file the approved finals, refresh latest, close the review"),
    ("reopen", "video", "video.py", True, None, "lifecycle", "a finished video drafts again, from exactly its last final"),
    ("restructure", "py", "restructure.py", False, None, "lifecycle", "move a studio from the older flat layout to the folders (--dry first)"),
    ("ingest", "py", "ingest.py", True, "openai (own narration)", "studio", "bring your own media"),
    ("learn", "py", "learn.py", True, None, "studio", "after approval: keep what was decided"),
    ("latest", "py", "latest.py", False, None, "studio", "studio/latest/: the newest version of every video, plain names"),
    ("mark3d", "py", "mark3d.py", False, None, "studio", "your end card's mark in 3D, if Blender is installed (free)"),
]
ALIASES = {"audit": "inspect"}  # the old name for vs inspect
SELF_HELP = {  # the steps studio.py runs itself
    "setup": ("vs setup [--studio PATH] [--default]\n"
              "  Makes the studio (default ~/video-studio, remembered in ~/.config/video-studio), installs the\n"
              "  engine's packages and a Python with numpy once, fetches the profile's fonts, and runs vs doctor."),
    "new": ("vs new <video> --kind explainer|reel --shape vertical|widescreen\n"
            "  A new video in studio/projects/<video>, from the templates; its folder's name is the video's name, in\n"
            "  every file it makes (lowercase words and hyphens). --shape is the one it starts in: the other is made once\n"
            "  that one is approved (vs shape). The studio's profile fills in the look, the narrator and the levels;\n"
            "  anything the project's plan.json or reel.json sets overrides it. vs protocol files: the whole path."),
    "where": ("vs where\n"
              "  The kit, the studio, this project, and what the profile has settled (brand, narrator, mix, videos)."),
    "spent": "vs spent [--all]\n  What this video (or every video) has cost, per vendor, from the studio's ledger.csv.",
    "protocol": ("vs protocol [review | studio | files]\n"
                 "  The rules every skill follows, printed from engine/protocol/: review = how a version is handed to the human\n"
                 "  and their intent taken back (the loop, the lifecycle, the exit criteria, learning, finishing); studio = where\n"
                 "  every piece of information lives (engine, studio, project) and the gates every step shares; files = every\n"
                 "  name and folder, and how a video moves from first draft to final and back (vs reopen)."),
    "test": ("vs test [--fast] [a test file or folder…] [pytest or node --test arguments…]\n"
             "  The kit's own tests (tests/): unit, contract (the same cases in Python and JavaScript), regression and\n"
             "  integration (fixtures built and inspected in a browser; --fast skips those). Name a file or folder (a\n"
             "  .py, a .test.mjs, file.py::test) and only that runs; otherwise everything does. Nothing paid can run:\n"
             "  VIDEO_KIT_NO_SPEND is set. Python's tests need pytest; the first run installs it into the engine's Python."),
}
GROUPS = ["setup", "lifecycle", "checks", "voice", "picture", "sound", "review", "studio"]
CMD = {c[0]: c for c in COMMANDS}
NODE = {n: sc for n, r, sc, *_ in COMMANDS if r == "node"}
PY = {n: os.path.basename(sc) for n, r, sc, *_ in COMMANDS if r in ("py", "video")}
VIDEO = {n for n, r, *_ in COMMANDS if r == "video"}  # video.py's moves: it takes the step's name first
ANYWHERE = {n for n, r, sc, proj, *_ in COMMANDS if not proj and r != "self"} | {"spent"}


def header(name):
    """A step's own notes: the Python docstring or the JavaScript file's leading // comments."""
    n, runs, script, *_ = CMD[name]
    if runs == "self":
        return SELF_HELP[name]
    path = os.path.join(ENGINE, script if runs == "node" else os.path.join("py", script))
    src = open(path).read()
    if runs in ("py", "video"):
        import ast
        return ast.get_docstring(ast.parse(src)) or ""
    lines = [l for l in src.splitlines() if not l.startswith("#!")]
    out = []
    for l in lines:
        if not l.startswith("//"):
            break
        out.append(l[3:] if l.startswith("// ") else l[2:])
    return "\n".join(out)


# vs help scenes: every helper a scenes.js can call, read from the code each time (sessions used to re-read the library's
# source, 20 to 40 steps, to remember a signature). The renderer's own helpers are listed by name; the library's in full.
RENDERER_HELPERS = {  # the renderer's few shared helpers, each with its note (its source has none worth printing)
    "js/reel/00-core.js": {
        "exName": "names an element for vs inspect and the review page (\"tier-label\")",
        "svg": "an SVG element appended to parent; attrs as an object; the last argument names it",
        "div": "a div with class cls appended to parent, inner html, inline style; the last argument names it",
        "clamp": "x held between a and b", "easeOut": "cubic ease-out of x in 0..1", "easeInOut": "ease-in-out of x in 0..1",
        "mulberry32": "a seeded random number function (never Math.random: every frame must be a pure function of time)",
        "IR": "{ immediateRender: false }: spread into every tween after the first on the same property",
        "TP": "{ transformPerspective: 1800 }: spread into a 3D tween"},
    "js/reel/10-camera.js": {
        "tw3": "tl.fromTo for a 3D turn (rotationX/Y), also written down so a panel's glare follows its tilt", "punch": "a quick camera push-in at t that settles (a drum hit)"},
}
LIBRARY = ["js/scenes/base.js", "js/scenes/props.js", "js/scenes/icons.js"]


def scene_api():
    import re
    decl = re.compile(r"^(\s{0,2})(?:function\s+(\w+)\s*\((.*)\)\s*\{|const\s+(\w+)\s*=\s*(?:\((.*?)\)\s*=>)?)")

    def entries(path, only=None):
        lines, out = open(path).read().split("\n"), []
        for i, ln in enumerate(lines):
            m = decl.match(ln)
            if not m or len(m.group(1)) > (2 if only else 0):
                continue
            name = m.group(2) or m.group(4)
            if not name or (only and name not in only) or name.startswith("_"):
                continue
            args = m.group(3) if m.group(2) else m.group(5)
            sig = f"{name}({args})" if args is not None else name
            notes, j = [], i - 1
            while j >= 0 and lines[j].strip().startswith("//"):
                notes.insert(0, lines[j].strip()[2:].strip().strip("─ "))
                j -= 1
            if j < 0:  # the block runs up into the file's header: only its last line is about this helper
                notes = notes[-1:]
            tail = ln.split("//", 1)[1].strip() if "//" in ln and not notes else ""
            # no comment: the first line of what it does says enough (exFade → gsap.to(el, { opacity: to …)
            body = "" if notes or tail else (ln.split("=>", 1)[1].strip() if "=>" in ln else
                                            (lines[i + 1].strip() if i + 1 < len(lines) else ""))
            if body in ("", "{"):
                body = lines[i + 1].strip() if i + 1 < len(lines) else ""
            note = " ".join(notes) or tail or (f"does: {body[:110]}" if body else "")
            out.append((sig, note[:240] + ("…" if len(note) > 240 else "")))
        return out

    print("Scene library: every helper a scenes.js can call (read from the code just now). Positions are in the 1080×1400\n"
          "design space; t is seconds on the video's clock (a word's cue from R.scenes.<scene>.cues). Also in scope: tl (the\n"
          "GSAP timeline), ticks (per-frame work), P (the palette), W, H, LAND (true on a widescreen cut), EXIT (×2 on wide).")
    for f, only in RENDERER_HELPERS.items():
        print(f"\nrenderer ({f})")
        for sig, _ in entries(os.path.join(ENGINE, f), only):
            print(f"  {sig}\n      {only[sig.split('(')[0]]}")
    for f in LIBRARY:
        print(f"\nlibrary ({f})")
        for sig, note in entries(os.path.join(ENGINE, f)):
            if sig.startswith(("GLX", "KIT_SCENES", "exM", "GREEN")):
                continue
            print(f"  {sig}" + (f"\n      {note}" if note else ""))
    import re as _re
    icons = _re.findall(r"^\s{2}(\w+):", open(os.path.join(ENGINE, "js/scenes/icons.js")).read(), _re.M)
    print("\nicons (exIcon's g): " + " ".join(icons))
    css = sorted(set(_re.findall(r"\.(ex-[\w-]+)", open(os.path.join(ENGINE, "js/scenes/base.js")).read())))
    print("classes (div's cls): " + " ".join(css))
    st = vslib.studio_root()
    lib = os.path.join(st, "library", "scenes") if st else None
    if lib and os.path.isdir(lib):
        for f in sorted(x for x in os.listdir(lib) if x.endswith(".js")):
            e = entries(os.path.join(lib, f))
            if e:
                print(f"\nyour studio's library ({os.path.join('library/scenes', f)})")
                for sig, note in e:
                    print(f"  {sig}" + (f"\n      {note}" if note else ""))
    print("\nThe design rules, the overlap rules and widescreen: references/scenes.md. A helper's body: open its file at its name.")


def help_cmd(args):
    if args and args[0] == "scenes":
        return scene_api()
    if args and args[0] == "--md":
        print("# vs: the command reference\n\nEvery step is `<skill>/vs <step>`; `vs -p <slug> <step>` runs it in a studio "
              "project from anywhere. Paid steps print the cost and stop until you add `--yes`.\n")
        for g in GROUPS:
            print(f"## {g}\n")
            for n, runs, script, proj, paid, grp, what in COMMANDS:
                if grp != g:
                    continue
                al = [a for a, t in ALIASES.items() if t == n]
                print(f"### vs {n}" + (f" (also: vs {', vs '.join(al)})" if al else "") + "\n")
                print(f"{what}." + (f" **Paid:** {paid}." if paid else "") + ("" if proj else " Runs anywhere.") + "\n")
                print("```\n" + header(n).strip() + "\n```\n")
        return
    if args:
        n = ALIASES.get(args[0], args[0])
        if n not in CMD:
            sys.exit(f"⛔ no step {args[0]!r}: vs help lists them")
        _, runs, script, proj, paid, grp, what = CMD[n]
        print(f"vs {n}: {what}")
        print(f"  {'paid: ' + paid + ' (prints the cost and stops until --yes)' if paid else 'free'} · "
              f"{'runs in a project folder (or vs -p <slug>)' if proj else 'runs anywhere'}"
              + (f" · {script if runs == 'node' else 'py/' + script}" if script else ""))
        print("\n" + header(n).strip())
        return
    print(__doc__)
    for g in GROUPS:
        print(f"{g}:")
        for n, runs, script, proj, paid, grp, what in COMMANDS:
            if grp == g:
                print(f"  {n:11s} {what}" + (f"   [paid: {paid}]" if paid else ""))
    print("\nvs help <step> for its own notes.")


def python():
    """A Python with numpy: $PYTHON, the studio's choice (studio.json → "python"), the engine's own venv, or this one."""
    s = vslib.studio_root()
    for p in [os.environ.get("PYTHON"), s and vslib.read_json(os.path.join(s, "studio.json")).get("python"),
              os.path.join(ENGINE, ".venv/bin/python"), sys.executable]:
        if p and os.path.exists(p) and subprocess.run([p, "-c", "import numpy"], capture_output=True).returncode == 0:
            return p
    sys.exit("⛔ no Python with numpy: run vs setup (it makes one for the engine), or set PYTHON")


def project_dir(arg):
    if arg:
        s = vslib.studio_root()
        for d in [arg, s and os.path.join(s, "projects", arg)]:
            if d and os.path.isdir(d): return os.path.abspath(d)
        sys.exit(f"⛔ no project {arg!r} (here or in the studio's projects/)")
    d = os.getcwd()
    while True:
        if any(os.path.exists(os.path.join(d, f)) for f in ("plan.json", "reel.json")): return d
        if os.path.dirname(d) == d: return None
        d = os.path.dirname(d)


def setup(args):
    studio = os.path.abspath(os.path.expanduser(args[args.index("--studio") + 1])) if "--studio" in args else (vslib.studio_root() or os.path.expanduser("~/video-studio"))
    print(f"studio: {studio}")
    for d in ["library/sfx", "library/music", "library/brand/fonts", "library/media", "library/scenes", "library/originals", "projects", "finals"]:
        os.makedirs(os.path.join(studio, d), exist_ok=True)
    t = os.path.join(KIT, "templates/studio")
    for f in ["profile.json", "lessons.md", "README.md", "gitignore"]:
        dst = os.path.join(studio, ".gitignore" if f == "gitignore" else f)
        if not os.path.exists(dst): shutil.copy(os.path.join(t, f), dst); print(f"  wrote {os.path.basename(dst)}")
    sj = os.path.join(studio, "studio.json")
    if not os.path.exists(sj): json.dump({"kit": KIT, "version": 1}, open(sj, "w"), indent=1)
    # remember it as THE studio for this user, unless one is already remembered (then only with --default)
    cfg = os.path.expanduser("~/.config/video-studio/config.json")
    if not os.path.exists(cfg) or "--default" in args:
        os.makedirs(os.path.dirname(cfg), exist_ok=True)
        json.dump({"studio": studio}, open(cfg, "w"), indent=1)
    elif vslib.read_json(cfg).get("studio") != studio:
        print(f"  (the default studio stays {vslib.read_json(cfg).get('studio')}; --default makes this one the default)")
    os.environ["VIDEO_STUDIO"] = studio
    want = json.load(open(os.path.join(ENGINE, "package.json"))).get("dependencies", {})
    if not all(os.path.exists(os.path.join(ENGINE, "node_modules", p, "package.json")) for p in want):
        print("  installing the engine's packages (HyperFrames renders, GSAP animates, puppeteer brings a Chrome, ajv checks the"
              " files): about 190 MB the first time")
        subprocess.run(["npm", "install", "--no-fund", "--no-audit"], cwd=ENGINE, check=True)
    try:
        python()
    except SystemExit:
        print("  making a Python for the engine with numpy (engine/.venv)")
        subprocess.run([sys.executable, "-m", "venv", os.path.join(ENGINE, ".venv")], check=True)
        subprocess.run([os.path.join(ENGINE, ".venv/bin/pip"), "install", "-q", "numpy"], check=True)
    b = vslib.profile().get("brand", {})
    for k, w in (("font", "500,600,700,800"), ("mono", "500,700")):
        fam = b.get(k, {}).get("family")
        if fam and not os.path.exists(os.path.join(studio, "library/brand/fonts", fam.replace(" ", "") + ".css")):
            subprocess.run(["node", os.path.join(ENGINE, NODE["fonts"]), fam, b.get(k, {}).get("weights", w)], cwd=studio)
    subprocess.run(["node", os.path.join(ENGINE, NODE["doctor"])], cwd=studio)


def new(args):
    import re
    if not args or "--kind" not in args or "--shape" not in args:
        sys.exit("vs new <video> --kind explainer|reel --shape vertical|widescreen   (the shape it starts in)")
    slug, kind, shape = args[0], args[args.index("--kind") + 1], args[args.index("--shape") + 1]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug) or re.search(r"-(vertical|widescreen|9x16|16x9|v\d+)$", slug):
        sys.exit(f"⛔ {slug!r}: a video's name is lowercase words joined by hyphens, with no shape or version in it "
                 "(the kit adds those to every file)")
    if shape not in vslib.SHAPES: sys.exit(f"⛔ --shape {shape}: vertical or widescreen")
    s = vslib.studio_root() or sys.exit("⛔ no studio yet: vs setup")
    d = os.path.join(s, "projects", slug)
    if os.path.exists(d): sys.exit(f"⛔ {d} exists (a finished video changes with vs reopen {slug})")
    shutil.copytree(os.path.join(KIT, "templates", kind), d)
    if os.path.exists(os.path.join(d, "gitignore")): os.rename(os.path.join(d, "gitignore"), os.path.join(d, ".gitignore"))
    for sub in ["inputs", "media", "drafts", "build"] + (["voice", "music"] if kind == "explainer" else ["music"]):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    f = os.path.join(d, "plan.json" if kind == "explainer" else "reel.json")
    j = json.load(open(f)); j["name"] = slug; j["size"] = vslib.CONTRACTS["sizes"][shape]
    json.dump(j, open(f, "w"), indent=1)
    from datetime import datetime
    vslib.save_video_state({"schema_version": 1, "video": slug, "first": shape, "building": shape, "status": "first",
                            "finals": [], "log": [{"at": datetime.now().astimezone().isoformat(timespec="seconds"),
                                                   "event": f"started in {shape} (vs new)"}]}, os.path.join(d, "video.json"))
    print(f"{d}\n  starts {shape}; the other shape comes once it's approved (vs status says the next step)\n"
          f"  the studio's profile fills in the look, the narrator and the levels; anything set in {os.path.basename(f)} overrides it")


def where():
    s, pr = vslib.studio_root(), vslib.profile()
    print(f"kit      {KIT}\nstudio   {s or '— none yet (vs setup)'}\nproject  {project_dir(None) or '— (not in one)'}")
    b = pr.get("brand", {})
    print(f"brand    accent {b.get('palette', {}).get('accent')} · {b.get('font', {}).get('family')} / {b.get('mono', {}).get('family')} · end card {b.get('endcard', {}).get('wordmark', '—')}")
    print(f"narrator {pr.get('narrator', {}).get('voice') or '— not chosen'} · mix {pr.get('mix')} · videos made {len(pr.get('history', []))}")


def spent(args):
    rows = vslib.rows() if "--all" in args else vslib.rows(project=vslib.project_name())
    tot = {}
    for r in rows:
        k = (r.get("project"), r.get("vendor"))
        c, u = tot.get(k, (0, 0))
        tot[k] = (c + float(r.get("credits") or 0), u + float(r.get("usd") or 0))
    for (p, v), (c, u) in sorted(tot.items()):
        print(f"  {p:28s} {v:12s} {c:8.0f} credits  ${u:.2f}")
    print(f"({vslib.ledger_path()})" if rows else "nothing logged")


def protocol(args):
    """Print one of the shared protocols (engine/protocol/<topic>.md)."""
    topic = (args[0] if args else "review").removesuffix(".md")
    path = os.path.join(ENGINE, "protocol", f"{topic}.md")
    if not os.path.exists(path):
        have = sorted(f[:-3] for f in os.listdir(os.path.join(ENGINE, "protocol")) if f.endswith(".md"))
        sys.exit(f"⛔ no protocol {topic!r}: {', '.join(have)}")
    print(open(path).read())


def run_tests(args):
    """Node's built-in runner for the .test.mjs files, pytest for the Python ones; both with nothing paid allowed."""
    import glob
    tests, fast = os.path.join(KIT, "tests"), "--fast" in args
    args = [a for a in args if a != "--fast"]
    env = {**os.environ, "VIDEO_KIT_NO_SPEND": "1"}
    py = python()
    if subprocess.run([py, "-c", "import pytest"], capture_output=True).returncode:
        print("installing pytest into the engine's Python (for the kit's own tests only)")
        subprocess.run([py, "-m", "pip", "install", "-q", "pytest"], check=True)
    # a file or folder named: run just that (it used to be added to the whole suite, so one file ran everything)
    picked = [a for a in args if not a.startswith("-") and os.path.exists(a.split("::")[0])]
    named_js = [a for a in picked if a.endswith(".mjs")]
    args = [a for a in args if a not in named_js]
    mjs = named_js if picked else sorted(glob.glob(os.path.join(tests, "**", "*.test.mjs"), recursive=True))
    js = subprocess.run(["node", "--test", "--test-reporter=dot", *mjs], env=env).returncode if mjs else 0
    run_py = not picked or len(named_js) < len(picked)
    pyt = subprocess.run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider", *([] if picked else [tests]),
                          *(["-m", "not slow"] if fast else []), *args], env=env).returncode if run_py else 0
    print("✓ all passed" if not (js or pyt) else f"⛔ failed: {'JavaScript ' if js else ''}{'Python' if pyt else ''}")
    sys.exit(js or pyt)


def main():
    a = sys.argv[1:]
    proj = None
    if a[:1] in (["-p"], ["--project"]): proj, a = a[1], a[2:]
    if not a or a[0] in ("-h", "--help", "help"): return help_cmd(a[1:])
    cmd, rest = ALIASES.get(a[0], a[0]), a[1:]
    if cmd == "reopen" and rest[:1] and not rest[0].startswith("-"): proj, rest = rest[0], rest[1:]  # vs reopen <video>
    if "--shape" in rest and cmd not in ("new", "shape", "reopen"):  # this run builds/plans/inspects that shape
        i = rest.index("--shape")
        if rest[i + 1:i + 2] and rest[i + 1] in vslib.SHAPES:
            os.environ["VS_SHAPE"] = rest[i + 1]
            rest = rest[:i] + rest[i + 2:]
    if cmd == "setup": return setup(rest)
    if cmd == "new": return new(rest)
    if cmd == "where": return where()
    if cmd == "test": return run_tests(rest)
    if cmd == "protocol": return protocol(rest)
    if cmd not in CMD: sys.exit(f"⛔ unknown step {a[0]!r}{near(a[0])}: vs help lists them")
    d = project_dir(proj)
    if not d and cmd not in ANYWHERE: sys.exit("⛔ not in a project folder: cd into one, or vs -p <slug> " + cmd)
    if d: os.chdir(d)
    if cmd == "spent": return spent(rest)
    run = ["node", os.path.join(ENGINE, NODE[cmd])] if cmd in NODE else [python(), os.path.join(ENGINE, "py", PY[cmd])]
    os.execvp(run[0], run + ([cmd] if cmd in VIDEO else []) + rest)


def near(x):
    import difflib
    m = difflib.get_close_matches(x, list(CMD) + list(ALIASES), n=1)
    return f" (did you mean {m[0]!r}?)" if m else ""


if __name__ == "__main__":
    main()
