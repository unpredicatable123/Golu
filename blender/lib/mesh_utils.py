"""Geometry helpers shared by every builder (headless-safe; no UI-context operators except join)."""
from __future__ import annotations

import math
from typing import Any, Callable, Iterable, Sequence

import bmesh
import bpy
from mathutils import Matrix, Vector

RGB = tuple[float, float, float]

# --------------------------------------------------------------------------- collections & objects


def ensure_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if col.name not in parent.children and col != parent:
        try:
            parent.children.link(col)
        except RuntimeError:
            pass
    return col


def link(obj: bpy.types.Object, collection: bpy.types.Collection | None) -> bpy.types.Object:
    collection = collection or bpy.context.scene.collection
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    return obj


def new_mesh_object(name: str, verts: Sequence, faces: Sequence, collection=None, edges: Sequence = ()) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], list(edges), [tuple(f) for f in faces])
    me.validate(clean_customdata=False)
    me.update()
    return link(bpy.data.objects.new(name, me), collection)


def bmesh_to_object(bm: bmesh.types.BMesh, name: str, collection=None) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return link(bpy.data.objects.new(name, me), collection)


def delete_object(obj: bpy.types.Object) -> None:
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and getattr(data, "users", 1) == 0:
        if isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
        elif isinstance(data, bpy.types.Curve):
            bpy.data.curves.remove(data)
        elif isinstance(data, bpy.types.MetaBall):
            bpy.data.metaballs.remove(data)


# --------------------------------------------------------------------------- modifiers


def depsgraph() -> bpy.types.Depsgraph:
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    return dg


def apply_all_modifiers(obj: bpy.types.Object) -> None:
    """Bake the evaluated mesh into obj.data and clear its modifiers (works for curves/metaballs too)."""
    dg = depsgraph()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    if obj.type == "MESH":
        old = obj.data
        obj.modifiers.clear()
        obj.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)
    else:
        raise TypeError("apply_all_modifiers only for meshes; use convert_to_mesh for curves/metaballs")


def convert_to_mesh(obj: bpy.types.Object, name: str | None = None) -> bpy.types.Object:
    """Curve/metaball/text → new mesh object at the same transform; the source object is deleted."""
    dg = depsgraph()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    new = bpy.data.objects.new(name or obj.name + "_m", me)
    new.matrix_world = obj.matrix_world.copy()
    cols = list(obj.users_collection) or [bpy.context.scene.collection]
    for c in cols:
        c.objects.link(new)
    delete_object(obj)
    return new


def add_subsurf(obj, viewport: int = 1, render: int = 1) -> bpy.types.Modifier:
    m = obj.modifiers.new("Subsurf", "SUBSURF")
    m.levels = viewport
    m.render_levels = render
    m.quality = 3
    return m


def voxel_remesh(obj, voxel: float, smooth_iters: int = 2, apply: bool = True) -> None:
    m = obj.modifiers.new("Remesh", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    m.adaptivity = 0.0
    m.use_smooth_shade = True
    if smooth_iters:
        s = obj.modifiers.new("Smooth", "LAPLACIANSMOOTH")
        s.iterations = smooth_iters
        s.lambda_factor = 0.6
        s.use_volume_preserve = True
    if apply:
        apply_all_modifiers(obj)


def solidify(obj, thickness: float, offset: float = -1.0, apply: bool = True) -> None:
    m = obj.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness = thickness
    m.offset = offset
    m.use_even_offset = True
    m.use_quality_normals = True
    if apply:
        apply_all_modifiers(obj)


def displace(obj, tex: bpy.types.Texture, strength: float, mid: float = 0.5, vgroup: str | None = None,
             direction: str = "NORMAL", coords: str = "LOCAL", apply: bool = True) -> None:
    m = obj.modifiers.new("Displace", "DISPLACE")
    m.texture = tex
    m.strength = strength
    m.mid_level = mid
    m.direction = direction
    m.texture_coords = coords
    if vgroup:
        m.vertex_group = vgroup
    if apply:
        apply_all_modifiers(obj)


def texture(name: str, kind: str, **props) -> bpy.types.Texture:
    """Legacy texture datablock for Displace modifiers (CLOUDS, WOOD, VORONOI, STUCCI, MUSGRAVE...)."""
    tex = bpy.data.textures.get(name) or bpy.data.textures.new(name, kind)
    for k, v in props.items():
        setattr(tex, k, v)
    return tex


def simple_deform(obj, mode: str, angle_or_factor: float, axis: str = "Z", origin: bpy.types.Object | None = None,
                  apply: bool = True) -> None:
    m = obj.modifiers.new("Deform", "SIMPLE_DEFORM")
    m.deform_method = mode
    if mode in ("BEND", "TWIST"):
        m.angle = angle_or_factor
    else:
        m.factor = angle_or_factor
    m.deform_axis = axis
    if origin:
        m.origin = origin
    if apply:
        apply_all_modifiers(obj)


def shade_smooth(obj, sharp_angle_deg: float | None = 35.0) -> None:
    me = obj.data
    me.shade_smooth()
    if sharp_angle_deg is not None and hasattr(me, "set_sharp_from_angle"):
        me.set_sharp_from_angle(angle=math.radians(sharp_angle_deg))


def shade_flat(obj) -> None:
    obj.data.shade_flat()


# --------------------------------------------------------------------------- lathe / primitives


def lathe_bm(profile: Sequence[tuple[float, float]], segments: int = 48) -> bmesh.types.BMesh:
    """Spin an (r, z) profile 360° around Z. Points with r≈0 are merged onto the axis."""
    bm = bmesh.new()
    verts = [bm.verts.new((max(r, 0.0), 0.0, z)) for r, z in profile]
    for a, b in zip(verts, verts[1:]):
        bm.edges.new((a, b))
    geom = list(bm.verts) + list(bm.edges)
    bmesh.ops.spin(bm, geom=geom, cent=(0, 0, 0), axis=(0, 0, 1), angle=math.tau, steps=segments,
                   use_merge=True, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def lathe(name: str, profile: Sequence[tuple[float, float]], segments: int = 48, collection=None,
          smooth: bool = True, screw: bool = True) -> bpy.types.Object:
    """Lathe via the Screw modifier (SPEC §4.2) from a profile polyline in the XZ plane."""
    if not screw:
        obj = bmesh_to_object(lathe_bm(profile, segments), name, collection)
    else:
        verts = [(max(r, 0.0), 0.0, z) for r, z in profile]
        edges = [(i, i + 1) for i in range(len(verts) - 1)]
        obj = new_mesh_object(name, verts, [], collection, edges)
        m = obj.modifiers.new("Screw", "SCREW")
        m.axis = "Z"
        m.angle = math.tau
        m.steps = segments
        m.render_steps = segments
        m.use_merge_vertices = True
        m.merge_threshold = 1e-5
        m.use_normal_calculate = True
        m.use_smooth_shade = smooth
        apply_all_modifiers(obj)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
        bm.free()
    if smooth:
        shade_smooth(obj, 50)
    return obj


def uv_sphere(name: str, radius: float, segments: int = 24, rings: int = 12, collection=None,
              scale: tuple[float, float, float] = (1, 1, 1)) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    obj = bmesh_to_object(bm, name, collection)
    shade_smooth(obj, None)
    return obj


def ico_sphere(name: str, radius: float, subdiv: int = 2, collection=None) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    obj = bmesh_to_object(bm, name, collection)
    shade_smooth(obj, None)
    return obj


def box(name: str, size: tuple[float, float, float], center: tuple[float, float, float] = (0, 0, 0),
        collection=None, bevel: float = 0.0, bevel_segments: int = 2) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=bevel_segments,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    obj = bmesh_to_object(bm, name, collection)
    if bevel > 0:
        shade_smooth(obj, 40)
    return obj


def cylinder(name: str, radius: float, depth: float, segments: int = 24, collection=None,
             center: tuple[float, float, float] = (0, 0, 0), radius_top: float | None = None) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=radius,
                          radius2=radius if radius_top is None else radius_top, depth=depth)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    obj = bmesh_to_object(bm, name, collection)
    shade_smooth(obj, 40)
    return obj


def torus(name: str, major: float, minor: float, major_seg: int = 32, minor_seg: int = 10, collection=None) -> bpy.types.Object:
    verts, faces = [], []
    for i in range(major_seg):
        a = i / major_seg * math.tau
        for j in range(minor_seg):
            b = j / minor_seg * math.tau
            r = major + minor * math.cos(b)
            verts.append((r * math.cos(a), r * math.sin(a), minor * math.sin(b)))
    for i in range(major_seg):
        for j in range(minor_seg):
            a = i * minor_seg + j
            b = ((i + 1) % major_seg) * minor_seg + j
            c = ((i + 1) % major_seg) * minor_seg + (j + 1) % minor_seg
            d = i * minor_seg + (j + 1) % minor_seg
            faces.append((a, b, c, d))
    obj = new_mesh_object(name, verts, faces, collection)
    shade_smooth(obj, None)
    return obj


def grid(name: str, size_x: float, size_y: float, nx: int, ny: int, collection=None) -> bpy.types.Object:
    verts = [((i / nx - 0.5) * size_x, (j / ny - 0.5) * size_y, 0.0) for j in range(ny + 1) for i in range(nx + 1)]
    faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i)
             for j in range(ny) for i in range(nx)]
    obj = new_mesh_object(name, verts, faces, collection)
    uv = obj.data.uv_layers.new(name="UVMap")
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            co = obj.data.vertices[obj.data.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / size_x + 0.5, co.y / size_y + 0.5)
    return obj


# --------------------------------------------------------------------------- metaballs

class MetaElem:
    __slots__ = ("kind", "co", "radius", "size", "rot", "stiffness", "negative")

    def __init__(self, kind: str, co, radius: float, size=(0.0, 0.0, 0.0), rot: Any = None,
                 stiffness: float = 2.0, negative: bool = False):
        self.kind, self.co, self.radius, self.size = kind, Vector(co), radius, size
        self.rot, self.stiffness, self.negative = rot, stiffness, negative


def capsule_between(a: Vector, b: Vector, radius: float, stiffness: float = 2.0) -> MetaElem:
    """Metaball CAPSULE spanning segment a→b (size_x is the half-length)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    length = d.length
    rot = Vector((1, 0, 0)).rotation_difference(d.normalized() if length > 1e-9 else Vector((1, 0, 0)))
    return MetaElem("CAPSULE", (a + b) / 2, radius, (length / 2, 0, 0), rot, stiffness)


def metaball_object(name: str, elements: Iterable[MetaElem], resolution: float, collection=None) -> bpy.types.Object:
    """Unique base name per call — Blender fuses metaballs whose names share a base (family gotcha)."""
    mb = bpy.data.metaballs.new(name)
    mb.resolution = resolution
    mb.render_resolution = resolution
    mb.threshold = 0.6
    for e in elements:
        el = mb.elements.new(type=e.kind)
        el.co = e.co
        el.radius = e.radius
        el.stiffness = e.stiffness
        el.use_negative = e.negative
        if e.kind in ("CAPSULE", "PLANE", "ELLIPSOID", "CUBE"):
            el.size_x = max(e.size[0], 1e-5)
            el.size_y = max(e.size[1], 1e-5)
            el.size_z = max(e.size[2], 1e-5)
        if e.rot is not None:
            el.rotation = e.rot
    return link(bpy.data.objects.new(name, mb), collection)


def metaball_to_mesh(mb_obj: bpy.types.Object, name: str) -> bpy.types.Object:
    return convert_to_mesh(mb_obj, name)


# --------------------------------------------------------------------------- curves


def curve_object(name: str, points: Sequence, bevel: float = 0.0, resolution: int = 12, cyclic: bool = False,
                 radii: Sequence[float] | None = None, collection=None, kind: str = "POLY",
                 bevel_resolution: int = 4, fill_caps: bool = True, tilts: Sequence[float] | None = None) -> bpy.types.Object:
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = resolution
    cu.bevel_depth = bevel
    cu.bevel_resolution = bevel_resolution
    cu.use_fill_caps = fill_caps
    if kind == "BEZIER":
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(points) - 1)
        for i, p in enumerate(points):
            bp = sp.bezier_points[i]
            bp.co = Vector(p)
            bp.handle_left_type = bp.handle_right_type = "AUTO"
            if radii:
                bp.radius = radii[i]
            if tilts:
                bp.tilt = tilts[i]
    else:
        sp = cu.splines.new("NURBS" if kind == "NURBS" else "POLY")
        sp.points.add(len(points) - 1)
        for i, p in enumerate(points):
            sp.points[i].co = (*Vector(p), 1.0)
            if radii:
                sp.points[i].radius = radii[i]
            if tilts:
                sp.points[i].tilt = tilts[i]
        if kind == "NURBS":
            sp.order_u = min(4, len(points))
            sp.use_endpoint_u = True
    sp.use_cyclic_u = cyclic
    return link(bpy.data.objects.new(name, cu), collection)


def tube(name: str, points: Sequence, radius: float, radii: Sequence[float] | None = None, collection=None,
         resolution: int = 8, bevel_resolution: int = 3, cyclic: bool = False) -> bpy.types.Object:
    """Smooth tapered tube along points → mesh."""
    obj = curve_object(name + "_c", points, bevel=radius, resolution=resolution, cyclic=cyclic, radii=radii,
                       collection=collection, kind="BEZIER", bevel_resolution=bevel_resolution)
    m = convert_to_mesh(obj, name)
    shade_smooth(m, None)
    return m


def catenary(p0, p1, sag: float, n: int) -> list[Vector]:
    p0, p1 = Vector(p0), Vector(p1)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = p0.lerp(p1, t)
        p.z -= sag * 4 * t * (1 - t) * (1 - 0.15 * (2 * t - 1) ** 2)
        pts.append(p)
    return pts


def spiral_points(r0: float, r1: float, turns: float, height: float, n: int) -> list[Vector]:
    return [Vector(((r0 + (r1 - r0) * t) * math.cos(t * turns * math.tau),
                    (r0 + (r1 - r0) * t) * math.sin(t * turns * math.tau), height * t))
            for t in (i / n for i in range(n + 1))]


# --------------------------------------------------------------------------- joining, attributes, transforms


def join(objs: list[bpy.types.Object], name: str) -> bpy.types.Object:
    """Join objects into objs[0] (renamed). Attributes absent on some parts get default values."""
    objs = [o for o in objs if o is not None]
    if len(objs) == 1:
        objs[0].name = name
        objs[0].data.name = name
        return objs[0]
    target = objs[0]
    for o in objs:
        if not o.users_collection:
            bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    with bpy.context.temp_override(active_object=target, object=target, selected_objects=objs,
                                   selected_editable_objects=objs):
        bpy.ops.object.join()
    target.name = name
    target.data.name = name
    return target


def apply_transform(obj: bpy.types.Object) -> None:
    obj.data.transform(obj.matrix_basis)
    obj.matrix_basis = Matrix.Identity(4)


def transform(obj: bpy.types.Object, mat: Matrix) -> bpy.types.Object:
    obj.data.transform(mat)
    obj.data.update()
    return obj


def bounds_world(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def bounds_local(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    vs = [v.co for v in obj.data.vertices]
    if not vs:
        return Vector(), Vector()
    return (Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))),
            Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs))))


def set_origin_bottom_center(obj: bpy.types.Object) -> None:
    lo, hi = bounds_local(obj)
    off = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    obj.data.transform(Matrix.Translation(-off))
    obj.location += obj.matrix_world.to_3x3() @ off


def _ensure_attr(me, name: str, dtype: str, domain: str = "CORNER"):
    a = me.attributes.get(name)
    if a is None or a.data_type != dtype or a.domain != domain:
        if a is not None:
            me.attributes.remove(a)
        a = me.attributes.new(name, dtype, domain)
    return a


def set_part_attributes(obj: bpy.types.Object, paint: Sequence[float], metal: float, rough: float, kind: int,
                        zari: int = 0, garment_uv: tuple[float, float] | None = None) -> None:
    """Write the four doll-shader attributes on every corner (PLAN §1.3)."""
    me = obj.data
    n = len(me.loops)
    p = _ensure_attr(me, "paint", "FLOAT_COLOR")
    rgba = (paint[0], paint[1], paint[2], 1.0)
    p.data.foreach_set("color", rgba * n)
    b = _ensure_attr(me, "pbr", "FLOAT_VECTOR")
    b.data.foreach_set("vector", (metal, rough, float(kind)) * n)
    z = _ensure_attr(me, "zari", "FLOAT")
    z.data.foreach_set("value", (float(zari),) * n)
    if garment_uv is None or not me.attributes.get("garment_uv"):
        g = _ensure_attr(me, "garment_uv", "FLOAT2")
        g.data.foreach_set("vector", (garment_uv or (-1.0, -1.0)) * n)


def set_garment_uv(obj: bpy.types.Object, fn: Callable[[Vector], tuple[float, float]]) -> None:
    """Per-corner garment UV computed from the vertex position (u around, v along)."""
    me = obj.data
    g = _ensure_attr(me, "garment_uv", "FLOAT2")
    vals = []
    for loop in me.loops:
        u, v = fn(me.vertices[loop.vertex_index].co)
        vals.extend((u, v))
    g.data.foreach_set("vector", vals)


def paint_corners(obj: bpy.types.Object, fn: Callable[[Vector, Vector], tuple | None]) -> None:
    """Override paint/pbr per corner. fn(co, normal) → None or (rgb, metal, rough, kind)."""
    me = obj.data
    p = me.attributes["paint"]
    b = me.attributes["pbr"]
    cols = [0.0] * (len(me.loops) * 4)
    pbrs = [0.0] * (len(me.loops) * 3)
    p.data.foreach_get("color", cols)
    b.data.foreach_get("vector", pbrs)
    for li, loop in enumerate(me.loops):
        v = me.vertices[loop.vertex_index]
        r = fn(v.co, v.normal)
        if r is not None:
            rgb, metal, rough, kind = r
            cols[li * 4:li * 4 + 3] = rgb
            pbrs[li * 3:li * 3 + 3] = (metal, rough, float(kind))
    p.data.foreach_set("color", cols)
    b.data.foreach_set("vector", pbrs)


def set_uv_from(obj: bpy.types.Object, fn: Callable[[Vector], tuple[float, float]], name: str = "UVMap") -> None:
    me = obj.data
    uv = me.uv_layers.get(name) or me.uv_layers.new(name=name)
    for loop in me.loops:
        uv.data[loop.index].uv = fn(me.vertices[loop.vertex_index].co)


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material, clear: bool = True) -> None:
    if clear:
        obj.data.materials.clear()
    obj.data.materials.append(mat)


# --------------------------------------------------------------------------- geometry nodes scatter


def _gn_new(name: str) -> bpy.types.NodeTree:
    tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
    tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    return tree


def _node(tree, kind: str, loc=(0, 0), **inputs):
    n = tree.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        if k.startswith("_"):
            setattr(n, k[1:], v)
        else:
            n.inputs[k].default_value = v
    return n


def scatter_tree(name: str, seed: int, *, source: str, collection: bpy.types.Collection,
                 density: float = 1000.0, min_dist: float = 0.01, spacing: float = 0.02,
                 scale_range: tuple[float, float] = (0.9, 1.1), align_to_normal: bool = True,
                 random_rot: tuple[float, float, float] = (0.0, 0.0, math.tau),
                 pattern: tuple[int, int, int, int] | None = None, keep_source: bool = False,
                 offset_along_normal: float = 0.0) -> bpy.types.NodeTree:
    """GN instancing (DECISIONS D21).

    source="faces": Distribute Points on Faces (Poisson) on the object surface.
    source="curve": Curve to Points every `spacing` metres, instances aligned to the curve.
    pattern=(n_a, n_b, count_a, count_b): along the index, n_a instances picked from the first count_a
    collection children then n_b from the next count_b (e.g. 6 marigolds : 3 jasmine).
    """
    tree = _gn_new(name)
    nd = tree.nodes
    lk = tree.links
    gin = nd.new("NodeGroupInput")
    gin.location = (-1200, 0)
    gout = nd.new("NodeGroupOutput")
    gout.location = (900, 0)

    if source == "faces":
        dist = _node(tree, "GeometryNodeDistributePointsOnFaces", (-900, 0))
        dist.distribute_method = "POISSON"
        dist.inputs["Distance Min"].default_value = min_dist
        dist.inputs["Density Max"].default_value = density
        dist.inputs["Seed"].default_value = seed % 100000
        lk.new(gin.outputs[0], dist.inputs["Mesh"])
        pts = dist.outputs["Points"]
        if align_to_normal:
            align = _node(tree, "FunctionNodeAlignRotationToVector", (-650, -200))
            align.axis = "Z"
            lk.new(dist.outputs["Normal"], align.inputs["Vector"])
            base_rot = align.outputs["Rotation"]
        else:
            base_rot = None
        if offset_along_normal:
            sp = _node(tree, "GeometryNodeSetPosition", (-650, 100))
            nrm = _node(tree, "GeometryNodeInputNormal", (-900, 250))
            sc = _node(tree, "ShaderNodeVectorMath", (-800, 250), _operation="SCALE")
            sc.inputs[3].default_value = offset_along_normal
            lk.new(nrm.outputs[0], sc.inputs[0])
            lk.new(pts, sp.inputs["Geometry"])
            lk.new(sc.outputs[0], sp.inputs["Offset"])
            pts = sp.outputs[0]
    else:
        c2p = _node(tree, "GeometryNodeCurveToPoints", (-900, 0))
        c2p.mode = "LENGTH"
        c2p.inputs["Length"].default_value = spacing
        lk.new(gin.outputs[0], c2p.inputs["Curve"])
        pts = c2p.outputs["Points"]
        base_rot = c2p.outputs["Rotation"]

    col = _node(tree, "GeometryNodeCollectionInfo", (-650, 300))
    col.inputs["Collection"].default_value = collection
    col.inputs["Separate Children"].default_value = True
    col.inputs["Reset Children"].default_value = True
    col.transform_space = "ORIGINAL"

    inst = _node(tree, "GeometryNodeInstanceOnPoints", (-200, 0))
    lk.new(pts, inst.inputs["Points"])
    lk.new(col.outputs[0], inst.inputs["Instance"])
    inst.inputs["Pick Instance"].default_value = True

    n_children = len(collection.all_objects)
    if pattern:
        na, nb, ca, cb = pattern
        idx = _node(tree, "GeometryNodeInputIndex", (-1000, -500))
        mod = _node(tree, "ShaderNodeMath", (-850, -500), _operation="FLOORED_MODULO")
        mod.inputs[1].default_value = na + nb
        lk.new(idx.outputs[0], mod.inputs[0])
        cmp = _node(tree, "FunctionNodeCompare", (-700, -500))
        cmp.data_type = "FLOAT"
        cmp.operation = "LESS_THAN"
        cmp.inputs[1].default_value = na
        lk.new(mod.outputs[0], cmp.inputs[0])
        ra = _node(tree, "FunctionNodeRandomValue", (-700, -650), _data_type="INT")
        ra.inputs["Min"].default_value = 0
        ra.inputs["Max"].default_value = ca - 1
        ra.inputs["Seed"].default_value = seed % 9973
        rb = _node(tree, "FunctionNodeRandomValue", (-700, -800), _data_type="INT")
        rb.inputs["Min"].default_value = ca
        rb.inputs["Max"].default_value = ca + cb - 1
        rb.inputs["Seed"].default_value = (seed + 7) % 9973
        sw = _node(tree, "GeometryNodeSwitch", (-450, -600), _input_type="INT")
        lk.new(cmp.outputs[0], sw.inputs["Switch"])
        lk.new(ra.outputs[2] if len(ra.outputs) > 2 else ra.outputs["Value"], sw.inputs["True"])
        lk.new(rb.outputs[2] if len(rb.outputs) > 2 else rb.outputs["Value"], sw.inputs["False"])
        lk.new(sw.outputs[0], inst.inputs["Instance Index"])
    else:
        ri = _node(tree, "FunctionNodeRandomValue", (-450, -500), _data_type="INT")
        ri.inputs["Min"].default_value = 0
        ri.inputs["Max"].default_value = max(0, n_children - 1)
        ri.inputs["Seed"].default_value = seed % 9973
        lk.new(_int_out(ri), inst.inputs["Instance Index"])

    # random extra rotation (euler → rotation, combined with the base alignment)
    rv = _node(tree, "FunctionNodeRandomValue", (-700, -250), _data_type="FLOAT_VECTOR")
    rv.inputs["Min"].default_value = (-random_rot[0] / 2, -random_rot[1] / 2, -random_rot[2] / 2)
    rv.inputs["Max"].default_value = (random_rot[0] / 2, random_rot[1] / 2, random_rot[2] / 2)
    rv.inputs["Seed"].default_value = (seed + 3) % 9973
    e2r = _node(tree, "FunctionNodeEulerToRotation", (-500, -250))
    lk.new(rv.outputs[0], e2r.inputs[0])
    if base_rot is not None:
        rot = _node(tree, "FunctionNodeRotateRotation", (-350, -200))
        rot.rotation_space = "LOCAL"
        lk.new(base_rot, rot.inputs["Rotation"])
        lk.new(e2r.outputs[0], rot.inputs["Rotate By"])
        lk.new(rot.outputs[0], inst.inputs["Rotation"])
    else:
        lk.new(e2r.outputs[0], inst.inputs["Rotation"])

    rs = _node(tree, "FunctionNodeRandomValue", (-450, -380), _data_type="FLOAT")
    rs.inputs[2].default_value = scale_range[0]
    rs.inputs[3].default_value = scale_range[1]
    rs.inputs["Seed"].default_value = (seed + 11) % 9973
    lk.new(_float_out(rs), inst.inputs["Scale"])

    out_geo = inst.outputs[0]
    if keep_source:
        j = _node(tree, "GeometryNodeJoinGeometry", (400, 0))
        lk.new(gin.outputs[0], j.inputs[0])
        lk.new(inst.outputs[0], j.inputs[0])
        out_geo = j.outputs[0]
    lk.new(out_geo, gout.inputs[0])
    return tree


def _int_out(rnd_node):
    for o in rnd_node.outputs:
        if o.type == "INT" and o.enabled:
            return o
    return rnd_node.outputs[2]


def _float_out(rnd_node):
    for o in rnd_node.outputs:
        if o.type == "VALUE" and o.enabled:
            return o
    return rnd_node.outputs[1]


def add_gn_modifier(obj: bpy.types.Object, tree: bpy.types.NodeTree, inputs: dict | None = None) -> bpy.types.Modifier:
    m = obj.modifiers.new(tree.name, "NODES")
    m.node_group = tree
    for k, v in (inputs or {}).items():
        m[k] = v
    return m


def instance_collection(name: str, objs: list[bpy.types.Object], parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    """Hidden collection holding instance sources (excluded from render via a hidden parent)."""
    lib = ensure_collection("_instance_sources", parent or bpy.context.scene.collection)
    lib.hide_render = True
    lib.hide_viewport = True
    col = bpy.data.collections.new(name)
    lib.children.link(col)
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
        o.location = (0, 0, 0)
    return col
