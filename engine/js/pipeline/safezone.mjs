// Build step 6, words vs the phone safe zone (and titles wider than their box), measured in the browser with the real
// fonts loaded. A font that never loads is reported too: the render would silently use a fallback.
import path from "node:path";
import { pathToFileURL } from "node:url";
import { launch } from "../lib/browser.mjs";
import { R, W, H, LAND, COMP, die } from "./context.mjs";

export async function checkSafeZone() {
  const b = await launch(),
    p = await b.newPage();
  await p.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  const errs = [];
  p.on("pageerror", (e) => errs.push(e.message));
  await p.goto(pathToFileURL(path.resolve(COMP, "index.html")).href, { waitUntil: "load" });
  if (errs.length) die(`reel.js failed in the browser: ${errs[0]}`);
  // Measure with the real fonts. A face that never loads renders in a fallback, silently, and every width is wrong
  // (v20: widths read before the font arrived left the marker short of "measures" and the check mark on "checked").
  const fams = [R.font, R.mono].filter((f) => f?.family && f?.css).map((f) => f.family);
  const noFont = await p.evaluate(async (fams) => {
    await document.fonts.ready;
    const out = [];
    for (const f of fams) {
      try {
        if (!(await document.fonts.load(`700 48px "${f}"`)).length) out.push(f);
      } catch {
        out.push(f);
      }
    }
    return out;
  }, fams);
  noFont.forEach((f) =>
    console.log(
      `  ⚠️  the font "${f}" never loaded in the composition — the render will use a fallback (vs fonts "${f}")`,
    ),
  );
  const found = await p.evaluate(
    (W, H, LAND) => {
      const S = { l: 0.11, r: 0.89, t: 0.1, b: 0.84, railX: 0.8, railY: 0.62 },
        out = [],
        e = 2; // 2px: words set ON the line are inside
      const check = (name, el) => {
        // measure where each word ENDS UP: clear the entrance tweens' start state (a card line waits at 1.4× scale)
        el.querySelectorAll(".line,.w,.ch,.num,.sub,.em-check").forEach((e) => {
          e.style.transform = "none";
          e.style.filter = "none";
        });
        // emphasis marks count as words: a check mark past the last word can run off the safe side
        const rs = [...el.querySelectorAll(".w,.num,.sub,.em-check,.em-beats,.em-ruler")]
          .map((e) => e.getBoundingClientRect())
          .filter((r) => r.width);
        if (!rs.length) return;
        const box = {
          l: Math.min(...rs.map((r) => r.left)),
          r: Math.max(...rs.map((r) => r.right)),
          t: Math.min(...rs.map((r) => r.top)),
          b: Math.max(...rs.map((r) => r.bottom)),
        };
        const miss = [];
        if (!LAND) {
          if (box.l < W * S.l - e || box.r > W * S.r + e) miss.push("the side crop");
          if (box.t < H * S.t - e) miss.push("the status bar");
          if (box.b > H * S.b + e) miss.push("the caption");
          if (box.b > H * S.railY && box.r > W * S.railX + e) miss.push("the button rail");
        }
        if (
          [...el.querySelectorAll(".line")].some((ln) => ln.scrollWidth > el.clientWidth + 2) &&
          el.classList.contains("lower")
        )
          miss.push("its box (too wide)");
        // a mark drawn beside its word must clear it; a marker behind its word must cover all of it (a reviewer caught both, v20)
        el.querySelectorAll(".em-check").forEach((c) => {
          const w = c.parentElement.getBoundingClientRect(),
            r = c.getBoundingClientRect();
          if (r.left < w.right - 1)
            out.push(`${name}: the check mark overlaps its word — it hangs past the word in em (.em-check)`);
        });
        el.querySelectorAll(".em-mark").forEach((w) => {
          const cs = getComputedStyle(w);
          if (cs.display === "inline" && w.getClientRects().length > 1)
            out.push(`${name}: the marked word breaks across two lines, so the marker splits — move the <br>`);
        });
        if (miss.length)
          out.push(`${name} runs under ${miss.join(" and ")} — shorten it, add a <br>, or give it "size": 0.9`);
      };
      document.querySelectorAll("[data-title]").forEach((el) => check(el.dataset.title, el));
      return out;
    },
    W,
    H,
    LAND,
  );
  await b.close();
  found.forEach((m) => console.log(`  ⚠️  ${m}`));
  if (!found.length) console.log(`  safe zone: every word clear${LAND ? " (widescreen: no phone crop to check)" : ""}`);
}
