"""Voice splices, sound-effect names, sound measuring and the beat grid (vslib + beats.py)."""
import os, subprocess, sys
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


def test_a_splice_needs_an_act_before_it():
    with pytest.raises(ValueError):
        vslib.splice_plan(BASE, W(1, (0.1, 0.4)))


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
