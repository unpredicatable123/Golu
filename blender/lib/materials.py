"""Shader library (SPEC §4.2/§4.3). Base colours come from the config palette; structure lives here."""
from __future__ import annotations

from typing import Any

import bpy

from . import render as R
from .config import GoluConfig, Palette

_PAL: Palette | None = None
_CACHE: dict[str, bpy.types.Material] = {}


def init(cfg: GoluConfig) -> None:
    global _PAL
    _PAL = cfg.palette
    _CACHE.clear()


def pal() -> Palette:
    if _PAL is None:
        raise RuntimeError("materials.init(cfg) not called")
    return _PAL


def rgba(rgb, a: float = 1.0) -> tuple[float, float, float, float]:
    return (rgb[0], rgb[1], rgb[2], a)


def lift(rgb, k: float):
    return tuple(min(1.0, c * k) for c in rgb)


# =========================================================================== node builder


class NB:
    """Tiny node-graph builder: every method returns an output socket."""

    def __init__(self, tree: bpy.types.NodeTree):
        self.t = tree
        self.n = tree.nodes
        self.l = tree.links
        self.x = 0

    def node(self, kind: str, **props):
        nd = self.n.new(kind)
        nd.location = (self.x, -len(self.n) * 25)
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def _in(self, sock, val):
        if val is None:
            return
        if isinstance(val, bpy.types.NodeSocket):
            self.l.new(val, sock)
        else:
            sock.default_value = val

    def math(self, op: str, a, b=None, c=None, clamp: bool = False):
        nd = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self._in(nd.inputs[0], a)
        if b is not None:
            self._in(nd.inputs[1], b)
        if c is not None:
            self._in(nd.inputs[2], c)
        return nd.outputs[0]

    def add(self, a, b): return self.math("ADD", a, b)
    def sub(self, a, b): return self.math("SUBTRACT", a, b)
    def mul(self, a, b): return self.math("MULTIPLY", a, b)
    def div(self, a, b): return self.math("DIVIDE", a, b)
    def mx(self, a, b): return self.math("MAXIMUM", a, b)
    def mn(self, a, b): return self.math("MINIMUM", a, b)
    def absv(self, a): return self.math("ABSOLUTE", a)
    def sqrt(self, a): return self.math("SQRT", a)
    def pw(self, a, b): return self.math("POWER", a, b)
    def lt(self, a, b): return self.math("LESS_THAN", a, b)
    def gt(self, a, b): return self.math("GREATER_THAN", a, b)
    def cmp(self, a, b, eps): return self.math("COMPARE", a, b, eps)
    def sin(self, a): return self.math("SINE", a)
    def cos(self, a): return self.math("COSINE", a)

    def hypot(self, a, b):
        return self.sqrt(self.add(self.mul(a, a), self.mul(b, b)))

    def vec(self, kind: str, a, b=None, scale=None):
        nd = self.node("ShaderNodeVectorMath", operation=kind)
        self._in(nd.inputs[0], a)
        if b is not None:
            self._in(nd.inputs[1], b)
        if scale is not None:
            self._in(nd.inputs[3], scale)
        return nd.outputs[1] if kind in ("LENGTH", "DOT_PRODUCT", "DISTANCE") else nd.outputs[0]

    def sep(self, v):
        nd = self.node("ShaderNodeSeparateXYZ")
        self._in(nd.inputs[0], v)
        return nd.outputs[0], nd.outputs[1], nd.outputs[2]

    def comb(self, x, y, z):
        nd = self.node("ShaderNodeCombineXYZ")
        self._in(nd.inputs[0], x)
        self._in(nd.inputs[1], y)
        self._in(nd.inputs[2], z)
        return nd.outputs[0]

    def smooth_mask(self, sdf, aa: float = 0.006):
        """1 inside (sdf<0) → 0 outside, antialiased."""
        nd = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        self._in(nd.inputs["Value"], sdf)
        nd.inputs["From Min"].default_value = -aa
        nd.inputs["From Max"].default_value = aa
        nd.inputs["To Min"].default_value = 1.0
        nd.inputs["To Max"].default_value = 0.0
        return nd.outputs["Result"]

    def map_range(self, v, a, b, c=0.0, d=1.0, interp="LINEAR", clamp=True):
        nd = self.node("ShaderNodeMapRange", interpolation_type=interp, clamp=clamp)
        self._in(nd.inputs["Value"], v)
        self._in(nd.inputs["From Min"], a)
        self._in(nd.inputs["From Max"], b)
        self._in(nd.inputs["To Min"], c)
        self._in(nd.inputs["To Max"], d)
        return nd.outputs["Result"]

    def mix_rgb(self, fac, a, b, blend="MIX"):
        nd = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=True)
        self._in(nd.inputs["Factor"], fac)
        self._in(nd.inputs[6], a)
        self._in(nd.inputs[7], b)
        return nd.outputs[2]

    def mix_f(self, fac, a, b):
        nd = self.node("ShaderNodeMix", data_type="FLOAT", clamp_factor=True)
        self._in(nd.inputs["Factor"], fac)
        self._in(nd.inputs[2], a)
        self._in(nd.inputs[3], b)
        return nd.outputs[0]

    def attr(self, name: str, kind: str = "GEOMETRY"):
        nd = self.node("ShaderNodeAttribute", attribute_name=name, attribute_type=kind)
        return nd

    def tex_coord(self):
        return self.node("ShaderNodeTexCoord")

    def noise(self, vec, scale, detail=2.0, rough=0.5, distortion=0.0):
        nd = self.node("ShaderNodeTexNoise")
        self._in(nd.inputs["Vector"], vec)
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough
        nd.inputs["Distortion"].default_value = distortion
        return nd

    def wave(self, vec, scale, distortion=0.0, detail=2.0, kind="BANDS", direction="X", profile="SIN"):
        nd = self.node("ShaderNodeTexWave", wave_type=kind, bands_direction=direction, wave_profile=profile)
        self._in(nd.inputs["Vector"], vec)
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Distortion"].default_value = distortion
        nd.inputs["Detail"].default_value = detail
        return nd

    def voronoi(self, vec, scale, feature="F1", randomness=1.0):
        nd = self.node("ShaderNodeTexVoronoi", feature=feature)
        self._in(nd.inputs["Vector"], vec)
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Randomness"].default_value = randomness
        return nd

    def ramp(self, fac, stops: list[tuple[float, Any]]):
        nd = self.node("ShaderNodeValToRGB")
        self._in(nd.inputs[0], fac)
        cr = nd.color_ramp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]
        cr.elements[0].color = stops[0][1]
        for pos, col in stops[1:]:
            e = cr.elements.new(pos)
            e.color = col
        return nd.outputs[0]

    def bump(self, height, strength, distance=0.01, normal=None):
        nd = self.node("ShaderNodeBump")
        nd.inputs["Strength"].default_value = strength
        nd.inputs["Distance"].default_value = distance
        self._in(nd.inputs["Height"], height)
        if normal is not None:
            self._in(nd.inputs["Normal"], normal)
        return nd.outputs[0]

    def group(self, tree: bpy.types.NodeTree, **inputs):
        nd = self.node("ShaderNodeGroup")
        nd.node_tree = tree
        for k, v in inputs.items():
            self._in(nd.inputs[k], v)
        return nd


def _new_material(name: str):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    return mat, NB(nt), out


def _principled(b: NB, **vals):
    p = b.node("ShaderNodeBsdfPrincipled")
    for k, v in vals.items():
        b._in(R.principled_input(p, k), v)
    return p


def _set(p, name, val, b: NB):
    b._in(R.principled_input(p, name), val)


def _group_tree(name: str, inputs: list[tuple[str, str, Any]], outputs: list[tuple[str, str]]):
    g = bpy.data.node_groups.get(name)
    if g is not None:
        bpy.data.node_groups.remove(g)
    g = bpy.data.node_groups.new(name, "ShaderNodeTree")
    for nm, kind, default in inputs:
        s = g.interface.new_socket(nm, in_out="INPUT", socket_type=kind)
        if default is not None and hasattr(s, "default_value"):
            s.default_value = default
    for nm, kind in outputs:
        g.interface.new_socket(nm, in_out="OUTPUT", socket_type=kind)
    gi = g.nodes.new("NodeGroupInput")
    go = g.nodes.new("NodeGroupOutput")
    return g, NB(g), gi, go


# =========================================================================== node groups


def brush_strokes_group() -> bpy.types.NodeTree:
    """NG_Brush: hand-painted stroke variation (0..1) from object coordinates."""
    g, b, gi, go = _group_tree("NG_Brush", [("Vector", "NodeSocketVector", None), ("Seed", "NodeSocketFloat", 0.0)],
                               [("Fac", "NodeSocketFloat"), ("Height", "NodeSocketFloat")])
    rot = b.node("ShaderNodeVectorRotate", rotation_type="Z_AXIS")
    b._in(rot.inputs["Vector"], gi.outputs["Vector"])
    b._in(rot.inputs["Angle"], b.mul(gi.outputs["Seed"], 3.14159))
    w = b.wave(rot.outputs[0], 22.0, distortion=5.0, detail=3.0)
    n = b.noise(rot.outputs[0], 90.0, detail=3.0)
    fac = b.add(b.mul(w.outputs["Fac"], 0.7), b.mul(n.outputs["Fac"], 0.3))
    b.l.new(fac, go.inputs["Fac"])
    b.l.new(b.mul(w.outputs["Fac"], 1.0), go.inputs["Height"])
    return g


def zari_group() -> bpy.types.NodeTree:
    """NG_Zari: gold border mask from garment_uv + zari layout id (PLAN §1.3)."""
    g, b, gi, go = _group_tree("NG_Zari", [("UV", "NodeSocketVector", None), ("Zari", "NodeSocketFloat", 0.0)],
                               [("Mask", "NodeSocketFloat"), ("Pattern", "NodeSocketFloat")])
    u, v, _ = b.sep(gi.outputs["UV"])
    zid = gi.outputs["Zari"]
    is1 = b.cmp(zid, 1.0, 0.5)
    is2 = b.cmp(zid, 2.0, 0.5)
    is3 = b.cmp(zid, 3.0, 0.5)
    hem = b.mul(b.mx(is1, is2), b.lt(v, 0.075))
    edge_u = b.mx(b.lt(u, 0.11), b.gt(u, 0.89))
    end_v = b.gt(v, 0.9)
    edges = b.mul(b.mx(is3, is2), b.mx(edge_u, end_v))
    inner = b.mul(b.mx(is1, is2), b.mul(b.gt(v, 0.095), b.lt(v, 0.11)))  # thin kattam line above hem band
    mask = b.mx(b.mx(hem, edges), inner)
    valid = b.gt(v, -0.5)
    b.l.new(b.mul(mask, valid), go.inputs["Mask"])
    w = b.wave(b.comb(b.mul(u, 40.0), b.mul(v, 40.0), 0.0), 6.0, detail=0.0)
    b.l.new(w.outputs["Fac"], go.inputs["Pattern"])
    return g


def face_paint_group() -> bpy.types.NodeTree:
    """NG_FacePaint: golu-style painted face in head space (DECISIONS D25).

    Per-object vector properties (Attribute OBJECT; packed because EEVEE allows only 8 uniform attributes per
    material): face_a = head_center; face_b = (head_radius, face_yaw, mark_type);
    face_c = (eye_x, eye_z, eye_w); face_d = (eye_h, iris_scale, mark_z); face_e = (has_brow, has_lips, moustache).
    """
    g, b, gi, go = _group_tree(
        "NG_FacePaint",
        [("Object", "NodeSocketVector", None), ("Base", "NodeSocketColor", (0.6, 0.4, 0.3, 1.0))],
        [("Color", "NodeSocketColor"), ("Mask", "NodeSocketFloat")])
    P = pal()
    def unpack(name):
        return b.sep(b.attr(name, "OBJECT").outputs["Vector"])
    hc = b.attr("face_a", "OBJECT").outputs["Vector"]
    hr, yaw, mark_t = unpack("face_b")
    ex, ez, ew = unpack("face_c")
    eh, iris_k, mark_zz = unpack("face_d")
    has_brow, has_lips, has_must = unpack("face_e")
    rel = b.vec("SUBTRACT", gi.outputs["Object"], hc)
    rel = b.vec("DIVIDE", rel, b.comb(hr, hr, hr))
    rot = b.node("ShaderNodeVectorRotate", rotation_type="Z_AXIS", invert=True)
    b._in(rot.inputs["Vector"], rel)
    b._in(rot.inputs["Angle"], yaw)
    x, y, z = b.sep(rot.outputs[0])
    ax = b.absv(x)
    front = b.map_range(y, -0.15, -0.35, 0.0, 1.0)

    # almond lens: two circles of radius Rr offset vertically by d (Rr = (w²+h²)/2h, d = Rr - h)
    rr = b.div(b.add(b.mul(ew, ew), b.mul(eh, eh)), b.mul(eh, 2.0))
    dd = b.sub(rr, eh)
    dx = b.sub(ax, ex)
    dz = b.sub(z, ez)
    c1 = b.sub(b.hypot(dx, b.sub(dz, dd)), rr)
    c2 = b.sub(b.hypot(dx, b.add(dz, dd)), rr)
    lens = b.mx(c1, c2)
    # kajal thickens toward the outer corner and extends as a wing
    outer = b.map_range(dx, 0.0, ew, 0.0, 1.0)
    kaj_t = b.add(0.028, b.mul(outer, 0.03))
    kajal = b.smooth_mask(b.sub(lens, kaj_t))
    wing_line = b.absv(b.sub(dz, b.mul(b.sub(dx, ew), 0.45)))
    wing = b.mul(b.mul(b.smooth_mask(b.sub(wing_line, b.mul(b.map_range(dx, ew, b.mul(ew, 1.55), 0.022, 0.0), 1.0))),
                       b.gt(dx, b.mul(ew, 0.9))), b.lt(dx, b.mul(ew, 1.55)))
    white = b.smooth_mask(lens)
    iris_r = b.mul(eh, iris_k)
    iris = b.mul(b.smooth_mask(b.sub(b.hypot(dx, b.add(dz, b.mul(eh, 0.1))), iris_r)), white)
    glint = b.mul(b.smooth_mask(b.sub(b.hypot(b.add(dx, b.mul(iris_r, 0.35)), b.sub(dz, b.mul(iris_r, 0.35))),
                                       b.mul(iris_r, 0.22)), 0.004), iris)
    # brows: parabolic arc above each eye
    bx = b.div(dx, b.mul(ew, 1.25))
    zb = b.sub(b.add(ez, b.mul(eh, 2.6)), b.mul(b.mul(bx, bx), b.mul(eh, 1.4)))
    brow_th = b.mul(b.mul(eh, 0.32), b.mx(b.sub(1.0, b.mul(bx, bx)), 0.0))
    brow = b.mul(b.smooth_mask(b.sub(b.absv(b.sub(z, zb)), brow_th)), b.lt(b.absv(bx), 1.0))
    brow = b.mul(brow, has_brow)
    # lips
    lw, lh, lz = 0.12, 0.048, -0.44
    lrr = (lw * lw + lh * lh) / (2 * lh)
    ld = lrr - lh
    l1 = b.sub(b.hypot(x, b.sub(b.sub(z, lz), ld)), lrr)
    l2 = b.sub(b.hypot(x, b.add(b.sub(z, lz), ld)), lrr)
    lips = b.mul(b.smooth_mask(b.mx(l1, l2)), has_lips)
    lipline = b.mul(b.smooth_mask(b.sub(b.absv(b.sub(z, lz)), 0.006), 0.003), lips)
    # moustache: curved band above the lips, curling up at the ends
    mz = b.add(lz + 0.085, b.mul(b.mul(x, x), 2.2))
    must = b.mul(b.mul(b.smooth_mask(b.sub(b.absv(b.sub(z, mz)), b.sub(0.034, b.mul(ax, 0.09)))),
                       b.lt(ax, 0.23)), has_must)
    lips = b.mul(lips, b.sub(1.0, must))
    # forehead marks
    mt = mark_t
    mz = mark_zz
    fz = b.sub(z, mz)
    m_dot = b.mul(b.cmp(mt, 1.0, 0.5), b.smooth_mask(b.sub(b.hypot(x, fz), 0.05)))
    ring = b.hypot(x, fz)
    u_band = b.mul(b.smooth_mask(b.sub(b.absv(b.sub(ring, 0.105)), 0.03)), b.lt(fz, 0.0))
    bars = b.mul(b.mul(b.smooth_mask(b.sub(b.absv(b.sub(ax, 0.105)), 0.03)), b.gt(fz, -0.001)), b.lt(fz, 0.22))
    namam_w = b.mul(b.cmp(mt, 2.0, 0.5), b.mx(u_band, bars))
    namam_r = b.mul(b.mul(b.cmp(mt, 2.0, 0.5), b.smooth_mask(b.sub(ax, 0.024))),
                    b.mul(b.gt(fz, -0.08), b.lt(fz, 0.24)))
    stripes = b.mx(b.mx(b.smooth_mask(b.sub(b.absv(b.sub(fz, 0.08)), 0.017)),
                        b.smooth_mask(b.sub(b.absv(b.sub(fz, 0.16)), 0.017))),
                   b.smooth_mask(b.sub(b.absv(b.sub(fz, 0.24)), 0.017)))
    vib_w = b.mul(b.mul(b.cmp(mt, 3.0, 0.5), stripes), b.lt(ax, b.sub(0.30, b.mul(b.absv(b.sub(fz, 0.16)), 0.6))))
    vib_r = b.mul(b.cmp(mt, 3.0, 0.5), b.smooth_mask(b.sub(b.hypot(x, b.add(fz, 0.0)), 0.034)))
    tv = b.mul(b.cmp(mt, 4.0, 0.5), b.smooth_mask(b.sub(b.hypot(b.mul(x, 2.6), b.mul(b.sub(fz, 0.08), 0.85)), 0.085)))

    white_c = rgba((0.92, 0.9, 0.86))
    black_c = rgba(P.material("kajal"))
    red_c = rgba(P.material("namam-red"))
    lip_c = rgba(P.material("lip"))
    kum_c = rgba(P.material("kumkum-powder"))
    vib_c = rgba(P.material("vibhuti"))

    col = gi.outputs["Base"]
    col = b.mix_rgb(b.mul(kajal, front), col, black_c)
    col = b.mix_rgb(b.mul(wing, front), col, black_c)
    col = b.mix_rgb(b.mul(white, front), col, white_c)
    col = b.mix_rgb(b.mul(iris, front), col, black_c)
    col = b.mix_rgb(b.mul(glint, front), col, white_c)
    col = b.mix_rgb(b.mul(brow, front), col, black_c)
    col = b.mix_rgb(b.mul(must, front), col, black_c)
    col = b.mix_rgb(b.mul(lips, front), col, lip_c)
    col = b.mix_rgb(b.mul(lipline, front), col, rgba((0.25, 0.02, 0.03)))
    col = b.mix_rgb(b.mul(b.mx(namam_w, vib_w), front), col, vib_c)
    col = b.mix_rgb(b.mul(namam_r, front), col, red_c)
    col = b.mix_rgb(b.mul(b.mx(b.mx(m_dot, vib_r), tv), front), col, kum_c)
    mask = b.mul(front, b.mx(b.mx(b.mx(kajal, white), b.mx(b.mx(brow, must), lips)),
                             b.mx(b.mx(namam_w, vib_w), b.mx(m_dot, tv))))
    b.l.new(col, go.inputs["Color"])
    b.l.new(mask, go.inputs["Mask"])
    return g


# =========================================================================== materials


def clay_gloss() -> bpy.types.Material:
    """M_ClayGloss — the single doll shader: painted clay under a 0.6 clear-coat varnish (SPEC §4.3)."""
    if "clay" in _CACHE:
        return _CACHE["clay"]
    mat, b, out = _new_material("M_ClayGloss")
    tc = b.tex_coord()
    oi = b.node("ShaderNodeObjectInfo")
    paint = b.attr("paint").outputs["Color"]
    pbr = b.attr("pbr").outputs["Vector"]
    guv = b.attr("garment_uv").outputs["Vector"]
    zari = b.attr("zari").outputs["Fac"]
    metal, rough, kind = b.sep(pbr)
    brush = b.group(brush_strokes_group(), Vector=tc.outputs["Object"], Seed=oi.outputs["Random"])
    # brush-stroke value variation ±5%
    k = b.add(0.95, b.mul(brush.outputs["Fac"], 0.1))
    base = b.mix_rgb(1.0, paint, b.comb(k, k, k), blend="MULTIPLY")
    # wood grain (Marapachi, kind 4)
    is_wood = b.cmp(kind, 4.0, 0.5)
    ring = b.wave(tc.outputs["Object"], 55.0, distortion=8.0, detail=4.0, kind="RINGS")
    wood_k = b.add(0.72, b.mul(ring.outputs["Fac"], 0.42))
    base = b.mix_rgb(is_wood, base, b.mix_rgb(1.0, paint, b.comb(wood_k, wood_k, wood_k), blend="MULTIPLY"))
    # scales/shell pattern (kind 7)
    is_scale = b.cmp(kind, 7.0, 0.5)
    vor = b.voronoi(tc.outputs["Object"], 160.0, feature="DISTANCE_TO_EDGE")
    edge = b.map_range(vor.outputs["Distance"], 0.0, 0.08, 0.55, 1.0)
    base = b.mix_rgb(is_scale, base, b.mix_rgb(1.0, base, b.comb(edge, edge, edge), blend="MULTIPLY"))
    # peacock eye-feather ocellus (kind 8) from the feather's garment_uv (u across, v along)
    is_eye = b.cmp(kind, 8.0, 0.5)
    fu, fv, _ = b.sep(guv)
    od = b.hypot(b.sub(fu, 0.5), b.mul(b.sub(fv, 0.84), 1.7))
    eye_col = b.ramp(od, [(0.0, (0.01, 0.02, 0.10, 1)), (0.07, (0.02, 0.08, 0.5, 1)), (0.115, (0.0, 0.32, 0.33, 1)),
                          (0.16, (0.55, 0.33, 0.04, 1)), (0.215, (0.07, 0.26, 0.04, 1)),
                          (0.32, (0.16, 0.2, 0.04, 1))])
    barbs = b.wave(b.comb(b.mul(b.sub(fu, 0.5), 30.0), fv, 0.0), 1.0, detail=0.0, direction="X")
    eye_col = b.mix_rgb(b.mul(b.mul(barbs.outputs["Fac"], 0.35), b.gt(od, 0.2)), eye_col, (0.02, 0.05, 0.01, 1))
    base = b.mix_rgb(is_eye, base, eye_col)
    # zari (garment kind 1)
    is_garment = b.cmp(kind, 1.0, 0.5)
    z = b.group(zari_group(), UV=guv, Zari=zari)
    zmask = b.mul(z.outputs["Mask"], is_garment)
    gold = pal().material("gold")
    gold_pat = b.mix_rgb(b.mul(z.outputs["Pattern"], 0.35), rgba(gold), rgba(lift(gold, 0.6)))
    base = b.mix_rgb(zmask, base, gold_pat)
    metal = b.mx(metal, b.mul(zmask, 0.7))
    rough = b.mix_f(zmask, rough, 0.3)
    # painted face (skin kind 0)
    is_skin = b.cmp(kind, 0.0, 0.5)
    face = b.group(face_paint_group(), Object=tc.outputs["Object"], Base=base)
    base = b.mix_rgb(is_skin, base, face.outputs["Color"])
    nz = b.noise(tc.outputs["Object"], 60.0)
    rough = b.add(rough, b.mul(b.sub(nz.outputs["Fac"], 0.5), 0.08))
    normal = b.bump(brush.outputs["Height"], 0.03, 0.002)
    # matte painted terrain (kind 5: hills, rocks, soil): thin varnish so it doesn't read as plastic
    is_matte = b.cmp(kind, 5.0, 0.5)
    coat = b.sub(0.6, b.mul(is_matte, 0.5))
    p = _principled(b, **{"Base Color": base, "Metallic": metal, "Roughness": rough, "Coat Weight": coat,
                          "Coat Roughness": 0.06, "Coat IOR": 1.5, "Normal": normal})
    if "Thin Film Thickness" in p.inputs:      # iridescent peacock feathers (Blender 4.2+)
        b._in(p.inputs["Thin Film Thickness"], b.mul(is_eye, 380.0))
        p.inputs["Thin Film IOR"].default_value = 1.4
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE["clay"] = mat
    return mat


def silk(color_key: str) -> bpy.types.Material:
    """M_Silk_<key>: anisotropic sheen silk with gold zari border at UV v > 0.9 (step drapes)."""
    key = f"silk_{color_key}"
    if key in _CACHE:
        return _CACHE[key]
    mat, b, out = _new_material(f"M_Silk_{color_key}")
    P = pal()
    base_c = P.cloth(color_key) if color_key in P.raw["cloth"] else P.silk(color_key)
    tc = b.tex_coord()
    uv = tc.outputs["UV"]
    u, v, _ = b.sep(uv)
    tan = b.node("ShaderNodeTangent", direction_type="UV_MAP")
    weave_a = b.wave(b.comb(b.mul(u, 1.0), b.mul(v, 1.0), 0.0), 900.0, detail=0.0, direction="X")
    weave_b = b.wave(b.comb(b.mul(u, 1.0), b.mul(v, 1.0), 0.0), 900.0, detail=0.0, direction="Y")
    weave = b.mul(weave_a.outputs["Fac"], weave_b.outputs["Fac"])
    butta = b.voronoi(b.comb(b.mul(u, 2.6), b.mul(v, 1.0), 0.0), 18.0, randomness=0.3)
    butta_m = b.mul(b.smooth_mask(b.sub(butta.outputs["Distance"], 0.07), 0.01), b.lt(v, 0.82))
    zari_m = b.map_range(v, 0.895, 0.905, 0.0, 1.0)
    kattam = b.mul(b.gt(v, 0.875), b.lt(v, 0.887))
    gold = P.material("gold")
    shot = b.node("ShaderNodeLayerWeight")
    shot.inputs["Blend"].default_value = 0.35
    base_col = b.mix_rgb(b.mul(shot.outputs["Facing"], 0.35), rgba(base_c), rgba(lift(base_c, 1.6)))
    twill = b.wave(b.comb(b.add(u, v), b.sub(u, v), 0.0), 400.0, detail=0.0)
    gold_col = b.mix_rgb(b.mul(twill.outputs["Fac"], 0.3), rgba(gold), rgba(lift(gold, 0.55)))
    col = b.mix_rgb(b.mul(butta_m, 0.85), base_col, rgba(gold))
    col = b.mix_rgb(kattam, col, rgba(lift(gold, 0.7)))
    col = b.mix_rgb(zari_m, col, gold_col)
    metal = b.mx(zari_m, b.mul(butta_m, 0.8))
    rough = b.mix_f(zari_m, 0.32, 0.27)
    normal = b.bump(weave, 0.08, 0.0005)
    p = _principled(b, **{"Base Color": col, "Metallic": metal, "Roughness": rough, "Anisotropic": 0.65,
                          "Sheen Weight": 0.45, "Sheen Roughness": 0.28,
                          "Sheen Tint": rgba(lift(base_c, 1.25)), "Normal": normal})
    b.l.new(tan.outputs[0], p.inputs["Tangent"])
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE[key] = mat
    return mat


def _metal(name: str, color, rough: float, rough_var: float, hammer: float, patina: float) -> bpy.types.Material:
    mat, b, out = _new_material(name)
    tc = b.tex_coord()
    nz = b.noise(tc.outputs["Object"], 40.0, detail=3.0)
    rough_s = b.add(rough, b.mul(b.sub(nz.outputs["Fac"], 0.5), rough_var * 2))
    vor = b.voronoi(tc.outputs["Object"], 70.0)
    col = rgba(color)
    if patina > 0:
        ao = b.node("ShaderNodeAmbientOcclusion", samples=8, only_local=True)
        ao.inputs["Distance"].default_value = 0.16
        dark = rgba((color[0] * 0.25, color[1] * 0.22, color[2] * 0.12))
        col = b.mix_rgb(b.mul(b.sub(1.0, ao.outputs["AO"]), patina), col, dark)
    p = _principled(b, **{"Base Color": col, "Metallic": 1.0, "Roughness": rough_s,
                          "Normal": b.bump(vor.outputs["Distance"], hammer, 0.001)})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    return mat


def brass() -> bpy.types.Material:
    if "brass" not in _CACHE:
        _CACHE["brass"] = _metal("M_Brass", pal().material("brass"), 0.26, 0.06, 0.015, 0.35)
    return _CACHE["brass"]


def gold() -> bpy.types.Material:
    if "gold" not in _CACHE:
        _CACHE["gold"] = _metal("M_Gold", pal().material("gold"), 0.22, 0.04, 0.008, 0.15)
    return _CACHE["gold"]


def silver() -> bpy.types.Material:
    if "silver" not in _CACHE:
        _CACHE["silver"] = _metal("M_Silver", pal().material("silver"), 0.2, 0.05, 0.01, 0.25)
    return _CACHE["silver"]


def teak() -> bpy.types.Material:
    if "teak" in _CACHE:
        return _CACHE["teak"]
    mat, b, out = _new_material("M_Teak")
    tc = b.tex_coord()
    mp = b.node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 8.0)
    b.l.new(tc.outputs["Object"], mp.inputs["Vector"])
    w = b.wave(mp.outputs[0], 6.0, distortion=7.0, detail=5.0, kind="RINGS")
    c0 = pal().material("teak")
    col = b.ramp(w.outputs["Fac"], [(0.0, rgba(lift(c0, 0.55))), (0.55, rgba(c0)), (1.0, rgba(lift(c0, 1.35)))])
    p = _principled(b, **{"Base Color": col, "Roughness": 0.45, "Coat Weight": 0.3, "Coat Roughness": 0.15,
                          "Normal": b.bump(w.outputs["Fac"], 0.08, 0.001)})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE["teak"] = mat
    return mat


def red_oxide() -> bpy.types.Material:
    if "redox" in _CACHE:
        return _CACHE["redox"]
    mat, b, out = _new_material("M_RedOxide")
    tc = b.tex_coord()
    c0 = pal().material("red-oxide")
    nz = b.noise(tc.outputs["Object"], 2.5, detail=4.0)
    col = b.mix_rgb(nz.outputs["Fac"], rgba(lift(c0, 0.85)), rgba(lift(c0, 1.15)))
    brick = b.node("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0 / 0.6
    brick.inputs["Mortar Size"].default_value = 0.002 / 0.6
    brick.inputs["Brick Width"].default_value = 1.0
    brick.inputs["Row Height"].default_value = 1.0
    brick.offset = 0.0
    b.l.new(tc.outputs["Object"], brick.inputs["Vector"])
    col = b.mix_rgb(b.mul(brick.outputs["Fac"], 0.5), col, rgba(lift(c0, 0.5)))
    rough = b.map_range(nz.outputs["Fac"], 0.3, 0.7, 0.22, 0.35)
    p = _principled(b, **{"Base Color": col, "Roughness": rough, "Coat Weight": 0.35, "Coat Roughness": 0.1,
                          "Normal": b.bump(b.sub(1.0, brick.outputs["Fac"]), 0.3, 0.004)})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE["redox"] = mat
    return mat


def temple_wall() -> bpy.types.Material:
    if "wall" in _CACHE:
        return _CACHE["wall"]
    mat, b, out = _new_material("M_TempleWall")
    tc = b.tex_coord()
    c0 = pal().material("temple-wall")
    nz = b.noise(tc.outputs["Object"], 4.0, detail=6.0, rough=0.6)
    col = b.mix_rgb(nz.outputs["Fac"], rgba(lift(c0, 0.8)), rgba(lift(c0, 1.1)))
    p = _principled(b, **{"Base Color": col, "Roughness": 0.85,
                          "Normal": b.bump(nz.outputs["Fac"], 0.15, 0.003)})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE["wall"] = mat
    return mat


def granite() -> bpy.types.Material:
    if "granite" in _CACHE:
        return _CACHE["granite"]
    mat, b, out = _new_material("M_Granite")
    tc = b.tex_coord()
    c0 = pal().material("granite")
    v = b.voronoi(tc.outputs["Object"], 220.0)
    nz = b.noise(tc.outputs["Object"], 30.0, detail=4.0)
    col = b.mix_rgb(b.mul(v.outputs["Distance"], 1.5), rgba(lift(c0, 0.6)), rgba(lift(c0, 1.35)))
    col = b.mix_rgb(b.mul(nz.outputs["Fac"], 0.4), col, rgba(lift(pal().material("turmeric-powder"), 0.5)))
    p = _principled(b, **{"Base Color": col, "Roughness": 0.55,
                          "Normal": b.bump(nz.outputs["Fac"], 0.1, 0.002)})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE["granite"] = mat
    return mat


def rice_flour() -> bpy.types.Material:
    """M_RiceFlour: white powder line; edges break up along the ribbon's UV v (DECISIONS D22)."""
    if "rice" in _CACHE:
        return _CACHE["rice"]
    mat, b, out = _new_material("M_RiceFlour")
    tc = b.tex_coord()
    _, v, _ = b.sep(tc.outputs["UV"])
    edge = b.mul(b.absv(b.sub(v, 0.5)), 2.0)
    nz = b.noise(tc.outputs["Object"], 300.0, detail=3.0)
    keep = b.lt(edge, b.add(0.72, b.mul(nz.outputs["Fac"], 0.3)))
    grain = b.noise(tc.outputs["Object"], 900.0, detail=1.0)
    p = _principled(b, **{"Base Color": rgba(pal().material("rice-flour")), "Roughness": 0.95,
                          "Normal": b.bump(grain.outputs["Fac"], 0.2, 0.0005)})
    tr = b.node("ShaderNodeBsdfTransparent")
    mix = b.node("ShaderNodeMixShader")
    b.l.new(keep, mix.inputs[0])
    b.l.new(tr.outputs[0], mix.inputs[1])
    b.l.new(p.outputs[0], mix.inputs[2])
    b.l.new(mix.outputs[0], out.inputs["Surface"])
    _CACHE["rice"] = mat
    return mat


def terracotta() -> bpy.types.Material:
    if "terra" in _CACHE:
        return _CACHE["terra"]
    mat, b, out = _new_material("M_Terracotta")
    tc = b.tex_coord()
    c0 = pal().material("terracotta")
    nz = b.noise(tc.outputs["Object"], 120.0, detail=3.0)
    col = b.mix_rgb(b.mul(nz.outputs["Fac"], 0.5), rgba(lift(c0, 0.8)), rgba(lift(c0, 1.15)))
    p = _principled(b, **{"Base Color": col, "Roughness": 0.8, "Normal": b.bump(nz.outputs["Fac"], 0.2, 0.0008)})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE["terra"] = mat
    return mat


def flame(kind: str = "ghee") -> bpy.types.Material:
    key = f"flame_{kind}"
    if key in _CACHE:
        return _CACHE[key]
    mat, b, out = _new_material(f"M_Flame_{kind}")
    P = pal()
    tc = b.tex_coord()
    _, _, gz = b.sep(tc.outputs["Generated"])
    strength = {"ghee": 7.0, "camphor": 12.0, "agal": 5.0}.get(kind, 7.0)
    base_c, mid_c, tip_c = P.material("flame-base"), P.material("flame-mid"), P.material("flame-tip")
    if kind == "camphor":
        base_c, mid_c = mid_c, tip_c
    col = b.ramp(gz, [(0.0, rgba(lift(base_c, 0.8))), (0.35, rgba(mid_c)), (0.85, rgba(tip_c)), (1.0, rgba(tip_c))])
    em = b.node("ShaderNodeEmission")
    b.l.new(col, em.inputs["Color"])
    em.inputs["Strength"].default_value = strength
    lw = b.node("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    fac = b.pw(b.sub(1.0, lw.outputs["Facing"]), 2.0)
    tr = b.node("ShaderNodeBsdfTransparent")
    mix = b.node("ShaderNodeMixShader")
    b.l.new(fac, mix.inputs[0])
    b.l.new(tr.outputs[0], mix.inputs[1])
    b.l.new(em.outputs[0], mix.inputs[2])
    b.l.new(mix.outputs[0], out.inputs["Surface"])
    _CACHE[key] = mat
    return mat


def marigold(color_key: str) -> bpy.types.Material:
    key = f"marigold_{color_key}"
    if key in _CACHE:
        return _CACHE[key]
    mat, b, out = _new_material(f"M_Marigold_{color_key}")
    c0 = pal().material(color_key)
    oi = b.node("ShaderNodeObjectInfo")
    hsv = b.node("ShaderNodeHueSaturation")
    b._in(hsv.inputs["Hue"], b.add(0.47, b.mul(oi.outputs["Random"], 0.06)))
    b._in(hsv.inputs["Value"], b.add(0.9, b.mul(oi.outputs["Random"], 0.2)))
    hsv.inputs["Color"].default_value = rgba(c0)
    tc = b.tex_coord()
    vor = b.voronoi(tc.outputs["Object"], 350.0, feature="DISTANCE_TO_EDGE")
    p = _principled(b, **{"Base Color": hsv.outputs[0], "Roughness": 0.55, "Subsurface Weight": 0.25,
                          "Normal": b.bump(vor.outputs["Distance"], 0.6, 0.002)})
    p.inputs["Subsurface Radius"].default_value = (0.9, 0.4, 0.1)
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE[key] = mat
    return mat


def jasmine() -> bpy.types.Material:
    if "jasmine" in _CACHE:
        return _CACHE["jasmine"]
    mat, b, out = _new_material("M_Jasmine")
    tc = b.tex_coord()
    _, _, gz = b.sep(tc.outputs["Generated"])
    col = b.mix_rgb(b.map_range(gz, 0.0, 0.3, 1.0, 0.0), rgba(pal().material("jasmine")), rgba((0.55, 0.7, 0.35)))
    p = _principled(b, **{"Base Color": col, "Roughness": 0.5, "Subsurface Weight": 0.3})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE["jasmine"] = mat
    return mat


def _leaf(name: str, color_key: str, gloss: float) -> bpy.types.Material:
    mat, b, out = _new_material(name)
    c0 = pal().material(color_key)
    tc = b.tex_coord()
    u, v, _ = b.sep(tc.outputs["UV"])
    oi = b.node("ShaderNodeObjectInfo")
    midrib = b.smooth_mask(b.sub(b.absv(b.sub(u, 0.5)), 0.015), 0.004)
    veins = b.wave(b.comb(b.add(b.mul(b.absv(b.sub(u, 0.5)), 1.0), b.mul(v, 0.6)), v, 0.0), 30.0, detail=0.0)
    base = b.mix_rgb(b.mul(oi.outputs["Random"], 0.35), rgba(c0), rgba(lift(c0, 1.35)))
    col = b.mix_rgb(b.mul(midrib, 0.6), base, rgba(lift(c0, 1.9)))
    col = b.mix_rgb(b.mul(veins.outputs["Fac"], 0.12), col, rgba(lift(c0, 1.5)))
    p = _principled(b, **{"Base Color": col, "Roughness": gloss})
    tl = b.node("ShaderNodeBsdfTranslucent")
    b.l.new(col, tl.inputs["Color"])
    mix = b.node("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.15
    b.l.new(p.outputs[0], mix.inputs[1])
    b.l.new(tl.outputs[0], mix.inputs[2])
    b.l.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def mango_leaf() -> bpy.types.Material:
    if "mango" not in _CACHE:
        _CACHE["mango"] = _leaf("M_MangoLeaf", "mango-leaf", 0.35)
    return _CACHE["mango"]


def banana_leaf() -> bpy.types.Material:
    if "banleaf" not in _CACHE:
        _CACHE["banleaf"] = _leaf("M_BananaLeaf", "banana-leaf", 0.4)
    return _CACHE["banleaf"]


def banana_stem() -> bpy.types.Material:
    if "banstem" in _CACHE:
        return _CACHE["banstem"]
    mat, b, out = _new_material("M_BananaStem")
    c0 = pal().material("banana-stem")
    tc = b.tex_coord()
    mp = b.node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 0.04)
    b.l.new(tc.outputs["Object"], mp.inputs["Vector"])
    streak = b.noise(mp.outputs[0], 60.0, detail=4.0, rough=0.6)
    blotch = b.noise(tc.outputs["Object"], 6.0, detail=3.0)
    col = b.mix_rgb(b.map_range(streak.outputs["Fac"], 0.35, 0.65, 0.0, 1.0), rgba(lift(c0, 0.7)), rgba(c0))
    col = b.mix_rgb(b.mul(blotch.outputs["Fac"], 0.35), col, rgba((0.16, 0.24, 0.07)))
    p = _principled(b, **{"Base Color": col, "Roughness": 0.45, "Subsurface Weight": 0.15})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE["banstem"] = mat
    return mat


def powder(color_key: str) -> bpy.types.Material:
    key = f"powder_{color_key}"
    if key in _CACHE:
        return _CACHE[key]
    mat, b, out = _new_material(f"M_Powder_{color_key}")
    tc = b.tex_coord()
    g = b.noise(tc.outputs["Object"], 800.0, detail=1.0)
    p = _principled(b, **{"Base Color": rgba(pal().material(color_key)), "Roughness": 0.95,
                          "Normal": b.bump(g.outputs["Fac"], 0.3, 0.0004)})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE[key] = mat
    return mat


def cotton_wick() -> bpy.types.Material:
    if "wick" in _CACHE:
        return _CACHE["wick"]
    mat, b, out = _new_material("M_Wick")
    p = _principled(b, **{"Base Color": rgba((0.75, 0.68, 0.55)), "Roughness": 0.9})
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE["wick"] = mat
    return mat


def haze_volume(kelvin: float = 2300.0, density: float = 0.035) -> bpy.types.Material:
    mat, b, out = _new_material("M_HazeVolume")
    tc = b.tex_coord()
    gx, gy, gz = b.sep(tc.outputs["Generated"])
    edge = b.mn(b.mn(b.mn(gx, b.sub(1.0, gx)), b.mn(gy, b.sub(1.0, gy))), b.mn(gz, b.sub(1.0, gz)))
    falloff = b.map_range(edge, 0.0, 0.25, 0.0, 1.0)
    vol = b.node("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = rgba(R.kelvin_to_rgb(kelvin))
    vol.inputs["Anisotropy"].default_value = 0.65
    b._in(vol.inputs["Density"], b.mul(falloff, density))
    b.l.new(vol.outputs[0], out.inputs["Volume"])
    return mat


def simple(name: str, rgb, rough: float = 0.5, metal: float = 0.0, coat: float = 0.0,
           emission: float = 0.0, sss: float = 0.0, transmission: float = 0.0) -> bpy.types.Material:
    key = f"simple_{name}"
    if key in _CACHE:
        return _CACHE[key]
    mat, b, out = _new_material(name)
    vals = {"Base Color": rgba(rgb), "Roughness": rough, "Metallic": metal, "Coat Weight": coat}
    if sss:
        vals["Subsurface Weight"] = sss
    if transmission:
        vals["Transmission Weight"] = transmission
    if emission:
        vals["Emission Color"] = rgba(rgb)
        vals["Emission Strength"] = emission
    p = _principled(b, **vals)
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE[key] = mat
    return mat


def food(kind: str) -> bpy.types.Material:
    """Prasadam food materials (SPEC §4.7)."""
    specs = {
        "chickpea": ((0.62, 0.42, 0.20), 0.5, 0.2, 0.25),
        "coconut": ((0.92, 0.9, 0.84), 0.6, 0.0, 0.35),
        "curry_leaf": ((0.06, 0.16, 0.03), 0.3, 0.5, 0.0),
        "mustard": ((0.04, 0.025, 0.02), 0.25, 0.4, 0.0),
        "pongal_rice": ((0.42, 0.20, 0.06), 0.35, 0.55, 0.3),
        "cashew": ((0.85, 0.62, 0.32), 0.45, 0.3, 0.3),
        "raisin": ((0.15, 0.05, 0.03), 0.3, 0.5, 0.0),
        "tamarind_rice": ((0.45, 0.24, 0.08), 0.45, 0.35, 0.25),
        "peanut": ((0.62, 0.38, 0.18), 0.4, 0.3, 0.15),
        "curd_rice": ((0.93, 0.92, 0.86), 0.5, 0.25, 0.5),
        "pomegranate": ((0.55, 0.02, 0.08), 0.08, 0.6, 0.0),
        "sambar_rice": ((0.62, 0.28, 0.08), 0.35, 0.6, 0.25),
        "drumstick": ((0.25, 0.38, 0.12), 0.45, 0.3, 0.1),
        "carrot": ((0.85, 0.32, 0.05), 0.4, 0.3, 0.2),
        "red_chilli": ((0.5, 0.04, 0.02), 0.35, 0.4, 0.0),
        "camphor": ((0.95, 0.95, 0.93), 0.4, 0.0, 0.5),
        "ghee_film": ((0.85, 0.6, 0.2), 0.05, 0.9, 0.0),
    }
    if kind not in specs:
        raise KeyError(f"unknown food material {kind}")
    rgb, rough, coat, sss = specs[kind]
    key = f"food_{kind}"
    if key in _CACHE:
        return _CACHE[key]
    mat, b, out = _new_material(f"M_Food_{kind}")
    oi = b.node("ShaderNodeObjectInfo")
    hsv = b.node("ShaderNodeHueSaturation")
    b._in(hsv.inputs["Value"], b.add(0.85, b.mul(oi.outputs["Random"], 0.3)))
    hsv.inputs["Color"].default_value = rgba(rgb)
    tc = b.tex_coord()
    nz = b.noise(tc.outputs["Object"], 900.0, detail=2.0)
    vals = {"Base Color": hsv.outputs[0], "Roughness": rough, "Coat Weight": coat, "Coat Roughness": 0.08,
            "Subsurface Weight": sss, "Normal": b.bump(nz.outputs["Fac"], 0.12, 0.0003)}
    if kind == "pomegranate":
        vals["Transmission Weight"] = 0.6
    p = _principled(b, **vals)
    b.l.new(p.outputs[0], out.inputs["Surface"])
    _CACHE[key] = mat
    return mat


def emissive_screen(rgb=(0.45, 0.6, 0.9), strength: float = 0.6) -> bpy.types.Material:
    return simple("M_Screen", rgb, rough=0.2, emission=strength)
