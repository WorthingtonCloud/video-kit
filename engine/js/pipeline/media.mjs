// Build step 3, the media: the music bed cut to length, page recordings / clips / stills sized to their slots, the
// collage tiles, the fonts and the logo, all copied next to the composition. Only redoes what changed.
import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { ENGINE, NODE_MODULES, recDir } from "../lib/paths.mjs";
import { R, W, H, FPS, LAND, M, COMP, A, die, run, ff, probe, r3, fresh, stamp, mtime, copy } from "./context.mjs";
import { SEGS, END } from "./timing.mjs";

export function prepareMedia() {
  // ───────── the music: one track, trimmed to the cut, faded only at the very end ─────────
  const offset = +(M.offset || 0),
    fade = +(M.fade ?? 2.2),
    mlen = probe(M.file);
  // a narrated video's track is its voice bed (the narration + 6 s for the end card), not music (jev-explainer, Oct 1, 2026)
  if (mlen < offset + END - 0.05)
    die(
      R.acts?.length
        ? `the voice bed is ${mlen.toFixed(1)}s but the cut needs ${(offset + END).toFixed(1)}s: lower plan.json → "total" to ${(mlen - offset).toFixed(1)} or less, then vs plan.`
        : `the music is ${mlen.toFixed(1)}s but the cut needs ${(offset + END).toFixed(1)}s. Shorten the cut, replay whole bars, or extend the track.`,
    );
  const bedKey = `${M.file}|${mtime(M.file)}|${offset}|${END}|${fade}`;
  if (!fresh(`${A}/bed.wav`, bedKey)) {
    ff(
      "-ss",
      String(offset),
      "-i",
      M.file,
      "-t",
      String(END),
      "-af",
      `afade=t=out:st=${Math.max(0, END - fade)}:d=${fade}`,
      "-ar",
      "48000",
      "-ac",
      "2",
      `${A}/bed.wav`,
    );
    stamp(`${A}/bed.wav`, bedKey);
  }

  // ───────── footage: page recordings, clips and stills become media files sized to their slot ─────────
  const frames = (d) =>
    fs.existsSync(d)
      ? fs
          .readdirSync(d)
          .filter((f) => /^f\d+\.jpg$/.test(f))
          .sort()
      : [];
  const media = { tiles: {}, logo: null };
  const LEAD_MAX = 0.4,
    TAIL = 0.45;
  const segHTML = SEGS.map((seg, i) => {
    const src = seg.source,
      len = seg.t1 - seg.t0,
      LEAD = r3(Math.min(LEAD_MAX, seg.t0)),
      v = (file) =>
        `<video id="v${i}" src="${file}" muted playsinline data-start="${r3(seg.t0 - LEAD)}" data-duration="${r3(LEAD + len + TAIL)}" data-track-index="${i + 1}"></video>`;
    const lead = `tpad=start_mode=clone:start_duration=${LEAD}`;
    let inner = "",
      footage = false;
    if (src.shot) {
      const shot = (R.shots || {})[src.shot];
      if (!shot) die(`${seg.name}: no shot "${src.shot}" in reel.json → shots`);
      // "video": your own screen recording · "dir": a folder of f0000.jpg… · otherwise record.mjs records the url,
      // and re-records when the shot's entry (url, range, frames…) or the reel's size changed
      const dir = shot.dir || recDir(src.shot),
        out = `${A}/shot-${src.shot}-${i}.mp4`,
        scale = `scale=${LAND ? 1920 : 1080}:-2:flags=lanczos`;
      if (shot.video) {
        const key = `${shot.video}|${mtime(shot.video)}|${shot.ss || 0}|${len}|${LEAD}`;
        if (!fresh(out, key)) {
          ff(
            "-ss",
            String(shot.ss || 0),
            "-i",
            shot.video,
            "-vf",
            `fps=${FPS},${scale},${lead},tpad=stop_mode=clone:stop_duration=30,format=yuv420p`,
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-t",
            String(LEAD + len + TAIL + 0.1),
            out,
          );
          stamp(out, key);
        }
      } else {
        if (!shot.dir) {
          const want = JSON.stringify({ ...shot, size: R.size });
          const have = fs.existsSync(`${dir}/shot.json`)
            ? JSON.stringify(JSON.parse(fs.readFileSync(`${dir}/shot.json`, "utf8")))
            : null;
          if (!frames(dir).length || have !== want) run("node", [path.join(ENGINE, "js/record.mjs"), src.shot]);
        }
        const n = frames(dir).length,
          key = `${dir}|${n}|${len}|${mtime(`${dir}/${frames(dir)[0]}`)}|${mtime(`${dir}/shot.json`)}|${LEAD}`;
        if (!n) die(`${seg.name}: no frames in ${dir}`);
        if (!fresh(out, key)) {
          // stretch or squeeze the recorded frames to fill the slot exactly
          ff(
            "-framerate",
            (n / len).toFixed(5),
            "-start_number",
            "0",
            "-i",
            `${dir}/f%04d.jpg`,
            "-vf",
            `fps=${FPS},${scale},${lead},tpad=stop_mode=clone:stop_duration=${TAIL + 0.2},format=yuv420p`,
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-t",
            String(LEAD + len + TAIL + 0.1),
            out,
          );
          stamp(out, key);
        }
      }
      // A real page runs its text to its own edges, and phones crop ~9% off each side of a vertical video:
      // the page sits in a framed panel at 78% so its words survive. Widescreen: a panel on the right.
      const inset = src.inset ?? shot.inset ?? R.shot_inset ?? 0.78;
      const [mw, mh] = spawnSync(
        "ffprobe",
        ["-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", out],
        { encoding: "utf8" },
      )
        .stdout.trim()
        .split(",")
        .map(Number);
      const lh = Math.min(H * 0.8, (W * 0.52 * mh) / mw); // widescreen: the page's own shape, right side, never cropped to 16:9
      const box = LAND
        ? { w: (lh * mw) / mh, h: lh, x: W * 0.96 - (lh * mw) / mh }
        : { w: W * inset, h: H * inset, x: (W * (1 - inset)) / 2 };
      let top = (H - box.h) / 2;
      // vertical, a recording of another shape (an app window, not a phone page) keeps its own shape instead of being
      // cropped to the frame's; with words over the segment it sits high, above the titles, like a drawn scene
      if (!LAND && Math.abs(mw / mh - W / H) > 0.03) {
        box.h = Math.min(H * inset, (box.w * mh) / mw);
        box.w = (box.h * mw) / mh;
        box.x = (W - box.w) / 2;
        const words = seg.titles.some((tt) => ["lower", "stat", undefined].includes(R.titles[tt.id]?.kind));
        top = words ? Math.max(H * 0.12, Math.min((H - box.h) / 2, H * 0.6 - box.h)) : (H - box.h) / 2; // 0.12: room for its 3D sway
      }
      const radius = inset >= 1 && !LAND ? 0 : 34;
      inner = `<div class="panel" data-el="page" style="left:${r3(box.x)}px;top:${r3(top)}px;width:${r3(box.w)}px;height:${r3(box.h)}px;border-radius:${radius}px">${v(path.relative(COMP, out))}</div>`;
      footage = true;
    } else if (src.clip) {
      const out = `${A}/clip-${i}.mp4`,
        sp = src.speed || 1,
        key = `${src.clip}|${mtime(src.clip)}|${src.ss || 0}|${sp}|${len}|${LEAD}`;
      if (!fresh(out, key)) {
        ff(
          "-ss",
          String(src.ss || 0),
          "-i",
          src.clip,
          "-vf",
          `setpts=(PTS-STARTPTS)/${sp},fps=${FPS},scale=${W}:${H}:force_original_aspect_ratio=increase:flags=lanczos,crop=${W}:${H},setsar=1,${lead},tpad=stop_mode=clone:stop_duration=30,format=yuv420p`,
          "-an",
          "-c:v",
          "libx264",
          "-crf",
          "16",
          "-t",
          String(LEAD + len + TAIL + 0.1),
          out,
        );
        stamp(out, key);
      }
      inner = `<div class="full" data-el="clip">${v(path.relative(COMP, out))}</div>`;
      footage = true;
    } else if (src.still) {
      const out = `${A}/still-${i}${path.extname(src.still)}`;
      copy(src.still, out);
      inner = `<div class="full" data-el="still"><img src="${path.relative(COMP, out)}" alt=""></div>`;
      footage = true;
    }
    const words = seg.titles.some((tt) => ["lower", "stat", undefined].includes(R.titles[tt.id]?.kind));
    const scrim = footage && words && seg.scrim !== false ? `<div class="scrim" data-el="scrim"></div>` : "";
    // data-seg: the segment's name, the first half of every address on it (segment/element; js/reel/55-names.js)
    return `<div class="seg" id="seg-${i}" data-seg="${seg.name}"><div class="mover"><div class="cam">${inner}</div></div>${scrim}</div>`;
  });

  // grid tiles: files, frames of clips ("clip.mp4@1.5"), or frames of this very reel ("@5.2", snapshotted below)
  const snapTimes = [];
  SEGS.forEach((seg, i) => {
    if (!seg.source.grid) return;
    const cols = seg.source.cols || 3;
    if (seg.source.grid.length % cols)
      console.log(
        `  ⚠️  ${seg.name}: ${seg.source.grid.length} tiles leaves a gap in a ${cols}-wide grid — an unfilled grid reads as a mistake`,
      );
    // the wall showcases the thing's own work: a frame of this reel, or the same picture twice, reads as repetition (v21)
    const own = seg.source.grid.filter((g) => g.startsWith("@")).length;
    if (own)
      console.log(
        `  ⚠️  ${seg.name}: ${own} of ${seg.source.grid.length} tiles are frames of this reel — build the wall from the thing's own work (collage.mjs)`,
      );
    const missing = seg.source.grid.map((g) => g.split("@")[0]).filter((f) => f && !fs.existsSync(f));
    if (missing.length)
      die(`${seg.name}: ${missing.length} of the grid's pictures don't exist yet (first: ${missing[0]}). Make them with ` +
        `vs collage (reel.json → "collage"), or list your own pictures in the grid.`);
    const seen = new Map();
    seg.source.grid.forEach((g) => {
      const [file, at] = g.split("@");
      if (!file || !fs.existsSync(file)) return;
      const h = crypto
        .createHash("sha1")
        .update(fs.readFileSync(file))
        .update(at || "")
        .digest("hex");
      if (seen.has(h))
        console.log(`  ⚠️  ${seg.name}: ${g} is the same picture as ${seen.get(h)} — every tile a different source`);
      else seen.set(h, g);
    });
    media.tiles[i] = seg.source.grid.map((g, k) => {
      const out = `${A}/tiles/g${i}-${k}.jpg`,
        [file, at] = g.split("@");
      if (!file) snapTimes.push({ at: +at, out });
      else if (at != null) {
        const key = `${file}|${mtime(file)}|${at}`;
        if (!fresh(out, key)) {
          ff("-ss", at, "-i", file, "-frames:v", "1", "-vf", `scale=${Math.round(W / 2)}:-2`, "-q:v", "3", out);
          stamp(out, key);
        }
      } else ff("-i", file, "-vf", `scale=${Math.round(W / 2)}:-2`, "-q:v", "3", out);
      return path.relative(COMP, out);
    });
  });

  // fonts: @font-face from the css fonts.mjs wrote, files copied next to the composition (never a remote @import)
  const fontFace = (f) => {
    if (!f?.css || !fs.existsSync(f.css)) return "";
    const dir = path.dirname(f.css);
    return fs.readFileSync(f.css, "utf8").replace(/url\((?![a-z]+:)["']?([^)"']+)["']?\)/g, (_, u) => {
      copy(path.join(dir, u), `${A}/fonts/${path.basename(u)}`);
      return `url('assets/fonts/${path.basename(u)}')`;
    });
  };
  const SANS = R.font?.family || "system-ui",
    MONO = R.mono?.family || "monospace";
  const faces = fontFace(R.font) + fontFace(R.mono);
  if (!faces && R.font?.family)
    console.log(
      `  ⚠️  no font css for "${R.font.family}": run vs fonts "${R.font.family}" (else the render falls back to a system font)`,
    );
  const logo = R.scenes?.endcard?.logo;
  if (logo && fs.existsSync(logo)) {
    media.logo = `assets/logo${path.extname(logo)}`;
    copy(logo, `${COMP}/${media.logo}`);
  } else if (logo && !R.scenes?.endcard?.mark)
    console.log(`  ⚠️  logo "${logo}" not found — end card drawn without it`);
  // a rendered mark: a folder of see-through frames (f0001.png …), played in place of the drawn mark
  const m3 = R.scenes?.endcard?.mark3d;
  if (m3?.frames) {
    const fr = fs.existsSync(m3.frames) ? fs.readdirSync(m3.frames).filter((f) => /\.(png|webp)$/i.test(f)).sort() : [];
    if (fr.length) {
      media.mark3d = fr.map((f) => `assets/mark3d/${f}`);
      fs.mkdirSync(`${COMP}/assets/mark3d`, { recursive: true });
      fr.forEach((f) => copy(path.join(m3.frames, f), `${COMP}/assets/mark3d/${f}`));
    } else console.log(`  ⚠️  mark3d frames "${m3.frames}" not found — end card drawn with the flat mark`);
  }

  const gsapFile = [
    path.join(NODE_MODULES, "gsap/dist/gsap.min.js"),
    "node_modules/gsap/dist/gsap.min.js",
    ...(process.env.PUPPETEER_FROM
      ? [path.join(path.dirname(process.env.PUPPETEER_FROM), "node_modules/gsap/dist/gsap.min.js")]
      : []),
  ].find((f) => fs.existsSync(f));
  if (!gsapFile) die("gsap not installed: run vs setup");
  copy(gsapFile, `${COMP}/gsap.min.js`);
  return { segHTML, media, snapTimes, faces, SANS, MONO };
}
