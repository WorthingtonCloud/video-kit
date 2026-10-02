// The player: the rendered MP4 is the truth for pixels and sound. A transport made for reviewing (a frame at a time,
// four speeds, a jump by scene), one clock everything else reads (player.t), and an overlay over the picture where the
// timeline (and later the marks) draw in fractions of the frame, so it fits any size the stage takes.
import { app, $, fmt } from "./core.js";

const v = app.video,
  NS = "http://www.w3.org/2000/svg";
const listeners = new Set();
let fps = 30,
  last = -1;

// Frame k of the render is the composition at k/fps, and it shows while the video's clock is in [k/fps, (k+1)/fps).
// So a paused player's moment is its frame's own time (what a note records, what the composition seeks to), and a seek
// lands in the middle of the frame (a clock exactly on the boundary can show the frame before).
//
// While the Mix panel is open its stems are the sound, and the picture follows their clock (player.clock): the video
// plays muted and is pulled back into step whenever it drifts more than 0.08 s, as the mixer always did.
export const player = {
  clock: null,
  t: () => (player.playing() ? (player.clock?.running ? player.clock.time() : v.currentTime || 0) : player.frame() / fps),
  end: () => app.maps?.timeline?.end || v.duration || 0,
  fps: () => fps,
  on: (fn) => listeners.add(fn),
  playing: () => !v.paused && !v.ended,
  play() {
    if (v.ended || v.currentTime >= player.end() - 0.02) v.currentTime = 0;
    v.play().catch(() => {});
  },
  pause: () => v.pause(),
  toggle: () => (player.playing() ? player.pause() : player.play()),
  // the first frame at or after t (a scene's start lands on its first frame, not the last of the one before)
  seek(t) {
    v.pause();
    const last = Math.max(0, Math.ceil(player.end() * fps) - 1);
    show(Math.max(0, Math.min(last, Math.ceil(t * fps - 0.01))));
  },
  frame: () => Math.floor((v.currentTime || 0) * fps + 1e-6),
  step(n) {
    v.pause();
    show(Math.max(0, player.frame() + n));
  },
  // hand the sound to a clock (the Mix panel's stems), or back to the video (null)
  useClock(c) {
    if (player.playing()) player.pause();
    player.clock = c;
    v.muted = !!c;
    if (c) player.rate(1);
    document.querySelectorAll("#t-speeds button").forEach((b) => (b.disabled = !!c && +b.dataset.r !== 1));
  },
  rate(r) {
    v.playbackRate = r;
    document.querySelectorAll("#t-speeds button").forEach((b) => b.classList.toggle("on", +b.dataset.r === r));
  },
  // the overlay: named layers of SVG drawn in frame fractions (the timeline's hover outline, later the marks)
  draw(layer, shapes) {
    const svg = $("#overlay");
    let g = svg.querySelector(`g[data-layer="${layer}"]`);
    if (!g) {
      g = document.createElementNS(NS, "g");
      g.dataset.layer = layer;
      svg.appendChild(g);
    }
    g.replaceChildren(
      ...shapes.map((s) => {
        const el = document.createElementNS(NS, s.tag || "rect");
        for (const [k, val] of Object.entries(s)) if (k !== "tag" && k !== "text") el.setAttribute(k, val);
        el.setAttribute("vector-effect", "non-scaling-stroke");
        return el;
      }),
    );
  },
  // fractions of the frame under a mouse event on the stage
  at(e) {
    const r = $("#stage").getBoundingClientRect();
    return [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height];
  },
};

function show(k) {
  v.currentTime = (k + 0.5) / fps;
  tick(true);
}

function tick(force) {
  const t = player.t();
  if (!force && t === last) return;
  last = t;
  $("#t-now").textContent = fmt(t);
  listeners.forEach((fn) => fn(t));
}
(function loop() {
  if (player.playing()) {
    const c = player.clock;
    if (c?.running) {
      const t = c.time();
      if (t >= player.end() - 0.02) player.pause();
      else if (Math.abs(v.currentTime - t) > 0.08) v.currentTime = t; // the sound leads; the picture follows
    }
    tick();
  }
  requestAnimationFrame(loop);
})();
v.addEventListener("seeked", () => tick(true));
v.addEventListener("loadedmetadata", () => tick(true));
v.addEventListener("timeupdate", () => tick()); // when the tab is hidden, animation frames stop but this still fires
v.addEventListener("play", () => {
  $("#t-play").textContent = "❚❚";
  player.clock?.start(v.currentTime);
});
v.addEventListener("pause", () => {
  $("#t-play").textContent = "▶";
  const c = player.clock;
  if (c?.running) {
    const t = c.stop();
    v.currentTime = Math.min(t, player.end() - 0.5 / fps); // the picture stops where the sound did
  }
  tick(true);
});

export function setup(timeline) {
  fps = timeline?.fps || 30;
  $("#t-end").textContent = fmt(player.end());
  tick(true);
}

// jump to the start of the scene before or after this moment
export function sceneJump(dir) {
  const segs = app.maps?.timeline?.segments || [];
  const t = player.t() + 1e-3;
  const i = segs.findIndex((s) => t >= s.t0 && t < s.t1);
  const target = dir < 0 ? (t - segs[i]?.t0 > 0.6 ? segs[i] : segs[i - 1]) : segs[i + 1];
  if (target) player.seek(target.t0);
}

$("#t-play").onclick = () => player.toggle();
$("#t-back").onclick = () => player.step(-1);
$("#t-fwd").onclick = () => player.step(1);
$("#t-speeds").onclick = (e) => {
  const b = e.target.closest("button");
  if (b) player.rate(+b.dataset.r);
};
