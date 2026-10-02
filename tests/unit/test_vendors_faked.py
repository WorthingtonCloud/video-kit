"""The vendor scars, with the vendors faked: urllib's urlopen is swapped for a recorder that answers like the vendor
did, and sleep is skipped. The gate is open in these tests (they must reach the request), but nothing can leave the
machine: every request lands in the fake, and the keys are fake too."""
import base64, csv, io, json, os, runpy, sys, time, urllib.error, urllib.request
import pytest
from conftest import ENGINE, write_tree


class Vendor:
    """Answers each request with handler(url, body, n); records url, body and headers."""
    def __init__(self, handler):
        self.calls, self.handler = [], handler

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        body = json.loads(req.data) if getattr(req, "data", None) else None
        self.calls.append({"url": url, "body": body, "headers": dict(req.header_items()) if hasattr(req, "header_items") else {}})
        out = self.handler(url, body, len(self.calls))
        if isinstance(out, Exception):
            raise out
        return io.BytesIO(out if isinstance(out, bytes) else json.dumps(out).encode())


@pytest.fixture
def run(tmp_path, monkeypatch):
    """Run a step's script in a fresh project inside a fresh studio, with a faked vendor."""
    write_tree(tmp_path, {"s/studio.json": {}, "s/projects/vid/reel.json": {
        "name": "vid", "music": {"file": "voice/bed.wav", "beat": 0.5}, "segments": [{"name": "a", "secs": 60, "source": {"scene": "x"}}]}})
    monkeypatch.setenv("VIDEO_STUDIO", str(tmp_path / "s"))
    monkeypatch.delenv("VIDEO_KIT_NO_SPEND")
    for k in ("ELEVENLABS_API_KEY", "KIE_AI_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(k, "fake")
    monkeypatch.setenv("HIGGSFIELD_API_KEY", "fake:fake")
    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.chdir(tmp_path / "s/projects/vid")

    def go(script, argv, handler, files=None):
        write_tree(tmp_path / "s/projects/vid", files or {})
        v = Vendor(handler)
        monkeypatch.setattr(urllib.request, "urlopen", v)
        monkeypatch.setattr(sys, "argv", [script, *argv])
        try:
            runpy.run_path(os.path.join(ENGINE, "py", script), run_name="__main__")
        except SystemExit as e:
            v.exit = e.code
        v.ledger = list(csv.DictReader(open(tmp_path / "s/ledger.csv"))) if (tmp_path / "s/ledger.csv").exists() else []
        return v
    return go


def test_suno_wants_its_model_nested_and_a_failed_poll_is_unknown(run, capsys):
    polls = []

    def kie(url, body, n):
        if "chat/credit" in url:
            return {"data": 100}
        if "createTask" in url:
            return {"data": {"taskId": "T1"}}
        polls.append(url)  # the first poll fails outright; the second says the job failed
        return urllib.error.URLError("timed out") if len(polls) == 1 else {"data": {"state": "fail"}}
    v = run("music.py", ["--yes"], kie, files={"music.json": json.dumps([{"label": "A pulse", "style": "a steady pulse"}])})
    task = next(c["body"] for c in v.calls if "createTask" in c["url"])
    # a top-level "V6" was a 422: the outer model is the generator, the inner one is V6
    assert task["model"] == "ai-music-api/generate" and task["input"]["model"] == "V6"
    out = capsys.readouterr().out
    assert "status unknown" in out  # a failed poll is unknown, never done
    assert [r["status"] for r in v.ledger] == ["failed"] and v.ledger[0]["credits"] == "12"


def test_narrate_waits_for_its_own_history_entry(run):
    text, starts, now, seen = "Hi there", [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], time.time(), []

    def eleven(url, body, n):
        if "text-to-speech" in url:
            return {"audio_base64": base64.b64encode(b"ID3").decode(),
                    "alignment": {"characters": list(text), "character_start_times_seconds": starts,
                                  "character_end_times_seconds": [s + 0.1 for s in starts]}}
        # the history logs a call late: read at once it's still the PREVIOUS call (Oct 1, 2026: 144 for a 25-credit act)
        seen.append(url)
        old = len(seen) == 1
        return {"history": [{"date_unix": now - 100 if old else now + 1, "character_count_change_from": 1000,
                             "character_count_change_to": 1144 if old else 1025}]}
    v = run("narrate.py", ["t1", "--voice", "UgBBYS2sOqTuMpoF3BR0", "--yes"], eleven, files={"narration.txt": "Hi there\n"})
    assert len(seen) == 2  # it asked again until the entry was its own
    assert [r["credits"] for r in v.ledger] == ["25"] and v.ledger[0]["status"] == "done"
    assert json.load(open("voice/narration-t1.words.json"))[0]["w"] == "Hi"


def test_higgsfield_gets_curls_user_agent(run, tmp_path):
    def vendors(url, body, n):
        if "file-base64-upload" in url:
            return {"data": {"downloadUrl": "https://files.example/x.png"}}
        if "image-to-video" in url:
            return {"request_id": "R1"}
        if "/status" in url:
            return {"status": "completed", "video": {"url": "https://files.example/x.mp4"}}
        return b"\x00\x00\x00 ftypmp4"
    v = run("gen.py", ["clip", "--image", "x.png", "--prompt", "a slow push in", "--out", "clips/x.mp4", "--yes"],
            vendors, files={"x.png": "not really a png"})
    hf = next(c for c in v.calls if "image-to-video" in c["url"])
    # Higgsfield's firewall rejected Python's default user agent (error 1010) before any job existed
    assert hf["headers"].get("User-agent") == "curl/8.7.1"
    assert [r["status"] for r in v.ledger] == ["done"] and float(v.ledger[0]["usd"]) == pytest.approx(1.03, abs=0.01)
