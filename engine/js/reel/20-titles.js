// The reel runtime, part 3 of 7. build concatenates js/reel/*.js in name order into ONE closure (00 opens it, 60
// closes it), so a part is not a module on its own: it shares every const and helper defined in the parts before it.
  // ───────── titles: "a<br>b" lines, <span class=a> = accent color, <span class=apart> = letters that drift apart ─────────
  function words(html, chars) {
    const box = document.createElement("div");
    box.innerHTML = html;
    const out = [];
    const inner = (w) => (chars ? [...w].map((c) => `<span class="ch">${c}</span>`).join("") : w);
    const push = (text, cls) =>
      text.split(/(\s+)/).forEach((w) => {
        if (!w) return;
        out.push(/^\s+$/.test(w) ? " " : `<span class="w ${cls}">${inner(w)}</span>`);
      });
    box.childNodes.forEach((n) =>
      n.nodeType === 3
        ? push(n.textContent, "")
        : n.classList.contains("apart")
          ? out.push(
              `<span class="w apart ${n.classList.contains("a") ? "a" : ""}">${[...n.textContent].map((c) => `<span class="ch">${c}</span>`).join("")}</span>`,
            )
          : push(n.textContent, n.className),
    );
    return out.join("");
  }
  const lines = (text, chars) =>
    text
      .split(/<br\s*\/?>/i)
      .map((ln) => `<span class="line">${words(ln, chars)}</span>`)
      .join("");
  const MASK = "inset(-60% -40% -14% -40%)"; // a line's own box, a little generous: words rise into it from below

  // one emphasis move on a title's key word, timed on the beat ("b" = beats after the title's slot starts).
  // Everything hangs off the word itself and is sized in em, never measured: the font can finish loading after this
  // runs, so a width read now is the fallback font's (v19: the marker came up short, the check mark sat on the text).
  const span = (cls, parent) => {
    const e = document.createElement("span");
    e.className = cls;
    parent.appendChild(e);
    return e;
  };
  function emphasize(t, el, slotT0) {
    const em = typeof t.em === "string" ? { fx: t.em } : t.em;
    if (!em) return [];
    const ws = em.word ? $$(".w", el).filter((w) => w.textContent.trim() === em.word) : $$(".w.a", el);
    if (!ws.length) return [];
    const te = slotT0 + (em.b ?? 1) * B,
      made = [],
      w0 = ws[0],
      wl = ws[ws.length - 1];
    if (em.fx === "pulse") {
      const col = getComputedStyle(w0).color;
      // grows away from the word before it (the key word ends its line), so it never bumps into its neighbor
      tl.fromTo(
        ws,
        { scale: 1, color: col, transformOrigin: "0% 70%" },
        { scale: 1.08, color: P.ink, duration: 0.14, ease: "power2.out", yoyo: true, repeat: 1, ...IR },
        te,
      );
    } else if (em.fx === "box") {
      // a red marker wipes in behind the word (its own background); the word turns white on it
      const col = getComputedStyle(w0).color;
      ws.forEach((w) => w.classList.add("em-mark"));
      tl.fromTo(
        ws,
        { backgroundSize: "0% 100%" },
        { backgroundSize: "100% 100%", duration: 0.34, ease: "power3.inOut", ...IR },
        te,
      );
      tl.fromTo(ws, { color: col }, { color: P.ink, duration: 0.12, ...IR }, te + 0.14);
    } else if (em.fx === "check") {
      // a check mark draws itself just past the word
      wl.classList.add("em-anchor");
      const s = svg("svg", { class: "em-check", viewBox: "0 0 10 10" }, wl);
      const p = svg(
        "path",
        {
          d: "M1.2 5.4 L4 8.1 L8.9 1.8",
          fill: "none",
          stroke: P.accent,
          "stroke-width": 1.6,
          "stroke-linecap": "round",
          "stroke-linejoin": "round",
          "stroke-dasharray": 13,
          "stroke-dashoffset": 13,
        },
        s,
      );
      tl.to(p, { attr: { "stroke-dashoffset": 0 }, duration: 0.3, ease: "power2.out" }, te);
      tl.fromTo(
        s,
        { scale: 1.5 },
        { scale: 1, duration: 0.45, ease: "back.out(3)", transformOrigin: "30% 70%", ...IR },
        te + 0.2,
      );
      made.push(s);
    } else if (em.fx === "beats") {
      // "on a schedule": four dots under the word, one lighting per beat
      w0.classList.add("em-anchor");
      const row = span("em-beats", w0),
        dots = [0, 1, 2, 3].map(() => span("em-dot", row));
      ticks.push((tt) => {
        const lt = tt - te;
        dots.forEach((d, k) => {
          if (lt < k * 0.06) {
            d.style.opacity = 0;
            return;
          }
          const n = Math.floor(lt / B),
            ph = lt / B - n,
            on = n % 4 === k;
          d.style.opacity = on ? 1 : 0.45;
          d.style.background = on ? P.accent : P.dim;
          d.style.transform = `scale(${(on ? 1 + 0.6 * (1 - easeOut(ph * 2)) : 1).toFixed(3)})`;
        });
      });
      made.push(row);
    } else if (em.fx === "ruler") {
      // a ruler draws under the word; its marker slides and snaps onto a reading on the beat
      w0.classList.add("em-anchor");
      const box = span("em-ruler", w0),
        base = span("em-base", box),
        N = 25,
        at = 72;
      tl.fromTo(base, { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: "power2.inOut", ...IR }, te);
      for (let k = 0; k <= N; k++) {
        const tall = k % 5 === 0,
          tk = span(tall ? "em-tick tall" : "em-tick", box);
        tk.style.left = ((k / N) * 100).toFixed(2) + "%";
        tl.fromTo(tk, { opacity: 0 }, { opacity: 1, duration: 0.08, ...IR }, te + 0.57 * easeInOut(k / N));
      }
      // the marker rides a full-width track moved by xPercent: a transform, so it glides sub-pixel (never tween "left")
      const snapAt = slotT0 + (em.snap ?? 3) * B,
        trk = span("em-track", box),
        mk = span("em-marker", trk),
        hit = span("em-hit", box);
      hit.style.left = at + "%";
      tl.fromTo(mk, { opacity: 0 }, { opacity: 1, duration: 0.15, ...IR }, te + 0.55);
      tl.fromTo(
        trk,
        { xPercent: 0 },
        { xPercent: at + 3, duration: snapAt - te - 0.8, ease: "power2.inOut", ...IR },
        te + 0.7,
      );
      tl.fromTo(
        trk,
        { xPercent: at + 3 },
        { xPercent: at, duration: 0.3, ease: "elastic.out(1.4,0.4)", ...IR },
        snapAt - 0.05,
      );
      tl.fromTo(hit, { opacity: 0 }, { opacity: 1, duration: 0.05, ...IR }, snapAt);
      punch(snapAt, 0.03);
      made.push(box);
    }
    return made;
  }

