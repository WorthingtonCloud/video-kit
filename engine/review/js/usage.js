// Two small things for the dogfood. The review clock: seconds this page was reviewing (visible, and playing or used in
// the last minute), and of those, playing; sent as time.spent every five minutes and whenever the page is hidden or
// closed, so vs review report can say how long reviewing took. And the "Report a tool problem" button: a sentence
// that goes to the kit's dogfood log (DOGFOOD.md), never to Claude's fix list.
import { app, $, toast } from "./core.js";
import { player } from "./player.js";

let secs = 0,
  playing = 0,
  last = Date.now();
const used = () => (last = Date.now());
["pointerdown", "keydown", "wheel"].forEach((e) => addEventListener(e, used, { passive: true }));

function flush() {
  if (secs < 1) return;
  const body = JSON.stringify({ events: [{ type: "time.spent", secs: Math.round(secs), playing: Math.round(playing) }] });
  secs = playing = 0;
  // keepalive: it still goes when the tab is closing
  fetch("api/events", { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {});
}
setInterval(() => {
  if (document.visibilityState !== "visible") return;
  const p = player.playing();
  if (p || Date.now() - last < 60_000) secs++;
  if (p) playing++;
  if (secs >= 300) flush();
}, 1000);
document.addEventListener("visibilitychange", () => document.visibilityState === "hidden" && flush());
addEventListener("pagehide", flush);

// the tool-problem button
const btn = $("#friction"),
  box = $("#friction-box");
btn.onclick = () => {
  box.hidden = !box.hidden;
  if (!box.hidden) box.querySelector("textarea").focus();
};
box.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.f === "cancel") return (box.hidden = true);
  const t = box.querySelector("textarea"),
    text = t.value.trim();
  if (!text) return t.focus();
  const where = `${document.querySelector("#drawer").hidden ? "the video" : "the round's panel"} at ${document.querySelector("#t-now").textContent}`;
  await fetch("api/events", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ events: [{ type: "friction.noted", text, where }] }) });
  t.value = "";
  box.hidden = true;
  toast("Reported to the tool's test log. Thanks: that's what it's for.");
});
box.addEventListener("keydown", (e) => {
  if (e.key === "Escape") box.hidden = true;
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    box.querySelector('[data-f="send"]').click();
  }
});

export const usage = { flush };
