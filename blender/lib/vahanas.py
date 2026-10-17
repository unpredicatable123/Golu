"""Vahanas and golu animals (SPEC §4.3), sculpted from metaballs → voxel remesh, painted clay.

Built in species unit space (1 = shoulder height, or body height for birds). Quadrupeds stand with their
body along X and the head toward −X; birds and the mouse face −Y. `build_vahana` returns the mesh and, for
mounts, the saddle frame where a rider's pelvis sits.
"""
from __future__ import annotations

import math
import random

import bpy
from mathutils import Matrix, Vector

from . import attributes as A
from . import mesh_utils as MU
from .config import Palette, seed_for

SIZES_M = {"elephant": 0.20, "peacock": 0.18, "cow": 0.14, "calf": 0.09, "horse": 0.15, "lion": 0.13,
           "mouse": 0.04, "swan": 0.09, "gaja_pair": 0.09, "bullock": 0.13, "bullock_pair": 0.13, "garuda": 0.18,
           "kaliya": 0.0}

V = Vector
BLACK = (0.012, 0.01, 0.009)


def _cap(a, b, r, stiff=2.0):
    return MU.capsule_between(V(a), V(b), r / 0.67, stiff)


def _ell(co, r, size, rot=None):
    return MU.MetaElem("ELLIPSOID", co, r / 0.67, size, rot)


def _ball(co, r):
    return MU.MetaElem("BALL", co, r / 0.67)


def _sculpt(name: str, els, res: float, color, rough=0.42, voxel: float | None = None) -> bpy.types.Object:
    mb = MU.metaball_object(f"mb_{name}", els, res)
    ob = MU.metaball_to_mesh(mb, name)
    MU.voxel_remesh(ob, voxel or res * 0.8, smooth_iters=2)
    MU.set_part_attributes(ob, color, 0.0, rough, 6)
    MU.shade_smooth(ob, None)
    return ob


def _saddle_cloth(name: str, length: float, radius: float, z: float, P: A.Paint, color,
                  x: float = 0.0, spread_deg: float = 75.0) -> bpy.types.Object:
    """Caparison draped over the back: an arched shell along X with a gold zari border."""
    verts, faces = [], []
    n_a, n_l = 18, 10
    spread = math.radians(spread_deg)
    for i in range(n_l + 1):
        xx = x - length / 2 + length * i / n_l
        for j in range(n_a + 1):
            a = -spread + 2 * spread * j / n_a
            verts.append((xx, math.sin(a) * radius, z + math.cos(a) * radius))
    for i in range(n_l):
        for j in range(n_a):
            q = i * (n_a + 1) + j
            faces.append((q, q + 1, q + n_a + 2, q + n_a + 1))
    ob = MU.new_mesh_object(name, verts, faces)
    MU.solidify(ob, radius * 0.04)
    MU.shade_smooth(ob, None)
    MU.set_part_attributes(ob, color, 0.0, 0.4, 6)
    edge_y = math.sin(spread) * radius * 0.85
    MU.paint_corners(ob, lambda co, n: (P.p.material("gold"), 0.65, 0.3, 3)
                     if abs(co.y) > edge_y or abs(co.x - x) > length / 2 * 0.86 else None)
    return ob


def _eyes(name: str, positions, r: float, P: A.Paint) -> list[bpy.types.Object]:
    out = []
    for i, p in enumerate(positions):
        e = MU.uv_sphere(f"{name}_eye{i}", r, 10, 6)
        A._place(e, p)
        P.col(e, BLACK, 0.15)
        out.append(e)
    return out


def _paint_region(ob, fn):
    MU.paint_corners(ob, fn)


# =========================================================================== quadrupeds


def _quadruped(name, P: A.Paint, *, length, girth, leg_r, neck_to, head_at, head_r, head_size,
               color, raise_front=0.0, belly_drop=0.0, hump=0.0, res=0.02):
    """Metaball body: torso along X (head −X), four legs, neck, head. Returns mesh."""
    h = 1.0
    els = [
        _ell((0, 0, h * 0.78 - belly_drop * 0.5), girth, (length / girth * 0.5, 0.75, 0.8)),
        _ball((-length * 0.32, 0, h * 0.82), girth * 0.9),
        _ball((length * 0.3, 0, h * 0.8), girth * 0.85),
    ]
    if hump:
        els.append(_ell((-length * 0.3, 0, h * 0.82 + girth * 0.75), hump, (1.0, 0.8, 1.0)))
    for sx, front in ((-1, True), (1, False)):
        for sy in (-1, 1):
            x = sx * length * 0.33
            top = V((x, sy * girth * 0.45, h * 0.72))
            lift = raise_front if (front and sy < 0) else 0.0
            knee = V((x + (0.04 if front else -0.03), sy * girth * 0.45, h * 0.38 + lift * 0.5))
            foot = V((x + (-lift * 0.5 if front else 0.0), sy * girth * 0.45, 0.05 + lift))
            els.append(_cap(top, knee, leg_r * 1.15))
            els.append(_cap(knee, foot, leg_r))
            els.append(_ell(foot + V((-0.02, 0, -0.02)), leg_r * 1.1, (1.2, 1.0, 0.7)))
    els.append(_cap((-length * 0.45, 0, h * 0.85), neck_to, girth * 0.55))
    els.append(_ell(head_at, head_r, head_size))
    return _sculpt(name, els, res, color)


def lion(P: A.Paint, rng) -> tuple[bpy.types.Object, Matrix]:
    tan = P.p.silk("turmeric")
    body = _quadruped("lion", P, length=1.3, girth=0.34, leg_r=0.12, neck_to=V((-0.78, 0, 1.12)),
                      head_at=V((-0.86, -0.02, 1.2)), head_r=0.22, head_size=(1.05, 0.95, 1.0), color=tan,
                      raise_front=0.12)
    parts = [body]
    # mane: two rings of curled tufts around the face
    for ring in range(3):
        n = 18 + ring * 6
        for i in range(n):
            a = i / n * math.tau + ring * 0.13
            r = 0.2 + ring * 0.07
            p = V((-0.82 + ring * 0.07, math.cos(a) * r * 0.9, 1.2 + math.sin(a) * r))
            t = MU.cylinder(f"mane{ring}_{i}", 0.05 - ring * 0.008, 0.16 + ring * 0.03, 8, radius_top=0.0)
            t.scale = (1.0, 0.6, 1.0)
            MU.apply_transform(t)
            tip = V((0.25, math.cos(a), math.sin(a))).normalized()
            A._place(t, p + tip * 0.05, V((0, 0, 1)).rotation_difference(tip).to_euler())
            P.col(t, (P.p.silk("saffron"), P.p.silk("turmeric"), P.p.material("flame-base"))[ring], 0.5)
            parts.append(t)
    muzzle = MU.uv_sphere("lion_muzzle", 0.11, 14, 8, scale=(1.2, 0.95, 0.75))
    A._place(muzzle, (-1.04, -0.02, 1.14))
    P.col(muzzle, tan, 0.45)
    mouth = MU.uv_sphere("lion_mouth", 0.07, 12, 8, scale=(1.0, 0.8, 0.45))
    A._place(mouth, (-1.12, -0.02, 1.07))
    P.col(mouth, P.p.silk("kumkum"), 0.3)
    nose = MU.uv_sphere("lion_nose", 0.035, 10, 6)
    A._place(nose, (-1.15, -0.02, 1.2))
    P.col(nose, BLACK, 0.3)
    tail = MU.tube("lion_tail", [V((0.66, 0, 0.9)), V((0.95, 0, 0.75)), V((1.05, 0, 1.0)), V((1.0, 0, 1.2))], 0.035)
    P.col(tail, tan, 0.45)
    tuft = MU.uv_sphere("lion_tuft", 0.07, 10, 6, scale=(1, 1, 1.4))
    A._place(tuft, (1.0, 0, 1.25))
    P.col(tuft, P.p.silk("saffron"), 0.5)
    parts += [muzzle, mouth, nose, tail, tuft]
    parts += _eyes("lion", [V((-1.02, -0.12, 1.3)), V((-1.02, 0.08, 1.3))], 0.03, P)
    ob = MU.join(parts, "lion")
    saddle = Matrix.Translation(V((0.05, 0, 1.12)))
    return ob, saddle


def horse(P: A.Paint, rng) -> tuple[bpy.types.Object, Matrix]:
    white = P.p.silk("white")
    body = _quadruped("horse", P, length=1.25, girth=0.24, leg_r=0.055, neck_to=V((-0.85, 0, 1.4)),
                      head_at=V((-1.05, 0, 1.45)), head_r=0.12, head_size=(1.9, 0.75, 0.9), color=white,
                      raise_front=0.28)
    parts = [body]
    for i in range(9):
        m = MU.uv_sphere(f"hmane{i}", 0.06, 8, 6, scale=(1, 0.6, 1.3))
        A._place(m, (-0.55 - i * 0.04, 0, 1.05 + i * 0.045))
        parts.append(P.col(m, BLACK, 0.5))
    cap = _saddle_cloth("caparison", 0.55, 0.22, 0.78, P, P.p.silk("kumkum"), x=0.0, spread_deg=80)
    tail = MU.tube("htail", [V((0.6, 0, 1.0)), V((0.8, 0, 0.8)), V((0.85, 0, 0.45))], 0.05, radii=[0.6, 1, 0.7])
    parts += [cap, P.col(tail, BLACK, 0.5)]
    for s in (-1, 1):
        ear = MU.cylinder(f"hear{s}", 0.03, 0.09, 6, radius_top=0.0)
        A._place(ear, (-0.92, s * 0.06, 1.6))
        parts.append(P.col(ear, white, 0.4))
    parts += _eyes("horse", [V((-1.08, -0.08, 1.52)), V((-1.08, 0.08, 1.52))], 0.022, P)
    ob = MU.join(parts, "horse")
    return ob, Matrix.Translation(V((0.0, 0, 1.1)))


def _elephant_parts(P: A.Paint, rng, tag: str, trunk_raised: bool, ears_spread: bool,
                    caparison: bool = True) -> list[bpy.types.Object]:
    grey = P.p.skin("elephant-grey")
    body = _quadruped(f"eleph_{tag}", P, length=1.2, girth=0.42, leg_r=0.13, neck_to=V((-0.62, 0, 1.0)),
                      head_at=V((-0.72, 0, 1.05)), head_r=0.3, head_size=(0.9, 0.9, 1.0), color=grey,
                      raise_front=0.1 if trunk_raised else 0.0)
    parts = [body]
    if trunk_raised:
        pts = [V((-0.95, 0, 0.98)), V((-1.15, 0, 0.9)), V((-1.25, 0, 1.15)), V((-1.15, 0, 1.45)), V((-1.0, 0, 1.55))]
    else:
        pts = [V((-0.95, 0, 0.98)), V((-1.05, 0, 0.7)), V((-1.08, 0, 0.35)), V((-1.0, 0, 0.18))]
    trunk = MU.tube(f"trunk_{tag}", pts, 0.1, radii=[1.0, 0.8, 0.6, 0.45, 0.4][:len(pts)])
    parts.append(P.col(trunk, grey, 0.45))
    for s in (-1, 1):
        ear = MU.uv_sphere(f"ear_{tag}{s}", 0.26, 14, 8, scale=(0.18 if not ears_spread else 0.3, 1.0, 1.1))
        A._place(ear, (-0.62, s * (0.3 if not ears_spread else 0.36), 1.08), (0, 0, s * (0.5 if ears_spread else 0.15)))
        P.col(ear, grey, 0.45)
        _paint_region(ear, lambda co, n, s=s: (P.p.silk("lotus-pink"), 0.0, 0.5, 6) if co.y * s < 0 else None)
        parts.append(ear)
        tusk = MU.tube(f"tusk_{tag}{s}", [V((-0.92, s * 0.1, 0.92)), V((-1.08, s * 0.12, 0.85)),
                                         V((-1.18, s * 0.12, 0.95))], 0.035, radii=[1, 0.8, 0.3])
        parts.append(P.col(tusk, P.p.silk("ivory"), 0.3))
    if caparison:
        parts.append(_saddle_cloth(f"cap_{tag}", 0.7, 0.36, 0.78, P, P.p.silk("kumkum"), x=0.05, spread_deg=82))
        mark = MU.uv_sphere(f"fmark_{tag}", 0.05, 10, 6, scale=(0.3, 1, 1.4))
        A._place(mark, (-0.98, 0, 1.2))
        parts.append(P.mat(mark, "kumkum-powder", 0.6))
    tail = MU.tube(f"etail_{tag}", [V((0.6, 0, 0.95)), V((0.7, 0, 0.6))], 0.025)
    parts.append(P.col(tail, grey, 0.45))
    parts += _eyes(f"el_{tag}", [V((-0.92, -0.17, 1.15)), V((-0.92, 0.17, 1.15))], 0.025, P)
    return parts


def elephant(P: A.Paint, rng, pose: str = "standing") -> tuple[bpy.types.Object, Matrix]:
    parts = _elephant_parts(P, rng, "solo", trunk_raised=pose == "charging", ears_spread=pose == "charging",
                            caparison=pose != "charging")
    return MU.join(parts, "elephant"), Matrix.Translation(V((0, 0, 1.3)))


def gaja_pair(P: A.Paint, rng) -> tuple[bpy.types.Object, None]:
    """Two small elephants flanking the goddess, trunks raised holding kalashas (Gaja Lakshmi)."""
    out = []
    for s in (-1, 1):
        parts = _elephant_parts(P, rng, f"g{s}", trunk_raised=True, ears_spread=False)
        el = MU.join(parts, f"gaja_{s}")
        kal = A.kalasam(P, rng, scale=3.0)
        A._place(kal, (-1.08, 0, 1.55), (0, -2.2, 0))
        el = MU.join([el, kal], f"gaja_{s}")
        # face inward toward x = 0: head (−X) points to the centre for the right elephant, mirrored by rotation
        el.rotation_euler = (0, 0, 0 if s > 0 else math.pi)
        el.location = (s * 1.6, 0.35, 0)
        MU.apply_transform(el)
        out.append(el)
    return MU.join(out, "gaja_pair"), None


def cow(P: A.Paint, rng, variant: str = "cow") -> tuple[bpy.types.Object, None]:
    cream = P.p.silk("ivory")
    hump = 0.16 if variant == "bullock" else 0.06
    body = _quadruped(variant, P, length=1.45, girth=0.3, leg_r=0.06, neck_to=V((-0.85, 0, 1.0)),
                      head_at=V((-1.02, 0, 0.98)), head_r=0.15, head_size=(1.5, 0.8, 0.95), color=cream,
                      hump=hump, raise_front=0.0)
    parts = [body]
    if variant != "calf":
        for s in (-1, 1):
            horn = MU.tube(f"horn{s}", [V((-0.95, s * 0.08, 1.1)), V((-0.92, s * 0.18, 1.22)),
                                        V((-1.0, s * 0.2, 1.36))], 0.03, radii=[1, 0.7, 0.3])
            parts.append(P.col(horn, P.p.silk("kumkum") if s < 0 else P.p.silk("nilambara"), 0.35))
        bell = MU.uv_sphere("bell", 0.05, 10, 6)
        A._place(bell, (-0.85, 0, 0.72))
        rope = MU.torus("bellrope", 0.13, 0.014, 20, 5)
        A._place(rope, (-0.82, 0, 0.86), (0, 1.1, 0))
        parts += [P.brass(bell), P.col(rope, P.p.silk("kumkum"), 0.5)]
    for s in (-1, 1):
        ear = MU.uv_sphere(f"cear{s}", 0.07, 8, 6, scale=(0.5, 1.4, 0.35))
        A._place(ear, (-0.92, s * 0.15, 1.08))
        parts.append(P.col(ear, cream, 0.45))
    mark = MU.uv_sphere("cmark", 0.035, 8, 6, scale=(0.4, 1, 1))
    A._place(mark, (-1.18, 0, 1.05))
    parts.append(P.mat(mark, "kumkum-powder", 0.6))
    nose = MU.uv_sphere("cnose", 0.07, 10, 6, scale=(0.6, 1, 0.8))
    A._place(nose, (-1.22, 0, 0.92))
    parts.append(P.col(nose, P.p.silk("lotus-pink"), 0.4))
    tail = MU.tube("ctail", [V((0.72, 0, 0.95)), V((0.8, 0, 0.6)), V((0.78, 0, 0.3))], 0.02)
    parts.append(P.col(tail, cream, 0.45))
    if variant == "cow":   # brown patches
        _paint_region(body, lambda co, n: (P.p.silk("khaki"), 0.0, 0.45, 6)
                      if math.sin(co.x * 9 + 1.3) * math.cos(co.y * 11) > 0.55 and co.z > 0.55 else None)
    parts += _eyes(variant, [V((-1.1, -0.1, 1.04)), V((-1.1, 0.1, 1.04))], 0.022, P)
    return MU.join(parts, variant), None


def bullock_pair(P: A.Paint, rng) -> tuple[bpy.types.Object, None]:
    parts = []
    for s in (-1, 1):
        b, _ = cow(P, rng, "bullock")
        A._place(b, (0, s * 0.42, 0))
        parts.append(b)
    yoke = MU.cylinder("yoke", 0.035, 1.3, 12)
    A._place(yoke, (-0.7, 0, 1.12), (math.pi / 2, 0, 0))
    parts.append(P.col(yoke, P.p.silk("khaki"), 0.5))
    return MU.join(parts, "bullock_pair"), None


# =========================================================================== birds & small animals


def _feather(name: str, length: float, width: float) -> bpy.types.Object:
    """Spatulate eye-feather: narrow shaft widening into a rounded vane at the tip (garment_uv for the ocellus)."""
    nl, nw = 12, 4
    verts, faces, uvs = [], [], []
    for i in range(nl + 1):
        t = i / nl
        half = width / 2 * (0.12 + 0.88 * math.sin(math.pi * min(1.0, 0.25 + t * 0.78)) ** 0.6 * min(1.0, t * 2.2))
        for j in range(nw + 1):
            s = j / nw * 2 - 1
            verts.append((s * half, -0.04 * width * (1 - s * s), t * length))
            uvs.append((j / nw, t))
    for i in range(nl):
        for j in range(nw):
            a = i * (nw + 1) + j
            faces.append((a, a + 1, a + nw + 2, a + nw + 1))
    ob = MU.new_mesh_object(name, verts, faces)
    MU.set_part_attributes(ob, (0.1, 0.22, 0.05), 0.0, 0.35, 8)
    g = ob.data.attributes["garment_uv"]
    vals = []
    for loop in ob.data.loops:
        vals.extend(uvs[loop.vertex_index])
    g.data.foreach_set("vector", vals)
    MU.solidify(ob, 0.006, 0.0)
    MU.shade_smooth(ob, None)
    return ob


def peacock(P: A.Paint, rng, pose: str = "fanned") -> tuple[bpy.types.Object, None]:
    """Peacock facing −Y with a fanned tail of eye-feathers behind it (SPEC §4.3)."""
    blue = P.p.silk("peacock-blue")
    els = [_ell((0, 0.06, 0.4), 0.2, (0.85, 1.0, 1.0)),
           _cap((0, 0.0, 0.48), (0, -0.07, 0.74), 0.085),
           _ball((0, -0.09, 0.82), 0.085),
           _cap((-0.05, 0.05, 0.24), (-0.06, 0.03, 0.1), 0.03), _cap((0.05, 0.05, 0.24), (0.06, 0.03, 0.1), 0.03)]
    body = _sculpt("peacock_body", els, 0.012, blue, rough=0.3)
    parts = [body]
    beak = MU.cylinder("pc_beak", 0.026, 0.08, 8, radius_top=0.0)
    A._place(beak, (0, -0.19, 0.8), (math.pi / 2 + 0.2, 0, 0))
    parts.append(P.col(beak, P.p.silk("khaki"), 0.35))
    for i in range(5):
        a = (i - 2) * 0.22
        st = MU.tube(f"crest{i}", [V((0, -0.08, 0.9)), V((math.sin(a) * 0.06, -0.07, 1.04))], 0.007)
        tip = MU.uv_sphere(f"crestt{i}", 0.018, 8, 6)
        A._place(tip, (math.sin(a) * 0.06, -0.07, 1.05))
        parts += [P.col(st, blue, 0.35), P.col(tip, blue, 0.35)]
    for s in (-1, 1):
        wing = A.leaf_shell(f"pc_wing{s}", 0.3, 0.17, cup=0.6)
        MU.set_part_attributes(wing, (0.16, 0.08, 0.03), 0.0, 0.4, 6)
        A._place(wing, (s * 0.13, 0.16, 0.6), (math.pi / 2 + 1.1, 0, s * 0.1))
        parts.append(wing)
        foot = MU.uv_sphere(f"pc_foot{s}", 0.04, 8, 6, scale=(1, 1.5, 0.35))
        A._place(foot, (s * 0.06, 0.0, 0.015))
        parts.append(P.col(foot, P.p.silk("khaki"), 0.5))
    if pose == "fanned":
        # 5 staggered rows: short inner feathers to long outer ones, eyes forming concentric arcs
        for ring in range(5):
            n = 13 + ring * 4
            length = 0.42 + ring * 0.17
            width = 0.15 + ring * 0.025
            for i in range(n):
                a = math.radians(-84 + 168 * (i + 0.5 * (ring % 2)) / (n - 1 + 0.5 * (ring % 2)))
                fe = _feather(f"fe{ring}_{i}", length, width)
                fe.rotation_euler = (0.12 + ring * 0.02, a, 0)
                MU.apply_transform(fe)
                A._place(fe, (0, 0.2 + (4 - ring) * 0.012, 0.42))
                parts.append(fe)
    else:
        train = _feather("pc_train", 0.8, 0.3)
        A._place(train, (0, 0.2, 0.35), (-1.3, 0, 0))
        parts.append(train)
    parts += _eyes("pc", [V((-0.05, -0.15, 0.85)), V((0.05, -0.15, 0.85))], 0.014, P)
    return MU.join(parts, "peacock"), None


def mouse(P: A.Paint, rng) -> tuple[bpy.types.Object, None]:
    grey = P.p.silk("ash")
    els = [_ell((0, 0.05, 0.35), 0.3, (0.9, 1.3, 0.9)), _ball((0, -0.33, 0.45), 0.2)]
    body = _sculpt("mouse_body", els, 0.03, grey)
    parts = [body]
    for s in (-1, 1):
        ear = MU.uv_sphere(f"m_ear{s}", 0.11, 10, 6, scale=(1, 0.35, 1))
        A._place(ear, (s * 0.16, -0.25, 0.68))
        parts.append(P.col(ear, P.p.silk("lotus-pink"), 0.45))
    nose = MU.uv_sphere("m_nose", 0.05, 8, 6)
    A._place(nose, (0, -0.55, 0.42))
    parts.append(P.col(nose, P.p.silk("lotus-pink"), 0.35))
    tail = MU.tube("m_tail", [V((0, 0.45, 0.2)), V((0.2, 0.8, 0.1)), V((0.1, 1.1, 0.15))], 0.03, radii=[1, 0.6, 0.3])
    parts.append(P.col(tail, grey, 0.45))
    mod = A.modaka(P, rng, bowl=False)
    A._place(mod, (0, -0.55, 0.2), scale=(6, 6, 6))
    parts.append(mod)
    parts += _eyes("m", [V((-0.08, -0.48, 0.55)), V((0.08, -0.48, 0.55))], 0.035, P)
    return MU.join(parts, "mouse"), None


def swan(P: A.Paint, rng) -> tuple[bpy.types.Object, None]:
    white = P.p.silk("white")
    els = [_ell((0, 0, 0.35), 0.3, (1.5, 0.85, 0.75))]
    body = _sculpt("swan_body", els, 0.03, white, rough=0.35)
    neck = MU.tube("swan_neck", [V((-0.3, 0, 0.45)), V((-0.42, 0, 0.75)), V((-0.32, 0, 1.0)), V((-0.42, 0, 1.12))],
                   0.07, radii=[1.1, 0.85, 0.8, 0.9])
    head = MU.uv_sphere("swan_head", 0.08, 12, 8, scale=(1.3, 0.85, 0.9))
    A._place(head, (-0.45, 0, 1.13))
    beak = MU.cylinder("swan_beak", 0.035, 0.14, 8, radius_top=0.004)
    A._place(beak, (-0.57, 0, 1.11), (0, -math.pi / 2 - 0.15, 0))
    parts = [body, P.col(neck, white, 0.35), P.col(head, white, 0.35), P.col(beak, P.p.silk("saffron"), 0.3)]
    for i in range(3):   # ornamental scroll tail of the annam
        sc = MU.tube(f"swan_scroll{i}", [V((0.35, (i - 1) * 0.08, 0.4)), V((0.55, (i - 1) * 0.1, 0.55)),
                                         V((0.6, (i - 1) * 0.1, 0.75)), V((0.5, (i - 1) * 0.1, 0.8))], 0.04,
                     radii=[1, 0.8, 0.6, 0.3])
        parts.append(P.col(sc, white, 0.35))
        _paint_region(sc, lambda co, n: (P.p.material("gold"), 1.0, 0.3, 3) if co.z > 0.7 else None)
    parts += _eyes("sw", [V((-0.5, -0.06, 1.16)), V((-0.5, 0.06, 1.16))], 0.015, P)
    return MU.join(parts, "swan"), None


def garuda(P: A.Paint, rng) -> tuple[bpy.types.Object, None]:
    """Kneeling Garuda in anjali with eagle beak and spread wings (parameter sweep only, D-plan §3.6)."""
    gold = P.p.material("gold")
    skin = P.p.skin("wheat")
    els = [_ell((0, 0, 0.55), 0.17, (0.9, 0.7, 1.0)), _ball((0, -0.02, 0.86), 0.12),
           _cap((-0.1, 0, 0.35), (-0.12, -0.25, 0.28), 0.07), _cap((-0.12, -0.25, 0.28), (-0.12, -0.25, 0.04), 0.06),
           _cap((0.1, 0, 0.35), (0.12, 0.2, 0.1), 0.07),
           _cap((-0.17, 0, 0.7), (-0.08, -0.15, 0.6), 0.05), _cap((0.17, 0, 0.7), (0.08, -0.15, 0.6), 0.05),
           _ball((0, -0.17, 0.62), 0.05)]
    body = _sculpt("garuda_body", els, 0.02, skin)
    beak = MU.cylinder("g_beak", 0.05, 0.13, 8, radius_top=0.0)
    A._place(beak, (0, -0.15, 0.84), (math.pi / 2 + 0.5, 0, 0))
    crown = MU.cylinder("g_crown", 0.09, 0.14, 12, center=(0, 0, 1.0), radius_top=0.02)
    parts = [body, P.col(beak, P.p.silk("saffron"), 0.3), P.gold(crown)]
    for s in (-1, 1):
        for k in range(3):
            w = A.leaf_shell(f"g_wing{s}{k}", 0.55 - k * 0.1, 0.18, cup=0.15)
            MU.set_part_attributes(w, P.p.silk("parrot-green") if k == 0 else P.p.silk("kumkum"), 0.0, 0.4, 6)
            A._place(w, (s * 0.15, 0.1 + k * 0.02, 0.65), (0, s * (0.9 + k * 0.25), 0))
            parts.append(w)
    parts += _eyes("g", [V((-0.05, -0.1, 0.9)), V((0.05, -0.1, 0.9))], 0.018, P)
    return MU.join(parts, "garuda"), None


# =========================================================================== dispatch


def build_vahana(kind: str, palette: Palette, rng: random.Random, pose: str = "standing"):
    P = A.Paint(palette)
    if kind == "lion":
        return lion(P, rng)
    if kind == "horse":
        return horse(P, rng)
    if kind == "elephant":
        return elephant(P, rng, pose)
    if kind == "gaja_pair":
        return gaja_pair(P, rng)
    if kind in ("cow", "calf", "bullock"):
        return cow(P, rng, kind)
    if kind == "bullock_pair":
        return bullock_pair(P, rng)
    if kind == "peacock":
        return peacock(P, rng, "fanned" if pose in ("fanned", "standing") else "folded")
    if kind == "mouse":
        return mouse(P, rng)
    if kind == "swan":
        return swan(P, rng)
    if kind == "garuda":
        return garuda(P, rng)
    raise KeyError(f"unknown vahana '{kind}'")


def size_m(kind: str) -> float:
    return SIZES_M[kind]
