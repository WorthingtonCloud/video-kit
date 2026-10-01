#!/usr/bin/env python3
"""Serve the project folder for its review pages, on this machine only:
    vs mixer [--port 4470]   →  http://localhost:4470/build/mixer/   (and /build/listen/, /build/voice-previews/)

Like `python3 -m http.server`, plus one thing: the mixer's Save button POSTs the human's choice (take, music level,
effects level) here, and it lands in the project's mix.json, where `vs mix --final` and `vs learn` read it. Nobody has to
copy a line out of the page."""
import http.server, json, os, sys
from datetime import datetime

port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 4470
KEYS = {"take", "music_db", "duck_db", "sfx_db", "fx_on", "summary", "saved"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path.split("?")[0] != "/mix.json":
            return self.send_error(404)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            choice = {k: body[k] for k in KEYS if k in body}
            choice.setdefault("saved", datetime.now().isoformat(timespec="seconds"))
            json.dump(choice, open("mix.json", "w"), indent=1)
            print(f"saved mix.json: {choice.get('summary', choice)}", flush=True)
        except Exception as e:
            return self.send_error(400, str(e))
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def end_headers(self):  # never cache: the mixer re-reads config.json and the stems after every re-mix
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass


os.makedirs("build/mixer", exist_ok=True)
print(f"http://localhost:{port}/build/mixer/  (serving {os.getcwd()}; Ctrl-C to stop)", flush=True)
http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
