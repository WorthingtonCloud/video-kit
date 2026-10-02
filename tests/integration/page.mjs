// Drives Review Studio's page in a headless browser, the way a person uses it, and prints what happened as JSON.
// test_review_page.py starts the server and runs one scenario at a time:  node page.mjs <url> <scenario>
// Every scenario also returns the page's console errors: a page that throws fails its test even if the steps went through.
import { launch } from "../../engine/js/lib/browser.mjs";

const [url, scenario] = process.argv.slice(2);
const b = await launch(),
  p = await b.newPage(),
  errors = [];
p.on("pageerror", (e) => errors.push(String(e.message || e)));
p.on("console", (m) => m.type() === "error" && !/^Failed to load resource/.test(m.text()) && errors.push(m.text()));
p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${new URL(r.url()).pathname}`));
await p.setViewport({ width: 1280, height: 800 });
// the panels start folded (the "room" scenario checks that); every other scenario works with both open, as if the
// person had opened them once (the page remembers that per browser)
if (scenario !== "room")
  await p.evaluateOnNewDocument(() => {
    try {
      localStorage.setItem("review.drawer", "1");
      localStorage.setItem("review.timeline", "1");
    } catch {}
  });
await p.goto(url, { waitUntil: "networkidle0" });
await p.waitForFunction(() => document.querySelector("#proj").textContent !== "…");
const text = (s) => p.$eval(s, (e) => e.textContent.trim());
const seek = (t) =>
  p.evaluate(async (t) => {
    const v = document.querySelector("#video");
    if (v.readyState < 1) await new Promise((r) => v.addEventListener("loadedmetadata", r, { once: true }));
    v.currentTime = t;
    await new Promise((r) => v.addEventListener("seeked", r, { once: true }));
  }, t);

const key = async (k, shift = false) => {
  if (shift) await p.keyboard.down("Shift");
  await p.keyboard.press(k);
  if (shift) await p.keyboard.up("Shift");
  await new Promise((r) => setTimeout(r, 80));
};
const now = () => text("#t-now");
// step 2–4 of the loop: Review & send, Approve & send, back to the video
const sendAll = async () => {
  await p.click("#send");
  await p.waitForFunction(() => !document.querySelector("#review-sheet").hidden);
  const list = await p.$$eval("#rv-list li .what b", (x) => x.map((e) => e.textContent));
  await p.click("#rv-send");
  await p.waitForFunction(() => !document.querySelector("#sent-sheet").hidden);
  const word = await text("#st-word");
  await p.click("#st-ok");
  return { list, word };
};
// the middle of an element's box in the frame, in page pixels (from the element map, at the paused moment)
const spot = (id) =>
  p.evaluate(async (id) => {
    const e = (await (await fetch("/build/elements.json")).json()).items.find((x) => x.id === id);
    const t = +document.querySelector("#t-now").textContent.split(":").reduce((m, s) => m * 60 + +s, 0);
    let b = e.boxes[0];
    for (const x of e.boxes) if (x[0] <= t + 1e-3) b = x;
    const r = document.querySelector("#stage").getBoundingClientRect();
    return [r.left + r.width * (b[1] + b[3]) / 2, r.top + r.height * (b[2] + b[4]) / 2];
  }, id);

const SCENARIOS = {
  // RS2: the loop. Each action says what it was and offers Undo; ⌘Z takes back the last; the Review list changes a note's
  // words and undoes a line; Approve & send; then "sent" for the chat, and the page knows when Claude has read it
  async loop() {
    const r = {};
    await seek(0.5);
    await p.type("#c-text", "too fast here");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => /waits for your send/.test(document.querySelector("#toast-t").textContent));
    r.toast = await text("#toast-t");
    r.loop = await text("#loop li.now");
    await p.click("#toast-u");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 0);
    await p.type("#c-text", "too fast here");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 1);
    await seek(1.5);
    await p.type("#c-text", "and here");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 2);
    await p.keyboard.down("Meta");
    await p.keyboard.press("z");
    await p.keyboard.up("Meta");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 1);
    r.send = await text("#send");
    await p.click("#send");
    await p.waitForFunction(() => !document.querySelector("#review-sheet").hidden);
    r.reviewLoop = await text("#loop li.now");
    await p.click('#rv-list [data-rv="edit"]');
    await p.$eval("#rv-list [data-edit]", (t) => (t.value = "too fast in the first second"));
    await p.click('#rv-list [data-rv="save"]');
    await p.waitForFunction(() => /first second/.test(document.querySelector("#tab-notes").textContent));
    r.list = await p.$$eval("#rv-list li .what b", (x) => x.map((e) => e.textContent));
    await p.click("#rv-send");
    await p.waitForFunction(() => !document.querySelector("#sent-sheet").hidden);
    r.word = await text("#st-word");
    r.turn = await text("#st-turn-t");
    r.after = await text("#loop li.now");
    return r;
  },
  // the loop, after Claude has read what was sent (vs review show): Claude's turn; then a note starts the next batch
  async read() {
    await p.waitForFunction(() => /Claude's turn/.test(document.querySelector("#loop li.now")?.textContent || ""));
    const r = { loop: await text("#loop li.now"), sendp: await text("#sendp") };
    await seek(1.0);
    await p.type("#c-text", "one more thing");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => /Review & send · 1 thing/.test(document.querySelector("#send").textContent));
    r.again = await text("#loop li.now");
    r.sent = await sendAll();
    return r;
  },
  // RS6: where you are. The top line's stages; "How we got here" lists your steps; a comment on one becomes a note
  async steps() {
    const r = { stages: await text("#stages") };
    await p.click("#crumbs");
    await p.waitForFunction(() => !document.querySelector("#plog").hidden);
    r.steps = await p.$$eval("#plog .pstep p", (x) => x.map((e) => e.textContent));
    r.groups = await p.$$eval("#plog .pg h4", (x) => x.map((e) => e.textContent));
    await p.click('#plog .pstep button[data-p="comment"]');
    await p.type("#plog [data-pc]", "I want to revisit this");
    await p.click('#plog [data-p="send"]');
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 1);
    r.note = await text("#tab-notes .item[data-id]");
    r.sent = await sendAll();
    return r;
  },
  // RS1: the video gets the room. Folded panels by default, full screen, and a top line that never overlaps or wraps
  async room() {
    const r = {};
    const box = (s) => p.$eval(s, (e) => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; });
    r.folded = await p.evaluate(() => [document.querySelector("#drawer").hidden, document.querySelector("#tl").hidden]);
    r.stage = (await box("#stage"))[3] / 800; // of the window's height
    await key("f");
    await new Promise((res) => setTimeout(res, 300));
    r.fs = [await p.evaluate(() => document.body.classList.contains("fs")), (await box("#stage"))[3]];
    await key("Escape");
    await new Promise((res) => setTimeout(res, 300));
    r.back = await p.evaluate(() => document.body.classList.contains("fs"));
    await p.click("#roundbtn");
    await p.click("#tl-toggle");
    r.open = await p.evaluate(() => [document.querySelector("#drawer").hidden, document.querySelector("#tl").hidden, localStorage.getItem("review.drawer")]);
    // the top line at every width: one line, nothing on top of anything
    r.widths = {};
    for (const w of [1680, 1440, 1280, 1100, 960, 820, 700, 520, 420]) {
      await p.setViewport({ width: w, height: 800 });
      await new Promise((res) => setTimeout(res, 120));
      r.widths[w] = await p.evaluate(() => {
        const top = document.querySelector(".top"),
          kids = [...top.children].filter((e) => !e.hidden && getComputedStyle(e).display !== "none" && getComputedStyle(e).position !== "absolute"),
          bs = kids.map((e) => e.getBoundingClientRect()).filter((b) => b.width > 0);
        const over = bs.some((a, i) => bs.some((b, j) => j > i && a.left < b.right - 1 && b.left < a.right - 1));
        const tall = [...top.querySelectorAll("button, li, span")].filter((e) => e.offsetParent && e.getBoundingClientRect().height > 40).map((e) => e.textContent.trim().slice(0, 30));
        return { h: Math.round(top.getBoundingClientRect().height), over, tall, scroll: document.documentElement.scrollWidth > innerWidth };
      });
    }
    return r;
  },
  // card 1: a note at a moment, then Send
  async notes() {
    await seek(0.5);
    await p.type("#c-text", "too fast here");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 1);
    const box = await p.$eval("#c-text", (e) => e.value);
    const sent = await sendAll();
    return { item: await text("#tab-notes .item[data-id]"), box, round: "sent", sent };
  },
  // card 2: the transport, the jumps, and the timeline pointing at the frame (the beat reel: no words, so beats)
  async player() {
    await p.waitForFunction(() => document.querySelectorAll("#tl-rows .row").length > 5);
    await seek(13.0);
    const r = { start: await now() };
    await key("ArrowRight");
    r.frame = await now();
    await key("ArrowLeft", true);
    r.second = await now();
    await key("]");
    r.scene = [await now(), await text("#tl-rows .bl.seg.act")];
    await key("[");
    await key("[");
    r.back = [await now(), await text("#tl-rows .bl.seg.act")];
    r.rows = await p.$$eval("#tl-rows .row.grp > .lb", (x) => x.map((e) => e.textContent.trim()));
    r.beats = await p.$$eval("#tl-rows .beat", (x) => [x.length, x.filter((e) => e.classList.contains("hit")).length]);
    // hover an element's row → it's outlined in the frame
    await seek(13.0);
    await p.hover('#tl-rows .row.el[data-el="s03_hub/core"] .lb');
    r.outline = await p.$eval('#overlay g[data-layer="hover"]', (g) => g.children.length);
    // hover the frame over it → its row lights up
    await p.mouse.move(0, 0);
    const [x, y] = await spot("title/t_layers");
    await p.mouse.move(x, y);
    r.lit = await p.$eval("#tl-rows .row.el.hl, #tl-rows .row.hl", (e) => e.dataset.el).catch(() => null);
    r.litTitle = await p.evaluate(() => document.querySelector('#overlay g[data-layer="hover"] rect') !== null);
    await key("-");
    r.zoom = await text("#tl-zoom .on");
    await key("f");
    r.watch = await p.evaluate(() => [document.body.classList.contains("fs"), getComputedStyle(document.querySelector("#drawer")).display]);
    return r;
  },
  // card 3: point at it. A click asks the composition; arrow and keep-clear marks; a range; the note carries it all.
  async point() {
    await p.waitForFunction(() => document.querySelectorAll("#tl-rows .row").length > 5);
    await seek(13.0);
    const r = {};
    await p.waitForFunction(() => !document.querySelector("#comp") || !!document.querySelector("#comp").contentWindow.__names, { timeout: 15000 });
    r.notice = await p.$eval("#notice", (e) => (e.hidden ? "" : e.textContent));
    let [x, y] = await spot("s03_hub/ring-layer-1-label");
    await p.mouse.click(x, y);
    r.tag = await text("#tag");
    r.crumbs = await p.$$eval("#c-extra .crumbs > button, #c-extra .crumbs > span", (x) => x.map((e) => e.textContent));
    r.chip = await text("#c-chip span");
    r.selRow = await p.$eval("#tl-rows .row.el.sel", (e) => e.dataset.el).catch(() => null);
    // arrow: from the label to empty space; keep-clear over the core
    await p.keyboard.press("a");
    await p.mouse.move(x, y);
    await p.mouse.down();
    const st = await p.$eval("#stage", (e) => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; });
    await p.mouse.move(st[0] + st[2] * 0.85, st[1] + st[3] * 0.85, { steps: 4 });
    await p.mouse.up();
    await p.keyboard.press("k");
    const [cx, cy] = await spot("s03_hub/core");
    await p.mouse.move(cx - 20, cy - 20);
    await p.mouse.down();
    await p.mouse.move(cx + 20, cy + 20, { steps: 4 });
    await p.mouse.up();
    r.markline = await text("#c-extra .markline");
    await p.type("#c-text", "this label fights the ring");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 1);
    r.cleared = await p.$eval("#tag", (e) => e.hidden);
    // a range, I and O, on a note with no mark
    await p.keyboard.press("v");
    await seek(9.6);
    await p.keyboard.press("i");
    await seek(11.0);
    await p.keyboard.press("o");
    r.range = await text("#c-chip span");
    await p.type("#c-text", "the hub takes too long to arrive");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 2);
    r.sent = await sendAll();
    return r;
  },
  // card 4 (RS3): findings in plain words, a card per check, Claude's advice taken in one click, one by one, a note on one
  async findings() {
    await p.waitForFunction(() => document.querySelectorAll("#asks-f .finding").length > 0);
    const r = { cards: await p.$$eval("#asks-f .finding", (x) => x.map((e) => [e.dataset.check, e.querySelector(".fname").textContent, !!e.querySelector(".advice")])) };
    r.qaRow = await p.$$eval("#tl-rows .bl.qa", (x) => x.length);
    r.todo = await text("#todo");
    // the advised check: one click takes the advice for both
    await p.click('#asks-f .finding[data-check="covered"] button[data-f="each"]');
    await p.click('#asks-f .one[data-id="q-covered-top-15.25"] button[data-f="fix1"]');
    await p.waitForFunction(() => /Fix it/.test(document.querySelector('#asks-f .one[data-id="q-covered-top-15.25"] .doneline')?.textContent || ""));
    r.toast = await text("#toast-t");
    await p.click('#asks-f .finding[data-check="spills"] button[data-f="leave"]');
    await p.waitForFunction(() => !!document.querySelector('#asks-f .finding[data-check="spills"] .doneline'));
    await p.click('#asks-f .one[data-id="q-covered-right-18.25"] button[data-f="note"]');
    r.comment = { now: await now(), about: (await text("#c-chip")) + " " + (await text("#c-extra")), focus: await p.evaluate(() => document.activeElement.id) };
    await p.keyboard.type("the claim runs off the right edge");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 1);
    r.sent = await sendAll();
    return r;
  },
  // card 5: the Mix section (vs mixer opens #mix): the stems play and the picture follows, a level (its number moves as
  // it's dragged), Save (it waits for the send), and the video's own sound back when the section folds
  async mix() {
    await p.goto(url + "#mix", { waitUntil: "networkidle0" });
    await p.reload({ waitUntil: "networkidle0" });
    await p.waitForFunction(() => /Your mix/i.test(document.querySelector("#tab-mix").textContent), { timeout: 20000 });
    const r = { open: await p.$eval("#mix-h", (b) => b.getAttribute("aria-expanded")), music: await p.$$eval("#tab-mix .takes", (x) => x.length), muted: await p.$eval("#video", (v) => v.muted) };
    await seek(5.0);
    await p.click("#t-play");
    await new Promise((res) => setTimeout(res, 1200));
    r.playing = await p.evaluate(() => [document.querySelector("#video").currentTime, document.querySelector("#t-play").textContent]);
    await p.click("#t-play");
    await p.$eval("#m-fx", (s) => {
      s.value = -3;
      s.dispatchEvent(new Event("input", { bubbles: true }));
    });
    r.label = await text("#m-fx + .val");
    r.summary = await text("#tab-mix .summary");
    await p.click("#m-save");
    await p.waitForFunction(() => /not sent/.test(document.querySelector("#m-saved").textContent));
    r.saved = await text("#m-saved");
    r.sent = await sendAll();
    await p.click("#mix-h");
    r.after = await p.evaluate(() => document.querySelector("#video").muted);
    return r;
  },
  // card 6 (RS2): Claude's fixes first. The answer with its measurement, Compare, Looks right, Still wrong, Follow up, and
  // approving the version in one click; all of it waits for the send
  async rounds() {
    await p.goto(url + "#rounds", { waitUntil: "networkidle0" });
    await p.reload({ waitUntil: "networkidle0" });
    await p.waitForFunction(() => document.querySelectorAll("#tab-rounds .res").length >= 2);
    const r = { cards: await p.$$eval("#tab-rounds .res", (x) => x.map((e) => [e.dataset.id, e.querySelector(".when").textContent.split(" · ").pop(), e.classList.contains("flagged")])) };
    await p.click('.res[data-id="n-0001"] button[data-r="compare"]');
    await p.waitForFunction(() => [...document.querySelectorAll(".compare video")].every((v) => v.readyState >= 1));
    r.compare = await p.$$eval(".compare video", (x) => x.map((v) => v.getAttribute("src")));
    r.outlines = await p.$$eval(".compare rect", (x) => x.length);
    await p.keyboard.press("Escape");
    await p.click('.res[data-id="n-0001"] button[data-r="accept"]');
    await p.waitForFunction(() => /looks right/.test(document.querySelector('.res[data-id="n-0001"] .doneline')?.textContent || ""));
    await p.click('.res[data-id="n-0002"] button[data-r="reopen"]');
    await p.type('.res[data-id="n-0002"] textarea', "still too slow");
    await p.click('.res[data-id="n-0002"] button[data-r="reopen-send"]');
    await p.waitForFunction(() => /still wrong/.test(document.querySelector('.res[data-id="n-0002"] .doneline')?.textContent || ""));
    await p.click('.res[data-id="n-0001"] button[data-r="follow"]').catch(() => {}); // accepted: no Follow up any more
    r.follow = await p.$('.res[data-id="n-0001"] button[data-r="follow"]');
    await p.click('#verdict-approve button[data-r="approve"]');
    await p.waitForFunction(() => /Approved: v2 is done/.test(document.querySelector("#verdict-approve").textContent));
    r.approve = await text("#verdict-approve");
    r.sent = await sendAll();
    r.approved = await text("#verdict-approve");
    return r;
  },
  // card 6, a follow-up: back to the answer's moment and target, a new note that points at it
  async follow() {
    await p.goto(url + "#rounds", { waitUntil: "networkidle0" });
    await p.reload({ waitUntil: "networkidle0" });
    await p.waitForFunction(() => document.querySelectorAll("#tab-rounds .res").length >= 1);
    await p.click('.res[data-id="n-0001"] button[data-r="follow"]');
    const r = { point: await text("#c-extra"), focus: await p.evaluate(() => document.activeElement.id) };
    await p.keyboard.type("and a touch bigger");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 1);
    r.sent = await sendAll();
    return r;
  },
  // card 8: the learning prompt. A proposal Claude worded; the human's click decides it
  async learn() {
    await p.waitForFunction(() => !!document.querySelector("#asks-l .res.lesson"));
    const r = { card: await text("#asks-l .res.lesson"), badge: await text("#sec-asks > .k em") };
    await p.click('#asks-l .res.lesson button[data-r="ignore"]');
    await p.waitForFunction(() => !!document.querySelector("#asks-l .doneline"));
    r.decided = await text("#asks-l .doneline");
    r.sent = await sendAll();
    return r;
  },
  // card 9: the review clock and the Report a tool problem button
  async usage() {
    await seek(2.0);
    await p.click("#t-play");
    await new Promise((res) => setTimeout(res, 2600));
    await p.click("#t-play");
    await p.evaluate(async () => (await import("/review/js/usage.js")).usage.flush()); // what hiding the tab does
    await p.click("#friction");
    await p.type("#friction-box textarea", "no handle on the range");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => document.querySelector("#friction-box").hidden);
    await new Promise((res) => setTimeout(res, 300));
    return { toast: await text("#toast-t") };
  },
  // Phase 3, Decide (RS4): "See option B" shows it on the stage (live, following the player's clock) and says it isn't
  // picked; 0–9 switch; Play the choice stops at its end; Pick B is its own button, and waits for the send
  async decide() {
    await p.goto(url + "#decide", { waitUntil: "networkidle0" });
    await p.reload({ waitUntil: "networkidle0" });
    await p.waitForFunction(() => !!document.querySelector("#tab-decide .res.choice"));
    const r = { opts: await p.$$eval("#tab-decide .opt", (x) => x.map((e) => e.innerText.replace(/\s+/g, " ").trim())) };
    await p.click('#tab-decide [data-c="see"][data-o="b"]');
    await p.waitForFunction(() => [...document.querySelectorAll(".preview iframe")].length === 2);
    await p.waitForFunction(() => {
      const f = [...document.querySelectorAll(".preview iframe")].find((x) => !x.hidden);
      return f && f.contentWindow.__timelines?.main && !document.querySelector(".preview").hidden;
    }, { timeout: 20000 });
    r.now = await now(); // shown at the choice's moment, playing
    await p.click("#t-play");
    r.banner = await text("#banner span");
    r.preview = await p.$eval("#stage", (e) => e.dataset.preview);
    r.label = await text('#tab-decide [data-c="see"][data-o="b"] .see');
    await seek(8.5);
    await new Promise((res) => setTimeout(res, 150));
    r.paused = await p.evaluate(() => [...document.querySelectorAll(".preview iframe")].find((x) => !x.hidden).contentWindow.__timelines.main.time());
    await p.click('#tab-decide [data-c="play"]');
    await new Promise((res) => setTimeout(res, 1000));
    r.playing = await p.evaluate(() => {
      const v = document.querySelector("#video"),
        tl = [...document.querySelectorAll(".preview iframe")].find((x) => !x.hidden).contentWindow.__timelines.main;
      return [v.currentTime, tl.time(), v.paused];
    });
    await p.waitForFunction(() => document.querySelector("#video").paused, { timeout: 6000 });
    r.stopped = await p.$eval("#video", (v) => v.currentTime);
    await key("1");
    r.key = await p.$eval("#stage", (e) => e.dataset.preview);
    r.notPicked = await p.evaluate(() => !document.querySelector("#tab-decide .doneline"));
    r.badgeBefore = await text("#todo");
    await p.click('#tab-decide [data-c="pick"][data-o="b"]');
    await p.waitForFunction(() => /Your pick: B/.test(document.querySelector("#tab-decide .doneline")?.textContent || ""));
    r.picked = await text("#tab-decide .doneline");
    r.badge = await text("#todo");
    await p.click("#banner button");
    r.back = await p.evaluate(() => [document.querySelector(".preview").hidden, document.querySelector("#stage").dataset.preview, document.querySelector("#banner").hidden]);
    r.sent = await sendAll();
    return r;
  },
  // Phase 3, ducking: the music comes un-ducked and the Mix panel ducks it live; the slider moves it while it plays
  async duck() {
    await p.goto(url + "#mix", { waitUntil: "networkidle0" });
    await p.reload({ waitUntil: "networkidle0" });
    await p.waitForFunction(() => /Your mix/i.test(document.querySelector("#tab-mix").textContent), { timeout: 20000 });
    const r = { slider: await p.$eval("#m-duck", (s) => +s.value), summary: await text("#tab-mix .summary") };
    await seek(3.0);
    await p.click("#t-play");
    await new Promise((res) => setTimeout(res, 700));
    const now = () => p.evaluate(async () => (await import("/review/js/mix.js")).stems.now());
    r.playing = await now();
    await p.$eval("#m-duck", (s) => {
      s.value = 12;
      s.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await new Promise((res) => setTimeout(res, 400));
    r.deeper = await now();
    await p.click("#t-play");
    r.summary2 = await text("#tab-mix .summary");
    r.label = await text("#m-duck + .val");
    r.meter = await text("#m-now");
    await p.click("#m-save");
    await p.waitForFunction(() => /not sent/.test(document.querySelector("#m-saved").textContent));
    r.sent = await sendAll();
    return r;
  },
  // Phase 3, one sound answered: a click on the Sound row picks the cue, it plays alone, a button makes the note
  async sound() {
    await p.waitForFunction(() => document.querySelectorAll("#tl-rows .dia[data-cue]").length > 0);
    await p.click("#tl-rows .dia[data-cue]");
    await p.waitForFunction(() => !!document.querySelector("#c-extra .sound"));
    const r = { point: await text("#c-extra .markline"), now: await now(), hint: await p.$eval("#c-text", (e) => e.placeholder) };
    r.alone = await p.evaluate(async () => {
      const q = (await (await fetch("/build/mix/cues.json")).json())[0];
      return (await import("/review/js/mix.js")).solo(q);
    });
    await p.type("#c-text", "it buries the word");
    await p.click('#c-extra [data-ask="quieter"]');
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 1);
    r.item = await text("#tab-notes .item[data-id] .seek");
    r.sent = await sendAll();
    return r;
  },
  // Phase 3, standing rules: "This scene is done" (and Reopen), and a sent keep-clear zone shown faintly in its scene
  async rules() {
    await p.waitForFunction(() => document.querySelectorAll("#tl-rows .row").length > 5);
    await seek(8.5);
    await p.waitForFunction(() => /s02_turn/.test(document.querySelector("#c-scene").textContent));
    const r = { line: await text("#c-scene") };
    await p.click('#c-scene button[data-scene="done"]');
    await p.waitForFunction(() => !!document.querySelector("#tl-rows .bl.seg.done"));
    r.done = [await text("#c-scene"), await text("#tl-rows .bl.seg.done")];
    await p.click('#c-scene button[data-act="undo"]'); // not sent yet: Undo takes it back
    await p.waitForFunction(() => !document.querySelector("#tl-rows .bl.seg.done"));
    await p.click('#c-scene button[data-scene="done"]');
    await p.waitForFunction(() => !!document.querySelector("#tl-rows .bl.seg.done"));
    // a keep-clear zone around the hub's core, sent: it shows while the playhead is in s03_hub, not elsewhere
    await seek(13.0);
    await p.keyboard.press("k");
    const [cx, cy] = await spot("s03_hub/core");
    await p.mouse.move(cx - 25, cy - 25);
    await p.mouse.down();
    await p.mouse.move(cx + 25, cy + 25, { steps: 4 });
    await p.mouse.up();
    await p.type("#c-text", "keep the middle clear");
    await p.keyboard.press("Enter");
    await p.waitForFunction(() => document.querySelectorAll("#tab-notes .item[data-id]").length === 1);
    r.draft = await p.$$eval('#overlay g[data-layer="rules"] rect', (x) => x.length); // a draft isn't a rule yet
    r.sent = await sendAll();
    await seek(5.0);
    await seek(13.5);
    await new Promise((res) => setTimeout(res, 200));
    r.inScene = await p.$$eval('#overlay g[data-layer="rules"] rect', (x) => x.length);
    await seek(19.0);
    await new Promise((res) => setTimeout(res, 200));
    r.elsewhere = await p.$$eval('#overlay g[data-layer="rules"] rect', (x) => x.length);
    return r;
  },
  // nothing to change: the send button says so, and one click sends "no notes" through the same Review list
  async nonotes() {
    const r = { before: await text("#send"), hint: await text("#sendp") };
    await p.click("#send");
    await p.waitForFunction(() => !document.querySelector("#review-sheet").hidden);
    r.list = await p.$$eval("#rv-list li .what b", (x) => x.map((e) => e.textContent));
    await p.click("#rv-send");
    await p.waitForFunction(() => !document.querySelector("#sent-sheet").hidden);
    await p.click("#st-ok");
    await p.waitForFunction(() => document.querySelector("#send").disabled);
    r.after = await text("#send");
    return r;
  },
  // an answer from an earlier round stands: shown as answered, nothing to click; Change brings the buttons back
  async carried() {
    await p.waitForFunction(() => /your answer from round/.test(document.querySelector("#asks-f")?.textContent || ""));
    const r = { line: await text("#asks-f .doneline"), todo: await p.$$eval("#asks-f [data-todo]", (x) => x.length) };
    await p.click('#asks-f button[data-f="change"]');
    await p.waitForFunction(() => document.querySelector('#asks-f button[data-f="fix"]'));
    r.buttons = await p.$$eval("#asks-f .btns > button", (x) => x.map((e) => e.textContent.trim()));
    r.was = await text("#asks-f .was");
    return r;
  },
  // the end of the flow: Done in the header, the finals to download, and a way back in (a part prefills the note)
  async finished() {
    await p.waitForFunction(() => !document.querySelector("#finish-sheet").hidden);
    const r = {
      done: await p.$eval("#donebtn", (e) => !e.hidden),
      files: await p.$$eval("#fn-files a", (x) => x.map((a) => [a.getAttribute("href"), a.getAttribute("download"), a.textContent.trim()])),
      parts: await p.$$eval("#fn-parts button", (x) => x.map((e) => e.textContent)),
    };
    r.fetched = await p.evaluate(async (u) => (await fetch(u, { method: "HEAD" })).status, r.files[0][0]);
    await p.click('#fn-parts button[data-p^="About the sound"]');
    r.sheetHidden = await p.$eval("#finish-sheet", (e) => e.hidden);
    r.note = await p.$eval("#c-text", (e) => e.value);
    r.focus = await p.evaluate(() => document.activeElement.id);
    await p.reload({ waitUntil: "networkidle0" });
    await p.waitForFunction(() => document.querySelector("#proj").textContent !== "…");
    await new Promise((res) => setTimeout(res, 300));
    r.againOnReload = !(await p.$eval("#finish-sheet", (e) => e.hidden)); // once per finish, in this browser
    await p.click("#donebtn");
    r.reopens = !(await p.$eval("#finish-sheet", (e) => e.hidden));
    return r;
  },
};

let out;
try {
  out = await SCENARIOS[scenario]();
} catch (e) {
  out = { failed: String(e.message || e) };
}
console.log(JSON.stringify({ ...out, errors }));
await b.close();
