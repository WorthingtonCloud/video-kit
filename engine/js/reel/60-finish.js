// The reel runtime, part 7 of 7. build concatenates js/reel/*.js in name order into ONE closure (00 opens it, 60
// closes it), so a part is not a module on its own: it shares every const and helper defined in the parts before it.
  // ───────── the finish: drifting texture, vignette, seeded grain ─────────
  if (FIN.texture === "dots") tl.fromTo("#paper", { x: 0, y: 0 }, { x: -30, y: -90, duration: END, ease: "none" }, 0);
  const grain = [];
  if (FIN.grain)
    for (let k = 0; k < 6; k++) {
      const cv = document.createElement("canvas");
      cv.width = Math.round(W / 3);
      cv.height = Math.round(H / 3);
      cv.className = "grain";
      const cx = cv.getContext("2d"),
        img = cx.createImageData(cv.width, cv.height),
        rnd = mulberry32(1000 + k);
      for (let p = 0; p < img.data.length; p += 4) {
        const v = 128 + (rnd() - 0.5) * 150;
        img.data[p] = img.data[p + 1] = img.data[p + 2] = v;
        img.data[p + 3] = 255;
      }
      cx.putImageData(img, 0, 0);
      $("#grain").appendChild(cv);
      grain.push(cv);
    }
  ticks.push((t) => {
    const gi = Math.floor(t * R.fps) % Math.max(grain.length, 1);
    grain.forEach((cv, k) => {
      cv.style.opacity = k === gi ? FIN.grain : 0;
    });
  });

  function frame(t) {
    ticks.forEach((f) => f(t));
  }
  const drv = { t: 0 };
  tl.fromTo(drv, { t: 0 }, { t: END, duration: END, ease: "none", onUpdate: () => frame(drv.t) }, 0);
  tl.seek(0);
  frame(0);
  window.__reelTimeline = tl; // index.html registers it: the lint only reads the page's own scripts
})();
