"""The OpenAI key never reaches a terminal: a failed transcription (vs check-take, vs ingest --voice) exits with one plain
line, not a traceback of curl's command line. Oct 7, 2026: `vs check-take v2` handed curl a tag for a path, curl exit 26,
and the CalledProcessError printed the whole argv, live key and all. A fake curl stands in, so nothing leaves the machine;
it records its command line, so the test also proves the key was never on it."""
import csv, os, subprocess, sys
from conftest import ENGINE, write_tree

KEY = "sk-test-DO-NOT-PRINT-0123456789"


def fake_curl(bin_dir, script):
    p = bin_dir / "curl"
    p.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$CURL_ARGV\"\n" + script)
    p.chmod(0o755)


def check_take(tmp_path, monkeypatch, curl_script, take="v2"):
    write_tree(tmp_path, {"s/studio.json": {}, "s/projects/vid/narration.txt": "Hello there.\n",
                          "s/projects/vid/voice/narration-v2.mp3": "not really audio"})
    (tmp_path / "bin").mkdir()
    fake_curl(tmp_path / "bin", curl_script)
    env = {**os.environ, "VIDEO_STUDIO": str(tmp_path / "s"), "OPENAI_API_KEY": KEY, "CURL_ARGV": str(tmp_path / "argv"),
           "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}"}
    env.pop("VIDEO_KIT_NO_SPEND")
    r = subprocess.run([sys.executable, os.path.join(ENGINE, "py", "check_take.py"), take, "--yes"],
                       cwd=tmp_path / "s/projects/vid", env=env, capture_output=True, text=True)
    ledger = list(csv.DictReader(open(tmp_path / "s/ledger.csv"))) if (tmp_path / "s/ledger.csv").exists() else []
    argv = (tmp_path / "argv").read_text() if (tmp_path / "argv").exists() else ""
    return r, ledger, argv


def test_a_failed_transcription_prints_one_line_and_no_key(tmp_path, monkeypatch):
    r, ledger, argv = check_take(tmp_path, monkeypatch, "echo 'curl: (26) Failed to open/read local data' >&2\nexit 26\n")
    out = r.stdout + r.stderr
    assert r.returncode != 0
    assert KEY not in out and KEY not in argv          # not in the error, and never on curl's command line
    assert "Traceback" not in out and "transcribing narration-v2.mp3 failed: curl: (26)" in out
    assert [x["status"] for x in ledger] == ["failed"]


def test_the_vendor_echoing_the_key_is_scrubbed(tmp_path, monkeypatch):
    r, _, _ = check_take(tmp_path, monkeypatch, f"echo '{{\"error\": \"Incorrect API key provided: {KEY}\"}}'\nexit 22\n")
    assert KEY not in r.stdout + r.stderr and "<key>" in r.stderr


def test_a_tag_finds_its_take_and_the_key_goes_on_stdin(tmp_path, monkeypatch):
    r, ledger, argv = check_take(tmp_path, monkeypatch, "cat > \"$CURL_ARGV.stdin\"\necho 'Hello there.'\n")
    assert r.returncode == 0, r.stderr
    assert "file=@voice/narration-v2.mp3" in argv and "-K\n-\n" in argv and KEY not in argv
    assert KEY in (tmp_path / "argv.stdin").read_text()   # the header went to curl as config on stdin
    assert "0 differences" in r.stdout and [x["status"] for x in ledger] == ["done"]


def test_no_such_take_stops_before_the_gate(tmp_path, monkeypatch):
    r, ledger, argv = check_take(tmp_path, monkeypatch, "exit 0\n", take="v9")
    assert r.returncode != 0 and "no take called v9" in r.stderr and not ledger and not argv
