// Build step 4, the page's styles: titles, emphasis marks, panels, the kit's drawn scenes, the end card. Every size is a
// fraction of the frame, so the same reel styles itself for vertical and widescreen.
import { R, W, H, LAND, P, r3 } from "./context.mjs";

export function css({ faces, SANS, MONO }) {
  const pct = (f, n) => r3(f * n);
  const lowerBox = LAND
    ? `left:${pct(0.057, W)}px;bottom:${pct(0.157, H)}px;width:${pct(0.4, W)}px;font-size:${pct(0.078, H)}px`
    : `left:${pct(0.11, W)}px;right:${pct(0.2, W)}px;top:${pct(0.615, H)}px;font-size:${pct(0.083, W)}px`;
  const statBox = LAND
    ? `left:${pct(0.057, W)}px;bottom:${pct(0.157, H)}px`
    : `left:${pct(0.11, W)}px;top:${pct(0.6, H)}px`;
  return `${faces}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:${W}px;height:${H}px;overflow:hidden;background:${P.ground}}
#root{position:relative;width:${W}px;height:${H}px;overflow:hidden;background:${P.ground};font-family:"${SANS}",sans-serif;color:${P.ink}}
.mono{font-family:"${MONO}",monospace}.sans{font-family:"${SANS}",sans-serif}
.seg{position:absolute;inset:0;opacity:0}#seg-0{opacity:1}
#camrig{position:absolute;inset:0}.mover{position:absolute;inset:0}
.cam{position:absolute;inset:0;perspective:1800px}.stage{position:absolute;left:0;top:0;width:1080px;height:1400px;transform-origin:0 0}
.rig3d{position:absolute;left:0;top:0;width:1080px;height:1400px;transform-origin:540px 700px}
#fx{position:absolute;left:0;top:0;overflow:visible;pointer-events:none}
#paper{position:absolute;inset:-120px;${(R.finish?.texture ?? "dots") === "dots" ? `background-image:radial-gradient(${P.card} 1.7px,transparent 2px);background-size:60px 60px` : ""}}
.vignette{position:absolute;inset:0;pointer-events:none;${R.finish?.vignette === false ? "" : "background:radial-gradient(ellipse 85% 70% at 50% 42%,transparent 55%,rgba(0,0,0,.5) 100%)"}}
.grain{position:absolute;left:0;top:0;width:${W}px;height:${H}px;opacity:0;mix-blend-mode:overlay}
.lower,.stat{position:absolute;isolation:isolate;opacity:0;text-shadow:0 4px 40px rgba(0,0,0,.85),0 2px 10px rgba(0,0,0,.9)}
.lower{${lowerBox};font-weight:800;line-height:1.03;letter-spacing:-.02em}
.lower .rule{display:block;width:.92em;height:.1em;background:${P.accent};margin-bottom:.38em;transform-origin:left center}
.stat{${statBox}}.stat .num{font-weight:800;font-size:${LAND ? pct(0.17, H) : pct(0.185, W)}px;line-height:.9;letter-spacing:-.035em;font-variant-numeric:tabular-nums}
.stat .sub{margin-top:.45em;font-weight:600;font-size:${LAND ? pct(0.042, H) : pct(0.046, W)}px;line-height:1.12;color:${P.ink};opacity:.82}
.line{display:block;white-space:nowrap}.w{display:inline-block}.ch{display:inline-block}.a{color:${P.accent}}
.lower .line{position:relative}.em-anchor{position:relative}
.em-mark{background:linear-gradient(${P.accent},${P.accent}) no-repeat 0 50%/0% 100%;padding:.03em .1em .02em;margin:-.03em -.1em -.02em;border-radius:.08em}
.em-check{position:absolute;left:calc(100% + .14em);top:.14em;width:.66em;height:.66em;overflow:visible}
.em-beats{position:absolute;left:0;top:calc(100% + .12em);display:flex;gap:.2em}.em-dot{display:block;width:.22em;height:.22em;border-radius:50%;background:${P.dim};opacity:0}
.em-ruler{position:absolute;left:0;width:100%;top:calc(100% + .04em);height:.3em}.em-base{position:absolute;left:0;top:0;width:100%;height:4px;background:${P.accent};transform-origin:0 50%;transform:scaleX(0)}
.em-tick{position:absolute;top:0;width:2px;height:.12em;margin-left:-1px;background:${P.dim};opacity:0}.em-tick.tall{width:3px;height:.24em;background:${P.ink}}
.em-track{position:absolute;left:0;top:0;width:100%;height:100%}.em-marker{position:absolute;left:0;top:-.2em;width:0;height:0;margin-left:-.11em;border-left:.11em solid transparent;border-right:.11em solid transparent;border-top:.2em solid ${P.accent};opacity:0}
.em-hit{position:absolute;top:0;width:5px;height:.3em;margin-left:-2px;background:${P.accent};opacity:0}
.cardwrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:0 ${LAND ? pct(0.06, W) : pct(0.11, W)}px}
.card{text-align:center;font-weight:800;font-size:${pct(0.118, Math.min(W, H))}px;line-height:1.03;letter-spacing:-.025em}
.panel{position:absolute;overflow:hidden;border:2px solid ${P.line};box-shadow:0 40px 100px rgba(0,0,0,.65);background:#000}
.sheen{position:absolute;top:-10%;bottom:-10%;left:0;width:60%;background:linear-gradient(100deg,transparent 0%,rgba(255,255,255,.035) 30%,rgba(255,255,255,.12) 50%,rgba(255,255,255,.035) 70%,transparent 100%);pointer-events:none}
.full{position:absolute;inset:0}.panel video,.full video,.full img{width:100%;height:100%;object-fit:cover;display:block}
.scrim{position:absolute;inset:0;background:${LAND ? `linear-gradient(to right,${P.ground}f0 0%,${P.ground}d0 38%,${P.ground}00 52%)` : `linear-gradient(to bottom,${P.ground}00 40%,${P.ground}e0 57%,${P.ground}f2 80%,${P.ground}b3 100%)`}}
.scan{position:absolute;left:0;right:0;height:5px;background:${P.accent};box-shadow:0 0 30px 6px ${P.accent}88;opacity:0}
.mote{position:absolute;left:0;top:0;border-radius:50%;background:#dfe7ec}.dust{position:absolute;inset:0;pointer-events:none}
.chat{position:absolute;left:120px;top:250px;width:840px;height:840px;background:${P.card};border:3px solid ${P.line};border-radius:40px;overflow:hidden}
.chat-h{height:120px;border-bottom:3px solid ${P.line};display:flex;align-items:center;padding:0 48px;font-weight:600;font-size:34px;color:${P.dim}}
.chat-b{padding:48px;display:flex;flex-direction:column;gap:34px}
.bub-q{align-self:flex-end;max-width:600px;background:${P.ink};color:${P.ground};font-weight:600;font-size:34px;padding:18px 30px;border-radius:40px}
.bub-a{max-width:660px;font-weight:500;font-size:38px;line-height:1.3}
.chat-in{position:absolute;left:36px;right:36px;bottom:38px;height:92px;border:3px solid ${P.line};border-radius:46px;display:flex;align-items:center;padding:0 30px;font-weight:500;font-size:30px;color:${P.dim}}
.caret{width:4px;height:40px;background:${P.ink};margin-right:10px}
.send{position:absolute;right:16px;top:15px;width:56px;height:56px;border-radius:50%;background:${P.accent}}
.claim{position:absolute;left:120px;top:260px;width:840px;height:250px;background:${P.card};border:3px solid ${P.line};border-radius:24px}
.claim .k{position:absolute;left:40px;top:30px;font-size:24px;font-weight:700;letter-spacing:.2em;color:${P.accent}}
.bar{position:absolute;left:40px;height:20px;border-radius:10px;background:${P.ink};opacity:.18}
.src{position:absolute;width:262px;height:200px;background:${P.card};border:3px solid ${P.line};border-radius:20px}
.src .k{position:absolute;left:22px;top:18px;font-size:18px;letter-spacing:.18em;color:${P.dim}}
.src svg{position:absolute;left:50%;top:58px;margin-left:-32px}.src .t{position:absolute;left:22px;bottom:18px;font-size:30px;font-weight:700}
.wall{position:absolute;transform-style:preserve-3d}
.tile{position:absolute;border-radius:16px;overflow:hidden;border:3px solid ${P.line};opacity:0;box-shadow:0 30px 60px rgba(0,0,0,.6);backface-visibility:hidden}.tile img{width:100%;height:100%;object-fit:cover;display:block}
.tileicon{position:absolute;left:420px;top:455px;width:240px;height:240px;background:${P.card};border:3px solid ${P.line};border-radius:56px;overflow:hidden}
.tileicon.is-3d{background:none;border-color:transparent}.mark3d{position:absolute}.mark3d img{position:absolute;inset:0;width:100%;height:100%;visibility:hidden}
.tileicon .logo{position:absolute;inset:36px}.tileicon .logo img{width:100%;height:100%;object-fit:contain}
.word{position:absolute;left:0;right:0;top:755px;text-align:center;font-weight:800;font-size:112px;letter-spacing:.01em;opacity:0;clip-path:inset(-20% -5% -8% -5%)}
.url{position:absolute;left:0;right:0;top:895px;text-align:center;font-weight:500;font-size:40px;color:${P.dim};opacity:0}
#dot,#ring{position:absolute;left:0;top:0;width:56px;height:56px;border-radius:50%;opacity:0}#dot{background:${P.accent}}#ring{border:4px solid ${P.accent}}`;
}
