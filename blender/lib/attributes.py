"""Hand-held emblems and props for dolls (SPEC §4.3). Built in doll unit space (doll height = 1).

Single-hand items: origin = grip point, +Z = grip axis (the item rises along +Z from the hand), −Y faces
the viewer. Two-hand items are placed relative to the body (`BODY_ITEMS`) and expose grip points that the
arms reach for with IK.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import mesh_utils as MU
from .config import Palette

# --------------------------------------------------------------------------- painting helpers


class Paint:
    def __init__(self, palette: Palette):
        self.p = palette

    def gold(self, ob, rough=0.3):
        # gilt paint, not polished metal: partly metallic so it keeps a gold diffuse body in dim light
        MU.set_part_attributes(ob, self.p.material("gold"), 0.65, rough, 3)
        return ob

    def silver(self, ob):
        MU.set_part_attributes(ob, self.p.material("silver"), 0.6, 0.28, 3)
        return ob

    def brass(self, ob):
        MU.set_part_attributes(ob, self.p.material("brass"), 0.65, 0.32, 3)
        return ob

    def col(self, ob, rgb, rough=0.42, kind=6, metal=0.0):
        MU.set_part_attributes(ob, rgb, metal, rough, kind)
        return ob

    def silk(self, ob, key, rough=0.4):
        MU.set_part_attributes(ob, self.p.silk(key), 0.0, rough, 6)
        return ob

    def mat(self, ob, key, rough=0.45):
        MU.set_part_attributes(ob, self.p.material(key), 0.0, rough, 6)
        return ob


def _place(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)) -> bpy.types.Object:
    ob.location = Vector(loc)
    ob.rotation_euler = rot
    ob.scale = scale
    MU.apply_transform(ob)
    return ob


def leaf_shell(name: str, length: float, width: float, cup: float = 0.3, tip_pointed: bool = True,
               nl: int = 8, nw: int = 4, thickness: float = 0.0) -> bpy.types.Object:
    """Petal/leaf: outline grid along +Z, cupped toward −Y. garment_uv = (u across, v along)."""
    verts, faces, uvs = [], [], []
    for i in range(nl + 1):
        t = i / nl
        half = width / 2 * (math.sin(math.pi * min(1.0, t * (1.0 if tip_pointed else 0.75) + 0.08)) ** 0.7)
        for j in range(nw + 1):
            s = j / nw * 2 - 1
            verts.append((s * half, -cup * width * (1 - s * s) * 0.5 * math.sin(math.pi * t), t * length))
            uvs.append((j / nw, t))
    for i in range(nl):
        for j in range(nw):
            a = i * (nw + 1) + j
            faces.append((a, a + 1, a + nw + 2, a + nw + 1))
    ob = MU.new_mesh_object(name, verts, faces)
    if thickness:
        MU.solidify(ob, thickness, 0.0)
    MU.shade_smooth(ob, None)
    me = ob.data
    MU.set_part_attributes(ob, (1, 1, 1), 0, 0.4, 6)
    g = me.attributes["garment_uv"]
    vals = []
    for loop in me.loops:
        vals.extend(uvs[loop.vertex_index % len(uvs)])
    g.data.foreach_set("vector", vals)
    return ob


def gradient_paint(ob, c0, c1, axis: int = 2, metal=0.0, rough=0.4, kind=6) -> None:
    """Paint corners with a linear gradient along an axis (e.g. white petal base → pink tip)."""
    lo, hi = MU.bounds_local(ob)
    span = max(hi[axis] - lo[axis], 1e-6)
    MU.set_part_attributes(ob, c0, metal, rough, kind)

    def fn(co, n):
        t = (co[axis] - lo[axis]) / span
        return (tuple(a + (b - a) * t for a, b in zip(c0, c1)), metal, rough, kind)
    MU.paint_corners(ob, fn)


# =========================================================================== single-hand builders


def shankha(P: Paint, rng) -> bpy.types.Object:
    prof = [(0.0, -0.035), (0.008, -0.03), (0.02, -0.012), (0.024, 0.002), (0.021, 0.018), (0.013, 0.032),
            (0.006, 0.042), (0.0, 0.05)]
    body = MU.lathe("shankha", prof, 24, screw=False)
    spiral = MU.tube("shankha_sp", [p + Vector((0, 0, 0.02)) for p in MU.spiral_points(0.016, 0.004, 2.2, 0.03, 30)],
                     0.0035)
    lip = MU.uv_sphere("shankha_lip", 0.016, 16, 8, scale=(0.5, 1.0, 1.8))
    _place(lip, (0.016, -0.004, -0.004))
    band = MU.torus("shankha_band", 0.0235, 0.0028, 24, 6)
    _place(band, (0, 0, 0.0))
    for o in (body, spiral, lip):
        P.col(o, P.p.silk("white"), 0.3, kind=6)
    P.gold(band)
    ob = MU.join([body, spiral, lip, band], "shankha")
    return _place(ob, (0, 0, 0.035), (0, 0.5, 0))


def chakra(P: Paint, rng) -> bpy.types.Object:
    parts = []
    rim = MU.torus("chakra_rim", 0.03, 0.0045, 32, 8)
    _place(rim, rot=(math.pi / 2, 0, 0))
    parts.append(P.gold(rim))
    hub = MU.uv_sphere("chakra_hub", 0.009, 12, 8, scale=(1, 0.6, 1))
    parts.append(P.col(hub, P.p.silk("kumkum"), 0.35))
    for i in range(8):
        a = i / 8 * math.tau
        sp = MU.cylinder(f"chakra_sp{i}", 0.0018, 0.03, 6)
        _place(sp, (math.cos(a) * 0.016, 0, math.sin(a) * 0.016), (0, -a + math.pi / 2, 0))
        parts.append(P.gold(sp))
    for i in range(16):   # flame edges (SPEC)
        a = i / 16 * math.tau
        length = 0.016 if i % 2 == 0 else 0.011
        fl = MU.cylinder(f"chakra_fl{i}", 0.006, length, 6, radius_top=0.0)
        fl.scale = (1, 0.35, 1)
        MU.apply_transform(fl)
        _place(fl, (math.cos(a) * (0.034 + length / 2), 0, math.sin(a) * (0.034 + length / 2)), (0, -a + math.pi / 2, 0))
        gradient_paint(fl, P.p.material("gold"), P.p.material("flame-base"), axis=0, metal=0.6, rough=0.3, kind=3)
        parts.append(fl)
    stub = MU.cylinder("chakra_stub", 0.003, 0.02, 6, center=(0, 0, -0.04))
    parts.append(P.gold(stub))
    ob = MU.join(parts, "chakra")
    return _place(ob, (0, 0, 0.05))


def gada(P: Paint, rng) -> bpy.types.Object:
    prof = [(0.0, -0.04), (0.006, -0.04), (0.005, 0.1), (0.012, 0.105), (0.024, 0.12), (0.028, 0.14),
            (0.024, 0.16), (0.012, 0.175), (0.006, 0.18), (0.009, 0.188), (0.0, 0.198)]
    bm = MU.lathe_bm(prof, 32)
    for v in bm.verts:
        if 0.105 < v.co.z < 0.178:
            a = math.atan2(v.co.y, v.co.x)
            k = 1 + 0.12 * math.cos(8 * a)
            v.co.x *= k
            v.co.y *= k
    ob = MU.bmesh_to_object(bm, "gada")
    MU.shade_smooth(ob, 60)
    return P.gold(ob)


def padma(P: Paint, rng, blue: bool = False) -> bpy.types.Object:
    parts = []
    stalk = MU.tube("padma_stalk", [Vector((0, 0, -0.03)), Vector((0, -0.004, 0.03)), Vector((0, 0, 0.07))], 0.0028)
    parts.append(P.col(stalk, P.p.material("mango-leaf"), 0.5))
    tip = P.p.silk("nilambara") if blue else P.p.silk("lotus-pink")
    base_c = P.p.silk("white")
    for ring, (n, ln, tilt) in enumerate(((8, 0.032, 0.55), (8, 0.028, 0.25), (6, 0.022, 0.08))):
        for i in range(n):
            a = (i + 0.5 * ring) / n * math.tau
            pet = leaf_shell(f"padma_p{ring}_{i}", ln, ln * 0.55, cup=0.5)
            gradient_paint(pet, base_c, tip, rough=0.38)
            pet.rotation_euler = (tilt + 0.15, 0, 0)
            MU.apply_transform(pet)
            pet.rotation_euler = (0, 0, a)
            MU.apply_transform(pet)
            _place(pet, (0, 0, 0.07))
            parts.append(pet)
    seed = MU.cylinder("padma_seed", 0.008, 0.006, 12, center=(0, 0, 0.073))
    parts.append(P.col(seed, P.p.silk("turmeric"), 0.5))
    return MU.join(parts, "padma")


def vel(P: Paint, rng) -> bpy.types.Object:
    shaft = MU.cylinder("vel_shaft", 0.0055, 0.5, 10, center=(0, 0, 0.1))
    P.gold(shaft)
    bm = bmesh.new()
    outline = []
    for i in range(25):
        t = i / 24
        w = 0.05 * math.sin(math.pi * t) ** 0.8 * (1.0 - 0.4 * t)
        outline.append((t, w))
    verts_l = [bm.verts.new((-w, 0, 0.35 + t * 0.17)) for t, w in outline]
    verts_r = [bm.verts.new((w, 0, 0.35 + t * 0.17)) for t, w in outline]
    for i in range(24):
        bm.faces.new((verts_l[i], verts_r[i], verts_r[i + 1], verts_l[i + 1]))
    ret = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    for v in [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.y += 0.004
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    blade = MU.bmesh_to_object(bm, "vel_blade")
    for v in blade.data.vertices:          # central ridge
        if abs(v.co.x) < 1e-6:
            v.co.y += -0.003 if v.co.y < 0.002 else 0.003
    MU.solidify(blade, 0.0005)
    MU.shade_smooth(blade, 30)
    P.gold(blade, 0.2)
    mark = MU.uv_sphere("vel_mark", 0.009, 10, 6, scale=(1, 0.3, 1.6))
    _place(mark, (0, -0.002, 0.405))
    P.col(mark, P.p.material("vibhuti"), 0.8)
    knob = MU.uv_sphere("vel_knob", 0.012, 12, 8)
    _place(knob, (0, 0, 0.345))
    P.gold(knob)
    return MU.join([shaft, blade, mark, knob], "vel")


def bow(P: Paint, rng, length: float = 0.36) -> bpy.types.Object:
    pts, radii = [], []
    for i in range(21):
        t = i / 20 * 2 - 1
        z = t * length / 2
        x = -0.035 * (1 - t * t) + 0.012 * (t ** 4)
        pts.append(Vector((x, 0, z)))
        radii.append(1.0 - 0.55 * abs(t))
    limb = MU.tube("bow_limb", pts, 0.0055, radii=radii)
    gradient_paint(limb, P.p.silk("saffron"), P.p.material("gold"), axis=2, rough=0.35)
    string = MU.tube("bow_str", [pts[0], pts[-1]], 0.0008)
    P.col(string, P.p.silk("ivory"), 0.6)
    grip = MU.cylinder("bow_grip", 0.0075, 0.03, 10, center=(-0.035, 0, 0))
    P.gold(grip)
    return MU.join([limb, string, grip], "bow")


def arrow(P: Paint, rng, length: float = 0.3) -> bpy.types.Object:
    shaft = MU.cylinder("arrow_shaft", 0.0022, length, 6, center=(0, 0, length * 0.35))
    P.col(shaft, P.p.silk("khaki"), 0.5)
    head = MU.cylinder("arrow_head", 0.006, 0.02, 4, center=(0, 0, length * 0.85 + 0.01), radius_top=0.0)
    P.gold(head)
    parts = [shaft, head]
    for i in range(3):
        f = leaf_shell(f"arrow_f{i}", 0.03, 0.012, cup=0.0)
        P.col(f, P.p.silk("kumkum"), 0.5)
        f.rotation_euler = (0, 0, i / 3 * math.tau)
        MU.apply_transform(f)
        _place(f, (0, 0, -length * 0.15 + 0.0))
        parts.append(f)
    return MU.join(parts, "arrow")


def bow_arrow(P: Paint, rng) -> bpy.types.Object:
    b = bow(P, rng, 0.26)
    a = arrow(P, rng, 0.22)
    _place(a, (0.004, -0.006, -0.04), (0, 0.15, 0))
    return MU.join([b, a], "bow_arrow")


def parashu(P: Paint, rng) -> bpy.types.Object:
    haft = MU.cylinder("axe_haft", 0.0045, 0.32, 8, center=(0, 0, 0.08))
    P.col(haft, P.p.silk("khaki"), 0.5)
    bm = bmesh.new()
    pts = []
    for i in range(17):
        a = -1.1 + 2.2 * i / 16
        pts.append((0.012 + 0.05 * math.cos(a), 0.2 + 0.045 * math.sin(a)))
    pts.append((0.008, 0.205))
    pts.append((0.008, 0.195))
    vs = [bm.verts.new((x, 0, z)) for x, z in pts]
    bm.faces.new(vs)
    ret = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    for v in [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.y += 0.006
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    blade = MU.bmesh_to_object(bm, "axe_blade")
    _place(blade, (0, -0.003, 0))
    P.silver(blade)
    return MU.join([haft, blade], "parashu")


def hala(P: Paint, rng) -> bpy.types.Object:
    beam = MU.tube("hala_beam", [Vector((0, 0, -0.08)), Vector((0, 0, 0.12)), Vector((0.03, 0, 0.2)),
                                 Vector((0.07, 0, 0.21))], 0.005)
    P.col(beam, P.p.silk("khaki"), 0.5)
    share = MU.cylinder("hala_share", 0.012, 0.04, 4, radius_top=0.0)
    _place(share, (0.085, 0, 0.21), (0, math.pi / 2, 0))
    P.silver(share)
    return MU.join([beam, share], "hala")


def musala(P: Paint, rng) -> bpy.types.Object:
    prof = [(0.0, -0.05), (0.007, -0.05), (0.006, 0.12), (0.014, 0.14), (0.016, 0.2), (0.012, 0.22), (0.0, 0.225)]
    ob = MU.lathe("musala", prof, 16, screw=False)
    gradient_paint(ob, P.p.silk("khaki"), P.p.material("gold"), rough=0.4)
    return ob


def khadga(P: Paint, rng) -> bpy.types.Object:
    hilt = MU.cylinder("sword_hilt", 0.005, 0.04, 8)
    guard = MU.cylinder("sword_guard", 0.004, 0.04, 8)
    _place(guard, (0, 0, 0.022), (0, math.pi / 2, 0))
    pts = [Vector((0, 0, 0.025)), Vector((0.004, 0, 0.12)), Vector((0.02, 0, 0.23))]
    blade = MU.tube("sword_blade", pts, 0.008, radii=[1.0, 0.8, 0.15])
    blade.scale = (1, 0.25, 1)
    MU.apply_transform(blade)
    P.gold(hilt)
    P.gold(guard)
    P.silver(blade)
    return MU.join([hilt, guard, blade], "khadga")


def shield(P: Paint, rng) -> bpy.types.Object:
    prof = [(0.0, 0.012), (0.03, 0.008), (0.045, 0.0), (0.048, -0.004), (0.0, -0.002)]
    ob = MU.lathe("shield", prof, 32, screw=False)
    _place(ob, rot=(math.pi / 2, 0, 0))
    P.col(ob, P.p.silk("maroon"), 0.35)
    boss = MU.uv_sphere("shield_boss", 0.01, 12, 8)
    _place(boss, (0, -0.012, 0))
    P.gold(boss)
    ring = MU.torus("shield_ring", 0.046, 0.003, 32, 6)
    _place(ring, rot=(math.pi / 2, 0, 0))
    P.gold(ring)
    ob = MU.join([ob, boss, ring], "shield")
    return _place(ob, (0, -0.01, 0.02))


def trishula(P: Paint, rng) -> bpy.types.Object:
    shaft = MU.cylinder("tri_shaft", 0.0042, 0.36, 8, center=(0, 0, 0.06))
    mid = MU.cylinder("tri_mid", 0.006, 0.06, 4, center=(0, 0, 0.27), radius_top=0.0)
    parts = [P.gold(shaft), P.silver(mid)]
    for s in (-1, 1):
        prong = MU.tube(f"tri_p{s}", [Vector((0, 0, 0.235)), Vector((s * 0.03, 0, 0.245)),
                                       Vector((s * 0.034, 0, 0.29))], 0.004, radii=[1, 0.8, 0.2])
        parts.append(P.silver(prong))
    bar = MU.cylinder("tri_bar", 0.004, 0.06, 8)
    _place(bar, (0, 0, 0.235), (0, math.pi / 2, 0))
    parts.append(P.gold(bar))
    dam = MU.uv_sphere("tri_damaru", 0.008, 10, 6, scale=(1, 1, 1.4))
    _place(dam, (0, 0, 0.215))
    parts.append(P.col(dam, P.p.silk("kumkum"), 0.4))
    return MU.join(parts, "trishula")


def butter_pot(P: Paint, rng, scale: float = 1.0) -> bpy.types.Object:
    prof = [(0.0, 0.0), (0.02, 0.002), (0.034, 0.02), (0.036, 0.034), (0.026, 0.05), (0.022, 0.056),
            (0.025, 0.06)]
    pot = MU.lathe("bpot", [(r * scale, z * scale) for r, z in prof], 24, screw=False)
    P.mat(pot, "terracotta", 0.6)
    butter = MU.uv_sphere("bpot_butter", 0.022 * scale, 14, 8, scale=(1, 1, 0.6))
    _place(butter, (0, 0, 0.058 * scale))
    P.col(butter, P.p.silk("white"), 0.35)
    return MU.join([pot, butter], "butter_pot")


def butter_ball(P: Paint, rng) -> bpy.types.Object:
    b = MU.uv_sphere("butter_ball", 0.014, 12, 8, scale=(1, 1, 0.8))
    _place(b, (0, -0.01, 0.01))
    return P.col(b, P.p.silk("white"), 0.3)


def kalasam(P: Paint, rng, scale: float = 1.0) -> bpy.types.Object:
    prof = [(0.0, 0.0), (0.02, 0.0), (0.024, 0.006), (0.04, 0.03), (0.044, 0.05), (0.036, 0.07), (0.02, 0.08),
            (0.017, 0.085), (0.024, 0.09), (0.0, 0.09)]
    pot = MU.lathe("kalasam_pot", [(r * scale, z * scale) for r, z in prof], 32, screw=False)
    P.brass(pot)
    parts = [pot]
    for i in range(5):
        a = i / 5 * math.tau
        lf = leaf_shell(f"kal_leaf{i}", 0.05 * scale, 0.016 * scale, cup=0.25)
        P.mat(lf, "mango-leaf", 0.35)
        lf.rotation_euler = (-0.9, 0, 0)
        MU.apply_transform(lf)
        lf.rotation_euler = (0, 0, a)
        MU.apply_transform(lf)
        _place(lf, (0, 0, 0.085 * scale))
        parts.append(lf)
    coco = MU.uv_sphere("kal_coconut", 0.024 * scale, 16, 10, scale=(1, 1, 1.25))
    _place(coco, (0, 0, 0.115 * scale))
    gradient_paint(coco, P.p.silk("khaki"), P.p.material("turmeric-powder"), rough=0.7)
    parts.append(coco)
    for i in range(3):
        dot = MU.uv_sphere(f"kal_dot{i}", 0.004 * scale, 8, 6, scale=(1, 0.3, 1))
        _place(dot, ((i - 1) * 0.014 * scale, -0.04 * scale, 0.05 * scale))
        parts.append(P.mat(dot, "kumkum-powder", 0.8))
    return MU.join(parts, "kalasam")


def ankusha(P: Paint, rng) -> bpy.types.Object:
    shaft = MU.cylinder("ank_shaft", 0.004, 0.2, 8, center=(0, 0, 0.06))
    hook = MU.tube("ank_hook", [Vector((0, 0, 0.16)), Vector((0, 0, 0.19)), Vector((0.02, 0, 0.2)),
                               Vector((0.026, 0, 0.18))], 0.0035, radii=[1, 1, 0.8, 0.3])
    spike = MU.cylinder("ank_spike", 0.004, 0.03, 6, center=(0, 0, 0.205), radius_top=0.0)
    return MU.join([P.gold(shaft), P.silver(hook), P.silver(spike)], "ankusha")


def pasha(P: Paint, rng) -> bpy.types.Object:
    loop = MU.torus("pasha_loop", 0.022, 0.0028, 24, 6)
    _place(loop, (0, 0, 0.03), (math.pi / 2, 0, 0))
    tail = MU.tube("pasha_tail", [Vector((0, 0, 0.008)), Vector((0.004, -0.004, -0.02)), Vector((-0.003, 0, -0.05))],
                   0.0026)
    return MU.join([P.col(loop, P.p.silk("saffron"), 0.5), P.col(tail, P.p.silk("saffron"), 0.5)], "pasha")


def modaka(P: Paint, rng, bowl: bool = True) -> bpy.types.Object:
    parts = []
    if bowl:
        bw = MU.lathe("mod_bowl", [(0.0, 0.0), (0.02, 0.0), (0.03, 0.012), (0.034, 0.02), (0.0, 0.016)], 24,
                      screw=False)
        parts.append(P.gold(bw))
    for i, (x, y, z) in enumerate(((0, 0, 0.016), (0.014, 0.006, 0.014), (-0.013, 0.006, 0.014))):
        bm = MU.lathe_bm([(0.0, 0.0), (0.011, 0.002), (0.012, 0.008), (0.006, 0.018), (0.0, 0.024)], 16)
        for v in bm.verts:
            a = math.atan2(v.co.y, v.co.x)
            k = 1 + 0.12 * math.cos(8 * a) * (v.co.z / 0.024)
            v.co.x *= k
            v.co.y *= k
        m = MU.bmesh_to_object(bm, f"modak{i}")
        MU.shade_smooth(m, 60)
        _place(m, (x, y, z))
        parts.append(P.col(m, P.p.silk("ivory"), 0.4))
    return MU.join(parts, "modaka")


def danta(P: Paint, rng) -> bpy.types.Object:
    t = MU.tube("danta", [Vector((0, 0, -0.01)), Vector((0.004, 0, 0.03)), Vector((0.012, 0, 0.06))], 0.008,
                radii=[1, 0.8, 0.3])
    return P.col(t, P.p.silk("ivory"), 0.3)


def chatra(P: Paint, rng) -> bpy.types.Object:
    handle = MU.cylinder("chatra_handle", 0.0035, 0.3, 8, center=(0, 0, 0.1))
    canopy = MU.lathe("chatra_top", [(0.0, 0.28), (0.02, 0.275), (0.08, 0.245), (0.1, 0.232), (0.098, 0.228),
                                     (0.0, 0.25)], 24, screw=False)
    parts = [P.col(handle, P.p.silk("khaki"), 0.5), P.col(canopy, P.p.silk("khaki"), 0.55)]
    for i in range(12):
        a = i / 12 * math.tau
        rib = MU.tube(f"chatra_rib{i}", [Vector((0, 0, 0.281)), Vector((math.cos(a) * 0.1, math.sin(a) * 0.1, 0.233))],
                      0.0016)
        parts.append(P.col(rib, P.p.silk("maroon"), 0.5))
    return MU.join(parts, "chatra")


def kamandalu(P: Paint, rng) -> bpy.types.Object:
    pot = MU.lathe("kam_pot", [(0.0, -0.05), (0.02, -0.05), (0.032, -0.03), (0.03, -0.012), (0.016, -0.004),
                               (0.0, -0.004)], 20, screw=False)
    handle = MU.tube("kam_handle", [Vector((0.012, 0, -0.006)), Vector((0, 0, 0.02)), Vector((-0.012, 0, -0.006))],
                     0.0025)
    spout = MU.tube("kam_spout", [Vector((0.02, -0.01, -0.03)), Vector((0.04, -0.016, -0.012))], 0.004,
                    radii=[1, 0.6])
    return MU.join([P.brass(pot), P.brass(handle), P.brass(spout)], "kamandalu")


def palm_leaf(P: Paint, rng) -> bpy.types.Object:
    parts = []
    for i in range(5):
        lf = MU.box(f"olai{i}", (0.09, 0.012, 0.0015), (0, 0, i * 0.0017), bevel=0.0005)
        parts.append(P.col(lf, P.p.silk("khaki") if i % 2 else P.p.silk("sandal"), 0.6))
    cord = MU.torus("olai_cord", 0.007, 0.0012, 12, 4)
    _place(cord, (0.03, 0, 0.004), (0, math.pi / 2, 0))
    parts.append(P.col(cord, P.p.silk("kumkum"), 0.6))
    ob = MU.join(parts, "palm_leaf")
    return _place(ob, (0, -0.01, 0.0), (math.pi / 2 - 0.4, 0, 0))


def stylus(P: Paint, rng) -> bpy.types.Object:
    ob = MU.cylinder("stylus", 0.0018, 0.06, 6, center=(0, 0, 0.02), radius_top=0.0005)
    return P.silver(ob)


def peacock_quill(P: Paint, rng) -> bpy.types.Object:
    shaft = MU.cylinder("quill_shaft", 0.0012, 0.12, 6, center=(0, 0, 0.05))
    vane = leaf_shell("quill_vane", 0.07, 0.03, cup=0.1)
    _place(vane, (0, 0, 0.06))
    MU.set_part_attributes(vane, P.p.silk("peacock-blue"), 0.0, 0.35, 8)
    g = vane.data.attributes["garment_uv"]
    return MU.join([P.col(shaft, P.p.silk("ivory"), 0.5), vane], "peacock_quill")


def parrot(P: Paint, rng) -> bpy.types.Object:
    els = [MU.MetaElem("ELLIPSOID", (0, 0, 0.022), 0.024, (0.7, 0.6, 1.0)),
           MU.MetaElem("BALL", (0, -0.006, 0.048), 0.017),
           MU.capsule_between(Vector((0, 0.008, 0.01)), Vector((0, 0.03, -0.03)), 0.008)]
    mb = MU.metaball_object(f"parrot_mb_{rng.randint(0, 10**6)}", els, 0.002)
    ob = MU.metaball_to_mesh(mb, "parrot")
    P.col(ob, P.p.silk("parrot-green"), 0.35)

    def fn(co, n):
        if co.z > 0.04 and co.y < -0.012:
            return (P.p.silk("kumkum"), 0.0, 0.35, 6)
        return None
    MU.paint_corners(ob, fn)
    beak = MU.cylinder("parrot_beak", 0.005, 0.012, 8, center=(0, -0.022, 0.044), radius_top=0.0)
    _place(beak, rot=(math.pi / 2 + 0.5, 0, 0))
    return MU.join([ob, P.col(beak, P.p.silk("kumkum"), 0.3)], "parrot")


def japa_mala(P: Paint, rng) -> bpy.types.Object:
    beads = []
    for i in range(24):
        a = i / 24 * math.tau
        b = MU.uv_sphere(f"mala{i}", 0.0032, 8, 5)
        _place(b, (math.sin(a) * 0.018, 0, -0.018 + math.cos(a) * 0.018 - 0.018))
        beads.append(b)
    ob = MU.join(beads, "japa_mala")
    return P.col(ob, P.p.silk("ivory"), 0.3)


def milk_cup(P: Paint, rng) -> bpy.types.Object:
    cup = MU.lathe("cup", [(0.0, 0.0), (0.012, 0.0), (0.018, 0.012), (0.02, 0.02), (0.0, 0.016)], 20, screw=False)
    milk = MU.cylinder("milk", 0.017, 0.002, 16, center=(0, 0, 0.017))
    return MU.join([P.gold(cup), P.col(milk, P.p.silk("white"), 0.2)], "milk_cup")


def stick(P: Paint, rng, length=0.55, key="khaki", r=0.005) -> bpy.types.Object:
    ob = MU.tube("stick", [Vector((0, 0, -length * 0.85)), Vector((0.004, 0, 0)), Vector((0, 0, length * 0.15))], r)
    return P.col(ob, P.p.silk(key), 0.55)


def sling(P: Paint, rng) -> bpy.types.Object:
    rope = MU.tube("sling", [Vector((0, 0, 0)), Vector((0.01, -0.01, 0.06)), Vector((0.03, -0.01, 0.1)),
                            Vector((0.05, 0, 0.08))], 0.0018)
    pouch = MU.uv_sphere("sling_stone", 0.009, 10, 6)
    _place(pouch, (0.05, 0, 0.08))
    return MU.join([P.col(rope, P.p.silk("khaki"), 0.6), P.col(pouch, P.p.silk("ash"), 0.7)], "sling")


def tambura(P: Paint, rng) -> bpy.types.Object:
    gourd = MU.uv_sphere("tam_gourd", 0.045, 20, 12, scale=(1, 0.8, 1))
    neck = MU.cylinder("tam_neck", 0.009, 0.36, 10, center=(0, 0, 0.2))
    head = MU.uv_sphere("tam_head", 0.012, 10, 6, scale=(1, 0.8, 1.6))
    _place(head, (0, 0, 0.385))
    ob = MU.join([P.col(gourd, P.p.silk("maroon"), 0.35), P.col(neck, P.p.silk("maroon"), 0.35),
                  P.gold(head)], "tambura")
    return _place(ob, (0, 0, -0.05))


def chipla(P: Paint, rng) -> bpy.types.Object:
    a = MU.box("chipla_a", (0.012, 0.004, 0.05), (0, 0, 0.0), bevel=0.0015)
    b = MU.box("chipla_b", (0.012, 0.004, 0.05), (0, 0.006, 0.0), bevel=0.0015)
    return MU.join([P.col(a, P.p.silk("khaki"), 0.4), P.col(b, P.p.silk("khaki"), 0.4)], "chipla")


def flag(P: Paint, rng) -> bpy.types.Object:
    staff = MU.cylinder("flag_staff", 0.0028, 0.3, 8, center=(0, 0, 0.08))
    cloth = leaf_shell("flag_cloth", 0.08, 0.06, cup=0.15, tip_pointed=True)
    _place(cloth, (0.035, 0, 0.19), (0, math.pi / 2 + 0.1, 0))
    return MU.join([P.gold(staff), P.silk(cloth, "kumkum", 0.45)], "flag")


def infant(P: Paint, rng) -> bpy.types.Object:
    els = [MU.MetaElem("BALL", (0, 0, 0.075), 0.04),
           MU.MetaElem("ELLIPSOID", (0, 0, 0.03), 0.045, (0.8, 0.7, 1.0)),
           MU.capsule_between(Vector((-0.012, -0.01, 0.0)), Vector((-0.02, -0.04, 0.005)), 0.016),
           MU.capsule_between(Vector((0.012, -0.01, 0.0)), Vector((0.02, -0.04, 0.005)), 0.016)]
    mb = MU.metaball_object(f"infant_mb_{rng.randint(0, 10**6)}", els, 0.002)
    ob = MU.metaball_to_mesh(mb, "infant")
    P.col(ob, P.p.skin("peach"), 0.4, kind=6)

    def fn(co, n):
        if co.z > 0.088 and co.y > -0.015:
            return ((0.02, 0.015, 0.012), 0.0, 0.35, 2)
        if co.z > 0.06 and co.y < -0.022 and abs(co.x) > 0.008 and abs(co.x) < 0.016 and 0.07 < co.z < 0.08:
            return ((0.02, 0.015, 0.012), 0.0, 0.3, 6)
        return None
    MU.paint_corners(ob, fn)
    lot = padma(P, rng)
    _place(lot, (0.02, -0.04, 0.02), scale=(0.6, 0.6, 0.6))
    return MU.join([ob, lot], "infant")


def bhudevi(P: Paint, rng) -> bpy.types.Object:
    els = [MU.MetaElem("BALL", (0, 0, 0.085), 0.034),
           MU.MetaElem("ELLIPSOID", (0, 0, 0.045), 0.04, (0.75, 0.6, 1.1)),
           MU.MetaElem("ELLIPSOID", (0, -0.01, 0.0), 0.05, (0.9, 0.8, 0.6))]
    mb = MU.metaball_object(f"bhudevi_mb_{rng.randint(0, 10**6)}", els, 0.002)
    ob = MU.metaball_to_mesh(mb, "bhudevi")
    P.silk(ob, "parrot-green", 0.4)

    def fn(co, n):
        if co.z > 0.07:
            return (P.p.skin("peach") if co.z < 0.1 or co.y < -0.01 else (0.02, 0.015, 0.012), 0.0, 0.4, 6)
        return None
    MU.paint_corners(ob, fn)
    crown = MU.cylinder("bhu_crown", 0.012, 0.02, 12, center=(0, 0.004, 0.112), radius_top=0.004)
    return MU.join([ob, P.gold(crown)], "bhudevi")


def ledger(P: Paint, rng) -> bpy.types.Object:
    ob = MU.box("ledger", (0.06, 0.012, 0.075), (0, -0.01, 0.02), bevel=0.002)
    return P.col(ob, P.p.silk("kumkum"), 0.45)


def weighing_scale(P: Paint, rng) -> bpy.types.Object:
    beam = MU.cylinder("scale_beam", 0.0018, 0.1, 6)
    _place(beam, (0, 0, 0.02), (0, math.pi / 2, 0))
    parts = [P.brass(beam)]
    for s in (-1, 1):
        for k in range(2):
            st = MU.tube(f"scale_st{s}{k}", [Vector((s * 0.05, 0, 0.02)), Vector((s * 0.05 + (k - 0.5) * 0.02, 0, -0.03))],
                         0.0006)
            parts.append(P.col(st, P.p.silk("khaki"), 0.6))
        pan = MU.lathe(f"scale_pan{s}", [(0.0, -0.035), (0.016, -0.033), (0.018, -0.028), (0.0, -0.03)], 16,
                       screw=False)
        _place(pan, (s * 0.05, 0, 0))
        parts.append(P.brass(pan))
    hook = MU.cylinder("scale_hook", 0.0015, 0.03, 6, center=(0, 0, 0.035))
    parts.append(P.brass(hook))
    ob = MU.join(parts, "weighing_scale")
    return _place(ob, (0, 0, -0.035))


def measure_padi(P: Paint, rng) -> bpy.types.Object:
    ob = MU.lathe("padi", [(0.0, 0.0), (0.018, 0.0), (0.02, 0.03), (0.016, 0.03), (0.014, 0.004), (0.0, 0.004)],
                  20, screw=False)
    grain = MU.uv_sphere("padi_grain", 0.016, 12, 6, scale=(1, 1, 0.4))
    _place(grain, (0, 0, 0.028))
    return MU.join([P.brass(ob), P.col(grain, P.p.silk("ivory"), 0.7)], "measure_padi")


def clipboard(P: Paint, rng) -> bpy.types.Object:
    board = MU.box("clip_board", (0.05, 0.004, 0.07), (0, 0, 0.0), bevel=0.001)
    paper = MU.box("clip_paper", (0.044, 0.002, 0.06), (0, -0.003, -0.003))
    clip = MU.box("clip_clip", (0.02, 0.006, 0.008), (0, -0.002, 0.034))
    ob = MU.join([P.col(board, P.p.silk("khaki"), 0.5), P.col(paper, P.p.silk("white"), 0.6),
                  P.silver(clip)], "clipboard")
    return _place(ob, (0, -0.012, 0.0), (0.5, 0, 0))


def goad_stick(P: Paint, rng) -> bpy.types.Object:
    return stick(P, rng, 0.3, "khaki", 0.003)


def reins(P: Paint, rng) -> bpy.types.Object:
    ob = MU.tube("reins", [Vector((0, 0, 0)), Vector((0, -0.05, -0.02)), Vector((0, -0.12, -0.05))], 0.0016)
    return P.col(ob, P.p.silk("khaki"), 0.6)


def danda(P: Paint, rng) -> bpy.types.Object:
    return stick(P, rng, 0.62, "khaki", 0.0045)


def walking_stick(P: Paint, rng) -> bpy.types.Object:
    return stick(P, rng, 0.5, "khaki", 0.005)


def paddy_sheaf(P: Paint, rng) -> bpy.types.Object:
    parts = []
    for i in range(7):
        a = i / 7 * math.tau
        stalk = MU.tube(f"paddy{i}", [Vector((0, 0, -0.02)), Vector((math.cos(a) * 0.006, math.sin(a) * 0.006, 0.06)),
                                       Vector((math.cos(a) * 0.02, math.sin(a) * 0.02, 0.09))], 0.0012)
        parts.append(P.col(stalk, P.p.silk("turmeric"), 0.6))
        for k in range(5):
            g = MU.uv_sphere(f"paddy_g{i}_{k}", 0.0022, 6, 4, scale=(1, 1, 1.8))
            _place(g, (math.cos(a) * (0.008 + k * 0.003), math.sin(a) * (0.008 + k * 0.003), 0.07 + k * 0.004))
            parts.append(P.col(g, P.p.material("turmeric-powder"), 0.6))
    return MU.join(parts, "paddy_sheaf")


def sugarcane(P: Paint, rng) -> bpy.types.Object:
    segs = []
    for i in range(8):
        s = MU.cylinder(f"cane{i}", 0.0045, 0.034, 8, center=(0, 0, -0.06 + i * 0.035))
        segs.append(P.col(s, P.p.silk("brinjal"), 0.35))
        n = MU.torus(f"cane_n{i}", 0.0047, 0.0012, 10, 4)
        _place(n, (0, 0, -0.077 + i * 0.035))
        segs.append(P.col(n, P.p.silk("khaki"), 0.5))
    lf = leaf_shell("cane_leaf", 0.06, 0.01, cup=0.1)
    _place(lf, (0, 0, 0.21), (0.4, 0, 0))
    segs.append(P.mat(lf, "mango-leaf"))
    return MU.join(segs, "sugarcane")


def banana_bunch(P: Paint, rng) -> bpy.types.Object:
    parts = []
    for k in range(6):
        a = (k - 2.5) * 0.25
        f = MU.tube(f"ban{k}", [Vector((0, 0, 0)), Vector((math.sin(a) * 0.02, -0.01, 0.03)),
                                Vector((math.sin(a) * 0.03, -0.022, 0.05))], 0.0055, radii=[0.7, 1, 0.5])
        parts.append(P.col(f, P.p.silk("turmeric"), 0.4))
    return MU.join(parts, "banana_bunch")


def thavil_stick(P: Paint, rng) -> bpy.types.Object:
    return stick(P, rng, 0.14, "khaki", 0.0035)


def nadaswaram(P: Paint, rng) -> bpy.types.Object:
    prof = [(0.0, 0.0), (0.004, 0.0), (0.006, 0.02), (0.009, 0.25), (0.012, 0.27), (0.016, 0.3), (0.026, 0.33),
            (0.032, 0.345), (0.0, 0.34)]
    body = MU.lathe("nada", prof, 20, screw=False)
    gradient_paint(body, P.p.silk("maroon"), P.p.silk("maroon"), rough=0.3)

    def fn(co, n):
        return (P.p.material("gold"), 1.0, 0.28, 3) if co.z > 0.27 or co.z < 0.02 else None
    MU.paint_corners(body, fn)
    return body


def churning_rope(P: Paint, rng) -> bpy.types.Object:
    rod = MU.cylinder("churn_rod", 0.004, 0.3, 8, center=(0, 0, 0.0))
    star = MU.cylinder("churn_star", 0.016, 0.01, 6, center=(0, 0, -0.14))
    rope = MU.tube("churn_rope", [Vector((-0.05, -0.02, 0.06)), Vector((0, -0.006, 0.05)), Vector((0.05, -0.02, 0.06))],
                   0.0018)
    return MU.join([P.col(rod, P.p.silk("khaki"), 0.5), P.col(star, P.p.silk("khaki"), 0.5),
                    P.col(rope, P.p.silk("ivory"), 0.6)], "churning_rope")


def garland(P: Paint, rng) -> bpy.types.Object:
    """Thick wedding garland: a loop of red roses, jasmine and marigold beads (two-handed)."""
    parts = []
    n = 64
    for i in range(n):
        t = i / n * math.tau
        x, z = math.sin(t) * 0.08, -math.cos(t) * 0.105 + 0.105
        for ring in range(2):
            kind = (i + ring * 2) % 4
            off = (ring - 0.5) * 0.009
            if kind == 3:
                f = MU.uv_sphere(f"gar{i}_{ring}", 0.0055, 8, 6, scale=(1.2, 1.2, 0.8))
                P.col(f, P.p.material("jasmine"), 0.5)
            else:
                f = MU.ico_sphere(f"gar{i}_{ring}", 0.0068, 2)
                P.col(f, P.p.material("marigold-orange") if kind == 1 else P.p.silk("kumkum"), 0.55)
            _place(f, (x * (1 + off * 8), -0.008 * math.cos(t) + off, -z))
            parts.append(f)
    tassel = MU.uv_sphere("gar_tassel", 0.012, 8, 6, scale=(1, 1, 1.8))
    _place(tassel, (0, 0, -0.24))
    parts.append(P.col(tassel, P.p.material("marigold-yellow"), 0.5))
    return MU.join(parts, "garland")


def laptop(P: Paint, rng) -> bpy.types.Object:
    base = MU.box("lap_base", (0.11, 0.075, 0.006), (0, 0, 0.0), bevel=0.0015)
    lid = MU.box("lap_lid", (0.11, 0.004, 0.072), (0, 0.04, 0.034), bevel=0.0015)
    _place(lid, rot=(-0.25, 0, 0))
    screen = MU.box("lap_screen", (0.098, 0.001, 0.06), (0, 0.035, 0.035))
    _place(screen, rot=(-0.25, 0, 0))
    MU.set_part_attributes(screen, (0.35, 0.5, 0.85), 0.0, 0.2, 6)
    return MU.join([P.col(base, P.p.silk("ash"), 0.35), P.col(lid, P.p.silk("ash"), 0.35), screen], "laptop")


def potters_wheel(P: Paint, rng) -> bpy.types.Object:
    wheel = MU.cylinder("pw_wheel", 0.07, 0.012, 32, center=(0, 0, 0.006))
    pot = MU.lathe("pw_pot", [(0.0, 0.012), (0.025, 0.014), (0.036, 0.04), (0.03, 0.06), (0.022, 0.07),
                              (0.026, 0.075), (0.0, 0.07)], 24, screw=False)
    return MU.join([P.col(wheel, P.p.silk("khaki"), 0.6), P.mat(pot, "terracotta", 0.7)], "potters_wheel")


def kolam_bowl(P: Paint, rng) -> bpy.types.Object:
    bowl = MU.lathe("kb", [(0.0, 0.0), (0.018, 0.0), (0.026, 0.014), (0.0, 0.01)], 16, screw=False)
    flour = MU.uv_sphere("kb_flour", 0.022, 12, 6, scale=(1, 1, 0.3))
    _place(flour, (0, 0, 0.012))
    return MU.join([P.brass(bowl), P.mat(flour, "rice-flour", 0.9)], "kolam_bowl")


REGISTRY: dict[str, Callable[[Paint, random.Random], bpy.types.Object]] = {
    "shankha": shankha, "chakra": chakra, "gada": gada, "padma": padma,
    "nilotpala": lambda P, r: padma(P, r, blue=True), "vel": vel, "bow": bow, "arrow": arrow,
    "bow_arrow": bow_arrow, "parashu": parashu, "hala": hala, "musala": musala, "khadga": khadga,
    "shield": shield, "trishula": trishula, "butter_pot": butter_pot, "butter_ball": butter_ball,
    "kalasam": kalasam, "ankusha": ankusha, "pasha": pasha, "modaka": modaka, "danta": danta,
    "chatra": chatra, "kamandalu": kamandalu, "palm_leaf": palm_leaf, "stylus": stylus,
    "peacock_quill": peacock_quill, "parrot": parrot, "japa_mala": japa_mala, "milk_cup": milk_cup,
    "walking_stick": walking_stick, "danda": danda, "goad_stick": goad_stick, "reins": reins, "sling": sling,
    "tambura": tambura, "chipla": chipla, "flag": flag, "infant": infant, "bhudevi": bhudevi, "ledger": ledger,
    "weighing_scale": weighing_scale, "measure_padi": measure_padi, "clipboard": clipboard,
    "paddy_sheaf": paddy_sheaf, "sugarcane": sugarcane, "banana_bunch": banana_bunch,
    "thavil_stick": thavil_stick, "kolam_bowl": kolam_bowl,
}

# Two-handed items: built once and placed relative to the body; hands reach their grip points.
BODY_ITEMS: dict[str, Callable[[Paint, random.Random], bpy.types.Object]] = {
    "veena": None,  # built by veena() below (needs body frame)
    "flute": None, "garland": garland, "nadaswaram": nadaswaram, "churning_rope": churning_rope,
    "laptop": laptop, "potters_wheel": potters_wheel,
}

MUDRAS = {"abhaya", "varada", "kati", "anjali", "chin", "hridaya", "lola", "point_up", "point", "abhaya_coins",
          "varada_coins", "serpent_tail", "lift_hill_finger", "pot_on_head_hold", "kolam_pinch", "thavil_thimble"}


def is_mudra(token: str) -> bool:
    return token in MUDRAS


def veena(P: Paint, rng) -> bpy.types.Object:
    """Tanjore veena along +X (resonator at origin, neck toward +X), held diagonally across the lap."""
    kudam = MU.uv_sphere("veena_kudam", 0.075, 24, 14, scale=(0.95, 1.0, 1.0))
    _place(kudam, (0, 0, 0))
    gradient_paint(kudam, P.p.silk("maroon"), P.p.silk("maroon"), rough=0.3)
    face = MU.cylinder("veena_face", 0.06, 0.004, 24, center=(0, 0, 0.0))
    _place(face, (0, -0.0, 0.07))
    P.col(face, P.p.silk("khaki"), 0.4)
    neck = MU.box("veena_neck", (0.42, 0.034, 0.03), (0.23, 0, 0.06), bevel=0.006)
    P.col(neck, P.p.silk("maroon"), 0.3)
    parts = [kudam, face, neck]
    for i in range(14):
        fr = MU.box(f"veena_fret{i}", (0.003, 0.03, 0.008), (0.1 + i * 0.022, 0, 0.078))
        parts.append(P.gold(fr))
    gourd = MU.uv_sphere("veena_gourd", 0.045, 16, 10)
    _place(gourd, (0.36, 0, -0.01))
    parts.append(P.col(gourd, P.p.silk("maroon"), 0.35))
    yali = MU.tube("veena_yali", [Vector((0.44, 0, 0.06)), Vector((0.5, 0, 0.07)), Vector((0.52, 0, 0.11)),
                                  Vector((0.5, 0, 0.13))], 0.016, radii=[1, 1, 0.8, 0.5])
    parts.append(P.gold(yali))
    for k in range(4):
        st = MU.tube(f"veena_str{k}", [Vector((0.02, (k - 1.5) * 0.006, 0.075)), Vector((0.44, (k - 1.5) * 0.006, 0.086))],
                     0.0007)
        parts.append(P.col(st, P.p.material("silver"), 0.3, metal=1.0, kind=3))
    return MU.join(parts, "veena")


def flute(P: Paint, rng) -> bpy.types.Object:
    tube_ = MU.cylinder("flute", 0.006, 0.26, 12, center=(0, 0, 0))
    _place(tube_, rot=(0, math.pi / 2, 0))
    P.col(tube_, P.p.silk("khaki"), 0.35)

    def fn(co, n):
        if co.y < -0.004 and any(abs(co.x - (0.02 + k * 0.022)) < 0.003 for k in range(6)):
            return ((0.02, 0.015, 0.01), 0.0, 0.5, 6)
        if abs(co.x + 0.11) < 0.008 or abs(co.x - 0.115) < 0.006:
            return (P.p.material("gold"), 1.0, 0.3, 3)
        return None
    MU.paint_corners(tube_, fn)
    tas = MU.uv_sphere("flute_tassel", 0.006, 8, 6, scale=(1, 1, 2))
    _place(tas, (0.13, 0, -0.018))
    return MU.join([tube_, P.col(tas, P.p.silk("kumkum"), 0.5)], "flute")


def build_attribute(token: str, palette: Palette, rng: random.Random) -> bpy.types.Object:
    P = Paint(palette)
    if token == "veena":
        return veena(P, rng)
    if token == "flute":
        return flute(P, rng)
    fn = REGISTRY.get(token) or BODY_ITEMS.get(token)
    if fn is None:
        raise KeyError(f"unknown attribute token '{token}'")
    return fn(P, rng)


def known_tokens() -> set[str]:
    return set(REGISTRY) | set(BODY_ITEMS) | MUDRAS
