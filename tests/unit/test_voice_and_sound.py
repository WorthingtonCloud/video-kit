"""Voice splices, sound-effect names, sound measuring and the beat grid (vslib + beats.py)."""
import json, os, re, subprocess, sys
import numpy as np
import pytest
from conftest import ENGINE, tone
import vslib

W = lambda act, *ts: [{"w": f"w{act}{i}", "t0": a, "t1": b, "act": act} for i, (a, b) in enumerate(ts)]
BASE = W(1, (0.2, 0.6), (0.7, 1.4)) + W(2, (2.0, 2.4), (2.5, 3.1)) + W(3, (4.0, 4.5))


def test_a_splice_cuts_after_the_last_word_never_mid_word():
    # the first splice cut at "new first word - its lead-in" and clipped the tail of "generously" (Sep 30, 2026)
    sp = vslib.splice_plan(BASE, W(2, (0.5, 0.9), (1.0, 1.6)))
    assert sp["cut"] == 1.6 and sp["start"] == 0.2  # 0.2 s after act 1's last word; 0.3 s before the run's first
    assert sp["words"][2]["t0"] == pytest.approx(0.5 + sp["off"])


def test_a_splice_from_the_middle_keeps_the_later_acts():
    # the old splice silently dropped acts 6-8 when act 5 was re-recorded (Oct 1, 2026)
    sp = vslib.splice_plan(BASE, W(2, (0.5, 0.9), (1.0, 1.6)))
    assert [w["act"] for w in sp["words"]] == [1, 1, 2, 2, 3]
    assert sp["cut2"] == 1.8 and sp["start2"] == 3.7


def test_a_splice_from_the_top_opens_the_take_and_keeps_the_rest():
    # a calmer open re-recorded as acts 1-2 was refused: "the base has no acts before act 1" (Oct 9, 2026)
    sp = vslib.splice_plan(BASE, W(1, (0.5, 0.9)) + W(2, (1.0, 1.6)))
    assert sp["cut"] == 0 and sp["start"] == 0.2 and sp["off"] == -0.2
    assert [w["act"] for w in sp["words"]] == [1, 2, 3] and sp["words"][0]["t0"] == pytest.approx(0.3)
    assert sp["cut2"] == 1.8 and sp["start2"] == 3.7
    assert sp["words"][-1]["t0"] == pytest.approx(4.0 + sp["off2"])


def test_a_run_that_is_the_whole_take_is_not_a_splice():
    with pytest.raises(ValueError):
        vslib.splice_plan(W(1, (0.2, 0.6)), W(1, (0.1, 0.4)))


def test_every_effect_is_named_by_what_its_pinned_to():
    T, TT, C = {"s01": 0.0, "s02": 5.0}, {"t_use": 2.0}, {"inbox": {"cancel": 3.4}}
    cues = [(4.92, "whoosh1", "peak", -12), (2.03, "land1", "on", -14), (3.45, "click", "on", -13), (3.5, "click", "on", -13),
            (7.0, "media/door.wav", "on", -10)]
    assert [c["el"] for c in vslib.name_cues(cues, T, TT, C)] == [
        "sfx/whoosh1@s02", "sfx/land1@t_use", "sfx/click@inbox.cancel", "sfx/click@inbox.cancel#2", "sfx/door@s02"]


def test_measure_finds_a_sound_and_flags_a_silent_one(tmp_path):
    m = vslib.measure(tone(tmp_path / "loud.wav", 0.5, db=-6))
    assert m["secs"] == pytest.approx(0.5, abs=0.02) and m["peak_dbfs"] == pytest.approx(-6, abs=1) and "warning" not in m
    # two "rubber stamps" came back at -55 and -49 dBFS; normalized, the noise would have been as loud as a stamp
    assert "nearly silent" in vslib.measure(tone(tmp_path / "quiet.wav", 0.5, db=-50)).get("warning", "")


def test_beats_finds_the_grid_of_a_click_track(tmp_path):
    sr = 22050
    x = np.zeros(sr * 12, np.float32)
    for k in range(24):
        t = int(k * 0.5 * sr)
        x[t:t + 200] += 0.6 * np.sin(np.arange(200) * 0.3) * np.exp(-np.arange(200) / 60)
    f = tmp_path / "clicks.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-", str(f)],
                   input=x.tobytes(), check=True)
    out = subprocess.run([sys.executable, os.path.join(ENGINE, "py/beats.py"), str(f)], capture_output=True, text=True).stdout
    beat = float(next(l for l in out.splitlines() if l.startswith("beat")).split()[1].rstrip("s"))
    assert beat == pytest.approx(0.5, abs=0.003)


def test_the_listen_page_titles_act_one_by_its_own_heading(tmp_path):
    # the template puts the file's comment lines right above "# 1 …" in one block; the page showed the comment as
    # act 1's title (jev-explainer, Oct 1, 2026)
    (tmp_path / "narration.txt").write_text("# Narration v1. About the file.\n# More about it.\n# 1 The hook\n[wry] Hello.\n\n"
                                            "# 2 The close\nBye.\n")
    subprocess.run([sys.executable, os.path.join(ENGINE, "py", "listen.py"), "voice/x.mp3"], cwd=tmp_path, check=True,
                   capture_output=True)
    page = (tmp_path / "build/listen/index.html").read_text()
    assert '<div class="at">1 The hook</div>' in page and '<div class="at">2 The close</div>' in page
    assert "About the file" not in page


def test_a_splice_refuses_to_write_over_the_timings_it_reads(tmp_path):
    # "narrate v2 --acts 5" then "voicebed --out v2" would have replaced the run's own words with the spliced ones
    # (jev-explainer, Oct 1, 2026)
    (tmp_path / "voice").mkdir()
    for tag in ("v1", "v2"):
        (tmp_path / f"voice/narration-{tag}.words.json").write_text("[]")
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "py", "voicebed.py"), "--base", "voice/narration-v1.mp3",
                        "--take", "voice/narration-v2.mp3", "--out", "v2"], cwd=tmp_path, capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": os.path.join(ENGINE, "py")})
    assert r.returncode and "would write over" in r.stderr
    assert (tmp_path / "voice/narration-v2.words.json").read_text() == "[]"


def test_a_splice_cuts_in_the_pause_the_audio_shows_not_where_the_timings_say(tmp_path):
    # word timings ran 0.2 s late on a real take: a cut 0.2 s after act 4's last word kept "Pic-" of the old act 5's
    # "Picture", and the new take said "Picture" again (the reviewer heard a repeat, jev-explainer round 1, Oct 1, 2026)
    import wave
    sr, x = 48000, np.zeros(int(48000 * 4.2), np.float32)
    for a, b in ((0.0, 1.0), (1.3, 2.3), (2.6, 3.6)):  # three acts, a real pause before each new one
        t = np.arange(int((b - a) * sr)) / sr
        x[int(a * sr):int(a * sr) + len(t)] = 0.5 * np.sin(2 * np.pi * 220 * t)
    with wave.open(str(tmp_path / "base.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr), w.writeframes((x * 32767).astype("<i2").tobytes())
    late = 0.25  # the timings say every word starts and ends a quarter second after it really does
    base = W(1, (0.0 + late, 1.0 + late)) + W(2, (1.3 + late, 2.3 + late)) + W(3, (2.6 + late, 3.6 + late))
    cut = vslib.quietest(str(tmp_path / "base.wav"), base[0]["t1"] - 0.3, base[1]["t0"] + 0.05)
    assert 1.0 < cut < 1.3  # in the silence, before the old act 2 starts (the timing rule would cut at 1.45: inside it)
    back = vslib.quietest(str(tmp_path / "base.wav"), base[1]["t1"] - 0.3, base[2]["t0"] + 0.05)
    assert 2.3 < back < 2.6
    sp = vslib.splice_plan(base, W(2, (0.3, 1.3)), cut_at=cut, start2_at=back)
    assert sp["cut"] == cut and sp["start2"] == back
    # cutting at the END of the pause keeps all of it before the new act; resuming at its START keeps the next one whole
    end = vslib.quietest(str(tmp_path / "base.wav"), base[0]["t1"] - 0.3, base[1]["t0"] + 0.05, prefer="last")
    beg = vslib.quietest(str(tmp_path / "base.wav"), base[1]["t1"] - 0.3, base[2]["t0"] + 0.05, prefer="first")
    assert 1.2 < end < 1.3 and 2.3 < beg < 2.4


def _speech(path, spans, secs, sr=48000):
    """A stand-in for a voice take: (start, end, Hz, level) tone bursts in digital silence, written as WAV, or as mp3 when
    the name says so (vs voicebed finds a take's timings next to its .mp3)."""
    import wave
    x = np.zeros(int(secs * sr), np.float32)
    for a, b, hz, amp in spans:
        t = np.arange(int(round((b - a) * sr))) / sr
        x[int(round(a * sr)):int(round(a * sr)) + len(t)] = amp * np.sin(2 * np.pi * hz * t)
    wav = str(path)[:-4] + ".src.wav" if str(path).endswith(".mp3") else str(path)
    with wave.open(wav, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr), w.writeframes((x * 32767).astype("<i2").tobytes())
    if wav != str(path):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-b:a", "192k", str(path)], check=True)
    return str(path)


def _act(rng, act, t, n, hz, first=None):
    """n words of uneven length and uneven pauses from t: (spans, words, end). `first` = (length, dip): an opening word
    followed by a dip that isn't silence (the "And | to" of a real take), the trap the old cut fell into."""
    spans, words = [], []
    for i in range(n):
        if i == 0 and first:
            ln, dip = first
            spans += [(t, t + ln, hz, 0.5), (t + ln, t + ln + dip, hz, 0.016)]
            words.append({"w": f"a{act}w0", "t0": round(t, 3), "t1": round(t + ln, 3), "act": act})
            t += ln + dip
            continue
        ln, gap = rng.uniform(0.18, 0.42), rng.uniform(0.12, 0.3)
        spans.append((t, t + ln, hz, 0.5))
        words.append({"w": f"a{act}w{i}", "t0": round(t, 3), "t1": round(t + ln, 3), "act": act})
        t += ln + (gap if i < n - 1 else 0)
    return spans, words, t


def _late(words, by):
    """The vendor's timings, late by `by`, every act's last word running on to the next act's first (no gap): the shape
    of a bake-off explainer's e2 timings at the act 7 → 8 join."""
    out = [{**w, "t0": round(w["t0"] + by, 3), "t1": round(w["t1"] + by, 3)} for w in words]
    for w, nx in zip(out, out[1:]):
        if nx["act"] != w["act"]:
            w["t1"] = nx["t0"]
    return out


def _hz(path, t, secs=0.05):
    """The pitch of a sound at t: which take a stretch of a bed came from."""
    x = vslib.decode(path)[int(t * 48000):int((t + secs) * 48000)]
    return float(np.fft.rfftfreq(len(x), 1 / 48000)[np.argmax(np.abs(np.fft.rfft(x)))])


def test_a_splice_cuts_before_the_old_first_word_when_the_timings_run_late(tmp_path):
    # a bake-off explainer, Oct 12, 2026: the base's timings ran ~0.3 s late (an earlier splice had shifted them), the act before's
    # last word ran on to the replaced act's first, so the old window (0.3 s before that end to the first word) held no
    # silence. Its quietest stretch was the dip AFTER the old "And", and the bed said "And ... And to be fair" (heard in two
    # review rounds). The base here is three acts of 220 Hz "words", the re-recorded act 2 is 330 Hz: a 220 Hz burst
    # between act 1 and the new act 2 is the old first word, kept.
    rng = __import__("random").Random(7)
    s1, w1, e1 = _act(rng, 1, 0.4, 16, 220)
    s2, w2, e2 = _act(rng, 2, e1 + 0.45, 16, 220, first=(0.2, 0.04))
    s3, w3, e3 = _act(rng, 3, e2 + 0.45, 16, 220)
    (tmp_path / "voice").mkdir()
    base = _speech(tmp_path / "voice/narration-b.mp3", s1 + s2 + s3, e3 + 0.5)
    late = _late(w1 + w2 + w3, 0.3)
    json.dump(late, open(tmp_path / "voice/narration-b.words.json", "w"))
    ep, r0 = max(w["t1"] for w in late if w["act"] == 1), min(w["t0"] for w in late if w["act"] == 2)
    old = vslib.quietest(base, ep - 0.3, r0 + 0.05, prefer="last")
    assert old > w2[0]["t1"]  # the old rule cuts after the old act 2's first word: the stutter
    assert abs(vslib.timing_lag(base, late, ep - 20, ep) - 0.3) <= 0.03

    # the re-recorded act 2: same shape, 330 Hz, accurate timings, whose last word "ends" past the end of its file (as
    # ElevenLabs' do): asked for up to that end + 0.2 s, atrim returned less, and the base's later words drifted late
    rng = __import__("random").Random(8)
    sn, wn, en = _act(rng, 2, 0.1, 16, 330, first=(0.2, 0.04))
    _speech(tmp_path / "voice/narration-n.mp3", sn, en + 0.05)
    wn[-1]["t1"] = round(en + 0.15, 3)
    json.dump(wn, open(tmp_path / "voice/narration-n.words.json", "w"))
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "py", "voicebed.py"), "--base", "voice/narration-b.mp3",
                        "--take", "voice/narration-n.mp3", "--out", "s"], cwd=tmp_path, capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": os.path.join(ENGINE, "py")})
    assert r.returncode == 0, r.stderr
    bed = str(tmp_path / "voice/voice-bed-s.wav")
    W = json.load(open(tmp_path / "voice/narration-s.words.json"))
    # after act 1's last word: one pause, then the NEW act 2 (330 Hz), never the old one's first word (220 Hz)
    gap = [p for p in vslib.pauses(bed, w1[-1]["t1"] - 0.1, w1[-1]["t1"] + 1.5, min_len=0.1)][0]
    assert abs(gap[0] - w1[-1]["t1"]) <= 0.03 and abs(_hz(bed, gap[1] + 0.03) - 330) < 30
    # and act 3 is back, whole, its timings exactly as late as they were in the base (the splice added no drift)
    a3 = [w for w in W if w["act"] == 3]
    assert len(a3) == 16 and abs(vslib.timing_lag(bed, W, a3[0]["t0"], a3[0]["t0"] + 20) - 0.3) <= 0.03
    assert abs(_hz(bed, a3[0]["t0"] - 0.3 + 0.03) - 220) < 30
    # it said what it measured, and had nothing to warn about
    assert re.search(r"run 0\.(29|30|31) s late in act 2", r.stdout) and "⚠️" not in r.stdout, r.stdout


def test_timing_lag_is_zero_for_timings_that_are_right(tmp_path):
    rng = __import__("random").Random(3)
    s, w, e = _act(rng, 1, 0.3, 30, 220)
    p = _speech(tmp_path / "t.wav", s, e + 0.3)
    assert abs(vslib.timing_lag(p, w, 0, e)) <= 0.01  # pauses are measured in 10 ms steps
    assert abs(vslib.timing_lag(p, [{**x, "t0": x["t0"] - 0.2, "t1": x["t1"] - 0.2} for x in w], 0, e) + 0.2) <= 0.02


def test_clicks_finds_a_spike_in_silence_and_leaves_short_words_alone(tmp_path):
    # act 13 of a bake-off explainer (Oct 12, 2026): a 20 ms spike to -14 dBFS between stretches of digital silence, inside the
    # word timing of "picture.". Not clicks: a lone "And" between two pauses (110 ms, level all the way), a lip smack at
    # -53 dBFS
    spans = [(0.5, 1.4, 220, 0.5), (1.9, 2.01, 220, 0.5), (2.5, 3.2, 220, 0.5), (3.7, 3.72, 2000, 0.28),
             (3.72, 3.78, 2000, 0.01), (4.3, 4.32, 2000, 0.003), (4.8, 5.5, 220, 0.5)]
    p = _speech(tmp_path / "c.wav", spans, 6.0)
    c = vslib.clicks(p)
    assert len(c) == 1 and 3.68 <= c[0][0] <= 3.71


def test_music_extend_repeats_whole_bars_and_leaves_the_take_alone(tmp_path):
    # a 40 s click track at 120 BPM (a 2 s bar) that's 9 s short of the video: 5 whole bars go in, on downbeats
    sr = 22050
    x = np.zeros(sr * 40, np.float32)
    for k in range(80):
        t = int(k * 0.5 * sr)
        x[t:t + 200] += 0.6 * np.sin(np.arange(200) * 0.3) * np.exp(-np.arange(200) / 60)
    (tmp_path / "music").mkdir()
    take = tmp_path / "music/take1.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-", "-b:a", "192k",
                    str(take)], input=x.tobytes(), check=True)
    before = take.read_bytes()
    (tmp_path / "music/takes.json").write_text(json.dumps({"take1": {"label": "pulse"}}))
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "py/music.py"), "extend", "take1", "--to", "49"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "5 bars of 2.000s" in r.stdout or "5 bars of 1.99" in r.stdout or "5 bars of 2.00" in r.stdout, r.stdout
    T = json.load(open(tmp_path / "music/takes.json"))
    assert T["take2"]["extended_from"] == "music/take1.mp3" and "extended" in T["take2"]["label"]
    assert "from" not in T["take2"]  # "from" = reused from the library: vs learn would copy nothing and file a ghost
    assert 49 <= T["take2"]["secs"] < 49 + 2.2
    assert take.read_bytes() == before  # the original take is untouched
    # a run that would eat the outro is refused, not stretched
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "py/music.py"), "extend", "take1", "--to", "90"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode != 0 and "outro" in r.stderr
