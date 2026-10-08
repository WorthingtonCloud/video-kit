"""Review Studio's server (vs review runs it; vs mixer too). Three jobs, on this machine only:
  · the page: /review/ is engine/review/ (the kit's, never copied into a project), its type from the studio's fonts
  · the project's files: the rendered versions (with byte ranges, so the video seeks to any frame), the build's
    composition and its maps (timeline, elements, findings), the mixer's stems
  · the diary's one door for the page: POST /review/api/events appends the human's events through review.append (the
    same lock the agent's commands take), then draws the stills; GET /review/api/state is the snapshot plus what the
    page needs to find the round's files. POST /mix.json still takes the mixer's Save (and logs it as mix.saved).
Requests must come from the page itself: the Host is this machine, and a write carries JSON from this origin (a web page
elsewhere in the same browser can't post to it)."""
import http.server, json, mimetypes, os, posixpath, re, socket, urllib.parse
from datetime import datetime

import vslib
import review

PAGE = os.path.join(vslib.ENGINE, "review")
MIX_KEYS = review.MIX_KEYS


def kit_version():
    return (vslib.read_json(os.path.join(vslib.KIT, ".claude-plugin/plugin.json")) or {}).get("version")


def url(p):
    """A project file's address (every shape of a video lives in its one project: engine/protocol/files.md)."""
    if not p:
        return None
    return "/" + os.path.normpath(p).replace(os.sep, "/")


def context(S):
    """Where the page finds the round's files. A version's own maps (drafts/vN/data/<shape>/, its timeline) win; the build's
    are used only when they're the same composition (same fingerprint). exact: false = the build moved on since this
    version was rendered, so outlines come from the nearest map and may be off."""
    versions = [{"video": url(p), "version": d["v"], "cut": vslib.SHAPES[d["shape"]]} for p, d in vslib.drafts()]
    kind = "explainer" if os.path.exists("plan.json") else "reel"
    ctx = {"project": vslib.project_name(), "kit": kit_version(), "versions": versions, "round": None, "mixer": None,
           "kind": kind, "stages": review.STAGES[kind], "plain": review.PLAIN, "waiting": review.agent_waiting(),
           "listen": None}
    lp = "build/listen/index.html"
    if os.path.exists(lp):  # vs listen's page: the narration takes, played here until a round has a picture
        ctx["listen"] = f"/build/listen/?v={int(os.path.getmtime(lp))}"
    cfg = vslib.read_json("build/mixer/config.json")
    if cfg:  # vs mix made stems: the Mix panel plays them (the video it mixed against, for vs mixer with no round)
        ctx["mixer"] = {"config": "/build/mixer/config.json", "media": "/build/mixer/media/",
                        "video": url(cfg.get("video")) or "/build/mixer/media/video.mp4", "tag": cfg.get("tag"),
                        "saved": vslib.read_json("mix.json")}
    R = review.current(S)
    if not R:
        return ctx
    words = (vslib.read_json("plan.json") or {}).get("words")  # an explainer's clock: the narrator's words

    def shape(video, cut, size):
        """One render's files: its version's own maps first, this project's build only when it's the same composition."""
        n, base = review.version_of(video)  # base: the render's data folder, drafts/vN/data/<shape>
        vtl = vslib.read_json(f"{base}/timeline.json")
        btl = vslib.read_json("build/timeline.json")
        fp = (vtl or {}).get("fingerprint")
        same = bool(btl and fp and btl.get("fingerprint") == fp)

        def pick(name):
            if os.path.exists(f"{base}/{name}"):
                return url(f"{base}/{name}"), True
            F = vslib.read_json(f"build/{name}")
            if F:
                return url(f"build/{name}"), bool(fp and F.get("fingerprint") == fp)
            return None, False

        els, els_exact = pick("elements.json")
        fnd, fnd_exact = pick("findings.json")
        comp = same and os.path.exists("build/comp/index.html")  # the composition that made this version, to hit-test
        return {
            "video": url(video), "version": n, "cut": cut, "size": size,
            "timeline": url(f"{base}/timeline.json") if vtl else url("build/timeline.json") if btl else None,
            "elements": els, "findings": fnd,
            "words": url(words) if words and os.path.exists(words) else None,
            "cues": url(f"{base}/cues.json") if os.path.exists(f"{base}/cues.json")
            else url("build/mix/cues.json") if same and os.path.exists("build/mix/cues.json") else None,
            "qa": url(f"{base}/qa.json") if os.path.exists(f"{base}/qa.json") else None,  # qa.py's warnings
            "comp": url("build/comp/index.html") if comp else None,
            "exact": {"timeline": bool(vtl), "elements": els_exact, "findings": fnd_exact, "comp": comp},
        }

    ctx["round"] = shape(R["video"], R["cut"], R.get("size"))
    if R.get("cuts"):  # both shapes: the page shows one at a time (ctx.round = the one it opens on)
        ctx["round"]["cuts"] = [shape(c["video"], c["cut"], c.get("size")) for c in R["cuts"]]
    return ctx


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = "video-kit-review"

    # ── who may ask ──
    def _ours(self, write):
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("localhost", "127.0.0.1"):
            return False  # another name pointing here (DNS rebinding) is refused
        if write:
            origin = self.headers.get("Origin")
            if origin and urllib.parse.urlsplit(origin).hostname not in ("localhost", "127.0.0.1"):
                return False
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return False  # a cross-site form can't send JSON without asking first, and nobody answers
        return True

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")

    # ── where a path lives: the page, the studio's fonts, else the project ──
    def translate_path(self, path):
        p = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        root = os.getcwd()
        if p == "/review" or p.startswith("/review/"):
            root, p = PAGE, p[len("/review"):]
            if p.startswith("/fonts/"):
                root, p = os.path.join(vslib.studio_root() or "", "library/brand/fonts"), p[len("/fonts"):]
        parts = [w for w in posixpath.normpath(p).split("/") if w and w not in (".", "..")]
        return os.path.join(root, *parts) + ("/" if p.endswith("/") else "")

    def do_GET(self):
        if not self._ours(False):
            return self.send_error(403)
        p = urllib.parse.urlsplit(self.path).path
        if p == "/review/api/state":  # the page's picture: the human's held feedback included
            S = review.state("human")
            return self._json(200, {"state": S, "context": context(S)})
        if p == "/":
            self.send_response(302)
            self.send_header("Location", "/review/")
            return self.end_headers()
        rng = self.headers.get("Range")
        f = self.translate_path(self.path)
        if p.startswith("/review/fonts/") and p.endswith(".css") and not os.path.isfile(f):
            # no studio fonts yet (vs setup fetches them): the page falls back to the system's type, quietly
            self.send_response(200)
            self.send_header("Content-Type", "text/css")
            self.send_header("Content-Length", "0")
            return self.end_headers()
        if rng and os.path.isfile(f):
            return self._range(f, rng)
        return super().do_GET()

    def do_HEAD(self):
        if not self._ours(False):
            return self.send_error(403)
        return super().do_HEAD()

    def _range(self, f, rng):
        """A byte range (the video asks for one on every seek)."""
        size = os.path.getsize(f)
        m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
        if not m or (m.group(1) == "" and m.group(2) == ""):
            return self.send_error(416)
        if m.group(1) == "":
            a, b = max(0, size - int(m.group(2))), size - 1
        else:
            a, b = int(m.group(1)), min(size - 1, int(m.group(2)) if m.group(2) else size - 1)
        if a >= size or a > b:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            return self.end_headers()
        self.send_response(206)
        self.send_header("Content-Type", mimetypes.guess_type(f)[0] or "application/octet-stream")
        self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
        self.send_header("Content-Length", str(b - a + 1))
        self.end_headers()
        with open(f, "rb") as fh:
            fh.seek(a)
            left = b - a + 1
            try:
                while left > 0:
                    chunk = fh.read(min(1 << 16, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the video moved on to another range

    def do_POST(self):
        if not self._ours(True):
            return self.send_error(403)
        p = urllib.parse.urlsplit(self.path).path
        try:
            body = self._body()
        except ValueError as x:
            return self._json(400, {"error": f"not JSON: {x}"})
        if p == "/review/api/events":
            events = body.get("events") or []
            bad = [e.get("type") for e in events if e.get("type") not in review.HUMAN]
            if bad:
                return self._json(403, {"error": f"the page can't write {', '.join(map(str, bad))}"})
            try:
                S, new = review.append(events, "human")
            except review.Refused as x:
                return self._json(409, {"error": str(x)})
            review.frames_for(S, new)
            for e in new:
                if e["type"] != "time.spent":
                    print(f"  {e['type']}" + (" (held)" if e.get("held") else "")
                          + (f" {(e.get('note') or {}).get('id') or e.get('id') or e.get('of') or ''}" if e["type"].startswith(("note", "finding", "choice", "undo")) else ""), flush=True)
            if any(e["type"] == "round.sent" for e in new):
                R = review.current(S)
                print(f"round {R['n']} sent ({R['sends']}): → vs review show", flush=True)
            first = S["events"] - len(new) + 1  # each new event's line in the log: what Undo names
            return self._json(200, {"ok": True, "state": S, "context": context(S),
                                    "ids": [(e.get("note") or {}).get("id") for e in new], "seqs": list(range(first, first + len(new)))})
        if p == "/mix.json":  # the mixer's Save: the human's levels, into the project
            choice = {k: body[k] for k in MIX_KEYS if k in body}
            choice.setdefault("saved", datetime.now().isoformat(timespec="seconds"))
            json.dump(choice, open("mix.json", "w"), indent=1)
            try:
                review.append([{"type": "mix.saved", "mix": choice}], "human")
            except review.Refused:
                pass
            print(f"saved mix.json: {choice.get('summary', choice)}", flush=True)
            return self._json(200, {"ok": True})
        return self.send_error(404)

    def end_headers(self):  # never cache: the page re-reads the state, the maps and the stems after every change
        self.send_header("Cache-Control", "no-store")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def log_message(self, *a):
        pass

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass


def free_port(port):
    for p in range(port, port + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)):
                return p
    raise SystemExit(f"⛔ ports {port}–{port + 19} are all in use: vs review --port <another>")


def serve(port=4470, path="/review/"):
    p = free_port(port)
    if p != port:
        print(f"(port {port} is in use: using {p})")
    os.makedirs(review.REVIEW, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", p), Handler)
    print(f"http://localhost:{p}{path}  (serving {os.getcwd()}; Ctrl-C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
