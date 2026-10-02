"""The scar ledger: every bullet in a skill's scars.md ends with what keeps it from coming back.
  ‹test: <path under tests/>[, …]›           a test that fails if the scar returns
  ‹partly: <path> · human: <what>›          a test catches part of it; a person confirms the rest
  ‹guard: <step>›                           a step the kit runs refuses or warns (the renderer's lint, vs qa, vs build)
  ‹planned: <card>›                         a check that's on the plan, not built yet
  ‹human: <why>›                            only a person can judge it
Mistake → scar → rule → test, enforced: an untagged scar, or a tag naming a test that doesn't exist, fails here, and so
does a regression fixture no scar points at."""
import collections, os, re
from conftest import KIT

KINDS = {"test", "partly", "guard", "planned", "human"}
TESTS = os.path.join(KIT, "tests")


def bullets():
    for skill in ("explainer-video", "sizzle-reel"):
        text = open(os.path.join(KIT, "skills", skill, "references/scars.md")).read()
        for b in re.findall(r"^- .*?(?=\n- |\n\n|\n#|\Z)", text, flags=re.S | re.M):
            yield skill, b


def paths(tag):
    kind, _, rest = tag.partition(":")
    return [p.strip() for p in rest.split("·")[0].split(",")] if kind in ("test", "partly") else []


def test_every_scar_says_what_keeps_it_from_coming_back():
    count = collections.Counter()
    for skill, b in bullets():
        tags = re.findall(r"‹([^›]*)›", b)
        assert len(tags) == 1, f"{skill}: one ‹kind: …› tag per scar, found {len(tags)}: {b[:90]!r}"
        kind = tags[0].split(":")[0].strip()
        assert kind in KINDS, f"{skill}: unknown kind {kind!r} in {b[:90]!r}"
        for p in paths(tags[0]):
            assert os.path.exists(os.path.join(TESTS, p)), f"{skill}: ‹{tags[0]}› names {p}, which doesn't exist"
        count[kind] += 1
    print("scar ledger:", dict(count))
    assert sum(count.values()) >= 57


def test_every_regression_fixture_is_some_scars_test():
    named = {p for _, b in bullets() for t in re.findall(r"‹([^›]*)›", b) for p in paths(t)}
    for d in os.listdir(os.path.join(TESTS, "regression")):
        if os.path.exists(os.path.join(TESTS, "regression", d, "expect.json")):
            assert f"regression/{d}" in named, f"regression/{d} pins no scar: tag the scar it guards"
