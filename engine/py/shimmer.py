"""Shimmer: thin lines, icons and small text flickering frame to frame while they stand still. A slow 3D camera turn
(the explainer's exRig tilt was the case, Oct 4, 2026) makes the rasterizer snap edges back and forth against the pixel
grid, so the same edge goes sharp, soft, sharp, soft on alternate frames. Viewers see it ("the icons flicker"); a still
frame, a one-a-second sheet and a one-frame comparison all miss it.

What counts, per 8×8 patch of the full-size frame, on three frames in a row (a, b, c):
  · some pixel jumps by more than JUMP (0–255) from a to b, and back by more than JUMP from b to c,
  · c is back where a was (the patch's mean |c − a| ≤ BACK): nothing moved, it only flickered,
  · the patch has an edge in both a and c (brightest − darkest ≥ EDGE): a thin line or a dot passing over flat ground
    flips a pixel the same way, but leaves the patch flat before and after.
A patch that does that FLIPS times or more inside one second is shimmering. Measured on an explainer:
v1 (tilting) 17–38 patches in its worst seconds, v2 (no tilt, approved) at most 15, and those were stray pixels.
"""
import subprocess

B, JUMP, BACK, EDGE, FLIPS = 8, 24, 2, 30, 3


def flips(a, b, c, np):
    """The 8×8 patches (a bool grid) where the middle frame flickered: out and straight back, on an edge that stayed."""
    d1, d2 = b - a, c - b
    px = ((d1 > JUMP) & (d2 < -JUMP)) | ((d1 < -JUMP) & (d2 > JUMP))
    hb, wb = a.shape[0] // B, a.shape[1] // B
    blk = lambda x: x[:hb * B, :wb * B].reshape(hb, B, wb, B)  # noqa: E731
    hit = blk(px).any(axis=(1, 3))
    if not hit.any():
        return hit
    back = blk(np.abs(c - a)).mean(axis=(1, 3)) <= BACK
    ba, bc = blk(a), blk(c)
    edge = np.minimum(ba.max(axis=(1, 3)) - ba.min(axis=(1, 3)), bc.max(axis=(1, 3)) - bc.min(axis=(1, 3))) >= EDGE
    return hit & back & edge


def _box(xs, ys, W, H):
    return (float(xs.min() * B / W), float(ys.min() * B / H), float((xs.max() + 1) * B / W), float((ys.max() + 1) * B / H))


def scan(src, W, H, fps, np):
    """Every second of the video with shimmering patches: [(t0, patches, (x0, y0, x1, y1) as fractions)]. Full size,
    every frame: shimmer is a one-pixel, one-frame thing, and a smaller copy averages it away."""
    p = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         stdout=subprocess.PIPE)
    n, per = W * H, max(1, round(fps))
    count, frames, i, out = None, [], 0, []
    while (buf := p.stdout.read(n)) and len(buf) == n:  # one frame at a time: a whole cut won't fit
        frames = (frames + [np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.int16)])[-3:]
        if len(frames) == 3:
            f = flips(*frames, np)
            count = f.astype(np.uint8) if count is None else count + f
        i += 1
        if i % per == 0 and count is not None:
            m = count >= FLIPS
            if m.any():
                ys, xs = np.nonzero(m)
                out.append((i // per - 1, int(m.sum()), _box(xs, ys, W, H)))
            count[:] = 0
    p.wait()
    if count is not None and i % per and (count >= FLIPS).any():  # the last part-second
        m = count >= FLIPS
        ys, xs = np.nonzero(m)
        out.append((i // per, int(m.sum()), _box(xs, ys, W, H)))
    return out
