# vs mark3d's Blender half: the studio's end-card mark, built in 3D and rendered as see-through frames the end card plays
# in place of the drawn mark. Run by vs mark3d (never by hand): Blender -b --python mark3d.py -- <job.json>
#
# job.json: {"mark": {"path", "point", "viewBox", "stroke"}, "palette": {"card", "ink", "accent"}, "out": dir,
#            "size": 1080, "samples": 64, "frames": [optional list, for a quick test]}
# Writes <out>/f0001.png … f0132.png (RGBA, see-through) and <out>/meta.json: the frame the point lands on and where the
# tile sits at rest, in the render's pixels, so the kit can lay the tile exactly over the drawn one.
#
# The motion (4.4 s at 30 fps): the tile swings up into place, the mark's lines draw in turn, the accent point drops and
# lands with a squash on frame 33 (the end card puts that frame on its beat), a light sweeps the tile, the camera settles
# face-on. Made from one studio's logo (Oct 4, 2026) and kept general: any mark drawn with straight lines (SVG M L H V Z,
# either case) and one accent rectangle. Right angles join cleanly: each line is swept with a square profile and runs
# past its corner by half a stroke, the next one starts half a stroke after it, so the two touch and never overlap (an
# overlap z-fights on the shared front face; one bent curve twists its profile through the corner and tapers both legs).
import bpy, bmesh, sys, math, os, json, re
from bpy_extras.object_utils import world_to_camera_view

job = json.load(open(sys.argv[sys.argv.index("--") + 1]))
M = job["mark"]
VB = [float(v) for v in (M.get("viewBox") or "-3 -3 30 30").split()]
STROKE = float(M.get("stroke", 2.2))
OUT = job["out"]
SIZE = int(job.get("size", 1080))
FPS, END, LAND = 30, 132, 33
# every keyframe below is written on a 4 s, 120-frame timeline; R() maps it onto the 132-frame end-card cut
RETIME = [(1, 1), (24, 12), (26, 14), (42, 19), (58, 27), (70, 33), (84, 46), (120, 132)]


def R(f):
    for (a0, b0), (a1, b1) in zip(RETIME, RETIME[1:]):
        if f <= a1:
            return b0 + (f - a0) * (b1 - b0) / (a1 - a0)
    return RETIME[-1][1]


def lin(h):  # hex sRGB → linear RGBA
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1,)


PAL = job.get("palette", {})
CARD, INK, ACCENT = lin(PAL.get("card", "#1c1d21")), lin(PAL.get("ink", "#ffffff")), lin(PAL.get("accent", "#e8402c"))
U = 3.0 / VB[2]  # the tile is 3 m across, whatever the viewBox's units
CX, CY = VB[0] + VB[2] / 2, VB[1] + VB[3] / 2


def P(x, y):  # SVG point → (X, Z) in Blender, centered on the viewBox (SVG y runs down, Blender z up)
    return ((x - CX) * U, -(y - CY) * U)


def polylines(d):
    """The path's straight lines as lists of points; anything curved is refused (vs mark3d says so in plain words)."""
    toks = re.findall(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?", d)
    lines, cur, x, y, start, cmd, i = [], [], 0.0, 0.0, (0.0, 0.0), None, 0
    num = lambda: float(toks[i])
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    cur.append(start)
                    lines.append(cur)
                cur, (x, y) = [], start
                continue
            if cmd not in "MmLlHhVv":
                raise SystemExit(f"REFUSED: the mark's path uses '{cmd}' (a curve); vs mark3d builds straight lines only")
        if cmd in "Mm":
            nx, ny = float(toks[i]), float(toks[i + 1])
            i += 2
            if cmd == "m":
                nx, ny = x + nx, y + ny
            if cur:
                lines.append(cur)
            x, y, start, cur = nx, ny, (nx, ny), [(nx, ny)]
            cmd = "L" if cmd == "M" else "l"  # more pairs after a moveto are lines
        elif cmd in "Ll":
            nx, ny = float(toks[i]), float(toks[i + 1])
            i += 2
            x, y = (x + nx, y + ny) if cmd == "l" else (nx, ny)
            cur.append((x, y))
        elif cmd in "Hh":
            v = num()
            i += 1
            x = x + v if cmd == "h" else v
            cur.append((x, y))
        elif cmd in "Vv":
            v = num()
            i += 1
            y = y + v if cmd == "v" else v
            cur.append((x, y))
    if len(cur) > 1:
        lines.append(cur)
    return [l for l in lines if len(l) > 1]


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
sc.render.fps, sc.frame_start, sc.frame_end = FPS, 1, END
sc.render.resolution_x = sc.render.resolution_y = SIZE
sc.view_settings.view_transform = "Standard"
try:
    sc.eevee.use_raytracing = True
except Exception:
    pass
sc.eevee.taa_render_samples = int(job.get("samples", 64))
sc.render.film_transparent = True

w = bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 1


def mat(name, col, rough, emit=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = col
        b.inputs["Emission Strength"].default_value = emit
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    return m


M_TILE, M_INK, M_PT = mat("tile", CARD, 0.35, coat=0.6), mat("ink", INK, 0.3, emit=0.35), mat("point", ACCENT, 0.25, emit=0.6)


def box(name, sx, sy, sz, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new("bevel", "BEVEL")
        bv.width = bevel
        bv.segments = 4
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


root = bpy.data.objects.new("root", None)
sc.collection.objects.link(root)

# the tile: the app-icon square with rounded corners (only the four edges that run front to back), 0.35 m deep
tile = box("tile", 3.0, 0.35, 3.0, M_TILE)
tile.parent = root
bv = tile.modifiers.new("round", "BEVEL")
bv.affect = "EDGES"
bv.width = 0.6
bv.segments = 12
bv.limit_method = "WEIGHT"
bm = bmesh.new()
bm.from_mesh(tile.data)
bw = bm.edges.layers.float.get("bevel_weight_edge") or bm.edges.layers.float.new("bevel_weight_edge")
for e in bm.edges:
    d = e.verts[0].co - e.verts[1].co
    e[bw] = 1.0 if abs(d.y) > 1e-4 else 0.0
bm.to_mesh(tile.data)
bm.free()
rim = tile.modifiers.new("rim", "BEVEL")
rim.width = 0.03
rim.segments = 3
rim.limit_method = "ANGLE"

# the lines: one straight leg per segment, swept with a square profile, drawn in turn
T, FACE = STROKE * U, -0.175 - 0.11
prof_d = bpy.data.curves.new("profile", "CURVE")
prof_d.dimensions = "2D"
ps = prof_d.splines.new("POLY")
ps.points.add(3)
ps.use_cyclic_u = True
for k, (a, b) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
    ps.points[k].co = (a * T / 2, b * T / 2, 0, 1)
prof = bpy.data.objects.new("profile", prof_d)
sc.collection.objects.link(prof)
prof.hide_render = prof.hide_viewport = True

legs, h = [], STROKE / 2
for line in polylines(M["path"]):
    for k, (a, b) in enumerate(zip(line, line[1:])):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-6:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        # square caps: half a stroke past both ends, except a leg after a corner starts half a stroke past the corner
        s = h if k > 0 else -h
        legs.append(((a[0] + ux * s, a[1] + uy * s), (b[0] + ux * h, b[1] + uy * h)))
if not legs:
    raise SystemExit("REFUSED: the mark's path has no lines to build")
total = sum(math.dist(a, b) for a, b in legs)
f0 = 24.0
for n, (a, b) in enumerate(legs):
    d = bpy.data.curves.new(f"leg{n}", "CURVE")
    d.dimensions = "3D"
    d.bevel_mode = "OBJECT"
    d.bevel_object = prof
    d.use_fill_caps = True
    d.twist_mode = "MINIMUM"
    d.bevel_factor_mapping_end = "SPLINE"
    sp = d.splines.new("POLY")
    sp.points.add(1)
    sp.use_smooth = False
    for j, (x, y) in enumerate((a, b)):
        X, Z = P(x, y)
        sp.points[j].co = (X, 0, Z, 1)
    o = bpy.data.objects.new(f"leg{n}", d)
    sc.collection.objects.link(o)
    o.location = (0, FACE, 0)
    o.parent = root
    d.materials.append(M_INK)
    f1 = f0 + 34 * math.dist(a, b) / total  # the draw shares frames 24–58 by length, like the drawn mark's dash
    legs[n] = (o, d, f0, f1)
    f0 = f1


def key(o, path, frame, val, idx=None, *_):
    """A keyframe on the end-card cut's frame. Every key keeps Blender's default smooth curve: the approved logo it came from was
    made that way (its script asked for BACK/QUAD easing, but Blender 5's layered actions have no action.fcurves, so the
    ask never landed, and the motion its reviewer approved is the default one). The easing names stay in the calls as notes."""
    frame = R(frame)
    if idx is None:
        setattr(o, path, val)
        o.keyframe_insert(path, frame=frame)
    else:
        getattr(o, path)[idx] = val
        o.keyframe_insert(path, index=idx, frame=frame)


# the accent point: a little block whose origin sits on its base, so the squash sits on the floor
pt = None
if M.get("point"):
    px, py, pw, ph = [float(v) for v in M["point"]]
    pt = box("point", pw * U, 0.3, ph * U, M_PT, bevel=0.02)
    pt.parent = root
    bpy.context.view_layer.objects.active = pt
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.transform.translate(value=(0, 0, ph * U / 2))
    bpy.ops.object.mode_set(mode="OBJECT")
    X, Z = P(px + pw / 2, py + ph)
    REST = (X, -0.175 - 0.15, Z)

# 1) the tile swings up into place
key(root, "rotation_euler", 1, math.radians(-75), 0, "BACK", "EASE_OUT")
key(root, "rotation_euler", 26, 0, 0)
key(root, "location", 1, -0.9, 2, "CUBIC", "EASE_OUT")
key(root, "location", 26, 0, 2)
key(root, "rotation_euler", 1, math.radians(-18), 2, "CUBIC", "EASE_OUT")
key(root, "rotation_euler", 120, math.radians(6), 2)
# 2) the lines draw in turn
for o, d, a, b in legs:
    key(d, "bevel_factor_end", 1, 0.0, None, "CONSTANT")
    key(d, "bevel_factor_end", a, 0.0, None, "SINE", "EASE_IN_OUT")
    key(d, "bevel_factor_end", b, 1.0, None)
    key(o, "hide_render", 1, True, None, "CONSTANT")
    key(o, "hide_render", a + 1, False, None, "CONSTANT")  # no sliver before it draws
# 3) the point drops, lands with a squash on frame 70 (→ 33 on the cut), settles
if pt:
    key(pt, "location", 1, REST[0], 0, "CONSTANT")
    key(pt, "location", 1, REST[1], 1, "CONSTANT")
    key(pt, "location", 1, REST[2] + 3.0, 2, "CONSTANT")
    key(pt, "location", 58, REST[2] + 3.0, 2, "QUAD", "EASE_IN")
    key(pt, "location", 70, REST[2], 2)
    for f, sx, sz in ((69, 0.9, 1.15), (71, 1.28, 0.62), (75, 0.94, 1.08), (79, 1.03, 0.97), (84, 1, 1)):
        key(pt, "scale", f, sx, 0)
        key(pt, "scale", f, sx, 1)
        key(pt, "scale", f, sz, 2)
    key(pt, "hide_render", 1, True, None, "CONSTANT")
    key(pt, "hide_render", 58, False, None, "CONSTANT")

# the camera: a slow push-in that ends face-on
cam_d = bpy.data.cameras.new("cam")
cam_d.lens = 70
cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
key(cam, "location", 1, (0.9, -14.5, 0.5), None, "CUBIC", "EASE_OUT")
key(cam, "location", 120, (0, -12.2, 0.05), None)
key(cam, "rotation_euler", 1, (math.radians(88), 0, math.radians(3.5)), None, "CUBIC", "EASE_OUT")
key(cam, "rotation_euler", 120, (math.radians(90), 0, 0), None)


def area(name, loc, rot, energy, size, col=(1, 1, 1)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy, d.size, d.color = energy, size, col
    o = bpy.data.objects.new(name, d)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = tuple(math.radians(r) for r in rot)
    return o


# soft key upper left, cool fill right, warm rim behind (an edge glow on the tile), and a strip that sweeps the tile
area("key", (-4, -6, 5), (55, 0, -35), 900, 4)
area("fill", (5, -5, -1), (95, 0, 45), 160, 5, (0.85, 0.9, 1))
area("rim", (0, 4, 3), (-55, 0, 0), 700, 6, (1, 0.55, 0.45))
sw = area("sweep", (-6, -4, 0), (90, 0, 0), 0, 0.4)
sw.data.shape = "RECTANGLE"
sw.data.size, sw.data.size_y = 0.4, 8
key(sw.data, "energy", 1, 0, None, "CONSTANT")
key(sw.data, "energy", 82, 0, None, "SINE", "EASE_IN_OUT")
key(sw.data, "energy", 92, 500, None)
key(sw.data, "energy", 108, 0, None)
key(sw, "location", 82, (-6, -4, 0), None, "SINE", "EASE_IN_OUT")
key(sw, "location", 112, (6, -4, 0), None)

# where the tile's front face sits at rest (the last frame), in the render's pixels: the kit lays it over the drawn tile
sc.frame_set(END)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
te = tile.evaluated_get(dg)
ymin = min(v.co.y for v in te.data.vertices)  # the face toward the camera, in the tile's own frame (it ends turned 6°)
front = [te.matrix_world @ v.co for v in te.data.vertices if v.co.y < ymin + 0.05]
uv = [world_to_camera_view(sc, cam, p) for p in front]
xs, ys = [u.x * SIZE for u in uv], [(1 - u.y) * SIZE for u in uv]
os.makedirs(OUT, exist_ok=True)
json.dump({"fps": FPS, "frames": END, "land_frame": LAND, "size": SIZE, "tile_px": [min(xs), min(ys), max(xs), max(ys)],
           "blender": bpy.app.version_string}, open(os.path.join(OUT, "meta.json"), "w"), indent=1)

sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
for f in job.get("frames") or range(1, END + 1):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(OUT, f"f{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"FRAME {f}/{END}", flush=True)
print("DONE", flush=True)
