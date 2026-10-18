"""QA turntable of representative dolls (SPEC §4.3) and the factory parameter sweep (PLAN §3.7).

blender -b -P blender/render_qa.py -- [--dolls id,id,…] [--angles 24] [--quality draft|final] [--sweep]
Outputs renders/qa/turntable/<id>/f_NN.png, renders/qa/turntable_<id>.png, renders/qa/thumbs.png,
renders/qa/sweep.png
"""
from __future__ import annotations

import dataclasses
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from lib import attributes as A  # noqa: E402
from lib import config as C  # noqa: E402
from lib import doll_factory as D  # noqa: E402
from lib import materials as M  # noqa: E402
from lib import mesh_utils as MU  # noqa: E402
from lib import qa as Q  # noqa: E402
from lib import render as R  # noqa: E402
from lib import vahanas as VH  # noqa: E402

QA_DOLLS = ["s9_ganesha", "s2_rama", "s3_sita", "s4_murugan", "s2_narasimha", "s5_chettiar"]
COMPANIONS = {"s4_murugan": ["s4_peacock"]}


def turntable_scene(cfg: C.GoluConfig, quality: str, res: int) -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    M.init(cfg)
    R.setup_color_management(scene, exposure=-0.1)
    R.apply_quality(scene, quality, resolution=(res, res), samples=48 if quality == "final" else 32)
    R.setup_glare(scene, True, 0.25)
    R.setup_world_color(scene, cfg.palette.material("world"), 0.8)
    col = MU.ensure_collection("Studio")
    # silk sweep backdrop: floor curving up into a back wall
    pts = [(0.0, -1.2 + i * 0.16, 0.0) for i in range(10)]          # floor up to y = 0.24
    for i in range(1, 13):                                          # quarter-circle cove, radius 0.3
        a = i / 12 * math.pi / 2
        pts.append((0.0, 0.24 + math.sin(a) * 0.3, (1 - math.cos(a)) * 0.3))
    pts += [(0.0, 0.54, 0.3 + i * 0.15) for i in range(1, 7)]       # back wall up to z = 1.2
    verts, faces = [], []
    for i, (_, y, z) in enumerate(pts):
        verts += [(-1.5, y, z), (1.5, y, z)]
    for i in range(len(pts) - 1):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    sweep = MU.new_mesh_object("Sweep", verts, faces, col)
    uv = sweep.data.uv_layers.new(name="UVMap")
    for li, loop in enumerate(sweep.data.loops):
        co = sweep.data.vertices[loop.vertex_index].co
        uv.data[li].uv = ((co.x + 1.5) / 3.0, 0.3 + 0.0 * co.y)
    MU.shade_smooth(sweep, None)
    MU.assign_material(sweep, M.silk("maroon"))
    from lib.environment import _area_light
    P_ = cfg.palette
    _area_light("QA_Key", (1.2, 1.0), (-0.9, -1.3, 1.1), Vector((0, 0, 0.13)), P_.kelvin("key"), 45, col)
    _area_light("QA_Rim", (0.6, 0.4), (0.8, 0.6, 0.9), Vector((0, 0, 0.15)), P_.kelvin("rim"), 30, col, 0.5, 1.4)
    _area_light("QA_Fill", (1.0, 1.0), (1.1, -1.0, 0.4), Vector((0, 0, 0.12)), P_.kelvin("fill"), 8, col)
    cam = bpy.data.objects.new("QA_Cam", bpy.data.cameras.new("QA_Cam"))
    cam.data.lens = 50
    cam.data.clip_start = 0.01
    col.objects.link(cam)
    scene.camera = cam
    return scene


def frame_camera(scene, objs: list[bpy.types.Object], margin: float = 1.18) -> None:
    bpy.context.view_layer.update()          # matrix_world must include the doll's real-size scale
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    for o in objs:
        a, b = MU.bounds_world(o)
        lo = Vector((min(lo.x, a.x), min(lo.y, a.y), min(lo.z, a.z)))
        hi = Vector((max(hi.x, b.x), max(hi.y, b.y), max(hi.z, b.z)))
    size = max(hi.z - lo.z, (hi.x - lo.x) * 0.9, (hi.y - lo.y) * 0.9) * margin
    cam = scene.camera
    fov = 2 * math.atan(cam.data.sensor_width / (2 * cam.data.lens))
    dist = size / (2 * math.tan(fov / 2))
    centre = (lo + hi) / 2
    eye = Vector((0.0, centre.y - dist, centre.z + size * 0.12))
    cam.matrix_world = Q.look_at(eye, centre)
    cam.data.dof.use_dof = False


def render_turntable(scene, root: bpy.types.Object, extra: list[bpy.types.Object], out_dir: Path, angles: int) -> list[Path]:
    pivot = bpy.data.objects.new("QA_Pivot", None)
    scene.collection.objects.link(pivot)
    for o in [root] + extra:
        o.parent = pivot
    frame_camera(scene, [root] + extra)
    paths = []
    for i in range(angles):
        pivot.rotation_euler = (0, 0, i / angles * math.tau)
        bpy.context.view_layer.update()
        p = out_dir / f"f_{i + 1:02d}.png"
        R.render_still(scene, p)
        paths.append(p)
    for o in [root] + extra:
        o.parent = None
    bpy.data.objects.remove(pivot)
    return paths


def structural_report(spec: C.DollSpec, ob: bpy.types.Object) -> list[str]:
    errs = []
    if ob.type != "MESH":
        errs.append("not a mesh")
    mats = [m.name for m in ob.data.materials if m]
    if mats != ["M_ClayGloss"]:
        errs.append(f"materials {mats}")
    lo, hi = MU.bounds_local(ob)
    if hi.z - lo.z <= 0:
        errs.append("degenerate bounds")
    for k in ("doll_id", "head_center", "hotspot_local", "mark_type"):
        if k not in ob:
            errs.append(f"missing prop {k}")
    unknown = [t for t in spec.attributes if t not in A.known_tokens()]
    if unknown:
        errs.append(f"unknown attribute tokens {unknown}")
    return errs


def sweep(cfg: C.GoluConfig, out: Path, quality: str) -> Path:
    scene = turntable_scene(cfg, quality, 640)
    base = cfg.doll("s8_vijaya")
    tiles = []
    col = MU.ensure_collection("Sweep")
    tmp = out / "sweep_tiles"
    toks = {2: ("abhaya", "varada"), 4: ("abhaya", "varada", "padma", "padma"),
            6: ("abhaya", "kalasam", "khadga", "shield", "padma", "padma"),
            8: base.attributes, 10: base.attributes + ("trishula", "bow")}
    for n, at in toks.items():
        spec = dataclasses.replace(base, id=f"sweep_arms{n}", arms=n, attributes=tuple(at), extras=("karanda_makuta",))
        ob = D.make_doll(spec, cfg, col)
        frame_camera(scene, [ob])
        tiles.append(tmp / f"arms{n}.png")
        R.render_still(scene, tiles[-1])
        bpy.data.objects.remove(ob)
    for skin in ("blue", "peach", "wheat", "dark", "elephant-grey", "red-sanders"):
        spec = dataclasses.replace(cfg.doll("s3_lakshmana"), id=f"sweep_skin_{skin}", skin=skin)
        ob = D.make_doll(spec, cfg, col)
        frame_camera(scene, [ob])
        tiles.append(tmp / f"skin_{skin}.png")
        R.render_still(scene, tiles[-1])
        bpy.data.objects.remove(ob)
    for kind in ("peacock", "lion", "mouse", "swan", "garuda", "elephant", "cow", "horse", "gaja_pair", "bullock_pair"):
        ob, _ = VH.build_vahana(kind, cfg.palette, C.rng_for("sweep", kind), "fanned" if kind == "peacock" else "standing")
        ob.data.materials.clear()
        ob.data.materials.append(M.clay_gloss())
        MU.add_subsurf(ob, 1, 1)
        s = VH.size_m(kind)
        ob.scale = (s, s, s)
        ob.rotation_euler = (0, 0, -0.6 if kind not in ("peacock", "mouse", "garuda") else 0.0)
        for k, v in dict(head_center=(0.0, 0.0, -10.0), head_radius=1.0, mark_type=0.0).items():
            ob[k] = v
        D.pack_face_props(ob)
        bpy.context.view_layer.update()
        frame_camera(scene, [ob])
        tiles.append(tmp / f"vahana_{kind}.png")
        R.render_still(scene, tiles[-1])
        bpy.data.objects.remove(ob)
    return Q.contact_sheet(tiles, 7, out / "sweep.png", 300)


def lineup(cfg: C.GoluConfig, args: C.CliArgs, out: Path) -> list[Path]:
    """Wide frontal view of each built step (all dolls in place) for the Phase 3 placement review."""
    blend = args.out / f"golu_{C.scene_quality(args.quality)}.blend"
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    R.apply_quality(scene, args.quality, resolution=(1600, 720))
    from lib.environment import step_geometry
    steps = step_geometry(cfg.layout)
    cam = Q.ensure_qa_camera(scene, lens=32)
    cam.data.dof.use_dof = False
    scene.camera = cam
    paths = []
    for h in steps:
        if h.n not in args.steps:
            continue
        fov = 2 * math.atan(18 / 32)
        dist = (h.width * 1.08) / 2 / math.tan(fov / 2)
        target = Vector((0.0, h.y_front + 0.12, h.z_top + 0.13))
        cam.matrix_world = Q.look_at(target + Vector((0.0, -dist, dist * math.tan(math.radians(9)))), target)
        p = out / f"lineup_step{h.n}.png"
        R.render_still(scene, p)
        paths.append(p)
        print(f"QA lineup step {h.n} → {p.name}")
    return paths


def main(argv: list[str]) -> int:
    args = C.parse_cli(argv, {"--dolls": dict(default=",".join(QA_DOLLS)), "--angles": dict(type=int, default=24),
                              "--sweep": dict(action="store_true"), "--res": dict(type=int, default=768),
                              "--lineup": dict(action="store_true")})
    cfg = C.load_config(args.config)
    out = args.out / "qa"
    if args.extra["lineup"]:
        lineup(cfg, args, out)
        return 0
    ids = [d for d in args.extra["dolls"].split(",") if d]
    angles = args.extra["angles"]
    failures = []
    fronts = []
    for did in ids:
        t0 = time.time()
        scene = turntable_scene(cfg, args.quality, args.extra["res"])
        col = MU.ensure_collection("Dolls")
        spec = cfg.doll(did)
        ob = D.make_doll(spec, cfg, col)
        extra = []
        for i, cid in enumerate(COMPANIONS.get(did, [])):
            c = D.make_doll(cfg.doll(cid), cfg, col)
            lo, hi = MU.bounds_world(ob)
            c.location = (hi.x + 0.06 + i * 0.1, 0.05, 0)
            extra.append(c)
        bpy.context.view_layer.update()
        errs = structural_report(spec, ob)
        build_s = time.time() - t0
        print(f"QA {did}: built in {build_s:.1f}s, verts={len(ob.data.vertices)}, H={ob['unit_height']:.3f}m"
              + (f", ERRORS {errs}" if errs else ""))
        failures += [f"{did}: {e}" for e in errs]
        paths = render_turntable(scene, ob, extra, out / "turntable" / did, angles)
        step = max(1, angles // 8)
        Q.contact_sheet(paths[::step][:8], 4, out / f"turntable_{did}.png", 384)
        fronts.append(paths[0])
        print(f"QA {did}: {angles} frames in {time.time() - t0 - build_s:.1f}s")
    if fronts:
        Q.contact_sheet(fronts, len(fronts), out / "thumbs.png", 160)
    if args.extra["sweep"]:
        p = sweep(cfg, out, args.quality)
        print(f"QA sweep → {p}")
    for f in failures:
        print("QA FAIL:", f)
    print(f"QA: {'PASS' if not failures else str(len(failures)) + ' failures'}")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        code = main(sys.argv)
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.exit(code)
