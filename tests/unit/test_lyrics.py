"""Audio with words is reviewed with its words on the screen (a reviewer, Oct 14, 2026): a song's lyrics are parsed,
laid onto what a transcript heard (which mishears rap), and a round on a sung take refuses to open without them."""
import json, os, sys
import pytest
from conftest import ENGINE, tone

sys.path.insert(0, os.path.join(ENGINE, "py"))
import lyrics  # noqa: E402
import review  # noqa: E402

SONG = """# approved Oct 14
[Intro: beat from the first downbeat]
They keep sayin' it works.
HOST: Put it on the table.

[Chorus: gang vocals]
Shake it, fix it, play it back! (HEY!)
Blue light cuttin' through the night! (ALL RIGHT!)

[Verse 1]
Put it on the table, let the code talk,
"""


def heard(*ws):
    """A transcript's words, 0.4 s apart."""
    return [{"word": w, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, w in enumerate(ws)]


def test_parse_one_block_per_line_with_its_section_and_speaker():
    B = lyrics.parse(SONG)
    assert [b["n"] for b in B] == [1, 2, 3, 4, 5]
    assert B[0] == {"n": 1, "section": "Intro", "who": "", "text": "They keep sayin' it works."}
    assert B[1]["who"] == "HOST" and B[1]["text"] == "Put it on the table."
    assert B[2]["section"] == "Chorus" and B[2]["text"].endswith("(HEY!)")  # the shouts stay: they're sung
    assert B[4]["section"] == "Verse 1"


def test_misheard_and_repeated_words_still_land_on_their_lines():
    B = lyrics.parse(SONG)
    # what whisper heard on a real take: the intro line twice, "Shake it" as "Doody, doody", "code" as "cold"
    H = heard("They", "keep", "sayin'", "it", "works", "uh", "They", "keep", "sayin'", "it", "works",
              "Put", "it", "on", "the", "table",
              "Doody", "doody", "fix", "it", "play", "it", "back", "hey",
              "Blue", "light", "cuttin'", "through", "the", "night", "all", "right",
              "Put", "it", "on", "the", "table", "let", "the", "cold", "talk")
    W = lyrics.timings(B, H, end=20.0)
    assert len(W) == sum(len(b["text"].split()) for b in B)
    t0s = [w["t0"] for w in W]
    assert t0s == sorted(t0s), "the words run in order"
    first = {w["act"]: w["t0"] for w in reversed(W)}
    assert first[3] == pytest.approx(16 * 0.4, abs=0.2)  # the chorus starts at the first "doody" (= "Shake"), not before
    assert first[5] == pytest.approx(32 * 0.4)             # verse 1's line, at its own "Put", not the intro's
    code = next(w for w in W if w["w"] == "code")
    assert code["heard"] and code["t0"] == pytest.approx(39 * 0.4)  # "cold" counts as "code"


def test_a_repeated_intro_doesnt_light_the_hook_early():
    """Suno sang the intro line three times; the hook's "Shake it" was heard as "doody, doody". The hook's line must
    light when the hook starts, not on a stray "it" inside a repeat."""
    B = lyrics.parse(SONG)
    H = heard(*("They keep sayin' it works uh".split() * 3), "Put", "it", "on", "the", "table",
              "Doody", "doody", "fix", "it", "play", "it", "back")
    W = lyrics.timings(B, H, end=12.0)
    chorus = min(w["t0"] for w in W if w["act"] == 3)
    assert chorus >= 22 * 0.4 - 0.7, f"the hook lit at {chorus}s, the intro still repeating until {17 * 0.4}s"


def test_overlapping_pieces_merge_onto_one_clock_with_no_word_twice():
    assert lyrics.pieces(20.0) == [0.0]
    assert lyrics.pieces(80.0) == [0.0, 26.0, 52.0]  # the last piece reaches the end
    w = lambda word, t: {"word": word, "start": t, "end": t + 0.3}
    # piece 2 starts at 26 s: "four" (27.0 on the clock) is heard by both pieces; the overlap splits at 28 s
    M = lyrics.merge([(0.0, [w("one", 1.0), w("four", 27.0)]), (26.0, [w("four", 1.0), w("five", 3.0)])])
    assert [(x["word"], x["start"]) for x in M] == [("one", 1.0), ("four", 27.0), ("five", 29.0)]


def test_two_passes_fill_each_others_holes_and_keep_a_shared_word_once():
    w = lambda word, t: {"word": word, "start": t, "end": t + 0.3}
    whole = [w("intro", 1.0), w("back", 50.0)]          # skipped the chorus
    parts = [w("back", 50.2), w("chorus", 60.0)]        # skipped the intro
    assert [x["word"] for x in lyrics.union(whole, parts)] == ["intro", "back", "chorus"]


def test_a_stretch_with_nothing_heard_is_reported():
    B = lyrics.parse(SONG)
    W = lyrics.timings(B, heard("They", "keep", "sayin'", "it", "works"), end=10.0)
    assert lyrics.unheard_runs(B, W) == [(2, 5)]


def test_nothing_heard_spreads_the_words_over_the_take():
    W = lyrics.timings(lyrics.parse(SONG), [], end=10.0)
    assert W[0]["t0"] == 0 and W[-1]["t1"] == pytest.approx(10.0, abs=0.01) and not any(w["heard"] for w in W)


def test_a_sung_take_with_no_timings_is_refused_and_one_with_them_gets_the_lyrics_page(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "lyrics.txt").write_text(SONG)
    take = "music/take1.mp3"
    os.makedirs("music")
    tone(take, secs=1.0)
    with pytest.raises(review.Refused, match="vs lyrics music/take1.mp3"):
        review.words_on_screen(take)
    json.dump(lyrics.timings(lyrics.parse(SONG), [], end=1.0), open("music/take1.words.json", "w"))
    review.words_on_screen(take)
    page = open("build/listen/index.html").read()
    assert "The lyrics" in page and 'data-act="5"' in page and "let the code talk" in page


def test_audio_with_no_words_anywhere_needs_to_say_its_an_instrumental(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("music")
    take = tone("music/bed.mp3", secs=1.0)
    with pytest.raises(review.Refused, match="--instrumental"):
        review.words_on_screen(take)
    review.words_on_screen(take, instrumental=True)
