"""Fly-through camera, timeline and manifest (SPEC §4.5, PLAN §4.3, DECISIONS D27/D28/D38)."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from . import mesh_utils as MU
from .config import GoluConfig
from .environment import StepHandle


@dataclass
class StepShot:
    step: int
    x0: float
    x1: float
    y: float
    dist0: float
    dist1: float
    z: float
    target_z: float
    focus_y: float


@dataclass
class Timeline:
    holds: list[tuple[int, int]]          # Blender frame numbers (1-based, inclusive)
    transitions: list[tuple[int, int]]
    finale: tuple[int, int]
    total: int


def build_timeline(cfg: GoluConfig) -> Timeline:
    cam = cfg.layout["camera"]
    hold, tr, fin = cam["hold_frames"], cam["transition_frames"], cam["finale_frames"]
    holds, trans = [], []
    f = 1
    for n in range(1, 10):
        holds.append((f, f + hold - 1))
        f += hold
        if n < 9:
            trans.append((f, f + tr - 1))
            f += tr
    finale = (f, f + fin - 1)
    return Timeline(holds, trans, finale, finale[1])


def build_rig(cfg: GoluConfig, scene) -> tuple[bpy.types.Object, bpy.types.Object]:
    cam = bpy.data.objects.get("CAM_Golu")
    if cam is None:
        cam = bpy.data.objects.new("CAM_Golu", bpy.data.cameras.new("CAM_Golu"))
        scene.collection.objects.link(cam)
    focus = bpy.data.objects.get("CAM_Focus")
    if focus is None:
        focus = bpy.data.objects.new("CAM_Focus", None)
        scene.collection.objects.link(focus)
    c = cam.data
    c.sensor_width = 36
    c.lens = cfg.layout["camera"]["lens_mm_hold"]
    c.clip_start = 0.05
    c.clip_end = 40
    c.dof.use_dof = True
    c.dof.focus_object = focus
    c.dof.aperture_fstop = cfg.layout["camera"]["fstop_hold"]
    c.dof.aperture_blades = 7
    scene.camera = cam
    return cam, focus


def plan_shot(cfg: GoluConfig, handle: StepHandle, dolls: list[bpy.types.Object]) -> StepShot:
    lens = cfg.layout["camera"]["lens_mm_hold"]
    hfov = 2 * math.atan(18.0 / lens)
    if dolls:
        los = [MU.bounds_world(o) for o in dolls]
        xmin = min(lo.x for lo, _ in los)
        xmax = max(hi.x for _, hi in los)
        top = sorted(hi.z for _, hi in los)[len(los) // 2]
    else:
        xmin, xmax, top = -handle.width / 2, handle.width / 2, handle.z_top + 0.22
    W = xmax - xmin
    cx = (xmin + xmax) / 2
    view_w = max(0.75 * W, 1.0)                        # frame most of the step; the dolly reveals the ends
    dist = view_w / 2 / math.tan(hfov / 2)
    sweep = max(0.0, (W - view_w) / 2 + 0.2 * view_w)  # end dolls sit ~30% inside the frame at the dolly ends
    doll_h = max(top - handle.z_top, 0.15)
    target_z = handle.z_top + doll_h * 0.5
    z = target_z + dist * math.tan(math.radians(10))
    focus_y = handle.front_line("front", cfg.layout) + 0.04
    return StepShot(step=handle.n, x0=cx - sweep, x1=cx + sweep, y=focus_y, dist0=dist, dist1=dist * 0.93, z=z,
                    target_z=target_z, focus_y=focus_y)


def _pose(cam, focus, loc: Vector, target: Vector) -> None:
    d = target - loc
    cam.location = loc
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    focus.location = target


def _key(cam, focus, frame: int, lens: float | None = None, fstop: float | None = None) -> None:
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)
    focus.keyframe_insert("location", frame=frame)
    if lens is not None:
        cam.data.lens = lens
        cam.data.keyframe_insert("lens", frame=frame)
    if fstop is not None:
        cam.data.dof.aperture_fstop = fstop
        cam.data.dof.keyframe_insert("aperture_fstop", frame=frame)


def _shot_pose(shot: StepShot, t: float) -> tuple[Vector, Vector]:
    x = shot.x0 + (shot.x1 - shot.x0) * t
    dist = shot.dist0 + (shot.dist1 - shot.dist0) * t
    target = Vector((x, shot.focus_y, shot.target_z))
    loc = Vector((x, shot.focus_y - dist, shot.z - (shot.dist0 - dist) * math.tan(math.radians(10))))
    return loc, target


def keyframe_all(cfg: GoluConfig, scene, cam, focus, shots: list[StepShot], tl: Timeline, establishing) -> None:
    cm = cfg.layout["camera"]
    if cam.animation_data:
        cam.animation_data_clear()
    if cam.data.animation_data:
        cam.data.animation_data_clear()
    if focus.animation_data:
        focus.animation_data_clear()
    for i, shot in enumerate(shots):
        a, b = tl.holds[i]
        loc, tgt = _shot_pose(shot, 0.0)
        _pose(cam, focus, loc, tgt)
        _key(cam, focus, a, cm["lens_mm_hold"], cm["fstop_hold"])
        loc, tgt = _shot_pose(shot, 1.0)
        _pose(cam, focus, loc, tgt)
        _key(cam, focus, b, cm["lens_mm_hold"], cm["fstop_hold"])
        if i < len(tl.transitions):
            # crane-up midpoint: rise above both shots so the move reads as a lift, not a slide
            t0, t1 = tl.transitions[i]
            nxt = shots[i + 1]
            l0, g0 = _shot_pose(shot, 1.0)
            l1, g1 = _shot_pose(nxt, 0.0)
            mid_loc = (l0 + l1) / 2 + Vector((0, -0.05, 0.06))
            mid_tgt = (g0 + g1) / 2
            _pose(cam, focus, mid_loc, mid_tgt)
            _key(cam, focus, (t0 + t1) // 2, cm["lens_mm_hold"], cm["fstop_hold"])
    fa, fb = tl.finale
    loc, tgt = establishing
    _pose(cam, focus, loc, tgt)
    _key(cam, focus, fb, cm["lens_mm_finale_end"], cm["fstop_finale_end"])
    for obj in (cam, focus, cam.data, cam.data.dof):
        ad = getattr(obj, "animation_data", None)
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
                fc.update()
    scene.frame_start = 1
    scene.frame_end = tl.total


def establishing_pose(cfg: GoluConfig, steps: list[StepHandle]) -> tuple[Vector, Vector]:
    y1 = steps[0].y_front
    return Vector((0.0, y1 - 4.6, 1.32)), Vector((0.0, -1.5, 0.95))


def project(scene, cam, co: Vector) -> tuple[float, float, float]:
    v = world_to_camera_view(scene, cam, co)
    return float(v.x), float(1.0 - v.y), float(v.z)


class Occluders:
    """Static BVH over the base meshes of dolls, story props and tiers (only the camera moves)."""

    def __init__(self, objects: list[bpy.types.Object]):
        from mathutils.bvhtree import BVHTree
        verts, polys, self.owner = [], [], []
        for ob in objects:
            if ob.type != "MESH" or not ob.data.polygons:
                continue
            mw = ob.matrix_world
            base = len(verts)
            verts.extend(mw @ v.co for v in ob.data.vertices)
            for p in ob.data.polygons:
                polys.append([base + i for i in p.vertices])
                self.owner.append(ob.name)
        self.tree = BVHTree.FromPolygons(verts, polys, all_triangles=False)

    def visible(self, cam_loc: Vector, co: Vector, target: bpy.types.Object) -> bool:
        d = co - cam_loc
        dist = d.length
        loc, _, idx, hit_d = self.tree.ray_cast(cam_loc, d.normalized(), dist + 0.01)
        if loc is None:
            return True
        return self.owner[idx] == target.name or hit_d >= dist - 0.03


def write_manifest(path: Path, cfg: GoluConfig, tl: Timeline, step_dolls: dict[int, list[bpy.types.Object]],
                   flames: list[bpy.types.Object], scene, cam) -> dict:
    every = cfg.layout["camera"]["hotspot_sample_every"]
    res_x, res_y = scene.render.resolution_x, scene.render.resolution_y
    occ_objs = [d for ds in step_dolls.values() for d in ds]
    for col_name in ("StoryProps", "Environment"):
        col = bpy.data.collections.get(col_name)
        if col:
            occ_objs += [o for o in col.objects if o.type == "MESH" and (col_name == "StoryProps" or o.name.startswith("Tier_"))]
    bpy.context.view_layer.update()
    occ = Occluders(occ_objs)
    steps_out = []
    for n in range(1, 10):
        a, b = tl.holds[n - 1]
        if n < 9:
            end = tl.transitions[n - 1][1]
        else:
            end = tl.finale[1]
        count = end - a + 1
        samples = list(range(a, b + 1, every))
        if samples[-1] != b:
            samples.append(b)
        hot: dict[str, dict] = {d["doll_id"]: {"every": every, "t": []} for d in step_dolls.get(n, [])}
        fl_track = []
        for f in samples:
            scene.frame_set(f)
            cam_loc = cam.matrix_world.translation.copy()
            for d in step_dolls.get(n, []):
                local = Vector(d["hotspot_local"])
                co = d.matrix_world @ local
                x, y, z = project(scene, cam, co)
                vis = 0 <= x <= 1 and 0 <= y <= 1 and z > 0 and occ.visible(cam_loc, co, d)
                hot[d["doll_id"]]["t"].append([round(x, 4), round(y, 4), 1 if vis else 0])
            pts = []
            for fl in flames:
                x, y, z = project(scene, cam, fl.matrix_world.translation)
                if 0 <= x <= 1 and 0 <= y <= 1 and z > 0:
                    pts.append([round(x, 4), round(y, 4)])
            fl_track.append(pts)
        steps_out.append({
            "id": n, "dir": f"step{n}", "count": count, "global_start": a - 1,
            "hold": [0, b - a], "transition": [b - a + 1, count - 1] if n < 9 else None,
            "finale": [b - a + 1, count - 1] if n == 9 else None,
            "key_frame": (b - a) // 2, "sample_frames": [f - a for f in samples],
            "hotspots": hot, "flames": {"every": every, "t": fl_track},
        })
    manifest = {"version": 1, "fps": scene.render.fps, "resolution": [res_x, res_y], "total": tl.total,
                "steps": steps_out, "doors": {"count": cfg.layout["camera"]["door_frames"]}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    scene.frame_set(1)
    return manifest
