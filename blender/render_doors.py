"""Entrance door sequence (SPEC §4.6, DECISIONS D30).

blender -b -P blender/render_doors.py -- [--quality draft|high|final] [--stride N] [--no-resume]
Adds a "Doors" scene to the built Golu .blend: carved teak doors in the front-wall doorway with brass studs
and bells, kumkum/turmeric marks, mango-leaf thoranam, threshold kolam and a kuthuvilakku each side. The
doors swing inward over 72 frames (frames 1–6 static, so frame 1 is the entrance poster) while warm golden
light and haze pour out, revealing a soft glimpse of the Golu.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from lib import config as C  # noqa: E402
from lib import materials as M  # noqa: E402
from lib import mesh_utils as MU  # noqa: E402
from lib import props as PR  # noqa: E402
from lib import qa as Q  # noqa: E402
from lib import render as R  # noqa: E402

DOOR_W, DOOR_H = 1.5, 2.45


def door_leaf(name: str, side: int, cfg: C.GoluConfig, rng) -> bpy.types.Object:
    """One carved teak leaf hinged at its outer edge (origin on the hinge)."""
    w, h, t = DOOR_W / 2 - 0.01, DOOR_H - 0.02, 0.06
    slab = MU.box(name, (w, t, h), (-side * w / 2, 0, h / 2), bevel=0.008)
    MU.assign_material(slab, M.teak())
    parts = [slab]
    # carved panels: raised frames and rosettes on the outer face (−Y)
    for row in range(4):
        zc = 0.32 + row * 0.58
        frame = MU.box(f"{name}_panel{row}", (w * 0.74, 0.012, 0.42), (-side * w / 2, -t / 2 - 0.004, zc), bevel=0.006)
        inner = MU.box(f"{name}_inner{row}", (w * 0.6, 0.014, 0.3), (-side * w / 2, -t / 2 - 0.01, zc), bevel=0.01)
        ros = MU.lathe(f"{name}_ros{row}", [(0.0, 0.03), (0.04, 0.026), (0.07, 0.012), (0.08, 0.0), (0.0, 0.0)], 24,
                       screw=False)
        ros.rotation_euler = (math.pi / 2, 0, 0)
        ros.location = (-side * w / 2, -t / 2 - 0.012, zc)
        MU.apply_transform(ros)
        MU.displace(ros, MU.texture(f"tx_{name}_ros{row}", "WOOD", wood_type="RINGNOISE", noise_scale=0.02), 0.004)
        for o in (frame, inner, ros):
            MU.assign_material(o, M.teak())
        parts += [frame, inner, ros]
    # brass studs grid
    for i in range(4):
        for j in range(7):
            stud = MU.uv_sphere(f"{name}_stud{i}{j}", 0.018, 12, 8, scale=(1, 0.6, 1))
            stud.location = (-side * (0.08 + i * (w - 0.16) / 3), -t / 2 - 0.006, 0.15 + j * (h - 0.3) / 6)
            MU.assign_material(stud, M.brass())
            parts.append(stud)
    # kumkum & turmeric marks near the hinge edge (applied on the threshold-facing stile)
    for k, key in enumerate(("kumkum-powder", "turmeric-powder", "kumkum-powder")):
        mark = MU.cylinder(f"{name}_mark{k}", 0.022, 0.002, 16)
        mark.rotation_euler = (math.pi / 2, 0, 0)
        mark.location = (-side * 0.04, -t / 2 - 0.002, 0.95 + k * 0.08)
        MU.assign_material(mark, M.powder(key))
        parts.append(mark)
    return MU.join(parts, name)


def build_door_set(cfg: C.GoluConfig, front_y: float, col) -> tuple[list[bpy.types.Object], list]:
    rng = C.rng_for("doors")
    leaves = []
    for side in (-1, 1):
        leaf = door_leaf(f"DoorLeaf_{'L' if side < 0 else 'R'}", side, cfg, rng)
        MU.link(leaf, col)
        hinge = bpy.data.objects.new(f"DoorHinge_{side}", None)
        col.objects.link(hinge)
        hinge.location = (side * DOOR_W / 2, front_y, 0.0)
        leaf.parent = hinge
        leaves.append(hinge)
    frame_parts = []
    for side in (-1, 1):
        jamb = MU.box(f"DoorJamb{side}", (0.14, 0.3, DOOR_H + 0.1), (side * (DOOR_W / 2 + 0.07), front_y, (DOOR_H + 0.1) / 2),
                      col, bevel=0.01)
        MU.assign_material(jamb, M.teak())
        frame_parts.append(jamb)
    lintel = MU.box("DoorLintel", (DOOR_W + 0.32, 0.32, 0.16), (0, front_y, DOOR_H + 0.12), col, bevel=0.01)
    MU.assign_material(lintel, M.teak())
    sill = MU.box("DoorThreshold", (DOOR_W + 0.3, 0.4, 0.08), (0, front_y - 0.05, 0.04), col, bevel=0.01)
    MU.assign_material(sill, M.granite())
    frame_parts += [lintel, sill]
    for i in range(9):    # brass bells along the lintel
        x = -DOOR_W / 2 + 0.08 + i * (DOOR_W - 0.16) / 8
        bell = MU.lathe(f"DoorBell{i}", [(0.0, 0.0), (0.03, 0.0), (0.028, 0.012), (0.018, 0.04), (0.008, 0.055),
                                        (0.0, 0.058)], 20, col, screw=False)
        bell.location = (x, front_y - 0.17, DOOR_H + 0.0)
        chain = MU.cylinder(f"DoorBellChain{i}", 0.002, 0.06, 6, col, center=(x, front_y - 0.17, DOOR_H + 0.088))
        for o in (bell, chain):
            MU.assign_material(o, M.brass())
        frame_parts += [bell, chain]
    th = PR.build_thoranam("DoorThoranam", (-DOOR_W / 2 - 0.15, front_y - 0.18, DOOR_H + 0.25),
                           (DOOR_W / 2 + 0.15, front_y - 0.18, DOOR_H + 0.25), rng, col, sag=0.08)
    kol = PR.build_kolam("DoorKolam", 9, 0.1, rng, col, line_width=0.01, density=0.3)
    kol.location = (0, front_y - 0.75, 0.0)
    lamps = []
    for side in (-1, 1):
        lamp, flames, lights = PR.build_kuthuvilakku(f"DoorLamp_{side}", 1.1, C.rng_for("doorlamp", side), col, 2.5)
        lamp.location = (side * (DOOR_W / 2 + 0.45), front_y - 0.45, 0)
        lamps.append(lamp)
    return leaves, frame_parts + [th, kol] + lamps


def animate_doors(hinges, start: int = 1, n: int = 72) -> None:
    for hinge, side in zip(hinges, (-1, 1)):
        hinge.rotation_euler = (0, 0, 0)
        hinge.keyframe_insert("rotation_euler", index=2, frame=start)
        hinge.keyframe_insert("rotation_euler", index=2, frame=start + 5)
        # inward swing (toward +Y, into the Golu room): left leaf turns clockwise, right anticlockwise
        hinge.rotation_euler = (0, 0, side * math.radians(104))
        hinge.keyframe_insert("rotation_euler", index=2, frame=start + n - 6)
        hinge.rotation_euler = (0, 0, side * math.radians(102))
        hinge.keyframe_insert("rotation_euler", index=2, frame=start + n - 1)
        fc = hinge.animation_data.action.fcurves.find("rotation_euler", index=2)
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "EASE_IN_OUT"
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"


def add_glow_and_haze(cfg: C.GoluConfig, front_y: float, col) -> None:
    from lib.environment import _area_light
    glow = _area_light("DoorGlow", (1.4, 2.2), (0, front_y + 0.9, 1.2), Vector((0, front_y - 2.0, 1.0)),
                       cfg.palette.kelvin("door_glow"), 0.0, col, spread_deg=120)
    ld = glow.data
    for f, w in ((1, 0.0), (8, 0.0), (40, 650.0), (60, 900.0), (72, 900.0)):
        ld.energy = w
        ld.keyframe_insert("energy", frame=f)
    # the visitor's side of the doors: a warm hallway lamp overhead and a low fill, so the carved teak, brass
    # studs, bells and thoranam read in the poster (frame 1) before any light comes from the Golu room
    _area_light("DoorKey", (1.2, 0.8), (0.3, front_y - 2.2, 3.0), Vector((0, front_y, 1.3)),
                cfg.palette.kelvin("key"), 220.0, col, spread_deg=70)
    _area_light("DoorFill", (2.5, 1.0), (0, front_y - 3.8, 1.0), Vector((0, front_y, 1.2)),
                cfg.palette.kelvin("fill"), 45.0, col, specular=0.3)
    haze = MU.box("DoorHaze", (DOOR_W + 0.6, 3.0, DOOR_H + 0.4), (0, front_y + 0.4, (DOOR_H + 0.4) / 2), col)
    haze.data.materials.append(M.haze_volume(cfg.palette.kelvin("door_glow"), 0.03))


def main(argv: list[str]) -> int:
    args = C.parse_cli(argv)
    cfg = C.load_config(args.config)
    blend = args.out / f"golu_{C.scene_quality(args.quality)}.blend"
    if not blend.exists():
        raise SystemExit(f"{blend} missing: run build_scene.py first")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    M.init(cfg)
    golu = bpy.context.scene
    front_y = -8.0
    doors = bpy.data.scenes.new("Doors")
    for c in golu.collection.children:          # link the Golu room and dolls (the glimpse through the doors)
        doors.collection.children.link(c)
    for o in golu.collection.objects:
        if o.type in ("LIGHT", "MESH") and not o.name.startswith("CAM"):
            doors.collection.objects.link(o)
    doors.world = golu.world
    if bpy.context.window is not None:
        bpy.context.window.scene = doors
    col = bpy.data.collections.new("DoorSet")
    doors.collection.children.link(col)
    hinges, _ = build_door_set(cfg, front_y, col)
    animate_doors(hinges)
    add_glow_and_haze(cfg, front_y, col)
    cam = bpy.data.objects.new("CAM_Doors", bpy.data.cameras.new("CAM_Doors"))
    col.objects.link(cam)
    # 24 mm from 3.6 m: the whole doorway (thoranam and bells above, threshold kolam below, both lamps) in frame
    cam.data.lens = 24
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 3.6
    cam.data.dof.aperture_fstop = 4.0
    cam.matrix_world = Q.look_at(Vector((0, front_y - 3.6, 1.45)), Vector((0, front_y, 1.2)))
    doors.camera = cam
    doors.frame_start, doors.frame_end = 1, cfg.layout["camera"]["door_frames"]
    doors.render.fps = cfg.raw["meta"]["fps"]
    R.apply_quality(doors, args.quality)
    # the door haze is a soft volume: coarse volume tiles keep it ~4x cheaper with no visible change
    for attr, val in (("volumetric_tile_size", "16"), ("volumetric_samples", 8)):
        if hasattr(doors.eevee, attr):
            setattr(doors.eevee, attr, val)
    R.setup_color_management(doors)
    R.setup_glare(doors, True, 0.45)
    out = args.out / args.quality / "doors"
    todo = list(range(1, doors.frame_end + 1, args.stride))     # --stride 2: odd frames; encode interpolates
    if args.frames:
        todo = [f for f in todo if f in set(args.frames)]
    log = R.ProgressLog(len(todo), "doors")
    for f in todo:
        p = out / f"f_{f:04d}.png"
        if args.resume and R.is_frame_done(p):
            log.tick(0.0, skipped=True)
            continue
        doors.frame_set(f)
        doors.render.filepath = str(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        t = time.time()
        bpy.ops.render.render(write_still=True, scene=doors.name)
        log.tick(time.time() - t)
    return 0


if __name__ == "__main__":
    try:
        code = main(sys.argv)
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.exit(code)
