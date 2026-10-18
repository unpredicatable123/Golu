"""Props: lamps, flames, flowers, garlands, thoranam, banana stems, kolam (environment section),
plus story props, golu objects and ritual/prasadam props (added in later phases)."""
from __future__ import annotations

import math
import random
from typing import Sequence

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import materials as M
from . import mesh_utils as MU
from . import render as R

# =========================================================================== flames & lamps


def flame_profile(h: float, width_ratio: float = 0.28, n: int = 14) -> list[tuple[float, float]]:
    pts = []
    for i in range(n + 1):
        t = i / n
        r = width_ratio * h * (math.sin(math.pi * min(t * 1.05, 1.0)) ** 0.75) * ((1 - t) ** 0.35) * 1.35
        pts.append((r, t * h))
    pts[0] = (0.0, 0.0)
    pts[-1] = (0.0, h)
    return pts


def build_flame(loc, height: float, kind: str, rng: random.Random, collection, power_w: float,
                lean: float = 0.0, with_light: bool = True, flicker: bool = True, name: str = "Flame"):
    """Teardrop emissive flame + warm point light with seeded flicker (DECISIONS D28)."""
    ob = MU.lathe(name, flame_profile(height, 0.30 if kind != "camphor" else 0.26), segments=16,
                  collection=collection, screw=False)
    MU.assign_material(ob, M.flame(kind))
    ob.location = Vector(loc)
    ob.rotation_euler = (rng.uniform(-0.06, 0.06) + lean, rng.uniform(-0.06, 0.06), 0)
    ob.visible_shadow = False
    ob["is_flame"] = True
    light = None
    if with_light:
        ld = bpy.data.lights.new(name + "_L", "POINT")
        ld.energy = power_w
        ld.shadow_soft_size = 0.012
        ld.color = R.kelvin_to_rgb(M.pal().kelvin("flame"))
        if hasattr(ld, "use_soft_falloff"):
            ld.use_soft_falloff = True
        light = bpy.data.objects.new(name + "_L", ld)
        light.location = Vector(loc) + Vector((0, 0, height * 0.38))
        MU.link(light, collection)
        if flicker:
            _flicker(ld, "energy", power_w, power_w * 0.06, rng)
    if flicker:
        ob.scale = (1, 1, 1)
        ob.keyframe_insert("scale", index=2, frame=1)
        fc = ob.animation_data.action.fcurves.find("scale", index=2)
        mod = fc.modifiers.new("NOISE")
        mod.scale = 4.0
        mod.strength = 0.06
        mod.phase = rng.uniform(0, 100)
    return ob, light


def _flicker(datablock, path: str, value: float, strength: float, rng: random.Random) -> None:
    setattr(datablock, path, value)
    datablock.keyframe_insert(path, frame=1)
    fc = datablock.animation_data.action.fcurves.find(path)
    mod = fc.modifiers.new("NOISE")
    mod.scale = 3.0
    mod.strength = strength * 2
    mod.phase = rng.uniform(0, 100)
    mod.depth = 1


def _annam_bird(scale: float, collection, name: str) -> bpy.types.Object:
    """Hamsa (annam) finial from metaballs."""
    s = scale
    els = [
        MU.MetaElem("ELLIPSOID", (0, 0, 0.03 * s), 0.035 * s, (0.75, 0.45, 0.45)),
        MU.capsule_between(Vector((0.02 * s, 0, 0.045 * s)), Vector((0.035 * s, 0, 0.085 * s)), 0.011 * s),
        MU.MetaElem("BALL", (0.038 * s, 0, 0.095 * s), 0.016 * s),
        MU.capsule_between(Vector((0.045 * s, 0, 0.095 * s)), Vector((0.065 * s, 0, 0.09 * s)), 0.005 * s),
        MU.capsule_between(Vector((-0.03 * s, 0, 0.035 * s)), Vector((-0.06 * s, 0, 0.075 * s)), 0.012 * s),
        MU.capsule_between(Vector((-0.06 * s, 0, 0.075 * s)), Vector((-0.045 * s, 0, 0.105 * s)), 0.009 * s),
    ]
    mb = MU.metaball_object(name + "_mb", els, 0.004 * s, collection)
    ob = MU.metaball_to_mesh(mb, name)
    MU.shade_smooth(ob, None)
    return ob


def build_kuthuvilakku(name: str, height: float, rng: random.Random, collection, wick_power: float = 3.0):
    """Tall brass five-faced lamp: Screw/lathe profile, 5 V spouts, crown with annam finial, 5 lit wicks."""
    k = height / 1.25
    prof = [(0.0, 0.0), (0.15, 0.0), (0.156, 0.012), (0.142, 0.026), (0.124, 0.032), (0.118, 0.05),
            (0.085, 0.07), (0.06, 0.09), (0.048, 0.11), (0.036, 0.135), (0.024, 0.16), (0.021, 0.3),
            (0.034, 0.315), (0.042, 0.335), (0.034, 0.355), (0.021, 0.37), (0.018, 0.52), (0.03, 0.535),
            (0.038, 0.552), (0.03, 0.57), (0.018, 0.585), (0.017, 0.74), (0.028, 0.77), (0.05, 0.795),
            (0.08, 0.818), (0.1, 0.84), (0.11, 0.862), (0.108, 0.874), (0.096, 0.872), (0.06, 0.862),
            (0.0, 0.858)]
    prof = [(r * k, z * k) for r, z in prof]
    bm = MU.lathe_bm(prof, segments=120)
    # five V spouts (mugam): pull rim vertices outward/upward in 5 angular windows
    win = math.radians(16)
    for v in bm.verts:
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.09 * k and v.co.z > 0.845 * k:
            ang = math.atan2(v.co.y, v.co.x)
            for s in range(5):
                a0 = math.radians(90 + s * 72)
                d = math.atan2(math.sin(ang - a0), math.cos(ang - a0))
                if abs(d) < win:
                    f = 1 - (abs(d) / win)
                    f = f * f * (3 - 2 * f)
                    sharp = 1 - abs(d) / win
                    out = (0.03 * f + 0.012 * sharp ** 3) * k
                    v.co.x += math.cos(ang) * out
                    v.co.y += math.sin(ang) * out
                    v.co.z += 0.01 * f * k
    body = MU.bmesh_to_object(bm, name, collection)
    MU.shade_smooth(body, 50)
    parts = [body]
    crown_prof = [(0.0, 0.858), (0.016, 0.858), (0.014, 0.9), (0.028, 0.915), (0.032, 0.93), (0.02, 0.945),
                  (0.013, 0.98), (0.026, 0.995), (0.03, 1.01), (0.018, 1.025), (0.012, 1.06), (0.022, 1.075),
                  (0.0, 1.085)]
    crown = MU.lathe(name + "_crown", [(r * k, z * k) for r, z in crown_prof], segments=48, collection=collection,
                     screw=True)
    parts.append(crown)
    bird = _annam_bird(1.6 * k, collection, name + "_annam")
    bird.location = (0, 0, 1.075 * k)
    MU.apply_transform(bird)
    parts.append(bird)
    lamp = MU.join(parts, name)
    MU.assign_material(lamp, M.brass())
    lamp["is_lamp"] = True
    flames, lights = [], []
    for s in range(5):
        a = math.radians(90 + s * 72)
        tip = Vector((math.cos(a) * 0.142 * k, math.sin(a) * 0.142 * k, 0.878 * k))
        wick = MU.tube(f"{name}_wick{s}", [tip - Vector((math.cos(a), math.sin(a), 0)) * 0.03 * k,
                                           tip + Vector((0, 0, 0.006 * k))], 0.0045 * k, collection=collection)
        MU.assign_material(wick, M.cotton_wick())
        fl, li = build_flame(tip + Vector((0, 0, 0.004 * k)), 0.034 * k, "ghee", rng, collection, wick_power,
                             name=f"{name}_flame{s}")
        flames.append(fl)
        lights.append(li)
        wick.parent = lamp
        fl.parent = lamp
        li.parent = lamp
    return lamp, flames, lights


def build_agal_vilakku(name: str, loc, rng: random.Random, collection, lit: bool = True, size: float = 1.0,
                       power: float = 0.4):
    """Terracotta agal lamp: lathe bowl with pinched spout, cotton wick and small flame."""
    s = size
    prof = [(0.0, 0.0), (0.022 * s, 0.0), (0.034 * s, 0.01 * s), (0.038 * s, 0.02 * s), (0.034 * s, 0.021 * s),
            (0.026 * s, 0.012 * s), (0.0, 0.009 * s)]
    bm = MU.lathe_bm(prof, 48)
    for v in bm.verts:
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.024 * s:
            ang = math.atan2(v.co.y, v.co.x)
            d = abs(math.atan2(math.sin(ang + math.pi / 2), math.cos(ang + math.pi / 2)))
            if d < 0.7:
                f = (1 - d / 0.7) ** 2
                v.co.x += math.cos(ang) * 0.016 * s * f
                v.co.y += math.sin(ang) * 0.016 * s * f
                v.co.z += 0.004 * s * f
                # pinch the spout sides together
                v.co.x *= 1 - 0.45 * f
    ob = MU.bmesh_to_object(bm, name, collection)
    MU.shade_smooth(ob, 60)
    MU.assign_material(ob, M.terracotta())
    ob.location = Vector(loc)
    if lit:
        tip = Vector(loc) + Vector((0, -0.048 * s, 0.022 * s))
        wick = MU.tube(name + "_wick", [tip + Vector((0, 0.012 * s, -0.004 * s)), tip], 0.0025 * s,
                       collection=collection)
        MU.assign_material(wick, M.cotton_wick())
        build_flame(tip + Vector((0, 0, 0.001)), 0.024 * s, "agal", rng, collection, power, name=name + "_flame")
    return ob


# =========================================================================== flowers & garlands


def make_marigold_head(name: str, color_key: str, rng: random.Random, radius: float = 0.016) -> bpy.types.Object:
    """Displaced icosphere marigold head (SPEC §4.2)."""
    ob = MU.ico_sphere(name, radius, 4)
    tex = MU.texture(f"tx_{name}", "VORONOI", noise_scale=0.0026 + rng.uniform(-0.0003, 0.0003),
                     distance_metric="DISTANCE_SQUARED")
    MU.displace(ob, tex, radius * 0.42, mid=0.35)
    tex2 = MU.texture(f"tx2_{name}", "CLOUDS", noise_scale=0.006)
    MU.displace(ob, tex2, radius * 0.12)
    ob.scale = (1.0, 1.0, 0.78)
    MU.apply_transform(ob)
    MU.shade_smooth(ob, None)
    MU.assign_material(ob, M.marigold(color_key))
    return ob


def make_jasmine_bud(name: str, rng: random.Random, length: float = 0.016) -> bpy.types.Object:
    prof = [(0.0, 0.0), (0.0018, 0.0005), (0.0032, 0.003), (0.0028, 0.006), (0.0034, 0.0095), (0.0042, 0.0125),
            (0.0036, 0.0148), (0.0, 0.016)]
    k = length / 0.016
    ob = MU.lathe(name, [(r * k * rng.uniform(0.9, 1.1), z * k) for r, z in prof], 10, screw=False)
    ob.rotation_euler = (math.pi / 2, 0, rng.uniform(0, math.tau))
    MU.apply_transform(ob)
    MU.assign_material(ob, M.jasmine())
    return ob


_FLOWER_LIB: bpy.types.Collection | None = None


def flower_library(rng: random.Random) -> bpy.types.Collection:
    """Instance-source collection: 4 marigold variants (2 orange, 2 yellow) then 3 jasmine clusters."""
    global _FLOWER_LIB
    if _FLOWER_LIB is not None:
        return _FLOWER_LIB
    objs = []
    for i in range(4):
        key = "marigold-orange" if i % 2 == 0 else "marigold-yellow"
        objs.append(make_marigold_head(f"g0_mari_{i}", key, rng))
    for i in range(3):
        buds = []
        for j in range(10):
            b = make_jasmine_bud(f"g1_jas_{i}_{j}", rng, 0.012)
            a = j / 10 * math.tau * 2 + rng.uniform(-0.25, 0.25)
            b.location = ((j - 4.5) * 0.0018, math.cos(a) * 0.004, math.sin(a) * 0.004)
            b.rotation_euler = (a, 0, rng.uniform(-0.5, 0.5))
            MU.apply_transform(b)
            buds.append(b)
        objs.append(MU.join(buds, f"g1_jas_{i}"))
    _FLOWER_LIB = MU.instance_collection("FlowerLib", objs)
    return _FLOWER_LIB


def build_garland(name: str, path: Sequence[Vector], rng: random.Random, collection, seed: int,
                  pattern: str = "M6J3", spacing: float = 0.021) -> bpy.types.Object:
    """Curve with GN-instanced marigold heads alternating with jasmine (SPEC §4.2, DECISIONS D21)."""
    lib = flower_library(rng)
    cu = MU.curve_object(name, path, collection=collection, kind="POLY")
    na, nb = (6, 4) if pattern == "M6J3" else (12, 0)
    tree = MU.scatter_tree(f"GN_{name}", seed, source="curve", collection=lib, spacing=spacing,
                           scale_range=(0.88, 1.12), random_rot=(0.6, 0.6, math.tau),
                           pattern=(na, max(nb, 1), 4, 3) if nb else None)
    MU.add_gn_modifier(cu, tree)
    return cu


def swag_path(x0: float, x1: float, y: float, z: float, sag: float, hooks: int) -> list[Vector]:
    pts: list[Vector] = []
    xs = [x0 + (x1 - x0) * i / hooks for i in range(hooks + 1)]
    for a, b in zip(xs, xs[1:]):
        seg = MU.catenary(Vector((a, y, z)), Vector((b, y, z)), sag, 14)
        pts.extend(seg if not pts else seg[1:])
    return pts


def make_mango_leaf(name: str, rng: random.Random, length: float = 0.11) -> bpy.types.Object:
    """Lanceolate mango leaf: outline grid folded on the midrib and curved along its length."""
    nl, nw = 14, 4
    verts, faces, uvs = [], [], []
    for i in range(nl + 1):
        t = i / nl
        half = length * 0.13 * (math.sin(math.pi * t) ** 0.8) * (1 - 0.35 * t) + 0.0008
        for j in range(nw + 1):
            s = j / nw * 2 - 1
            fold = abs(s) * half * 0.35
            verts.append((s * half, fold, -t * length))
            uvs.append((j / nw, t))
    for i in range(nl):
        for j in range(nw):
            a = i * (nw + 1) + j
            faces.append((a, a + 1, a + nw + 2, a + nw + 1))
    ob = MU.new_mesh_object(name, verts, faces)
    uv = ob.data.uv_layers.new(name="UVMap")
    for li, loop in enumerate(ob.data.loops):
        uv.data[li].uv = uvs[loop.vertex_index]
    MU.simple_deform(ob, "BEND", math.radians(rng.uniform(18, 32)), axis="X")
    MU.solidify(ob, 0.0006)
    MU.shade_smooth(ob, None)
    MU.assign_material(ob, M.mango_leaf())
    return ob


def build_thoranam(name: str, p0, p1, rng: random.Random, collection, leaf_spacing: float = 0.07,
                   sag: float = 0.06) -> bpy.types.Object:
    """Mango-leaf thoranam: sagging string with hanging leaves (shared-mesh instances), marigold every 5th."""
    path = MU.catenary(Vector(p0), Vector(p1), sag, 40)
    rope = MU.tube(name, path, 0.0025, collection=collection)
    MU.assign_material(rope, M.simple("M_Twine", (0.5, 0.38, 0.22), 0.8))
    proto = make_mango_leaf(name + "_leafproto", rng)
    mari = make_marigold_head(name + "_mariproto", "marigold-orange", rng, 0.02)
    total = (Vector(p1) - Vector(p0)).length
    n = int(total / leaf_spacing)
    for i in range(1, n):
        t = i / n
        p = Vector(p0).lerp(Vector(p1), t)
        p.z -= sag * 4 * t * (1 - t)
        if i % 5 == 0:
            ob = bpy.data.objects.new(f"{name}_mari{i}", mari.data)
            ob.location = p + Vector((0, -0.005, -0.012))
        else:
            ob = bpy.data.objects.new(f"{name}_leaf{i}", proto.data)
            ob.location = p
            ob.rotation_euler = (rng.uniform(-0.25, 0.1), rng.uniform(-0.2, 0.2), rng.uniform(-0.25, 0.25))
            s = rng.uniform(0.85, 1.12)
            ob.scale = (s, s, s)
        MU.link(ob, collection)
        ob.parent = rope
        ob.matrix_parent_inverse = rope.matrix_world.inverted()
    MU.delete_object(proto)
    MU.delete_object(mari)
    return rope


def make_banana_leaf(name: str, rng: random.Random, length: float, width: float) -> bpy.types.Object:
    nl, nw = 28, 10
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid = []
    for i in range(nl + 1):
        t = i / nl
        half = width / 2 * (math.sin(math.pi * min(1.0, t * 1.08)) ** 0.45) * (1 - 0.15 * t)
        row = []
        for j in range(nw + 1):
            s = j / nw * 2 - 1
            row.append(bm.verts.new((s * half, abs(s) * half * 0.12, t * length)))
        grid.append(row)
    torn_cols = set()
    for _ in range(rng.randint(6, 10)):
        torn_cols.add(rng.randint(3, nl - 2))
    for i in range(nl):
        for j in range(nw):
            s_mid = abs((j + 0.5) / nw * 2 - 1)
            if i in torn_cols and s_mid > rng.uniform(0.25, 0.6):
                continue
            f = bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
            for loop in f.loops:
                ii = next(k for k, row in enumerate(grid) if loop.vert in row)
                jj = grid[ii].index(loop.vert)
                loop[uvl].uv = (jj / nw, ii / nl)
    ob = MU.bmesh_to_object(bm, name)
    MU.simple_deform(ob, "BEND", math.radians(rng.uniform(55, 85)), axis="X")
    MU.solidify(ob, 0.001)
    MU.shade_smooth(ob, None)
    MU.assign_material(ob, M.banana_leaf())
    return ob


def build_banana_stem(name: str, height: float, rng: random.Random, collection, with_bunch: bool = True) -> bpy.types.Object:
    """Festive banana plant: banded pseudo-stem, 5 drooping torn leaves, small bunch and purple bud."""
    r0 = 0.075 * height / 2.2
    prof = [(0.0, 0.0), (r0, 0.0)] + [(r0 * (1 - 0.35 * t) * (1 + 0.04 * math.sin(t * 40)), t * height * 0.78)
                                       for t in (i / 24 for i in range(1, 25))] + [(0.0, height * 0.78)]
    stem = MU.lathe(name, prof, 24, collection=collection, screw=False)
    MU.assign_material(stem, M.banana_stem())
    parts = [stem]
    for i in range(5):
        lf = make_banana_leaf(f"{name}_leaf{i}", rng, height * rng.uniform(0.42, 0.55), height * 0.16)
        a = i / 5 * math.tau + rng.uniform(-0.3, 0.3)
        lf.rotation_euler = (rng.uniform(0.35, 0.75), 0, a)
        lf.location = (0, 0, height * (0.72 + 0.02 * i))
        MU.apply_transform(lf)
        MU.link(lf, collection)
        lf.parent = stem
    if with_bunch:
        bunch_parts = []
        for k in range(18):
            ring, idx = divmod(k, 6)
            a = idx / 6 * math.tau + ring * 0.4
            fruit = MU.uv_sphere(f"{name}_b{k}", 0.012, 10, 6, scale=(1, 1, 4.0))
            fruit.location = (math.cos(a) * 0.03, math.sin(a) * 0.03, -ring * 0.045)
            fruit.rotation_euler = (math.cos(a) * 0.6, -math.sin(a) * 0.6, 0)
            MU.apply_transform(fruit)
            bunch_parts.append(fruit)
        bunch = MU.join(bunch_parts, f"{name}_bunch")
        MU.assign_material(bunch, M.simple("M_RawBanana", (0.22, 0.35, 0.06), 0.4))
        bud = MU.uv_sphere(f"{name}_bud", 0.03, 16, 8, scale=(1, 1, 2.0))
        bud.location = (0, 0, -0.17)
        MU.apply_transform(bud)
        MU.assign_material(bud, M.simple("M_BananaBud", (0.22, 0.04, 0.09), 0.35))
        for ob in (bunch, bud):
            ob.location += Vector((0.08, -0.05, height * 0.62))
            MU.link(ob, collection)
            ob.parent = stem
    return stem


# =========================================================================== kolam


def kolam_cells(dots: int, shape: str) -> set[tuple[int, int]]:
    """Dot (cell) set in doubled coordinates: full square, or the classic diamond 1-3-5-…-5-3-1."""
    c = (dots - 1) / 2
    cells = set()
    for i in range(dots):
        for j in range(dots):
            if shape == "diamond" and abs(i - c) + abs(j - c) > c:
                continue
            cells.add((2 * i + 1, 2 * j + 1))
    return cells


def kolam_loops(dots: int, mirrors: set[tuple[int, int]], shape: str = "square") -> list[list[tuple[int, int]]]:
    """Mirror-curve (sikku) kolam (DECISIONS D22).

    Doubled coordinates: dot centres at odd (x, y); edge midpoints have exactly one odd coordinate. A ray
    moves diagonally between edge midpoints, cutting the corner of the cell it crosses so it loops around
    that cell's dot. It reflects at the outline of the dot set and at `mirrors` (internal edge midpoints),
    and passes straight through other edges (the sikku crossings). Returns closed loops of midpoints.
    """
    cells = kolam_cells(dots, shape)
    visited: set[tuple[int, int, int, int]] = set()
    loops = []

    def neighbours(x: int, y: int) -> tuple[tuple[int, int], tuple[int, int]]:
        return ((x - 1, y), (x + 1, y)) if x % 2 == 0 else ((x, y - 1), (x, y + 1))

    def is_mirror(x: int, y: int) -> bool:
        a, b = neighbours(x, y)
        return a not in cells or b not in cells or (x, y) in mirrors

    def crossed_cell(x: int, y: int, dx: int, dy: int) -> tuple[int, int]:
        return (x + dx, y) if x % 2 == 0 else (x, y + dy)

    size = 2 * dots
    starts = [(x, y) for x in range(size + 1) for y in range(size + 1) if (x + y) % 2 == 1]
    for sx, sy in starts:
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            if crossed_cell(sx, sy, dx, dy) not in cells:
                continue
            if (sx, sy, dx, dy) in visited:
                continue
            x, y = sx, sy
            pts: list[tuple[float, float]] = []
            cdx, cdy = dx, dy
            x, y = sx, sy
            pull: tuple[int, int] | None = None   # dot to pull toward when this point is a reflection
            while True:
                if (x, y, cdx, cdy) in visited:
                    break
                visited.add((x, y, cdx, cdy))
                if pull is None:
                    pts.append((float(x), float(y)))
                else:   # at a reflection the loop turns round the dot instead of touching its neighbour
                    pts.append((x + (pull[0] - x) * 0.38, y + (pull[1] - y) * 0.38))
                came_from = crossed_cell(x, y, cdx, cdy)
                x, y = x + cdx, y + cdy
                pull = None
                if is_mirror(x, y):
                    if x % 2 == 0:      # vertical edge → flip horizontal direction
                        cdx = -cdx
                    else:               # horizontal edge
                        cdy = -cdy
                    pull = came_from
                if (x, y) == (sx, sy) and (cdx, cdy) == (dx, dy):
                    if pull is not None and pts:   # the start point itself was a reflection
                        pts[0] = (sx + (pull[0] - sx) * 0.38, sy + (pull[1] - sy) * 0.38)
                    break
            if len(pts) >= 4:
                loops.append(pts)
    # remove duplicates traced in reverse
    uniq, seen = [], set()
    for lp in loops:
        key = frozenset((round(px, 3), round(py, 3)) for px, py in lp)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(lp)
    return uniq


def symmetric_mirrors(dots: int, rng: random.Random, density: float = 0.28) -> set[tuple[int, int]]:
    """Random internal mirror set with D4 symmetry about the grid centre."""
    size = 2 * dots
    c = dots

    def orbit(x: int, y: int) -> set[tuple[int, int]]:
        u, v = x - c, y - c
        pts = set()
        for a, b in ((u, v), (-u, v), (u, -v), (-u, -v), (v, u), (-v, u), (v, -u), (-v, -u)):
            pts.add((a + c, b + c))
        return pts

    internal = [(x, y) for x in range(1, size) for y in range(1, size) if (x + y) % 2 == 1]
    chosen: set[tuple[int, int]] = set()
    done: set[tuple[int, int]] = set()
    for p in internal:
        if p in done:
            continue
        orb = orbit(*p)
        done |= orb
        if rng.random() < density:
            chosen |= {q for q in orb if 0 < q[0] < size and 0 < q[1] < size}
    return chosen


def _catmull_closed(pts: list[Vector], samples: int = 6) -> list[Vector]:
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return out


def ribbon_mesh(name: str, loops: list[list[Vector]], width: float, collection) -> bpy.types.Object:
    """Flat closed ribbons with UV (u along, v across) for the rice-flour shader."""
    verts, faces, uvs = [], [], []
    for li, lp in enumerate(loops):
        n = len(lp)
        base = len(verts)
        for i, p in enumerate(lp):
            t = (lp[(i + 1) % n] - lp[i - 1])
            t.z = 0
            t.normalize()
            nrm = Vector((-t.y, t.x, 0))
            z = 0.0006 + li * 0.00015 + i * 0.000004
            verts.append((p.x + nrm.x * width / 2, p.y + nrm.y * width / 2, z))
            verts.append((p.x - nrm.x * width / 2, p.y - nrm.y * width / 2, z))
            uvs.extend([(i / n, 0.0), (i / n, 1.0)])
        for i in range(n):
            a = base + 2 * i
            b = base + 2 * ((i + 1) % n)
            faces.append((a, b, b + 1, a + 1))
    ob = MU.new_mesh_object(name, verts, faces, collection)
    uv = ob.data.uv_layers.new(name="UVMap")
    for li, loop in enumerate(ob.data.loops):
        uv.data[li].uv = uvs[loop.vertex_index]
    return ob


def build_kolam(name: str, dots: int, spacing: float, rng: random.Random, collection,
                line_width: float = 0.008, density: float = 0.28, shape: str = "diamond") -> bpy.types.Object:
    """Sikku kolam: mirror-curve loops around a pulli (dot) grid, as rice-flour ribbons + dots."""
    mirrors = symmetric_mirrors(dots, rng, density)
    loops = kolam_loops(dots, mirrors, shape)
    half = dots * spacing / 2
    world_loops = []
    for lp in loops:
        pts = [Vector((x * spacing / 2 - half, y * spacing / 2 - half, 0.0)) for x, y in lp]
        world_loops.append(_catmull_closed(pts, 6))
    ribbons = ribbon_mesh(name, world_loops, line_width, collection)
    dots_parts = []
    for (cx, cy) in sorted(kolam_cells(dots, shape)):
        d = MU.cylinder(f"{name}_d{cx}_{cy}", line_width * 0.75, 0.0012, 10,
                        center=(cx * spacing / 2 - half, cy * spacing / 2 - half, 0.0006))
        dots_parts.append(d)
    dj = MU.join(dots_parts, name + "_dots")
    MU.set_uv_from(dj, lambda co: (0.5, 0.5))
    kolam = MU.join([ribbons, dj], name)
    MU.link(kolam, collection)
    MU.assign_material(kolam, M.rice_flour())
    kolam["loops"] = len(loops)
    return kolam


# =========================================================================== golu objects & story props (Phase 3)
# Built in metres, painted with the doll attributes and finished with M_ClayGloss: golu sets are painted
# clay/papier-mache models, so they share the dolls' varnished look.

from . import attributes as A  # noqa: E402


def _paint(ob, rgb, rough=0.42, kind=6, metal=0.0):
    MU.set_part_attributes(ob, rgb, metal, rough, kind)
    return ob


def _finish(parts: list, name: str, collection=None, subsurf: bool = False) -> bpy.types.Object:
    from .doll_factory import pack_face_props
    for o in parts:
        if not o.users_collection:
            bpy.context.scene.collection.objects.link(o)
        MU.apply_transform(o)
    ob = MU.join(parts, name)
    MU.set_origin_bottom_center(ob)
    ob.location = (0, 0, 0)
    if subsurf:
        MU.add_subsurf(ob, 1, 1)
    ob.data.materials.clear()
    ob.data.materials.append(M.clay_gloss())
    ob["head_center"] = (0.0, 0.0, -10.0)
    ob["head_radius"] = 1.0
    pack_face_props(ob)
    if collection is not None:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        collection.objects.link(ob)
    return ob


class _Pal:
    def __init__(self, palette):
        self.p = palette

    def s(self, k):
        return self.p.silk(k)

    def m(self, k):
        return self.p.material(k)


# ---------------------------------------------------------------- step 1 models


def build_pslv(Pl: _Pal, rng) -> list:
    white, dark, grey = Pl.s("white"), (0.05, 0.05, 0.06), Pl.s("ash")
    prof = [(0.0, 0.0), (0.03, 0.0), (0.03, 0.17), (0.028, 0.175), (0.028, 0.3), (0.022, 0.31), (0.021, 0.355),
            (0.033, 0.37), (0.034, 0.41), (0.026, 0.435), (0.012, 0.452), (0.0, 0.46)]
    core = MU.lathe("pslv_core", prof, 32, screw=False)
    _paint(core, white, 0.35)

    def bands(co, n):
        if 0.168 < co.z < 0.18 or 0.3 < co.z < 0.31 or 0.36 < co.z < 0.37:
            return (dark, 0.0, 0.35, 6)
        if co.y < 0 and 0.22 < co.z < 0.256:      # small tricolour band on the second stage
            k = int((co.z - 0.22) / 0.012)
            return ((Pl.s("saffron"), Pl.s("white"), Pl.s("parrot-green"))[min(k, 2)], 0.0, 0.4, 6)
        return None
    MU.paint_corners(core, bands)
    parts = [core]
    for i in range(6):
        a = i / 6 * math.tau + 0.26
        sp = MU.lathe(f"pslv_strap{i}", [(0.0, 0.0), (0.011, 0.0), (0.011, 0.13), (0.006, 0.15), (0.0, 0.158)], 16,
                      screw=False)
        _paint(sp, white, 0.35)
        MU.paint_corners(sp, lambda co, n: (dark, 0.0, 0.35, 6) if co.z > 0.135 or co.z < 0.012 else None)
        sp.location = (math.cos(a) * 0.042, math.sin(a) * 0.042, 0.005)
        parts.append(sp)
    for i in range(4):
        a = i / 4 * math.tau + 0.78
        fin = MU.box(f"pslv_fin{i}", (0.02, 0.003, 0.03), (0, 0, 0))
        fin.location = (math.cos(a) * 0.036, math.sin(a) * 0.036, 0.018)
        fin.rotation_euler = (0, 0, a)
        parts.append(_paint(fin, grey, 0.4))
    return parts


def build_satellite_dish(Pl: _Pal, rng) -> list:
    white = Pl.s("white")
    base = MU.cylinder("dish_base", 0.02, 0.05, 16, center=(0, 0, 0.025))
    yoke = MU.box("dish_yoke", (0.05, 0.012, 0.03), (0, 0, 0.06), bevel=0.003)
    prof = [(0.0, 0.0), (0.02, 0.002), (0.045, 0.009), (0.068, 0.02), (0.072, 0.023), (0.07, 0.025),
            (0.045, 0.013), (0.0, 0.004)]
    dish = MU.lathe("dish", prof, 40, screw=False)
    dish.rotation_euler = (math.radians(-55), 0, 0)
    dish.location = (0, -0.005, 0.085)
    feed = MU.cylinder("dish_feed", 0.006, 0.012, 10)
    feed.location = (0, -0.05, 0.12)
    parts = [_paint(base, Pl.s("ash"), 0.45), _paint(yoke, Pl.s("ash"), 0.45), _paint(dish, white, 0.3),
             _paint(feed, Pl.s("ash"), 0.4)]
    for i in range(3):
        a = i / 3 * math.tau
        strut = MU.tube(f"dish_strut{i}", [Vector((math.cos(a) * 0.05, -0.012 + math.sin(a) * 0.03,
                                                   0.085 + math.sin(a) * 0.04)), Vector((0, -0.05, 0.118))], 0.0014)
        parts.append(_paint(strut, Pl.s("ash"), 0.4))
    return parts


def build_chandrayaan3(Pl: _Pal, rng) -> list:
    gold = Pl.m("gold")
    body = MU.box("vikram_body", (0.07, 0.07, 0.045), (0, 0, 0.055), bevel=0.004)
    _paint(body, gold, 0.5, kind=3, metal=0.75)
    MU.paint_corners(body, lambda co, n: ((0.5, 0.36, 0.1), 0.75, 0.55, 3)
                     if math.sin(co.x * 400 + co.z * 230) * math.sin(co.y * 380) > 0.4 else None)
    panel = MU.box("vikram_panel", (0.06, 0.004, 0.035), (0, 0.037, 0.06))
    top = MU.cylinder("vikram_top", 0.012, 0.014, 12, center=(0, 0, 0.084))
    parts = [body, _paint(panel, (0.03, 0.06, 0.2), 0.25), _paint(top, Pl.s("ash"), 0.35)]
    for i in range(4):
        a = i / 4 * math.tau + math.pi / 4
        leg = MU.tube(f"vikram_leg{i}", [Vector((math.cos(a) * 0.03, math.sin(a) * 0.03, 0.045)),
                                          Vector((math.cos(a) * 0.055, math.sin(a) * 0.055, 0.006))], 0.0025)
        pad = MU.cylinder(f"vikram_pad{i}", 0.008, 0.003, 12, center=(math.cos(a) * 0.056, math.sin(a) * 0.056, 0.0015))
        parts += [_paint(leg, Pl.s("ash"), 0.35), _paint(pad, Pl.s("ash"), 0.35)]
    ramp = MU.box("vikram_ramp", (0.026, 0.07, 0.003), (0, 0, 0))
    ramp.rotation_euler = (math.radians(-28), 0, 0)
    ramp.location = (0.0, -0.065, 0.017)
    parts.append(_paint(ramp, Pl.s("ash"), 0.4))
    rover = MU.box("pragyan_body", (0.03, 0.026, 0.012), (0, 0, 0), bevel=0.002)
    rover.location = (0.045, -0.12, 0.016)
    rpanel = MU.box("pragyan_panel", (0.034, 0.02, 0.002), (0, 0, 0))
    rpanel.location = (0.045, -0.12, 0.024)
    mast = MU.cylinder("pragyan_mast", 0.0015, 0.018, 6, center=(0.035, -0.128, 0.032))
    parts += [_paint(rover, gold, 0.45, kind=3, metal=0.7), _paint(rpanel, (0.03, 0.06, 0.2), 0.25),
              _paint(mast, Pl.s("ash"), 0.4)]
    for i in range(6):
        wx = 0.045 + (i % 3 - 1) * 0.011
        wy = -0.12 + (-0.016 if i < 3 else 0.016)
        w = MU.cylinder(f"pragyan_w{i}", 0.0055, 0.004, 12)
        w.rotation_euler = (math.pi / 2, 0, 0)
        w.location = (wx, wy, 0.0055)
        parts.append(_paint(w, (0.08, 0.08, 0.08), 0.5))
    return parts


def _coach(name: str, length: float, body_col, band_col, nose: bool, Pl: _Pal) -> list:
    w, h = 0.058, 0.06
    body = MU.box(f"{name}_body", (length, w, h), (0, 0, 0.012 + h / 2), bevel=0.008, bevel_segments=3)
    _paint(body, body_col, 0.3)
    MU.paint_corners(body, lambda co, n: ((0.02, 0.03, 0.05), 0.0, 0.15, 6) if 0.047 < co.z < 0.062 and abs(n.z) < 0.6
                     else ((band_col, 0.0, 0.3, 6) if 0.026 < co.z < 0.036 and abs(n.z) < 0.6 else None))
    parts = [body]
    if nose:
        els = [MU.MetaElem("ELLIPSOID", (length / 2 + 0.01, 0, 0.042), 0.07, (1.5, 0.62, 0.64))]
        mb = MU.metaball_object(f"mb_{name}_nose", els, 0.003)
        n_ob = MU.metaball_to_mesh(mb, f"{name}_nose")
        bm = bmesh.new()
        bm.from_mesh(n_ob.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x < length / 2 - 0.004 or v.co.z < 0.012],
                         context="VERTS")
        bm.to_mesh(n_ob.data)
        bm.free()
        _paint(n_ob, body_col, 0.3)
        MU.paint_corners(n_ob, lambda co, n: ((0.02, 0.03, 0.05), 0.0, 0.15, 6)
                         if co.z > 0.052 and co.x < length / 2 + 0.035 else
                         ((band_col, 0.0, 0.3, 6) if 0.026 < co.z < 0.04 else None))
        parts.append(n_ob)
    for sx in (-1, 1):
        bogie = MU.box(f"{name}_bogie{sx}", (0.04, w * 0.85, 0.012), (sx * (length / 2 - 0.035), 0, 0.007), bevel=0.002)
        parts.append(_paint(bogie, (0.06, 0.06, 0.07), 0.5))
    return parts


def build_vande_bharat(Pl: _Pal, rng) -> list:
    a = _coach("vb1", 0.2, Pl.s("white"), Pl.s("nilambara"), True, Pl)
    b = _coach("vb2", 0.18, Pl.s("white"), Pl.s("nilambara"), False, Pl)
    for o in a:
        MU.transform(o, Matrix.Translation((0.1, 0, 0)))
    for o in b:
        MU.transform(o, Matrix.Translation((-0.1, 0, 0)))
    return a + b


def build_metro_coach(Pl: _Pal, rng) -> list:
    parts = _coach("metro", 0.24, Pl.m("silver"), Pl.s("nilambara"), False, Pl)
    for i in range(3):
        d = MU.box(f"metro_door{i}", (0.022, 0.0605, 0.05), ((i - 1) * 0.075, 0, 0.042))
        parts.append(_paint(d, (0.15, 0.16, 0.18), 0.3))
    pant = MU.tube("metro_pant", [Vector((-0.02, 0, 0.074)), Vector((0.0, 0, 0.09)), Vector((0.02, 0, 0.074))], 0.0015)
    parts.append(_paint(pant, (0.08, 0.08, 0.08), 0.4))
    return parts


def build_shiva_dhanush_broken(Pl: _Pal, rng) -> list:
    parts = []
    for half in (-1, 1):
        pts, radii = [], []
        for i in range(11):
            t = i / 10
            x = half * (0.012 + t * 0.17)
            y = -0.035 * math.sin(t * math.pi * 0.9) + 0.01 * t ** 3
            pts.append(Vector((x, y, 0.016)))
            radii.append(1.0 - 0.5 * t)
        limb = MU.tube(f"dhanush{half}", pts, 0.013, radii=radii)
        _paint(limb, Pl.s("maroon"), 0.35)
        MU.paint_corners(limb, lambda co, n: (Pl.m("gold"), 0.7, 0.3, 3) if int(abs(co.x) * 70) % 4 == 0 else None)
        parts.append(limb)
        tip = MU.uv_sphere(f"dhanush_tip{half}", 0.01, 10, 6)
        tip.location = pts[-1]
        parts.append(_paint(tip, Pl.m("gold"), 0.3, kind=3, metal=0.7))
        for k in range(4):     # splintered break
            sp = MU.cylinder(f"dhanush_sp{half}{k}", 0.0025, 0.022, 4, radius_top=0.0)
            sp.rotation_euler = (rng.uniform(-0.4, 0.4), half * math.pi / 2 + rng.uniform(-0.3, 0.3), 0)
            sp.location = (half * 0.006, rng.uniform(-0.004, 0.004), 0.016 + rng.uniform(-0.005, 0.005))
            parts.append(_paint(sp, Pl.s("khaki"), 0.5))
    return parts


def build_kalasam_amman(Pl: _Pal, rng) -> list:
    P = A.Paint(Pl.p)
    k = A.kalasam(P, rng, scale=1.35)
    f = 1.35 / 1.9                      # face, crown and garland were laid out for a 1.9 pot
    els = [MU.MetaElem("ELLIPSOID", (0, -0.045 * f, 0.215 * f), 0.05 * f, (0.8, 0.35, 1.0)),
           MU.MetaElem("ELLIPSOID", (0, -0.062 * f, 0.21 * f), 0.012 * f, (0.6, 0.8, 1.2))]
    mb = MU.metaball_object(f"mb_amman_{rng.randint(0, 10**6)}", els, 0.002)
    face = MU.metaball_to_mesh(mb, "amman_face")
    P.gold(face, 0.25)
    parts = [k, face]
    for s in (-1, 1):
        # almond white with a small dark iris and a kajal line (the Amman face's wide, compassionate eyes)
        white = MU.uv_sphere(f"amman_eyew{s}", 0.0085 * f, 14, 8, scale=(1.7, 0.35, 0.62))
        white.location = (s * 0.0145 * f, -0.0625 * f, 0.226 * f)
        kajal = MU.uv_sphere(f"amman_kajal{s}", 0.0094 * f, 14, 8, scale=(1.75, 0.3, 0.7))
        kajal.location = (s * 0.0145 * f, -0.0618 * f, 0.226 * f)
        iris = MU.uv_sphere(f"amman_eye{s}", 0.0038 * f, 10, 6, scale=(1.0, 0.45, 1.0))
        iris.location = (s * 0.0145 * f, -0.0655 * f, 0.226 * f)
        parts += [_paint(kajal, (0.02, 0.015, 0.012), 0.3), _paint(white, Pl.s("white"), 0.2),
                  _paint(iris, (0.02, 0.02, 0.02), 0.15)]
    dot = MU.uv_sphere("amman_pottu", 0.006 * f, 8, 6, scale=(1, 0.4, 1))
    dot.location = (0, -0.066 * f, 0.245 * f)
    lips = MU.uv_sphere("amman_lips", 0.006 * f, 8, 6, scale=(1.8, 0.5, 0.8))
    lips.location = (0, -0.066 * f, 0.195 * f)
    crown = MU.lathe("amman_crown", [(0.0, 0.0), (0.03 * f, 0.0), (0.026 * f, 0.02 * f), (0.014 * f, 0.04 * f), (0.0, 0.052 * f)], 24,
                     screw=False)
    crown.location = (0, -0.035 * f, 0.252 * f)
    parts += [_paint(dot, Pl.m("kumkum-powder"), 0.6), _paint(lips, Pl.s("kumkum"), 0.3), P.gold(crown, 0.25)]
    for i in range(18):    # flower garland around the neck of the pot
        a = i / 18 * math.tau
        g = MU.ico_sphere(f"amman_gar{i}", 0.008 * f, 1)
        g.location = (math.cos(a) * 0.045 * f, math.sin(a) * 0.045 * f, 0.158 * f)
        parts.append(_paint(g, Pl.m("marigold-orange") if i % 3 else Pl.m("jasmine"), 0.5))
    return parts


def build_bullock_cart(Pl: _Pal, rng) -> tuple[list, Vector]:
    from . import vahanas as VH
    parts = []
    for sy in (-1, 1):
        rim = MU.torus(f"cart_rim{sy}", 0.05, 0.005, 32, 6)
        rim.rotation_euler = (math.pi / 2, 0, 0)
        rim.location = (0.06, sy * 0.055, 0.05)
        parts.append(_paint(rim, Pl.s("khaki"), 0.5))
        for k in range(8):
            a = k / 8 * math.tau
            sp = MU.cylinder(f"cart_sp{sy}{k}", 0.0022, 0.05, 6)
            sp.rotation_euler = (0, a, 0)
            sp.location = (0.06 + math.sin(a) * 0.025, sy * 0.055, 0.05 + math.cos(a) * 0.025)
            parts.append(_paint(sp, Pl.s("khaki"), 0.5))
    bed = MU.box("cart_bed", (0.17, 0.1, 0.012), (0.04, 0, 0.085), bevel=0.002)
    parts.append(_paint(bed, Pl.s("khaki"), 0.5))
    # thatched hood: upper half of a horizontal cylinder (arched over the bed)
    verts, faces = [], []
    n_a, n_l = 16, 8
    for i in range(n_l + 1):
        x = -0.02 + 0.13 * i / n_l
        for j in range(n_a + 1):
            a = math.pi * j / n_a
            verts.append((x, math.cos(a) * 0.055, 0.09 + math.sin(a) * 0.055))
    for i in range(n_l):
        for j in range(n_a):
            q = i * (n_a + 1) + j
            faces.append((q, q + 1, q + n_a + 2, q + n_a + 1))
    hood = MU.new_mesh_object("cart_hood", verts, faces)
    MU.solidify(hood, 0.004)
    _paint(hood, Pl.s("khaki"), 0.6)
    MU.paint_corners(hood, lambda co, n: ((0.35, 0.25, 0.1), 0.0, 0.6, 6) if int((co.x + 1) * 160) % 3 == 0 else None)
    shaft = MU.tube("cart_shaft", [Vector((-0.04, 0, 0.085)), Vector((-0.22, 0, 0.1))], 0.006)
    parts += [hood, _paint(shaft, Pl.s("khaki"), 0.5)]
    pair, _ = VH.bullock_pair(A.Paint(Pl.p), rng)
    s = VH.size_m("bullock")
    pair.scale = (s, s, s)
    pair.location = (-0.3, 0, 0)
    MU.apply_transform(pair)
    parts.append(pair)
    anchor = Vector((-0.06, 0.0, 0.092))
    return parts, anchor


GOLU_OBJECTS = {"pslv": build_pslv, "satellite_dish": build_satellite_dish, "chandrayaan3": build_chandrayaan3,
                "vande_bharat": build_vande_bharat, "metro_coach": build_metro_coach,
                "shiva_dhanush_broken": build_shiva_dhanush_broken, "kalasam_amman": build_kalasam_amman}


def build_golu_object(spec, cfg, collection=None) -> bpy.types.Object:
    """Dispatch for archetype "object" (called by doll_factory.make_doll). Real-size metres, scale 1."""
    from .config import rng_for
    Pl = _Pal(cfg.palette)
    rng = rng_for("object", spec.id)
    anchor = None
    if spec.model == "bullock_cart":
        parts, anchor = build_bullock_cart(Pl, rng)
    else:
        parts = GOLU_OBJECTS[spec.model](Pl, rng)
    ob = _finish(parts, spec.id, collection, subsurf=spec.model in ("vande_bharat", "metro_coach"))
    ob["doll_id"] = spec.id
    ob["step"] = spec.step
    ob["slot"] = spec.position.slot
    ob["archetype"] = "object"
    ob.scale = (spec.scale, spec.scale, spec.scale)
    ob["unit_height"] = spec.scale
    lo, hi = MU.bounds_local(ob)
    ob["hotspot_local"] = (0.0, 0.0, hi.z * 0.8)
    if anchor is not None:
        ob["anchor_cart_yoke"] = (anchor.x, anchor.y, anchor.z)
    return ob


# ---------------------------------------------------------------- story props (seats & sets)


TRINKETS = ("flower_plate", "kumkum_pair", "kindi", "flower_plate", "kumkum_pair")


def build_tread_trinket(kind: str, Pl: _Pal, rng, name: str) -> bpy.types.Object:
    """Small brass pooja items set between dolls on lineup steps (a real golu tread is never bare)."""
    gold = Pl.m("brass")
    parts = []
    if kind == "flower_plate":
        plate = MU.lathe(f"{name}_plate", [(0.0, 0.0), (0.03, 0.0), (0.036, 0.004), (0.04, 0.007), (0.0, 0.007)],
                         24, screw=False)
        parts.append(_paint(plate, gold, 0.28, kind=3, metal=0.75))
        for i in range(9):
            a, r = i * 2.4, 0.007 + 0.022 * math.sqrt(i / 9)
            f = MU.ico_sphere(f"{name}_fl{i}", rng.uniform(0.007, 0.009), 1)
            f.location = (r * math.cos(a), r * math.sin(a), 0.011 + 0.006 * (1 - r / 0.03))
            parts.append(_paint(f, Pl.m("marigold-orange") if i % 3 else Pl.m("jasmine"), 0.55))
    elif kind == "kumkum_pair":
        for k, (dx, powder) in enumerate(((-0.017, "kumkum-powder"), (0.017, "turmeric-powder"))):
            cup = MU.lathe(f"{name}_cup{k}", [(0.0, 0.0), (0.008, 0.0), (0.006, 0.006), (0.013, 0.016),
                                               (0.012, 0.018), (0.0, 0.018)], 18, screw=False)
            cup.location = (dx, 0, 0)
            parts.append(_paint(cup, gold, 0.28, kind=3, metal=0.75))
            heap = MU.uv_sphere(f"{name}_heap{k}", 0.011, 12, 6, scale=(1, 1, 0.45))
            heap.location = (dx, 0, 0.018)
            parts.append(_paint(heap, Pl.m(powder), 0.8))
    else:   # kindi: spouted brass water vessel
        body = MU.lathe(f"{name}_body", [(0.0, 0.0), (0.012, 0.0), (0.02, 0.01), (0.022, 0.022), (0.014, 0.034),
                                          (0.008, 0.04), (0.01, 0.05), (0.0, 0.05)], 24, screw=False)
        parts.append(_paint(body, gold, 0.25, kind=3, metal=0.8))
        spout = MU.tube(f"{name}_spout", [Vector((0.016, 0, 0.02)), Vector((0.03, 0, 0.03)),
                                          Vector((0.038, 0, 0.042))], 0.004, radii=[1.0, 0.8, 0.6])
        parts.append(_paint(spout, gold, 0.25, kind=3, metal=0.8))
    ob = _finish(parts, name)
    ob.rotation_euler = (0, 0, rng.uniform(-0.6, 0.6))
    return ob


def build_seat_prop(kind: str, Pl: _Pal, rng, width: float = 0.2) -> tuple[bpy.types.Object, float]:
    """Seat-type story props placed under one doll. Returns (object, top height in metres)."""
    if kind == "launch_pad":
        pad = MU.box("pad", (0.2, 0.2, 0.025), (0, 0, 0.0125), bevel=0.003)
        _paint(pad, Pl.s("ash"), 0.6)
        trench = MU.box("pad_trench", (0.06, 0.21, 0.004), (0, 0, 0.025))
        mount = MU.cylinder("pad_mount", 0.05, 0.012, 20, center=(0, 0, 0.031))
        ob = _finish([pad, _paint(trench, (0.04, 0.04, 0.04), 0.6), _paint(mount, (0.25, 0.25, 0.27), 0.4)],
                     "launch_pad")
        return ob, 0.037
    if kind == "lunar_patch":
        disc = MU.lathe("lunar", [(0.0, 0.009), (0.09, 0.009), (0.12, 0.006), (0.135, 0.0), (0.0, 0.0)], 64,
                        screw=False)
        disc.scale = (1.0, 0.85, 1.0)
        MU.apply_transform(disc)
        bm = bmesh.new()
        bm.from_mesh(disc.data)
        bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if e.calc_length() > 0.004], cuts=3, use_grid_fill=True)
        bm.to_mesh(disc.data)
        bm.free()
        for (cx, cy, cr) in ((0.04, 0.02, 0.025), (-0.05, -0.03, 0.018), (-0.02, 0.05, 0.012), (0.07, -0.04, 0.014)):
            for v in disc.data.vertices:
                d = math.hypot(v.co.x - cx, v.co.y - cy)
                if v.co.z > 0.005 and d < cr * 1.3:
                    v.co.z -= 0.004 * max(0.0, 1 - (d / cr) ** 2) - 0.0015 * max(0.0, 1 - abs(d - cr) / (cr * 0.3))
        MU.displace(disc, MU.texture("tx_lunar", "CLOUDS", noise_scale=0.01), 0.0015)
        _paint(disc, (0.42, 0.42, 0.4), 0.85)
        MU.paint_corners(disc, lambda co, n: ((0.3, 0.3, 0.29), 0.0, 0.85, 6) if n.z < 0.95 else None)
        return _finish([disc], "lunar_patch"), 0.008
    if kind == "rail_track":
        L = width + 0.08
        ballast = MU.box("ballast", (L, 0.075, 0.012), (0, 0, 0.006), bevel=0.003)
        parts = [_paint(ballast, (0.3, 0.29, 0.27), 0.8)]
        for sy in (-1, 1):
            r = MU.box(f"rail{sy}", (L, 0.004, 0.006), (0, sy * 0.022, 0.018))
            parts.append(_paint(r, (0.35, 0.35, 0.36), 0.3, metal=0.6))
        n = int(L / 0.018)
        for i in range(n):
            sl = MU.box(f"sleeper{i}", (0.008, 0.065, 0.004), (-L / 2 + (i + 0.5) * 0.018, 0, 0.014))
            parts.append(_paint(sl, (0.25, 0.2, 0.15), 0.6))
        return _finish(parts, "rail_track"), 0.021
    if kind == "metro_viaduct":
        deck = MU.box("via_deck", (width + 0.06, 0.08, 0.016), (0, 0, 0.07), bevel=0.003)
        parts = [_paint(deck, (0.62, 0.6, 0.57), 0.7)]
        for sx in (-1, 1):
            pil = MU.box(f"via_pier{sx}", (0.022, 0.03, 0.062), (sx * width * 0.32, 0, 0.031), bevel=0.003)
            parts.append(_paint(pil, (0.6, 0.58, 0.55), 0.7))
        return _finish(parts, "metro_viaduct"), 0.078
    if kind == "plinth":
        pl = MU.box("plinth", (0.12, 0.1, 0.03), (0, 0, 0.015), bevel=0.004)
        _paint(pl, Pl.m("pedestal"), 0.35)
        MU.paint_corners(pl, lambda co, n: (Pl.m("gold"), 0.7, 0.3, 3) if abs(co.z - 0.024) < 0.003 else None)
        return _finish([pl], "plinth"), 0.03
    if kind == "rice_mound":
        prof = [(0.0, 0.0), (0.075, 0.0), (0.06, 0.012), (0.035, 0.022), (0.0, 0.026)]
        mound = MU.lathe("rice_mound", prof, 32, screw=False)
        _paint(mound, Pl.s("ivory"), 0.85)
        tray = MU.cylinder("rice_tray", 0.085, 0.006, 32, center=(0, 0, 0.003))
        A.Paint(Pl.p).brass(tray)
        return _finish([tray, mound], "rice_mound"), 0.024
    if kind == "paran_platform":
        parts = []
        h = 0.11
        for sx in (-1, 1):
            for sy in (-1, 1):
                pole = MU.cylinder(f"paran_pole{sx}{sy}", 0.004, h + 0.06, 6,
                                   center=(sx * 0.05, sy * 0.04, (h + 0.06) / 2))
                parts.append(_paint(pole, Pl.s("khaki"), 0.6))
        deck = MU.box("paran_deck", (0.12, 0.1, 0.008), (0, 0, h), bevel=0.002)
        _paint(deck, Pl.s("khaki"), 0.6)
        MU.paint_corners(deck, lambda co, n: ((0.35, 0.25, 0.12), 0.0, 0.6, 6) if int((co.x + 1) * 300) % 4 == 0 else None)
        parts.append(deck)
        for k in range(4):
            rung = MU.cylinder(f"paran_rung{k}", 0.002, 0.03, 6)
            rung.rotation_euler = (0, math.pi / 2, 0)
            rung.location = (0, -0.075, 0.02 + k * 0.025)
            parts.append(_paint(rung, Pl.s("khaki"), 0.6))
        for sx in (-1, 1):
            rail = MU.cylinder(f"paran_ladder{sx}", 0.0025, 0.12, 6)
            rail.rotation_euler = (math.radians(-12), 0, 0)
            rail.location = (sx * 0.016, -0.075, 0.055)
            parts.append(_paint(rail, Pl.s("khaki"), 0.6))
        return _finish(parts, "paran_platform"), h + 0.004
    raise KeyError(kind)


def build_rocket_gantry(Pl: _Pal, rng, height: float = 0.52) -> bpy.types.Object:
    parts = []
    w = 0.07
    red, white = Pl.s("kumkum"), Pl.s("white")
    for sx in (-1, 1):
        for sy in (-1, 1):
            col_ = MU.box(f"gan_col{sx}{sy}", (0.006, 0.006, height), (sx * w / 2, sy * w / 2, height / 2))
            parts.append(_paint(col_, red, 0.45))
    levels = int(height / 0.045)
    for k in range(1, levels + 1):
        z = k * 0.045
        c = red if k % 2 else white
        for sx, sy, sz in ((0, -1, (w, 0.004, 0.004)), (0, 1, (w, 0.004, 0.004)), (-1, 0, (0.004, w, 0.004)),
                           (1, 0, (0.004, w, 0.004))):
            bar = MU.box(f"gan_bar{k}{sx}{sy}", sz, (sx * w / 2, sy * w / 2, z))
            parts.append(_paint(bar, c, 0.45))
        diag = MU.box(f"gan_diag{k}", (0.003, 0.003, 0.064), (0, 0, 0))
        diag.rotation_euler = (math.radians(47 if k % 2 else -47), 0, 0)
        diag.location = (-w / 2, 0, z - 0.022)
        parts.append(_paint(diag, white, 0.45))
    for k, z in enumerate((0.16, 0.3, 0.42)):
        arm = MU.box(f"gan_arm{k}", (0.07, 0.012, 0.008), (w / 2 + 0.035, 0, z))
        parts.append(_paint(arm, white, 0.4))
    roof = MU.box("gan_roof", (w + 0.02, w + 0.02, 0.012), (0, 0, height + 0.006))
    parts.append(_paint(roof, red, 0.45))
    return _finish(parts, "rocket_gantry")


def build_mandapam(Pl: _Pal, rng, width: float = 0.42, depth: float = 0.24, height: float = 0.267) -> bpy.types.Object:
    """Wedding mandapam: four plantain (banana-stem) pillars, beams, a near-flat silk canopy with a scalloped
    valance, zari edge and garland swags. Kept low (hanging edges just above the sight line to the couple's faces,
    canopy ≈ 0.30 m) so the
    step-4 camera's sight line to the next tread passes over it (DECISIONS D55)."""
    parts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * width / 2, sy * depth / 2
            prof = [(0.0, 0.0), (0.011, 0.0)] + [(0.011 * (1 - 0.25 * t), t * height)
                                                 for t in (i / 8 for i in range(1, 9))] + [(0.0, height)]
            st = MU.lathe(f"man_pillar{sx}{sy}", prof, 14, screw=False)
            _paint(st, Pl.m("banana-stem"), 0.45)
            MU.paint_corners(st, lambda co, n: ((0.3, 0.42, 0.14), 0.0, 0.45, 6)
                             if math.sin(math.atan2(co.y, co.x) * 9) > 0.6 else None)
            st.location = (x, y, 0)
            parts.append(st)
            for k in range(3):   # plantain leaves tied at the pillar head, drooping outward
                lf = A.leaf_shell(f"man_leaf{sx}{sy}{k}", 0.1, 0.04, cup=0.3)
                _paint(lf, Pl.m("banana-leaf"), 0.4)
                lf.rotation_euler = (2.25, 0, math.atan2(sy, sx) + math.pi / 2 + (k - 1) * 0.7)
                lf.location = (x, y, height + 0.012)
                parts.append(lf)
    for sy in (-1, 1):
        beam = MU.box(f"man_beam{sy}", (width + 0.04, 0.014, 0.018), (0, sy * depth / 2, height + 0.009), bevel=0.002)
        parts.append(_paint(beam, Pl.s("maroon"), 0.35))
    for sx in (-1, 1):
        beam = MU.box(f"man_beamx{sx}", (0.014, depth + 0.04, 0.018), (sx * width / 2, 0, height + 0.009), bevel=0.002)
        parts.append(_paint(beam, Pl.s("maroon"), 0.35))
    canopy = MU.grid("man_canopy", width + 0.05, depth + 0.05, 24, 14)
    for v in canopy.data.vertices:
        u, w2 = v.co.x / (width + 0.05), v.co.y / (depth + 0.05)
        v.co.z = height + 0.018 + 0.012 * (1 - (2 * u) ** 2) * (1 - (2 * w2) ** 2)    # silk canopy, gently domed
    MU.solidify(canopy, 0.003)
    _paint(canopy, Pl.s("kumkum"), 0.35)
    MU.paint_corners(canopy, lambda co, n: (Pl.m("gold"), 0.7, 0.3, 3)
                     if abs(co.x) > width / 2 - 0.004 or abs(co.y) > depth / 2 - 0.004 else None)
    parts.append(canopy)
    kalasa = MU.lathe("man_finial", [(0.0, 0.0), (0.014, 0.0), (0.018, 0.012), (0.01, 0.024), (0.004, 0.036),
                                     (0.0, 0.042)], 16, screw=False)
    kalasa.scale = (0.6, 0.6, 0.45)
    kalasa.location = (0, 0, height + 0.018 + 0.012)
    parts.append(_paint(kalasa, Pl.m("gold"), 0.3, kind=3, metal=0.7))
    for side in range(4):   # scalloped silk valance hanging from the canopy edge
        along = width + 0.05 if side < 2 else depth + 0.05
        n = 10 if side < 2 else 6
        vl = MU.grid(f"man_valance{side}", along, 0.03, n * 4, 3)
        for v in vl.data.vertices:
            t = (v.co.x / along + 0.5) * n
            frac = (0.015 - v.co.y) / 0.03                       # 0 at the canopy edge, 1 at the hem
            v.co.z = -frac * (0.018 + 0.01 * abs(math.sin(math.pi * t)))
            v.co.y = 0.0
        MU.solidify(vl, 0.002)
        _paint(vl, Pl.s("kumkum"), 0.35)
        MU.paint_corners(vl, lambda co, n_: (Pl.m("gold"), 0.7, 0.3, 3) if co.z > -0.006 else None)
        if side < 2:
            vl.location = (0, (-1 if side == 0 else 1) * (depth + 0.05) / 2, height + 0.019)
        else:
            vl.rotation_euler = (0, 0, math.pi / 2)
            vl.location = ((-1 if side == 2 else 1) * (width + 0.05) / 2, 0, height + 0.019)
        parts.append(vl)
    for i in range(14):   # tassels and marigold drops along the front beam
        x = -width / 2 + (i + 0.5) * width / 14
        drop = MU.uv_sphere(f"man_tassel{i}", 0.005, 8, 6, scale=(1, 1, 1.3))
        drop.location = (x, -depth / 2 - 0.006, height + 0.004 - 0.003 * (i % 2))   # above the couple's sight line
        parts.append(_paint(drop, Pl.m("marigold-orange") if i % 2 else Pl.m("gold"), 0.45))
    pts = swag_path(-width / 2, width / 2, -depth / 2 - 0.01, height + 0.006, 0.012, 3)
    for k, q in enumerate(pts[::2]):
        f = MU.ico_sphere(f"man_gar{k}", 0.007, 1)
        f.location = q
        parts.append(_paint(f, Pl.m("marigold-orange") if k % 3 else Pl.m("jasmine"), 0.5))
    return _finish(parts, "wedding_mandapam")


def build_thinai_field(Pl: _Pal, rng, width: float = 0.34, depth: float = 0.22) -> bpy.types.Object:
    """Foxtail-millet field (thinaipunam): soil bed with drooping golden panicles."""
    soil = MU.box("thinai_soil", (width, depth, 0.012), (0, 0, 0.006), bevel=0.004)
    _paint(soil, (0.2, 0.11, 0.05), 0.8)
    parts = [soil]
    for i in range(90):
        x = rng.uniform(-width / 2 + 0.01, width / 2 - 0.01)
        y = rng.uniform(-depth / 2 + 0.01, depth / 2 - 0.01)
        h = rng.uniform(0.09, 0.15)
        lean = rng.uniform(-0.25, 0.25)
        sgn = 1 if lean > 0 else -1
        top = Vector((x + lean * 0.05, y, h))
        stalk = MU.tube(f"thinai_st{i}", [Vector((x, y, 0.01)), Vector((x + lean * 0.02, y, h * 0.6)), top], 0.0012)
        head = MU.tube(f"thinai_hd{i}", [top, top + Vector((0.012 * sgn, 0, -0.006)),
                                         top + Vector((0.02 * sgn, 0, -0.025))], 0.0045, radii=[0.7, 1, 0.5])
        parts += [_paint(stalk, Pl.m("mango-leaf"), 0.5), _paint(head, Pl.s("turmeric"), 0.6)]
        if i % 3 == 0:
            lf = A.leaf_shell(f"thinai_lf{i}", 0.06, 0.008, cup=0.1)
            lf.rotation_euler = (rng.uniform(0.5, 1.0), 0, rng.uniform(0, 6.28))
            lf.location = (x, y, h * 0.35)
            parts.append(_paint(lf, Pl.m("mango-leaf"), 0.45))
    return _finish(parts, "thinai_field")


def build_chettiar_shop(Pl: _Pal, rng, width: float = 0.4, depth: float = 0.26) -> tuple[bpy.types.Object, float]:
    """The Chettiar stall: raised floor the couple sit on, sacks in front, back shelves of tiny jars."""
    floor_h = 0.03
    parts = []
    floor = MU.box("shop_floor", (width, depth, floor_h), (0, 0, floor_h / 2), bevel=0.003)
    parts.append(_paint(floor, Pl.s("khaki"), 0.55))
    shelf_cols = [Pl.s("kumkum"), Pl.s("turmeric"), Pl.s("parrot-green"), Pl.s("brinjal"), Pl.s("ivory")]
    for k in range(3):
        sh = MU.box(f"shop_shelf{k}", (width, 0.04, 0.005), (0, depth / 2 - 0.02, 0.07 + k * 0.06))
        parts.append(_paint(sh, Pl.s("khaki"), 0.55))
        for j in range(10):
            jar = MU.lathe(f"shop_jar{k}{j}", [(0.0, 0.0), (0.009, 0.0), (0.011, 0.018), (0.007, 0.03),
                                               (0.008, 0.034), (0.0, 0.034)], 12, screw=False)
            _paint(jar, (0.75, 0.82, 0.8), 0.15)
            MU.paint_corners(jar, lambda co, n, c=shelf_cols[(j + k) % 5]: (c, 0.0, 0.4, 6) if co.z < 0.022 else None)
            jar.location = (-width / 2 + 0.02 + j * (width - 0.04) / 9, depth / 2 - 0.02, 0.073 + k * 0.06)
            parts.append(jar)
    back = MU.box("shop_back", (width, 0.01, 0.24), (0, depth / 2, 0.12))
    parts.append(_paint(back, Pl.s("maroon"), 0.5))
    for sx in (-1, 1):
        post = MU.box(f"shop_post{sx}", (0.012, 0.012, 0.3), (sx * width / 2, -depth / 2 + 0.01, 0.15))
        parts.append(_paint(post, Pl.s("khaki"), 0.5))
    awning = MU.box("shop_awning", (width + 0.04, depth + 0.06, 0.008), (0, 0, 0), bevel=0.002)
    _paint(awning, Pl.s("kumkum"), 0.5)
    MU.paint_corners(awning, lambda co, n: (Pl.s("white"), 0.0, 0.5, 6) if int((co.x + 1) * 25) % 2 == 0 else None)
    awning.rotation_euler = (math.radians(-10), 0, 0)
    awning.location = (0, 0, 0.3)
    parts.append(awning)
    grains = [Pl.s("ivory"), Pl.s("turmeric"), Pl.s("kumkum"), Pl.s("khaki"), (0.3, 0.15, 0.05), Pl.s("ivory")]
    for i in range(6):
        x = -width / 2 + 0.04 + i * (width - 0.08) / 5
        sack = MU.lathe(f"shop_sack{i}", [(0.0, 0.0), (0.022, 0.0), (0.026, 0.02), (0.024, 0.04), (0.027, 0.046),
                                          (0.0, 0.044)], 16, screw=False)
        _paint(sack, Pl.s("khaki"), 0.75)
        MU.paint_corners(sack, lambda co, n, c=grains[i]: (c, 0.0, 0.7, 6) if co.z > 0.042 else None)
        sack.location = (x, -depth / 2 + 0.035, 0.0)
        parts.append(sack)
    return _finish(parts, "chettiar_shop"), floor_h


def build_drying_pots(Pl: _Pal, rng) -> bpy.types.Object:
    parts = []
    for i in range(7):
        s = rng.uniform(0.7, 1.15)
        prof = [(0.0, 0.0), (0.012 * s, 0.0), (0.024 * s, 0.018 * s), (0.026 * s, 0.03 * s), (0.016 * s, 0.045 * s),
                (0.018 * s, 0.05 * s), (0.0, 0.048 * s)]
        pot = MU.lathe(f"dpot{i}", prof, 18, screw=False)
        pot.location = ((i % 4) * 0.05 - 0.075, (i // 4) * 0.05, 0)
        parts.append(_paint(pot, Pl.m("terracotta"), 0.75))
    return _finish(parts, "drying_pots")


def build_kaliya(Pl: _Pal, rng) -> tuple[bpy.types.Object, float]:
    """Yamuna pool with the coiled serpent Kaliya: four hooded necks rise around Krishna, who dances on the
    broad central hood (painted dark peacock-blue with scales, turmeric belly and spectacle marks)."""
    serp = tuple(c * 0.42 for c in Pl.s("peacock-blue"))
    belly = Pl.s("turmeric")
    pool = MU.cylinder("kaliya_pool", 0.15, 0.012, 48, center=(0, 0, 0.006))
    _paint(pool, (0.03, 0.12, 0.25), 0.08)
    MU.paint_corners(pool, lambda co, n: ((0.12, 0.3, 0.45), 0.0, 0.08, 6)
                     if math.sin(math.hypot(co.x, co.y) * 160) > 0.7 and co.z > 0.01 else None)
    parts = [pool]

    def scaled(ob, neck: bool = False):
        _paint(ob, serp, 0.3, kind=7)
        if neck:     # narrow belly stripe down the front of a raised neck
            MU.paint_corners(ob, lambda co, n: (belly, 0.0, 0.35, 6) if n.y < -0.9 else None)
        else:        # coiled body: belly scutes on the underside only
            MU.paint_corners(ob, lambda co, n: (belly, 0.0, 0.35, 6) if n.z < -0.45 else None)
        return ob

    coil = [p + Vector((0, 0, 0.015)) for p in MU.spiral_points(0.09, 0.03, 1.6, 0.05, 60)]
    radii = [0.5 + 0.5 * t / 60 for t in range(61)] + [1.0]
    parts.append(scaled(MU.tube("kaliya_body", coil + [Vector((0.0, 0.0, 0.11))], 0.018, radii=radii)))
    tail = MU.tube("kaliya_tail", [Vector((0.1, -0.02, 0.02)), Vector((0.13, -0.05, 0.03)),
                                   Vector((0.14, -0.08, 0.05))], 0.008, radii=[1.0, 0.6, 0.25])
    parts.append(scaled(tail))

    def hood(name, base: Vector, top: Vector, size: float, yaw: float):
        neck = MU.tube(f"{name}_neck", [base, base.lerp(top, 0.5) + Vector((0, 0.01, 0)), top], 0.011 * size / 0.06,
                       radii=[1.0, 0.85, 0.75])
        parts.append(scaled(neck, neck=True))
        sh = A.leaf_shell(f"{name}_hood", size, size * 0.85, cup=0.45, tip_pointed=False)
        _paint(sh, serp, 0.3, kind=7)
        # spectacle mark on the hood front (cupped toward −Y), turmeric
        MU.paint_corners(sh, lambda co, n: (belly, 0.0, 0.35, 6)
                         if abs(math.hypot(abs(co.x) - size * 0.13, co.z - size * 0.55) - size * 0.08) < size * 0.025
                         else None)
        sh.rotation_euler = (0.15, 0, yaw)
        sh.location = top - Vector((0, 0, size * 0.25))
        parts.append(sh)
        head = MU.uv_sphere(f"{name}_head", size * 0.17, 10, 6, scale=(1, 1.3, 0.8))
        head.location = top + Vector((-math.sin(yaw) * 0.0, -size * 0.2, size * 0.42))
        parts.append(_paint(head, serp, 0.3))
        for e in (-1, 1):
            eye = MU.uv_sphere(f"{name}_eye{e}", size * 0.04, 6, 4)
            eye.location = head.location + Vector((e * size * 0.08, -size * 0.18, size * 0.04))
            parts.append(_paint(eye, Pl.s("kumkum"), 0.2))

    for i, (x, y, h, yaw) in enumerate(((-0.075, 0.025, 0.2, 0.35), (-0.04, 0.05, 0.245, 0.15),
                                       (0.04, 0.05, 0.245, -0.15), (0.075, 0.025, 0.2, -0.35))):
        hood(f"kaliya_h{i}", Vector((x * 0.4, y * 0.3, 0.09)), Vector((x, y, h)), 0.06, yaw)
    # broad central hood: the serpent's head under Krishna's dancing foot
    crown = MU.uv_sphere("kaliya_crown", 0.05, 24, 12, scale=(1.0, 0.8, 0.28))
    crown.location = (0.0, -0.012, 0.155)
    _paint(crown, serp, 0.3, kind=7)
    MU.paint_corners(crown, lambda co, n: (belly, 0.0, 0.35, 6)
                     if n.z > 0.6 and math.hypot(co.x, co.y + 0.012) < 0.022 else None)
    neck = MU.tube("kaliya_neck", [Vector((0.0, 0.0, 0.1)), Vector((0.0, -0.01, 0.15))], 0.022)
    parts += [crown, scaled(neck, neck=True)]
    return _finish(parts, "kaliya"), 0.168


def build_govardhana(Pl: _Pal, rng, width: float = 0.28) -> bpy.types.Object:
    """Govardhana hill held aloft: a lumpy dome with rock outcrops and tree clumps, matte-painted (kind 5)."""
    R = width / 2
    hill = MU.ico_sphere("govardhana", R, 4)
    MU.displace(hill, MU.texture("tx_gov", "CLOUDS", noise_scale=0.05, noise_depth=3), 0.045)
    for v in hill.data.vertices:
        v.co.z = v.co.z * 0.55 if v.co.z > 0 else v.co.z * 0.22
    green, dgreen = (0.16, 0.3, 0.07), (0.08, 0.18, 0.05)
    rock, under = (0.36, 0.27, 0.18), (0.3, 0.22, 0.14)

    def hill_paint(co, n):
        if n.z < -0.25:
            return (under, 0.0, 0.85, 5)
        band = math.sin(co.x * 70 + math.sin(co.y * 50) * 2.0) * math.sin(co.y * 60)
        if n.z < 0.35 and band > 0.1:
            return (rock, 0.0, 0.85, 5)
        return ((dgreen if band > 0.45 else green), 0.0, 0.8, 5)

    _paint(hill, green, 0.8, kind=5)
    MU.paint_corners(hill, hill_paint)
    parts = [hill]

    def surface_z(r):
        return R * 0.55 * math.sqrt(max(0.0, 1 - (r / R) ** 2))

    for i in range(9):                       # rock outcrops
        a, r = rng.uniform(0, math.tau), rng.uniform(R * 0.35, R * 0.85)
        x, y = math.cos(a) * r, math.sin(a) * r
        rk = MU.ico_sphere(f"gov_rock{i}", rng.uniform(0.014, 0.024), 1)
        rk.scale = (1.0, rng.uniform(0.7, 1.0), rng.uniform(0.6, 0.9))
        rk.location = (x, y, surface_z(r) - 0.004)
        parts.append(_paint(rk, tuple(c * rng.uniform(0.85, 1.15) for c in rock), 0.85, kind=5))
    for i in range(11):                      # tree clumps: trunk + three foliage balls
        a, r = rng.uniform(0, math.tau), rng.uniform(0, R * 0.7)
        x, y = math.cos(a) * r, math.sin(a) * r
        z = surface_z(r) - 0.004
        h = rng.uniform(0.025, 0.04)
        trunk = MU.cylinder(f"gov_trunk{i}", 0.0028, h, 6, center=(x, y, z + h / 2))
        parts.append(_paint(trunk, (0.25, 0.15, 0.08), 0.7, kind=5))
        leaf = Pl.m("mango-leaf") if i % 3 else (0.22, 0.34, 0.08)
        for k in range(3):
            b = MU.ico_sphere(f"gov_tree{i}_{k}", rng.uniform(0.011, 0.015), 1)
            b.location = (x + rng.uniform(-0.009, 0.009), y + rng.uniform(-0.009, 0.009), z + h + rng.uniform(-0.004, 0.008))
            parts.append(_paint(b, tuple(c * rng.uniform(0.8, 1.1) for c in leaf), 0.75, kind=5))
    return _finish(parts, "govardhana_hill")
