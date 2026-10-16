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
