// Compare: the version a note was made on and the version that answered it, side by side at the note's moment, the
// target outlined in both (its old box, and the box the new version's element map measured). They play, pause and
// step together. Esc closes it.
import { app, $, fmt, esc, asCut, href } from "./core.js";

let box = null;
const fps = () => app.maps?.timeline?.fps || 30;

export function compare(n) {
  const S = app.state,
    m = n.measured,
    old = asCut(S.rounds[n.round - 1], n.cut), // both shapes in a round: the note's own shape, then and now
    now = asCut(S.rounds.at(-1), n.cut);
  if (!m || !old || !now) return;
  const sound = !!n.sound || (m.moment && (m.audio?.changed_secs || 0) >= 0.1), // a sound note, or a moment whose sound changed
    t = "t" in n.time ? n.time.t : n.time.t0,
    tNew = m.off_at_t ? m.on[0] : t;
  // a sound is heard in a version's mixed file (a round can be open on the bare render, which has none)
  const heard = (R) => {
    if (!sound) return R.video;
    const mixed = (app.ctx.versions || []).filter((x) => x.version === R.version && x.cut === R.cut && /-(take\d+|mixed)\.mp4$/.test(x.video));
    return (mixed.find((x) => x.video.endsWith(`-take${app.ctx.mixer?.saved?.take}.mp4`)) || mixed[0])?.video.slice(1) || R.video;
  };
  const pane = (v, label, b, at) => `
    <figure><div class="cmp-stage" style="--ar:${(now.size || [9, 16]).join("/")};--arn:${((now.size || [9, 16])[0] / (now.size || [9, 16])[1]).toFixed(4)}">
      <video src="${esc(href(v))}" muted playsinline preload="auto" data-t="${at}"></video>
      ${b ? `<svg viewBox="0 0 1 1" preserveAspectRatio="none"><rect x="${b[0]}" y="${b[1]}" width="${b[2] - b[0]}" height="${b[3] - b[1]}" vector-effect="non-scaling-stroke"/></svg>` : ""}
    </div><figcaption>${label} · ${fmt(at)}</figcaption></figure>`;
  close();
  box = document.createElement("div");
  box.className = "compare";
  box.innerHTML = `<div class="cmp-in" role="dialog" aria-label="Compare v${m.from} and v${m.to}">
    <div class="cmp-top"><b>${esc(n.id)}</b> · ${esc((n.comment || "").slice(0, 90))}<button class="cmp-x" title="Close (Esc)">✕</button></div>
    <div class="cmp-panes">${pane(heard(old), `v${m.from} (the note)`, n.target?.box, t)}${pane(heard(now), `v${m.to} (the answer)`, m.new_box, tNew)}</div>
    <p class="cmp-m">${esc(m.summary || "")}</p>
    <div class="cmp-tr">${sound ? `<button data-c="hear">▶ hear v${m.from}, then v${m.to}</button>` : `<button data-c="-1">‹ frame</button><button data-c="play">▶ play both</button><button data-c="1">frame ›</button>`}<button data-c="back">back to the moment</button></div>
  </div>`;
  document.body.appendChild(box);
  const vids = [...box.querySelectorAll("video")];
  const reset = () => vids.forEach((v) => (v.currentTime = +v.dataset.t + 0.5 / fps()));
  vids.forEach((v) => v.addEventListener("loadedmetadata", () => (v.currentTime = +v.dataset.t + 0.5 / fps()), { once: true }));
  box.addEventListener("click", (e) => {
    if (e.target === box || e.target.closest(".cmp-x")) return close();
    const c = e.target.closest("button")?.dataset.c;
    if (!c) return;
    if (c === "hear") {
      // a sound: the old version around its moment, then the new one (one at a time: two at once is noise)
      const [a, b] = vids,
        from = Math.max(0, t - 1.2);
      const run = (v, next) => {
        v.muted = false;
        v.currentTime = from;
        v.play();
        setTimeout(() => (v.pause(), (v.muted = true), next?.()), 2600);
      };
      run(a, () => run(b));
    } else if (c === "play") {
      const go = vids[0].paused;
      vids.forEach((v) => (go ? v.play() : v.pause()));
      e.target.textContent = go ? "❚❚ pause both" : "▶ play both";
    } else if (c === "back") reset();
    else vids.forEach((v) => (v.pause(), (v.currentTime = Math.max(0, v.currentTime + +c / fps()))));
  });
}

export function close() {
  box?.querySelectorAll("video").forEach((v) => v.pause());
  box?.remove();
  box = null;
}
document.addEventListener("keydown", (e) => {
  if (box && e.key === "Escape") {
    close();
    e.stopPropagation();
  }
}, true);
