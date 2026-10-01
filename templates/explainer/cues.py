"""Where every sound effect goes: cues(T, TT, C, END_T) → [(seconds, sound, align, dB vs the voice), …].
  T[segment]   the segment's start      TT[title]  when a title lands      C[scene][cue]  a word-pinned cue (plan.py)
  END_T        the end card's start (the point lands at END_T + 1.0, the name at + 2.0, the address at + 3.0)
A sound is a library name (vs sfx list: the kit's 30 plus anything bought or brought) or a path ("media/door.wav").
align "peak" = the loudest moment on the time (a whoosh into a cut); "on" = the attack on the time (everything else).
Starting levels that were approved: transitions -12…-15, a number landing -14, key hits -12…-15, ticks and pops -16…-21,
long textures (a crowd, a shimmer) -16…-21, the logo sting -9. One sound per moment; a busy stretch gets fewer, not quieter.
The worked example with 95 cues is the kit's examples/meeting-explainer/cues.py."""

TRIM = {}  # {"receipt": (0.0, 0.9)}: play only part of a sound, every time it's used


def cues(T, TT, C, END_T):
    e = END_T
    return [
        (T["s02_close"] - 0.08, "whoosh1", "peak", -13),
        (TT["t_close"], "riser", "peak", -20),
        # the end card: into the point, the point lands (the hit), the name, the address
        (e - 0.1, "swish1", "peak", -15), (e + 1.0, "sting", "on", -9), (e + 2.0, "land2", "on", -15), (e + 3.0, "tick1", "on", -17),
    ]
