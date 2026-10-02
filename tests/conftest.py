"""Shared for the kit's Python tests (vs test runs them; pytest only, nothing to install for a user of the kit).
Every test runs with VIDEO_KIT_NO_SPEND=1 and its own HOME, so nothing paid can run and nobody's real studio is read."""
import json, os, subprocess, sys
import pytest

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# puppeteer's Chrome lives under the real home; the tests swap HOME, so they point puppeteer back at it
CHROME_CACHE = os.environ.get("PUPPETEER_CACHE_DIR") or os.path.expanduser("~/.cache/puppeteer")
ENGINE = os.path.join(KIT, "engine")
sys.path.insert(0, os.path.join(ENGINE, "py"))


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: builds and inspects a fixture in a browser (vs test --fast skips these)")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """A fresh HOME and no studio unless a test makes one; nothing paid can run."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("VIDEO_KIT_NO_SPEND", "1")
    monkeypatch.setenv("VIDEO_KIT_DOGFOOD", str(tmp_path / "DOGFOOD.md"))  # the tool-problem button never writes the real log
    monkeypatch.setenv("PUPPETEER_CACHE_DIR", CHROME_CACHE)
    for k in ("VIDEO_STUDIO", "ELEVENLABS_API_KEY", "OPENAI_API_KEY", "KIE_AI_API_KEY", "HIGGSFIELD_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    yield tmp_path


def write_tree(root, tree):
    """{"a/b.json": {...} | "text"} → files under root; {root} in any text becomes the root folder."""
    for rel, body in tree.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        text = body if isinstance(body, str) else json.dumps(body)
        open(p, "w").write(text.replace("{root}", str(root)))


def tone(path, secs=1.0, freq=440, db=-6):
    """A sine at `db` dBFS peak as an audio file, made with ffmpeg (no media is checked in). ffmpeg's sine source peaks
    at 1/8 (about -18 dBFS), so the volume makes up the difference."""
    vol = 10 ** (db / 20) * 8
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={secs}",
                    "-af", f"volume={vol}", str(path)], check=True)
    return str(path)


@pytest.fixture
def font_studio(tmp_path, monkeypatch):
    """A throwaway studio whose fonts are the machine's own (local()), so nothing is downloaded: HyperFrames refuses a
    font family with no @font-face, and a real studio gets its fonts from vs setup."""
    fonts = tmp_path / "studio/library/brand/fonts"
    fonts.mkdir(parents=True)
    (tmp_path / "studio/studio.json").write_text("{}")
    for fam, local in (("Archivo", "Helvetica Neue"), ("JetBrains Mono", "Menlo")):
        (fonts / (fam.replace(" ", "") + ".css")).write_text(
            "".join(f"@font-face{{font-family:'{fam}';font-weight:{w};src:local('{local}')}}\n" for w in (500, 600, 700, 800)))
    monkeypatch.setenv("VIDEO_STUDIO", str(tmp_path / "studio"))
    return tmp_path / "studio"


def vs(d, *args):
    """Run a step on a project folder the way a person would (the engine's own Python, the kit's dispatcher)."""
    return subprocess.run([sys.executable, os.path.join(ENGINE, "studio.py"), "-p", str(d), *args], capture_output=True,
                          text=True)
