#!/usr/bin/env python3
"""A listening page for narration takes, with the script beside them (stage directions shown as gray tags):
    vs listen voice/narration-v4.mp3 [more takes…] [--title "Explainer narration, take 4"]
→ build/listen/index.html. The human reviews a take here before any picture is built (notes as "time + what")."""
import html, os, re, sys
args = [a for a in sys.argv[1:]]
title = args.pop(args.index("--title") + 1) if "--title" in args else "Explainer narration"
if "--title" in args: args.remove("--title")
os.makedirs("build/listen", exist_ok=True)
acts = [b for b in open("narration.txt").read().split("\n\n") if b.strip()]
def act_html(b):
    head = next((l[1:].strip() for l in b.splitlines() if l.startswith("#")), "")
    body = " ".join(l for l in b.splitlines() if l.strip() and not l.startswith("#"))
    body = re.sub(r"\[([^\]]+)\]", lambda m: f'<span class="tag">{html.escape(m.group(1))}</span>', html.escape(body, quote=False).replace("&#x27;", "'"))
    return f'<div class="act"><div class="at">{html.escape(head)}</div><p>{body}</p></div>'
cards = "".join(f'<div class="card{" hero" if i == 0 else ""}"><div class="name">{html.escape(os.path.basename(t))}</div><audio controls preload="none" src="../../{t}"></audio></div>' for i, t in enumerate(args))
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>
:root{{--bg:#111114;--card:#1c1d21;--line:#2a2b30;--ink:#f4f4f2;--dim:#9b9da4;--accent:#e8402c}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,system-ui,sans-serif;padding:32px 16px}}.wrap{{max-width:760px;margin:0 auto}}
h1{{font-size:26px;margin:0 0 18px}}h2{{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);margin:28px 0 10px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}}.card.hero{{border-color:var(--accent)}}
.name{{font-weight:700;margin-bottom:8px}}audio{{width:100%}}.act{{border-left:3px solid var(--line);padding:2px 0 2px 14px;margin:0 0 14px}}
.at{{font:700 13px ui-monospace,monospace;color:var(--accent)}}.act p{{margin:4px 0 0}}.tag{{font:600 12px ui-monospace,monospace;color:var(--dim);background:#232327;border-radius:6px;padding:1px 6px;margin-right:4px}}
</style></head><body><div class="wrap"><h1>{html.escape(title)}</h1>{cards}<h2>The script (gray tags direct the voice; they aren't spoken)</h2>{"".join(act_html(b) for b in acts)}</div></body></html>"""
open("build/listen/index.html", "w").write(page)
print("build/listen/index.html")
