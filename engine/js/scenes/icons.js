// Explainer scene library, part 2 of 4: line icons on an 84-unit grid, white strokes and one detail in the accent color
// (drawn as the demo's red, swapped for the palette's accent). Add your own: Object.assign(GLX, { name: '<path …/>' }).
const GLX = {
  person:
    '<circle cx="42" cy="30" r="15" fill="none" stroke="#fff" stroke-width="5"/><path d="M14 78c3-17 14-26 28-26s25 9 28 26" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/>',
  clock:
    '<circle cx="42" cy="42" r="30" fill="#18191d" stroke="#fff" stroke-width="5"/><path d="M42 42V22M42 42l14 9" stroke="#e8402c" stroke-width="5" stroke-linecap="round"/>',
  mail: '<rect x="12" y="22" width="60" height="42" rx="4" fill="#18191d" stroke="#fff" stroke-width="5"/><path d="M13 25l29 21 29-21" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round"/>',
  pen: '<path d="M20 64l4-14 30-30 10 10-30 30z" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round"/><path d="M48 26l10 10" stroke="#e8402c" stroke-width="5"/>',
  eye: '<path d="M8 42c12-18 56-18 68 0-12 18-56 18-68 0z" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round"/><circle cx="42" cy="42" r="9" fill="#e8402c"/>',
  lock: '<rect x="20" y="38" width="44" height="32" rx="4" fill="#18191d" stroke="#e8402c" stroke-width="5"/><path d="M29 38v-8a13 13 0 0 1 26 0v8" fill="none" stroke="#e8402c" stroke-width="5"/>',
  ticket:
    '<rect x="12" y="18" width="60" height="48" rx="4" fill="none" stroke="#fff" stroke-width="5"/><path d="M22 32h40M22 44h28M22 56h18" stroke="#fff" stroke-width="5" stroke-linecap="round"/>',
  code: '<path d="M30 24L14 42l16 18M54 24l16 18-16 18" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><path d="M47 20L37 64" stroke="#e8402c" stroke-width="5" stroke-linecap="round"/>',
  logs: '<path d="M14 22h56M14 34h40M14 46h52M14 58h30" stroke="#fff" stroke-width="5" stroke-linecap="round"/><circle cx="62" cy="58" r="6" fill="#e8402c"/>',
  team: '<circle cx="30" cy="30" r="11" fill="none" stroke="#fff" stroke-width="5"/><circle cx="56" cy="30" r="11" fill="none" stroke="#fff" stroke-width="5"/><path d="M10 70c2-13 10-20 20-20s18 7 20 20M36 70c2-13 10-20 20-20s18 7 20 20" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/>',
  sheet:
    '<rect x="12" y="14" width="60" height="56" rx="3" fill="none" stroke="#fff" stroke-width="5"/><path d="M12 30h60M12 46h60M32 14v56M52 14v56" stroke="#fff" stroke-width="4"/>',
  chair:
    '<path d="M26 14v34h32V14M22 48h40M28 48v24M56 48v24" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/>',
  mag: '<circle cx="36" cy="36" r="20" fill="none" stroke="#fff" stroke-width="6"/><path d="M51 51l18 18" stroke="#e8402c" stroke-width="8" stroke-linecap="round"/>',
  car: '<rect x="6" y="30" width="72" height="26" rx="8" fill="#fff"/><path d="M20 30l8-12h26l10 12" fill="#fff"/><circle cx="24" cy="58" r="8" fill="#111114" stroke="#fff" stroke-width="3"/><circle cx="62" cy="58" r="8" fill="#111114" stroke="#fff" stroke-width="3"/><rect x="4" y="36" width="8" height="8" rx="2" fill="#e8402c"/>',

  bug: '<ellipse cx="42" cy="50" rx="15" ry="20" fill="#18191d" stroke="#fff" stroke-width="5"/><circle cx="42" cy="24" r="8" fill="#fff"/><path d="M27 42H13M27 54H11M29 64L17 73M57 42h14M57 54h16M55 64l12 9M37 18l-6-8M47 18l6-8M42 32v37" stroke="#fff" stroke-width="4" stroke-linecap="round"/>',
  q: '<rect x="10" y="12" width="64" height="60" rx="6" fill="#18191d" stroke="#fff" stroke-width="5"/><path d="M33 34a9 9 0 1 1 13 8c-3 2-4 4-4 8" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/><circle cx="42" cy="60" r="3.5" fill="#fff"/>',
  coin: '<circle cx="42" cy="42" r="28" fill="#2a2b30" stroke="#fff" stroke-width="5"/><path d="M50 31a13 13 0 1 0 0 22M43 24v36" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round"/>',
  eye2: '<path d="M8 42c12-18 56-18 68 0-12 18-56 18-68 0z" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round"/><circle cx="42" cy="42" r="9" fill="#fff"/>',
};
for (const k in GLX) GLX[k] = GLX[k].replaceAll("#e8402c", P.accent);
const exIcon = (parent, g, size, x, y) =>
  div(
    "ex-ic",
    parent,
    `<svg viewBox="0 0 84 84" width="${size}" height="${size}">${GLX[g]}</svg>`,
    `left:${x}px;top:${y}px;width:${size}px;height:${size}px`,
  );
