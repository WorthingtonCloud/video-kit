// The reel runtime, between parts 6 and 7: names. build concatenates js/reel/*.js in name order into ONE closure, so
// this part shares every const and helper defined before it, and runs once every segment and title has been built.
// Every element on screen gets an address, "segment/element", so a note, a finding or a click can point at it and
// still mean the same thing after a rebuild:
//   · a segment is its reel.json name (data-seg); a title is title/<id> wherever it shows; what sits outside every
//     segment (the camera's rings and sparks, the end card's dot, the grain) is frame/<name>
//   · the scene names what matters: div(cls, parent, html, style, "tier-episodic-label"), svg(tag, attrs, parent,
//     "spoke-3"), exName(el, "phone-mockup"), or data-el="…" in its own markup
//   · anything else the scene made with div() or svg() that paints (words, a fill, a border, a picture, a shape), or
//     that is empty and gets its words later, gets a derived name from its role (its first class, else its tag) and its
//     words: ~ex-k:episodic. A panel with no words of its own is known by the first words inside it (~ex-p:system-prompt),
//     an icon by its glyph, a picture by its file. The tilde means "derived": it lasts as long as those words do. One
//     with no words at all is numbered in page order: ~circle, ~circle#2
//   · markup inside a div's html, and everything inside a title, belongs to the element that holds it
//   · a name only has to be unique inside its segment (one scene function can draw two segments); a repeat gets #2
// window.__names: addr(node) → the address of the nearest named element at or above a node (what a click lands on),
// all() → [{addr, el}] for every named element, repeats → names the scene used twice in one segment, made(el) → the
// call stack that made it (or the element whose markup holds it), when vs inspect asked for stacks.
  {
    const SHAPES = new Set(["circle", "ellipse", "rect", "line", "polyline", "polygon", "path", "text", "image", "use"]);
    const seen = (c) => {
      const m = c && c.match(/rgba?\(([^)]+)\)/);
      if (!m) return false;
      const v = m[1].split(",").map(Number);
      return v.length < 4 || v[3] > 0;
    };
    // does this one node paint anything itself?
    const paints = (n) => {
      if (n.namespaceURI === NS) return SHAPES.has(n.tagName);
      if (/^(IMG|VIDEO|CANVAS)$/.test(n.tagName)) return true;
      for (const c of n.childNodes) if (c.nodeType === 3 && c.textContent.trim()) return true;
      const cs = getComputedStyle(n);
      if (seen(cs.backgroundColor) || cs.backgroundImage !== "none" || cs.boxShadow !== "none") return true;
      return ["Top", "Right", "Bottom", "Left"].some(
        (k) => parseFloat(cs[`border${k}Width`]) > 0 && seen(cs[`border${k}Color`]),
      );
    };
    // a unit: a node the scene made, plus the markup inside it, up to the next node the scene made or named
    const isOwn = (n, root) => n === root || !(MADE.has(n) || n.hasAttribute("data-el"));
    function unitNodes(root) {
      const out = [];
      const walk = (n) => {
        for (const c of n.children) {
          if (!isOwn(c, root)) continue;
          out.push(c);
          walk(c);
        }
      };
      out.push(root);
      walk(root);
      return out;
    }
    const unitText = (root) => {
      let s = "";
      const walk = (n) => {
        for (const c of n.childNodes) {
          if (c.nodeType === 3) s += " " + c.textContent;
          else if (c.nodeType === 1 && isOwn(c, root)) walk(c);
        }
      };
      walk(root);
      return s;
    };
    // every text node under a node, a space between them (textContent runs neighbors' words together)
    const allText = (n) => {
      const w = document.createTreeWalker(n, NodeFilter.SHOW_TEXT),
        out = [];
      for (let t; (t = w.nextNode()); ) out.push(t.textContent);
      return out.join(" ");
    };
    const slug = (s) =>
      s
        .normalize("NFKD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, " ")
        .trim()
        .split(" ")
        .filter(Boolean)
        .slice(0, 3)
        .join("-")
        .slice(0, 28);
    const role = (n) => (n.classList && n.classList[0]) || n.tagName.toLowerCase();
    const scopeOf = (n) => n.closest("[data-seg]")?.getAttribute("data-seg") || "frame";
    const taken = new Map(), // scope → Map(name → count)
      repeats = [];
    const claim = (scope, name, explicit) => {
      const m = taken.get(scope) || taken.set(scope, new Map()).get(scope),
        k = (m.get(name) || 0) + 1;
      m.set(name, k);
      if (k === 1) return name;
      if (explicit) repeats.push(`${scope}/${name}`);
      return `${name}#${k}`;
    };

    const all = document.getElementById("root").querySelectorAll("*");
    for (const n of all) {
      if (n.hasAttribute("data-title") && !n.hasAttribute("data-el"))
        n.setAttribute("data-el", `title/${n.getAttribute("data-title")}`);
    }
    for (const n of all) {
      const own = n.getAttribute("data-el");
      if (n.parentElement?.closest("[data-title]")) continue; // a title's insides are the title
      if (own) {
        n.setAttribute("data-el", claim(scopeOf(n), own, true));
        continue;
      }
      if (!MADE.has(n)) continue;
      const nodes = unitNodes(n),
        empty = n.childNodes.length === 0;
      if (!empty && !nodes.some(paints)) continue; // a wrapper, a rig, a stage: structure, not a thing on screen
      // its own words; else the first words inside it (a panel is known by its label: ~ex-p:system-prompt); else a hint
      // the scene left (an icon's glyph); else the picture it shows
      const img = n.tagName === "IMG" ? n : n.querySelector("img"),
        words =
          slug(unitText(n)) ||
          slug(allText(n)) ||
          slug(n.getAttribute("data-hint") || "") ||
          slug((img?.getAttribute("src") || "").split("/").pop().replace(/\.\w+$/, ""));
      n.setAttribute("data-el", claim(scopeOf(n), `~${role(n)}${words ? ":" + words : ""}`, false));
    }

    const addr = (node) => {
      for (let n = node; n && n.nodeType === 1; n = n.parentElement) {
        const name = n.getAttribute("data-el");
        if (name) return name.startsWith("title/") ? name : `${scopeOf(n)}/${name}`;
        if (n.hasAttribute("data-seg")) return n.getAttribute("data-seg");
      }
      return null;
    };
    window.__names = {
      addr,
      all: () => [...document.querySelectorAll("#root [data-el]")].map((el) => ({ addr: addr(el), el })),
      text: allText,
      repeats,
      made: (el) => {
        for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
          const s = MADE.get(n);
          if (s) return typeof s === "string" ? s : null;
        }
        return null;
      },
    };
  }
