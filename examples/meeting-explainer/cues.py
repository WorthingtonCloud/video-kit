"""Where every sound effect goes: cues(T, TT, C, END_T) → [(seconds, sound, align, dB vs the voice), …].
  T[segment]   the segment's start      TT[title]  when a title lands      C[scene][cue]  a word-pinned cue (plan.py)
  END_T        the end card's start (the red point lands at END_T + 1.0, the name at + 2.0, the address at + 3.0)
Sounds are the files in sfx/ (sfx.py): whoosh1/2 (into a cut) · swish1/2 (a whip, something flying by) · land1/2 (a stat
number or a panel landing) · tick1/2 (an item, a layer, a stop) · pop (an icon or app appearing) · counter · click (a
button) · powerup · shimmer (a field of things filling in) · paper (a card sliding in) · error · chime (a success) · lock
· pulse (a ring from a point) · riser (into a key line) · sting (the logo's red point landing).
align "peak" = the loudest moment on the time (whooshes into a cut); "on" = the attack on the time (everything else).
Levels approved on the demo explainer (Sep 30, 2026, "effects as mixed"): transitions -12…-14, stat thuds -14,
key hits -13…-15, small ticks and pops -16…-21, long textures -19…-21, the logo sting -9. One sound per moment; a busy
stretch gets fewer, not quieter. This file is the worked example (the demo explainer, 95 effects): rewrite it per project."""

TRIM = {"click": (0.0, 0.12)}  # ElevenLabs' "single click" came back as three clicks; keep the first


def cues(T, TT, C, END_T):
    p, f, n, w, co, jo, e = C["paradox"], C["found"], C["inbox"], C["web"], C["courier"], C["joe"], END_T
    lt, ml = C["lights"], C["meal"]
    return [
        # transitions, each on its cut
        (T["s02_switch"] - 0.08, "whoosh1", "peak", -12), (T["s03_inbox"], "swish1", "peak", -13),
        (T["s04_lights"], "swish2", "peak", -13), (T["s05_found"] - 0.08, "whoosh2", "peak", -12),
        (T["s07_courier"], "swish1", "peak", -13), (T["s08_joe"] - 0.08, "whoosh1", "peak", -12),
        (T["s09_meal"] - 0.08, "whoosh2", "peak", -13), (T["s10_room"] - 0.08, "whoosh1", "peak", -14),
        # every stat number lands with a soft thud
        *[(TT[k] + 0.03, "land1" if i % 2 else "land2", "on", -14) for i, k in enumerate(
            ["t_use", "t_pay", "t_ten", "t_190", "t_email", "t_review", "t_slow", "t_limits", "t_grade"])],
        (TT["t_thesis"], "riser", "peak", -19),
        # 1 · the rollout: the seat counter runs, the seats light up, the streak, the payroll panel
        (p["license"] - 0.1, "counter", "on", -21), (p["green"], "powerup", "peak", -19),
        (p["faster"] + 0.15, "swish2", "peak", -18), (p["payroll"] - 0.4, "paper", "on", -16),
        # 2 · the web: work items pop, the pair lights, twenty people and 190 lines fill in
        (w["work"], "pop", "on", -20), (w["pair"] - 0.1, "pulse", "on", -18), (w["twenty"] - 0.1, "shimmer", "on", -19),
        # 3 · the inbox: mail arrives, cards rise, the cancel click
        *[(n["inbox"] + 0.15 + k * 0.12, "tick1", "on", -19) for k in range(5)],
        (n["trial"] - 0.3, "paper", "on", -16), (n["one"] - 0.3, "paper", "on", -16), (n["cancel"] + 0.05, "click", "on", -13),
        # 4 · the handoffs: decisions tick in, the notes page, the action item lands on YOU, the reading card
        (lt["meeting"] - 0.1, "tick1", "on", -18), (lt["meeting"] + 0.12, "tick1", "on", -18),
        (lt["pages"] - 0.2, "paper", "on", -16), (lt["your"], "error", "on", -19), (lt["reading"] - 0.3, "paper", "on", -17),
        # 5-6 · the hundred projects, the pour into one foundation, the five layers, the agents, the chart
        (f["hundred"] - 0.4, "shimmer", "on", -20), (f["once"] + 0.1, "whoosh2", "peak", -19), (f["everyone"] + 0.1, "land2", "on", -16),
        *[(f[k], "tick1", "on", -16) for k in ("l0", "l1", "l2", "l3", "l4")],
        *[(f["build"] + k * 0.5, "pop", "on", -19) for k in range(3)], (f["one"], "land1", "on", -15),
        *[(f["uncurated"] + 0.1 + i * 0.28, "tick2", "on", -17) for i in range(3)], (f["worse"], "error", "on", -16),
        # 7 · the courier runs the stops; the agent pulses; the tools lock
        (co["expensive"], "pop", "on", -17), *[(co[k], "tick2", "on", -18) for k in ("s0", "s1", "s2", "s3", "s4")],
        (co["agent"] + 0.05, "pulse", "on", -14), (co["decides"] - 0.1, "tick1", "on", -18), (co["writes"] - 0.2, "tick1", "on", -18),
        (co["limits"] + 0.1, "lock", "on", -14),
        # 8 · Joe flies in, the spreadsheet, Joe leaves, the agent stays, the checks, the A+
        (jo["joe"] - 0.1, "swish2", "peak", -17), (jo["sheet"] - 0.5, "paper", "on", -15), (jo["leaves"] - 0.05, "swish1", "peak", -18),
        (jo["stays"] + 0.05, "pulse", "on", -16), (jo["check"], "tick1", "on", -17), (jo["grade"], "chime", "on", -15),
        # 9 · a model and a "good luck", an app for every task; the agent forms, the model swaps, the scaffolding fills in
        (ml["people"] - 0.3, "pop", "on", -20), (ml["model"] - 0.05, "land2", "on", -14), (ml["good"] + 0.05, "land1", "on", -15),
        *[(ml["different"] + k * 0.15, "pop" if k % 2 == 0 else "tick1", "on", -21) for k in range(8)],
        (ml["ai"], "whoosh2", "peak", -18), (ml["agents"] - 0.25, "paper", "on", -16), (ml["meal"], "pulse", "on", -14),
        (ml["models"] + 0.15, "swish1", "peak", -17), (ml["swapped"] + 0.1, "tick1", "on", -16),
        (ml["stays"], "swish2", "peak", -17), (ml["stays"] + 0.5, "tick1", "on", -17),
        *[(ml[k] - 0.1, "tick1", "on", -16) for k in ("data", "tools", "governance")],
        # the end card: collapse into the point, the red point lands (the hit), the name, the address
        (e - 0.1, "swish1", "peak", -15), (e + 1.0, "sting", "on", -9), (e + 2.0, "land2", "on", -15), (e + 3.0, "tick1", "on", -17),
    ]
