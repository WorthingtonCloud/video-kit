"""The command table (studio.py): every step's script exists, and every paid step goes through the one spend gate."""
import importlib.util, os, re, sys
from conftest import ENGINE


def table():
    spec = importlib.util.spec_from_file_location("studio", os.path.join(ENGINE, "studio.py"))
    m = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["vs"]
    try:
        spec.loader.exec_module(m)
    finally:
        sys.argv = argv
    return m


def path_of(runs, script):
    return os.path.join(ENGINE, script if runs == "node" else os.path.join("py", script))


def test_every_step_has_its_script():
    m = table()
    for name, runs, script, *_ in m.COMMANDS:
        assert runs == "self" or os.path.exists(path_of(runs, script)), name
    assert all(t in m.CMD for t in m.ALIASES.values())


def test_every_paid_step_calls_the_spend_gate():
    for name, runs, script, proj, paid, *_ in table().COMMANDS:
        if paid:
            assert re.search(r"\bgate\(", open(path_of(runs, script)).read()), f"{name} spends without vslib.gate()"


def test_nothing_else_talks_to_a_paid_vendor():
    hosts = r"api\.elevenlabs\.io/v1/(text-to-speech|sound-generation)|api\.kie\.ai|api\.openai\.com|higgsfield\.ai"
    paid = {path_of(r, s) for n, r, s, p, who, *_ in table().COMMANDS if who}
    for f in os.listdir(os.path.join(ENGINE, "py")):
        p = os.path.join(ENGINE, "py", f)
        if f.endswith(".py") and p not in paid and f != "vslib.py":
            assert not re.search(hosts, open(p).read()), f"{f} calls a paid API but isn't marked paid in the table"


def test_both_plugin_manifests_carry_the_same_version():
    # an update ships only when plugin.json AND marketplace.json say the new version (installed copies never update)
    import json
    kit = os.path.dirname(ENGINE)
    p = json.load(open(os.path.join(kit, ".claude-plugin/plugin.json")))
    m = json.load(open(os.path.join(kit, ".claude-plugin/marketplace.json")))
    versions = {p["version"]} | {e.get("version") for e in m["plugins"] if e.get("name") == p["name"]}
    assert len(versions) == 1, f"plugin.json and marketplace.json disagree: {versions}"
