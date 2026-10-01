#!/usr/bin/env python3
"""vs: the one command. It finds the engine (here), the studio (what you keep) and the project (this video), then runs
the step. Each skill folder has a `vs` launcher that lands here, wherever the kit is installed.

  vs setup [--studio PATH] [--default]   make the studio, install the engine once, fetch the profile's fonts, check it all
  vs new <slug> --kind explainer|reel     a new video in studio/projects/<slug>, from the templates and your profile
  vs where                        the kit, the studio, this project, and what the profile has settled
  vs spent [--all]                what this video (or every video) has cost, from the studio's ledger
  vs [-p <slug>] <step> …         run a step in a project (default: the folder you're in)

Steps: plan narrate check-take voicebed listen pitch voices · build audit snap crops qa record collage beats gen
       music sfx mix mixer · ingest learn · fonts doctor compare
"""
import json, os, shutil, subprocess, sys

ENGINE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(ENGINE)
sys.path.insert(0, os.path.join(ENGINE, "py"))
import vslib  # noqa: E402

NODE = {"build": "js/pipeline/index.mjs", "audit": "js/audit.mjs", "snap": "js/snap.mjs", "record": "js/record.mjs",
        "collage": "js/collage.mjs", "doctor": "js/doctor.mjs", "fonts": "js/fonts.mjs"}
PY = {"plan": "plan.py", "narrate": "narrate.py", "check-take": "check_take.py", "voicebed": "voicebed.py", "listen": "listen.py",
      "pitch": "pitch.py", "voices": "voices.py", "music": "music.py", "sfx": "sfx.py", "gen": "gen.py", "mix": "mix.py",
      "beats": "beats.py", "qa": "qa.py", "crops": "crops.py", "ingest": "ingest.py", "learn": "learn.py", "mixer": "serve.py",
      "compare": "compare.py"}
ANYWHERE = {"doctor", "fonts", "voices", "compare", "spent"}  # steps that don't need a project


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
    if not os.path.exists(os.path.join(ENGINE, "node_modules/.bin/hyperframes")):
        print("  installing the engine's packages once (HyperFrames renders, GSAP animates, puppeteer brings a Chrome): about 190 MB")
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
    if not args or "--kind" not in args: sys.exit("vs new <slug> --kind explainer|reel")
    slug, kind = args[0], args[args.index("--kind") + 1]
    s = vslib.studio_root() or sys.exit("⛔ no studio yet: vs setup")
    d = os.path.join(s, "projects", slug)
    if os.path.exists(d): sys.exit(f"⛔ {d} exists")
    shutil.copytree(os.path.join(KIT, "templates", kind), d)
    if os.path.exists(os.path.join(d, "gitignore")): os.rename(os.path.join(d, "gitignore"), os.path.join(d, ".gitignore"))
    for sub in ["inputs", "media", "out", "build"] + (["voice", "music"] if kind == "explainer" else ["music"]):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    f = os.path.join(d, "plan.json" if kind == "explainer" else "reel.json")
    j = json.load(open(f)); j["name"] = slug
    json.dump(j, open(f, "w"), indent=1)
    print(f"{d}\n  the studio's profile fills in the look, the narrator and the levels; anything set in {os.path.basename(f)} overrides it")


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


def main():
    a = sys.argv[1:]
    proj = None
    if a[:1] in (["-p"], ["--project"]): proj, a = a[1], a[2:]
    if not a or a[0] in ("-h", "--help", "help"): sys.exit(__doc__)
    cmd, rest = a[0], a[1:]
    if cmd == "setup": return setup(rest)
    if cmd == "new": return new(rest)
    if cmd == "where": return where()
    if cmd not in NODE and cmd not in PY and cmd != "spent": sys.exit(f"⛔ unknown step {cmd!r}\n{__doc__}")
    d = project_dir(proj)
    if not d and cmd not in ANYWHERE: sys.exit("⛔ not in a project folder: cd into one, or vs -p <slug> " + cmd)
    if d: os.chdir(d)
    if cmd == "spent": return spent(rest)
    run = ["node", os.path.join(ENGINE, NODE[cmd])] if cmd in NODE else [python(), os.path.join(ENGINE, "py", PY[cmd])]
    os.execvp(run[0], run + rest)


if __name__ == "__main__":
    main()
