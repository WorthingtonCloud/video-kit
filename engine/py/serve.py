#!/usr/bin/env python3
"""The mixer: Review Studio's Mix panel, on this machine only.
    vs mixer [--port 4470]   →  http://localhost:4470/review/#mix

Every stem plays at once, so a take switch is instant and in sync; the picture follows the sound. The human picks the
music take, sets the music and effects levels, and presses Save: the choice lands in the project's mix.json (and the
review diary logs it as mix.saved), where vs mix --final and vs learn read it. Nobody copies a line out of the page.
vs mix makes what it plays (build/mixer/: the stems and the settings); it's the same server as vs review."""
import sys
import review_server

port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 4470
review_server.serve(port, path="/review/#mix")
