"""Render engine setup, colour management, compositor and Blender-version compatibility (DECISIONS D20)."""
from __future__ import annotations

import math
import struct
import sys
import time
from pathlib import Path

import bpy

RGB = tuple[float, float, float]


# --------------------------------------------------------------------------- compat helpers


def blender_version() -> tuple[int, int, int]:
    return tuple(bpy.app.version)  # type: ignore[return-value]


def engine_id_eevee() -> str:
    ids = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if cand in ids:
            return cand
    raise RuntimeError("EEVEE engine not available")


_PRINCIPLED_ALIASES = {
    "Coat Weight": ("Coat Weight", "Clearcoat"),
    "Coat Roughness": ("Coat Roughness", "Clearcoat Roughness"),
    "Sheen Weight": ("Sheen Weight", "Sheen"),
    "Subsurface Weight": ("Subsurface Weight", "Subsurface"),
    "Emission Color": ("Emission Color", "Emission"),
    "Specular IOR Level": ("Specular IOR Level", "Specular"),
    "Transmission Weight": ("Transmission Weight", "Transmission"),
}


def principled_input(node: bpy.types.Node, name: str) -> bpy.types.NodeSocket:
    for cand in _PRINCIPLED_ALIASES.get(name, (name,)):
        sock = node.inputs.get(cand)
        if sock is not None:
            return sock
    raise KeyError(f"Principled input {name!r} not found")


def compositor_tree(scene: bpy.types.Scene) -> bpy.types.NodeTree:
    if hasattr(scene, "compositing_node_group"):          # Blender 5.x
        tree = scene.compositing_node_group
        if tree is None:
            tree = bpy.data.node_groups.new(f"Compositor_{scene.name}", "CompositorNodeTree")
            scene.compositing_node_group = tree
        return tree
    scene.use_nodes = True                                  # Blender 4.x
    return scene.node_tree


def set_glare(node: bpy.types.Node, **kw) -> None:
    """Set Glare options whether they are node properties (≤4.3) or input sockets (4.4+)."""
    names = {"threshold": "Threshold", "size": "Size", "mix": None, "strength": "Strength",
             "quality": None, "saturation": "Saturation", "smoothness": "Smoothness"}
    for k, v in kw.items():
        if hasattr(node, k) and not isinstance(getattr(type(node), k, None), property):
            try:
                setattr(node, k, v)
                continue
            except (AttributeError, TypeError):
                pass
        sock_name = names.get(k)
        if sock_name and sock_name in node.inputs:
            sock = node.inputs[sock_name]
            if sock.type in ("INT",):
                sock.default_value = int(v)
            elif sock.type == "MENU":
                sock.default_value = v
            else:
                sock.default_value = v


def kelvin_to_rgb(kelvin: float) -> RGB:
    """Tanner Helland blackbody fit (sRGB), converted to linear and normalised to max 1."""
    t = kelvin / 100.0
    if t <= 66:
        r = 255.0
        g = 99.4708025861 * math.log(t) - 161.1195681661
        b = 0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307
    else:
        r = 329.698727446 * ((t - 60) ** -0.1332047592)
        g = 288.1221695283 * ((t - 60) ** -0.0755148492)
        b = 255.0
    out = []
    for c in (r, g, b):
        c = min(max(c, 0.0), 255.0) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    m = max(out) or 1.0
    return (out[0] / m, out[1] / m, out[2] / m)


# --------------------------------------------------------------------------- devices & quality


def configure_cycles_device() -> str:
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        return "CPU"
    for kind in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        try:
            prefs.refresh_devices()
        except AttributeError:
            prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == kind]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == kind
            return kind
    prefs.compute_device_type = "NONE"
    return "CPU"


def apply_quality(scene: bpy.types.Scene, quality: str, *, transparent: bool = False,
                  resolution: tuple[int, int] | None = None, engine: str | None = None,
                  samples: int | None = None) -> str:
    """Configure engine + output. Returns the engine id used."""
    r = scene.render
    r.resolution_percentage = 100
    r.film_transparent = transparent
    r.use_motion_blur = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA" if transparent else "RGB"
    r.image_settings.color_depth = "8"
    r.image_settings.compression = 15
    r.use_persistent_data = True
    if quality == "final" or engine == "CYCLES":
        r.engine = "CYCLES"
        dev = configure_cycles_device()
        c = scene.cycles
        c.device = "GPU" if dev != "CPU" else "CPU"
        c.samples = samples or (96 if quality == "final" else 16)
        c.use_adaptive_sampling = True
        c.adaptive_threshold = 0.01 if quality == "final" else 0.05
        c.use_denoising = True
        c.denoiser = "OPENIMAGEDENOISE"
        c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        if hasattr(c, "denoising_use_gpu"):
            c.denoising_use_gpu = dev != "CPU"
        c.use_light_tree = True
        c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 8, 3, 4
        c.transmission_bounces, c.volume_bounces, c.transparent_max_bounces = 6, 1, 16
        c.sample_clamp_indirect = 8.0
        c.caustics_reflective = c.caustics_refractive = False
        c.seed = 0
        c.use_animated_seed = False
        c.film_exposure = 1.0
        c.volume_step_rate = 2.0 if quality == "draft" else 1.0
        c.filter_width = 1.5
        if resolution is None:
            resolution = (1920, 1080) if quality == "final" else (960, 540)
        engine_id = "CYCLES"
    else:
        r.engine = engine_id_eevee()
        e = scene.eevee
        e.taa_render_samples = samples or 32
        for attr, val in (("use_raytracing", True), ("use_shadows", True), ("use_volumetric_shadows", True),
                          ("volumetric_samples", 32), ("shadow_ray_count", 1), ("shadow_step_count", 6),
                          ("use_gtao", True), ("gtao_distance", 0.25), ("use_shadow_jitter_viewport", False)):
            if hasattr(e, attr):
                try:
                    setattr(e, attr, val)
                except (AttributeError, TypeError):
                    pass
        if hasattr(e, "ray_tracing_method"):
            e.ray_tracing_method = "SCREEN"
        if hasattr(e, "fast_gi_method"):
            try:
                e.fast_gi_method = "GLOBAL_ILLUMINATION"
            except TypeError:
                pass
        if resolution is None:
            resolution = (960, 540)
        engine_id = r.engine
    r.resolution_x, r.resolution_y = resolution
    return engine_id


def setup_color_management(scene: bpy.types.Scene, exposure: float = -0.3) -> None:
    vs = scene.view_settings
    scene.display_settings.display_device = "sRGB"
    vs.view_transform = "AgX"
    looks = [l.identifier for l in vs.bl_rna.properties["look"].enum_items]
    for want in ("Medium High Contrast", "Base Contrast"):
        hit = [l for l in looks if want in l]
        if hit:
            vs.look = hit[0]
            break
    vs.exposure = exposure
    vs.gamma = 1.0
    scene.sequencer_colorspace_settings.name = "sRGB"


def setup_glare(scene: bpy.types.Scene, enabled: bool = True, strength: float = 0.35) -> None:
    """Slight bloom on emissive flames (SPEC §4.2) via the compositor Glare node."""
    tree = compositor_tree(scene)
    tree.nodes.clear()
    rl = tree.nodes.new("CompositorNodeRLayers")
    rl.location = (-300, 0)
    out = tree.nodes.new("CompositorNodeComposite")
    out.location = (300, 0)
    if hasattr(scene, "compositing_node_group"):
        out = tree.nodes.new("NodeGroupOutput")
    if not enabled:
        tree.links.new(rl.outputs["Image"], out.inputs[0])
        return
    g = tree.nodes.new("CompositorNodeGlare")
    types = [e.identifier for e in g.bl_rna.properties["glare_type"].enum_items]
    g.glare_type = "BLOOM" if "BLOOM" in types else "FOG_GLOW"
    if hasattr(g, "quality"):
        g.quality = "HIGH"
    set_glare(g, threshold=1.0, size=6 if "Size" not in g.inputs else 0.6, strength=strength,
              saturation=1.0, smoothness=0.2)
    if hasattr(g, "mix"):
        g.mix = -1.0 + strength
    tree.links.new(rl.outputs["Image"], g.inputs["Image"])
    tree.links.new(g.outputs["Image"], out.inputs[0])


def setup_world_color(scene: bpy.types.Scene, rgb: RGB, strength: float) -> None:
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (*rgb, 1.0)
    bg.inputs["Strength"].default_value = strength


# --------------------------------------------------------------------------- frames & progress


def frame_path(root: Path, step: int, local_index: int) -> Path:
    return Path(root) / f"step{step}" / f"f_{local_index:04d}.png"


def is_frame_done(path: Path, min_bytes: int = 4096) -> bool:
    """Resume test: PNG exists, is non-trivial and ends with an IEND chunk."""
    p = Path(path)
    if not p.exists() or p.stat().st_size < min_bytes:
        return False
    with p.open("rb") as f:
        if f.read(8) != b"\x89PNG\r\n\x1a\n":
            return False
        f.seek(-12, 2)
        tail = f.read(12)
    return tail[4:8] == b"IEND"


def png_size(path: Path) -> tuple[int, int]:
    with Path(path).open("rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


class ProgressLog:
    def __init__(self, total: int, label: str):
        self.total, self.label, self.done, self.ema = total, label, 0, None
        self.t0 = time.time()

    def tick(self, seconds: float, skipped: bool = False) -> None:
        self.done += 1
        if not skipped:
            self.ema = seconds if self.ema is None else 0.15 * seconds + 0.85 * self.ema
        rem = self.total - self.done
        eta = (self.ema or 0.0) * rem
        h, m = divmod(int(eta), 3600)
        m, s = divmod(m, 60)
        rate = f"{self.ema:.1f} s/f" if self.ema else "skip"
        print(f"[{self.label}] {self.done}/{self.total} · {rate} · ETA {h}:{m:02d}:{s:02d}", flush=True)


def render_still(scene: bpy.types.Scene, path: Path) -> float:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    t = time.time()
    bpy.ops.render.render(write_still=True, scene=scene.name)
    return time.time() - t


def log(msg: str) -> None:
    print(f"[golu] {msg}", flush=True)
    sys.stdout.flush()
