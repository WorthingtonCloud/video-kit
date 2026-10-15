#!/usr/bin/env python3
"""A song take's lyrics, timed to the take, so Review Studio shows the words on screen with the line being sung lit and
the page scrolling along (a reviewer, Oct 14, 2026: any audio with words is reviewed with its words on the screen).
    vs lyrics music/take1.mp3 [more takes…] --yes
    vs lyrics mix/song-v1.mp3 --vocals mix/song-v1.vox.wav --yes   (hear the voices alone: use this whenever you have them)
The words come from lyrics.txt, the project's approved lyrics: a [Section] line heads each part (anything after a colon
in it is direction for the music model and isn't shown), one sung line per line, a spoken line as "NAME: words",
# lines are comments. Each take is transcribed once (OpenAI whisper-1 with word times, under a cent a minute; kept in
<take>.heard.json so it's never paid twice; twice over, whole and in pieces, since whisper drops whole stretches of a
mix at random; from the voices alone with --vocals, which is cleaner still), and the lyrics are laid onto it with a fuzzy word alignment, because a
transcript mishears rap. → <take>.words.json beside each take (the clock a take round lights the lines by) and the
listening page (vs listen) with the lyrics. vs review open and vs review offer refuse a song take that has none."""
import difflib, functools, json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vslib  # noqa: E402

LYRICS = "lyrics.txt"
SECTION = re.compile(r"^\[([^\]:]+)(?::[^\]]*)?\]$")
WHO = re.compile(r"^([A-Z][A-Z .'-]{0,20}):\s+(.+)$")
GAP = -0.35       # the cost of a word heard but not in the lyrics (an ad-lib, a repeat), or sung but not heard
SECS_PER = 0.28   # an unheard word's length, for words before the first heard one and after the last
CHUNK, OVER = 30.0, 4.0  # also transcribed in 30 s pieces overlapping 4 s. whisper-1 drops whole stretches of a song
                         # at random: on one mix the whole-song pass skipped the final chorus (20 s) and the pieces
                         # pass skipped the intro (Oct 14, 2026). Its misses are gaps, not wrong words, so both
                         # passes are kept and combined (union): each fills the other's holes.


def parse(text):
    """lyrics.txt → one block per sung or spoken line, in order: {n, section, who, text}."""
    blocks, sec = [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = SECTION.match(line)
        if m:
            sec = m.group(1).strip()
            continue
        m = WHO.match(line)
        who, words = (m.group(1).strip(), m.group(2).strip()) if m else ("", line)
        blocks.append({"n": len(blocks) + 1, "section": sec, "who": who, "text": words})
    return blocks


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


@functools.lru_cache(maxsize=None)
def sim(a, b):
    """How alike two words are, or -1: close enough counts ("cold" for "code"), a different word doesn't."""
    if not a or not b:
        return -1.0
    if a == b:
        return 1.0
    r = difflib.SequenceMatcher(a=a, b=b).ratio()
    return r if r >= 0.67 else -1.0


def align(A, B):
    """Needleman-Wunsch on fuzzy word likeness: the pairs (i in A, j in B), in order, of the words that match. An exact
    diff loses a line to one misheard word; this keeps every true pair around it."""
    n, m = len(A), len(B)
    S = [[0.0] * (m + 1) for _ in range(n + 1)]
    P = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        S[i][0], P[i][0] = GAP * i, 1
    for j in range(1, m + 1):
        S[0][j], P[0][j] = GAP * j, 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d, u, l = S[i - 1][j - 1] + sim(A[i - 1], B[j - 1]), S[i - 1][j] + GAP, S[i][j - 1] + GAP
            S[i][j], P[i][j] = (d, 0) if d >= u and d >= l else (u, 1) if u >= l else (l, 2)
    pairs, i, j = [], n, m
    while i > 0 or j > 0:
        p = P[i][j] if i > 0 and j > 0 else (1 if i > 0 else 2)
        if p == 0:
            if sim(A[i - 1], B[j - 1]) > 0:
                pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif p == 1:
            i -= 1
        else:
            j -= 1
    return pairs[::-1]


def place(T, toks, wt, a, b):
    """The unheard words between heard words a and b. Words of a's line follow a at a word's pace, words of b's line
    lead into b, and whole lines in between share what's left; a gap too short for that is shared by length. (A long
    gap is usually a repeat or an ad-lib: spreading the words over it lit a line seconds before it was sung.)"""
    lo, hi = T[a][1], max(T[a][1], T[b][0])
    run = list(range(a + 1, b))
    head = [i for i in run if toks[i][0] == toks[a][0]]
    tail = [i for i in run if toks[i][0] == toks[b][0] and i not in head]
    mid = [i for i in run if i not in head and i not in tail]
    need = sum(wt[i] for i in head + tail) * SECS_PER
    if hi - lo < need * 1.2 or (mid and hi - lo < (need + sum(wt[i] for i in mid) * SECS_PER)):
        tot, t = sum(wt[i] for i in run), lo
        for i in run:
            d = (hi - lo) * wt[i] / tot
            T[i] = (t, t + d)
            t += d
        return
    t = lo
    for i in head:
        T[i] = (t, t + wt[i] * SECS_PER)
        t = T[i][1]
    t2 = hi - sum(wt[i] for i in tail) * SECS_PER
    for i in tail:
        T[i] = (t2, t2 + wt[i] * SECS_PER)
        t2 = T[i][1]
    if mid:
        m0, m1 = t, hi - sum(wt[i] for i in tail) * SECS_PER
        tot = sum(wt[i] for i in mid)
        for i in mid:
            d = (m1 - m0) * wt[i] / tot
            T[i] = (m0, m0 + d)
            m0 += d


def timings(blocks, heard, end):
    """Every lyric word gets a time: the heard word it matched, or a share of the gap between the matched words around
    it (by length). heard: [{word, start, end}] → [{w, t0, t1, act}], act = the line's number."""
    toks = [(b["n"], w) for b in blocks for w in b["text"].split()]
    T = [None] * len(toks)
    pairs = align([norm(w) for _, w in toks], [norm(h["word"]) for h in heard])
    # a short word ("it", "the") matched on its own, with neither neighbor matched beside it, is a coincidence: the
    # intro line's "it", sung three times, gave the hook's first words a time 6 s early (Oct 14, 2026)
    P = set(pairs)
    pairs = [(i, j) for i, j in pairs if len(norm(toks[i][1])) > 3 or (i - 1, j - 1) in P or (i + 1, j + 1) in P]
    for i, j in pairs:
        T[i] = (float(heard[j]["start"]), float(heard[j]["end"]))
    got = {i for i, _ in pairs}
    wt = [max(1.0, len(norm(w)) / 3.0) for _, w in toks]
    k = [i for i, x in enumerate(T) if x]
    if not k:  # nothing heard: spread the words evenly over the take
        step = end / max(1, sum(wt))
        t = 0.0
        for i in range(len(toks)):
            T[i] = (t, t + wt[i] * step)
            t += wt[i] * step
    else:
        t = T[k[0]][0]  # before the first heard word: back from it
        for i in range(k[0] - 1, -1, -1):
            T[i] = (max(0.0, t - wt[i] * SECS_PER), t)
            t = T[i][0]
        for a, b in zip(k, k[1:]):  # between two heard words
            if b - a > 1:
                place(T, toks, wt, a, b)
        t = T[k[-1]][1]  # after the last heard word: forward from it
        for i in range(k[-1] + 1, len(toks)):
            T[i] = (t, min(end, t + wt[i] * SECS_PER))
            t = T[i][1]
    last = 0.0  # never out of order: a stray early match can't pull a later line before an earlier one
    for i in range(len(T)):
        a = max(T[i][0], last)
        T[i] = (a, max(a, T[i][1]))
        last = a
    return [{"w": w, "t0": round(T[i][0], 3), "t1": round(T[i][1], 3), "act": n, "heard": i in got}
            for i, (n, w) in enumerate(toks)]


def words_path(take):
    return re.sub(r"\.[a-z0-9]+$", ".words.json", take)


def heard_path(take):
    return re.sub(r"\.[a-z0-9]+$", ".heard.json", take)


def needs(takes):
    """The takes that have lyrics to show (lyrics.txt) but no timings yet."""
    return [t for t in takes if os.path.exists(LYRICS) and not os.path.exists(words_path(t))]


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def pieces(dur):
    """Where each transcribed piece starts: every CHUNK - OVER seconds, the last one reaching the end."""
    out, t = [], 0.0
    while True:
        out.append(round(t, 3))
        if t + CHUNK >= dur:
            return out
        t += CHUNK - OVER


def merge(chunks):
    """[(start, [{word, start, end}])] → one word list on the take's clock. Each piece keeps the words in its own
    middle (the overlap is split down its center), so a word heard twice in an overlap is kept once."""
    words = []
    for i, (s0, W) in enumerate(chunks):
        lo = s0 + OVER / 2 if i else -1.0
        hi = chunks[i + 1][0] + OVER / 2 if i + 1 < len(chunks) else float("inf")
        for w in W:
            t = s0 + float(w["start"])
            if lo <= t < hi:
                words.append({"word": w["word"], "start": round(t, 3), "end": round(s0 + float(w["end"]), 3)})
    return words


def union(*lists):
    """Several transcripts of one take → one word list in time order; a word heard by two passes (same word within
    0.35 s) is kept once."""
    out = []
    for w in sorted((w for L in lists for w in L), key=lambda w: w["start"]):
        if not any(norm(x["word"]) == norm(w["word"]) and abs(x["start"] - w["start"]) < 0.35 for x in out[-6:]):
            out.append(w)
    return out


def heard_of(take, yes, vocals=None):
    """The take's words as heard, with times: a whole-take pass and a pass in overlapping pieces, combined (paid
    once: kept beside the take). vocals: the take's voices alone on the same clock (a vocal stem, or a mix's voices
    rendered through the same edits), heard instead of the take: far cleaner than a full mix."""
    hp = heard_path(take)
    if os.path.exists(hp):
        return vslib.read_json(hp)
    src, take = take, vocals or take
    dur = duration(take)
    starts = pieces(dur)
    usd = round((2 * dur + OVER * (len(starts) - 1)) / 60 * 0.006, 4)
    vslib.gate("openai", f"Transcribing {os.path.basename(take)} twice (whole, and {len(starts)} pieces) to time its "
               "lyrics", usd=usd, yes=yes)
    row = vslib.log("openai", f"lyric timing {os.path.basename(take)}", usd=usd,
                    note=f"whisper-1, word times, whole + {len(starts)} pieces")
    fields = ["model=whisper-1", "response_format=verbose_json", "timestamp_granularities[]=word", "language=en"]
    chunks = []
    with tempfile.TemporaryDirectory() as d:
        whole = os.path.join(d, "whole.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", take, "-ac", "1", "-ar", "16000", "-b:a", "64k", whole], check=True)
        W0 = [{"word": w["word"], "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)}
              for w in json.loads(vslib.transcribe(whole, fields, row)).get("words") or []]
        for i, s0 in enumerate(starts):
            part = os.path.join(d, f"p{i}.mp3")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s0), "-t", str(CHUNK), "-i", take, "-ac", "1",
                            "-ar", "16000", "-b:a", "64k", part], check=True)
            chunks.append((s0, json.loads(vslib.transcribe(part, fields, row)).get("words") or []))
    vslib.done(row)
    W1 = merge(chunks)
    J = {"words": union(W0, W1), "passes": {"whole": len(W0), "pieces": len(W1)}, "pieces": starts, "piece_s": CHUNK,
         "heard_from": os.path.basename(take)}
    hp = heard_path(src)
    with open(hp, "w") as f:
        json.dump(J, f, indent=0)
    return J


def unheard_runs(blocks, W):
    """Runs of two or more lines in a row with no word matched: their times are a guess, and the human should know."""
    heard = {w["act"] for w in W if w.get("heard")}
    runs, cur = [], []
    for b in blocks:
        if b["n"] in heard:
            if len(cur) > 1:
                runs.append((cur[0], cur[-1]))
            cur = []
        else:
            cur.append(b["n"])
    if len(cur) > 1:
        runs.append((cur[0], cur[-1]))
    return runs


def main(argv):
    yes = "--yes" in argv
    title = argv[argv.index("--title") + 1] if "--title" in argv else None
    vocals = argv[argv.index("--vocals") + 1] if "--vocals" in argv else None
    takes = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in ("--title", "--vocals"))]
    if vocals and len(takes) != 1:
        sys.exit("⛔ --vocals goes with one take: the voices of that take, on its clock")
    if not takes:
        sys.exit(__doc__)
    if not os.path.exists(LYRICS):
        sys.exit(f"⛔ no {LYRICS} in this project: the approved lyrics, a [Section] line above each part, one line per line")
    blocks = parse(open(LYRICS, encoding="utf-8").read())
    if not blocks:
        sys.exit(f"⛔ {LYRICS} has no lines")
    for t in takes:
        if not os.path.exists(t):
            sys.exit(f"⛔ {t} doesn't exist")
        H = heard_of(t, yes, vocals)
        W = timings(blocks, H.get("words") or [], duration(t))
        with open(words_path(t), "w") as f:
            json.dump(W, f, indent=0)
        print(f"{words_path(t)}: {len(blocks)} lines, {sum(w['heard'] for w in W)} of {len(W)} words matched to what "
              "the transcript heard (the rest share the time between them)")
        for a, b in unheard_runs(blocks, W):
            print(f"  ⚠️  lines {a}-{b}: nothing heard there, so their times are a guess (listen to that stretch)")
    cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "listen.py"), *takes]
    if title:
        cmd += ["--title", title]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main(sys.argv[1:])
