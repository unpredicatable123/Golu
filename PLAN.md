# PLAN — Navaratri Golu Darshan

This is the ordered implementation plan for SPEC.md. SPEC.md stays the source of truth. Where this plan resolves an ambiguity it cites a `Dnn` entry in DECISIONS.md. The executor builds phase by phase, in order. Each phase ends with its verification steps, a visual inspection, fixes, and a commit `Phase N: <summary>`.

Companion files:
- `content/golu.config.json`: drafted in full, 73 dolls.
- `ICONOGRAPHY.md`: rules table (machine-checked) and per-doll visual sheet.
- `DECISIONS.md`: 47 resolved ambiguities and deviations.

---

## 0. Ground rules for the executor

1. **No TODOs or stubs** (SPEC §6). Every function listed here is implemented completely in the phase that introduces it.
2. **Content only from config.** No titles, names, colours, timings or dish names in code. Code holds structure and technique; config holds content (D19).
3. **Determinism.**
   - Every random draw uses `rng_for(*keys)`, built on `zlib.crc32` of the key path. Never Python's `hash()`, which is salted per process.
   - Cycles uses `seed = 0` and `use_animated_seed = False`.
   - Geometry Nodes Random Value seeds come from `seed_for(...)`.
4. **Headless only.** No `bpy.ops` that need a UI context. Use the data API, and `bpy.context.temp_override(...)` only where an operator is unavoidable (join, `shade_smooth_by_angle`).
5. **Version guards** (D20). All version-specific API calls go through `lib/render.py` compat helpers: `engine_id_eevee()`, `compositor_tree(scene)`, `set_glare(node, **kw)`, `principled_input(node, name)`, `agx_look(scene, contains)`.
6. **Units.** Metres, Z up. Dolls face −Y (toward the camera side). Left and right mean the viewer's left and right unless prefixed "doll's".

### 0.1 Environment found on the build machine (2026-10-16)

| Item | Found | Needed action |
|---|---|---|
| OS | Windows 11 Pro | Shell scripts run in Git Bash (D34) |
| CPU | Intel i5-10210U, 4 cores / 8 threads | Cycles renders on CPU here |
| GPU | Intel UHD (integrated) | Not supported by Cycles oneAPI. EEVEE works for drafts. Final render needs a CUDA/OptiX/HIP/Metal GPU or a lot of CPU time (§0.3) |
| RAM | 15.8 GB | Enough. Scene budget is about 10 M faces, about 3 GB in Cycles |
| Blender | **not installed** | Install Blender 4.5 LTS (portable zip is fine); set `BLENDER=<path>/blender.exe` |
| ffmpeg | 9.0.1 with `libwebp`, `libvpx-vp9`, `libx264` | Nothing to do |
| Node / npm | 24.11.1 / 11.6.2 | Nothing to do |
| Python | 3.14 system copy | Not used: all Python runs inside Blender (SPEC §4.1) |

### 0.2 Frame budget (from config `layout.camera`)

| Segment | Frames | Global range (0-based) | On disk |
|---|---|---|---|
| Step N hold (N = 1…9) | 96 each | `S_N = (N−1)×120` → `S_N+95` | `stepN/f_0001…f_0096` |
| Transition N→N+1 (N = 1…8) | 24 each | `S_N+96` → `S_N+119` | `stepN/f_0097…f_0120` |
| Finale pull-back | 72 | 1056 → 1127 | `step9/f_0097…f_0168` |
| **Fly-through total** | **1,128** | 0 → 1127 | 9 directories (D27) |
| Doors | 72 | — | `doors/f_0001…f_0072` |
| Sprites | 12 stills | — | `props/*.png` |
| QA turntables | 6 × 24 = 144 | — | `renders/qa/turntable/<id>/` |

### 0.3 Render-time estimates

These are planning estimates. `render_all.sh --quality final` replaces them with a **measured** estimate before the confirmation prompt (SPEC §4.8), as follows:
1. Render three probe frames at final settings: step 1 hold frame 48, step 9 hold frame 48, and the last finale frame.
2. Weight them by segment.
3. Add 10% for scene load and output I/O.

| Job | This laptop: EEVEE draft (UHD iGPU) | This laptop: Cycles CPU | Desktop RTX 3060-class (OptiX) | RTX 4090-class |
|---|---|---|---|---|
| Scene build (`build_scene.py`) | 6–10 min | 6–10 min | 3–5 min | 2–3 min |
| QA turntable, 144 frames at 768², 48 spp | 5–10 min | 50–100 min | 4–6 min | 2–3 min |
| **Draft fly-through**, 1,128 frames at 960×540 | 1.3–2.5 h (4–8 s/frame) | 6–12 h (Cycles 16 spp, 20–40 s/frame) | 20–40 min | 10–20 min |
| Draft doors, 72 frames | 6–10 min | 25–50 min | 2–3 min | 1 min |
| **Final fly-through**, 1,128 frames at 1920×1080, 96 spp adaptive + OIDN | — | **95–190 h** (5–10 min/frame, so 4–8 days) | 4–8 h (12–25 s/frame) | 1.3–2.5 h (4–8 s/frame) |
| Final doors, 72 frames (with haze volume) | — | 8–15 h (7–12 min/frame) | 25–45 min | 10–20 min |
| Sprites, 12 stills (9 at 1024², 3 petals at 256²) | — | 20–40 min | 2–3 min | 1 min |
| Encode, WebP × 2 sizes + door video | 8–15 min | same | same | same |

**Recommendation.** Do all drafts and iteration on this laptop with EEVEE. Run the final render on a CUDA/OptiX machine, local or rented, at an estimated 2–8 h. If the final must run on this laptop, it is resumable: re-running skips finished frames. Budget about a week of wall-clock time, and keep the laptop on mains power with cooling.

Output sizes (estimated):

| Output | Size |
|---|---|
| Final PNG frames | about 2.6 MB each, so ~3.0 GB |
| WebP desktop (1920w, q75) | about 110 KB/frame, so ~125 MB |
| WebP mobile (960w, q70) | about 38 KB/frame, so ~43 MB |
| Door video | about 1.2 MB desktop, 0.45 MB mobile |

### 0.4 Data flow

```
content/golu.config.json ─┬─► blender/build_scene.py ─► renders/golu_<q>.blend + renders/manifest.json
                          │        └─ lib/{config,materials,environment,doll_factory,attributes,vahanas,props,dioramas,camera,render,mesh_utils,qa}.py
                          │   blender/render_steps.py ─► renders/<q>/steps/stepN/f_####.png
                          │   blender/render_doors.py ─► renders/<q>/doors/f_####.png
                          │   blender/render_props.py ─► renders/<q>/props/*.png
                          │   scripts/encode_frames.sh ─► web/static/{frames,frames-mobile,doors,props}/  +  web/src/lib/frames.json
                          └─► web/ (SvelteKit, imports config via $content alias) ─► web/build (static)
```

### 0.5 Final file tree (★ = added beyond SPEC §2, see D33)

```
SPEC.md PLAN.md README.md ASSETS_NEEDED.md DECISIONS.md ICONOGRAPHY.md .gitignore .gitattributes
content/golu.config.json
blender/
  build_scene.py  render_steps.py  render_doors.py  render_props.py
  render_qa.py ★  check_iconography.py ★
  lib/__init__.py  config.py ★  render.py ★  mesh_utils.py ★  qa.py ★
      materials.py  environment.py  doll_factory.py  attributes.py  vahanas.py  props.py  dioramas.py  camera.py
scripts/
  render_all.sh  encode_frames.sh  build_frames_json.mjs ★  lib/common.sh ★
renders/            (gitignored)
web/
  package.json  svelte.config.js  vite.config.ts  tsconfig.json  tailwind.config.ts  playwright.config.ts  vitest.config.ts
  static/{frames,frames-mobile,doors,props,audio}/  static/_headers  static/robots.txt
  src/app.html  src/app.css  src/app.d.ts
  src/routes/+layout.ts  +layout.svelte  +page.svelte
  src/lib/config.ts  frames.json (generated)  frames.ts  stores.ts  theme.ts
  src/lib/engine/{FrameCache.ts,coverFit.ts,scrollMap.ts,hotspots.ts,scrollLock.ts}
  src/lib/components/{Entrance,AgalLoader,FrameScroller,StepTitleCard,Hotspots,InfoCard,StepNavigator,DustLayer,LampFlicker,ReducedMotionView,BrassPanel,BrassButton}.svelte
  src/lib/rituals/{RitualBar,PlateRitual,Prasadam}.svelte  {flame,smoke,steam,petals,orbit,glow,ritualState}.ts
  src/lib/audio/{audio.ts,synth.ts,AudioControls.svelte}
  src/lib/a11y/motion.ts
  tests/unit/*.test.ts  tests/e2e/*.spec.ts
```

---

## 1. Shared conventions used by all Blender modules

### 1.1 Golu geometry (from `layout`)

- Tier *n* (1 = bottom, 9 = top):
  - width `w_n = width_bottom − (n−1)·(width_bottom − width_top)/8`, so 2.60 m down to 1.40 m in 0.15 m steps.
  - top surface height `z_n = n·rise` (0.24 to 2.16 m).
  - tread front edge `y_n = −(9−n)·tread`. The top tier sits against the back wall at y = 0, and lower tiers step toward the camera.
- Usable doll width is `usable_width_ratio·w_n`. The front-row doll line is `y_n + 0.09`, and the back row is `+back_row_offset`.
- The kuthuvilakku pair stands on the floor at x = ±(w_1/2 + 0.42), y = y_1 − 0.15.
- The floor kolam is centred at (0, y_1 − 0.55 − half its size).

### 1.2 Doll canonical frame

Each doll is built at the origin, standing on z = 0 (the pedestal bottom) and facing −Y. Its height is `H = archetype_base_cm × scale / 100` m (tables in §4). Head height is `0.20·H` for adults, `0.24·H` for children and `0.30·H` for infants (SPEC §4.3: head about 1/5).

### 1.3 Mesh attributes written on every doll

These drive the single doll shader (D24, D25).

| Attribute | Domain / type | Meaning |
|---|---|---|
| `paint` | CORNER / FLOAT_COLOR | base paint colour (linear) |
| `pbr` | CORNER / FLOAT_VECTOR | x = metallic, y = roughness, z = kind (0 skin, 1 garment, 2 hair, 3 gold, 4 wood, 5 eye-white, 6 painted-detail, 7 scales/shell) |
| `garment_uv` | CORNER / FLOAT2 | u around the garment (0–1), v from hem (0) to waist or edge (1); (−1, −1) when not a garment |
| `zari` | CORNER / FLOAT | zari band layout id: 0 none, 1 hem band, 2 hem + pallu end, 3 both edges (angavastram) |

Object custom properties (read with Attribute nodes of type OBJECT):

| Property | Meaning |
|---|---|
| `head_center` (vec3) | head centre in object space |
| `head_radius` | head radius |
| `face_yaw` | face yaw offset |
| `mark_type` | 0 none, 1 tilak_dot, 2 namam, 3 vibhuti, 4 tilak_vertical |
| `eye_scale` | eye size multiplier |
| `brow_arch` | brow curvature |
| `face_kind` | 0 human, 1 elephant, 2 lion, 3 boar, 4 marapachi |
| `doll_id`, `step`, `slot` | strings / ints, used by verification |
| `hotspot_local` (vec3) | point projected for hotspots: head centre plus 0.3 × head radius upward |

---

## 2. Phase 1: config, materials, environment

**Goal:** a headless build of the empty Golu, meaning the room, 9 draped tiers, garlands, thoranam, banana stems, both kuthuvilakku and the lighting, and three draft stills that look warm and temple-like.

### 2.1 Files and functions, in build order

**1. `.gitignore`.** Ignores `renders/`, `web/node_modules/`, `web/.svelte-kit/`, `web/build/`, `web/static/frames*/`, `web/static/doors/`, `web/static/props/`, `web/src/lib/frames.json`, `*.blend1` and `__pycache__/`. `.gitattributes` sets `*.sh text eol=lf` so the scripts run in Git Bash.

**2. `content/golu.config.json`.** Already drafted.

**3. `blender/lib/__init__.py`.** Empty package marker (a docstring only).

**4. `blender/lib/config.py`**

```python
@dataclass(frozen=True) class CliArgs: config: Path; quality: Literal["draft","final"]; steps: list[int]; out: Path; empty: bool; verify: bool; only: list[str]; stride: int; resume: bool; frames: list[int] | None
@dataclass(frozen=True) class DollSpec: id: str; step: int; name_en: str; name_ta: str; archetype: str; model: str | None; skin: str; arms: int; attire: AttireSpec | None; attributes: tuple[str, ...]; extras: tuple[str, ...]; vahana: str | None; seat: str; pose: str; forehead: str | None; scale: float; position: PositionSpec
@dataclass(frozen=True) class AttireSpec: lower: str; upper: str; color: str; accent: str; zari: str
@dataclass(frozen=True) class PositionSpec: slot: int; x: float; row: Literal["front","back"]; turn: float
@dataclass(frozen=True) class StepSpec: id: int; title_en: str; cloth_color: str; story_props: tuple[str, ...]; dolls: tuple[DollSpec, ...]
@dataclass(frozen=True) class GoluConfig: raw: dict; layout: dict; palette: Palette; steps: tuple[StepSpec, ...]; prasadam: dict; seed: int
class Palette:  # wraps palette; all lookups return linear RGB
    def silk(self, key: str) -> RGB; def skin(self, key: str) -> RGB; def cloth(self, key: str) -> RGB
    def material(self, key: str) -> RGB; def token(self, key: str) -> RGB; def kelvin(self, key: str) -> float
def parse_cli(argv: list[str]) -> CliArgs                    # args after "--"; argparse with exit_on_error=False → clean message
def parse_steps(spec: str) -> list[int]                      # "1-9", "2,4,7", "3"
def load_config(path: Path) -> GoluConfig                    # json.load(utf-8) → validate → dataclasses
def validate_config(raw: dict) -> list[str]                  # required fields, enums, unique ids, slot order matches x order, arms ∈ {0,2,4,6,8,10}, len(attributes)==arms for figures, palette keys exist, 9 steps ids 1..9
def srgb_hex_to_linear(hexstr: str) -> RGB                   # IEC 61966-2-1 transfer function
def seed_for(*keys: object) -> int                           # zlib.crc32("/".join(map(str, keys)).encode()) ^ cfg seed
def rng_for(*keys: object) -> random.Random
def config_hash(path: Path) -> str                           # sha1 of config + every blender/*.py; written into the .blend for staleness checks
```

**5. `blender/lib/mesh_utils.py`.** Geometry helpers shared by every builder.

```python
def ensure_collection(name: str, parent: Collection | None = None) -> Collection
def new_mesh_object(name: str, verts, faces, collection: Collection, edges=()) -> Object
def bmesh_to_object(bm: BMesh, name: str, collection: Collection) -> Object
def lathe(name: str, profile: list[tuple[float, float]], segments: int = 48, collection=None, close_top=True, close_bottom=True) -> Object   # profile (r,z) polyline → Screw modifier 360° about Z, merge on axis, apply
def lathe_bm(profile, segments) -> BMesh                     # same, in bmesh (used when further vertex edits are needed: lamp spouts, pot lips)
def apply_all_modifiers(obj: Object) -> None                 # depsgraph-evaluated mesh → obj.data (no bpy.ops)
def metaball_object(name: str, elements: list[MetaElem], resolution: float, collection) -> Object   # unique base name (metaball family gotcha)
def metaball_to_mesh(mb: Object, name: str) -> Object        # new_from_object(evaluated) then delete metaball datablock
def voxel_remesh(obj: Object, voxel: float, smooth_iters: int = 2) -> None   # Remesh(VOXEL) + Laplacian/Corrective smooth, applied
def add_subsurf(obj: Object, viewport: int, render: int) -> Modifier
def solidify(obj: Object, thickness: float, offset: float = -1.0, apply: bool = True) -> None
def displace(obj: Object, tex: Texture, strength: float, mid: float = 0.5, vgroup: str | None = None, direction="NORMAL", apply=True) -> None
def shade_smooth(obj: Object, sharp_angle_deg: float | None = 35.0) -> None   # polygon smooth + Mesh.set_sharp_from_angle (4.1+)
def join(objs: list[Object], name: str) -> Object            # bmesh merge in a single target, preserves attributes/UV layers
def set_part_attributes(obj: Object, paint: RGB, metal: float, rough: float, kind: int, zari: int = 0) -> None
def set_garment_uv(obj: Object, fn: Callable[[Vector], tuple[float, float]]) -> None
def curve_object(name: str, points: list[Vector], bevel: float = 0.0, resolution: int = 12, cyclic: bool = False, taper: list[float] | None = None, collection=None) -> Object
def curve_to_mesh(obj: Object) -> Object
def catenary(p0: Vector, p1: Vector, sag: float, n: int) -> list[Vector]
def spiral_points(r0: float, r1: float, turns: float, height: float, n: int) -> list[Vector]
def bounds_world(obj: Object) -> tuple[Vector, Vector]
def set_origin_bottom_center(obj: Object) -> None
def instance_on_points_tree(name: str, seed: int, *, source: Literal["faces","curve"], density: float, min_dist: float, collection: Collection, scale_range: tuple[float, float], align_to_normal: bool, random_rot: Vector) -> NodeTree   # GN tree builder used by garlands, food, fields (D21)
def add_gn_modifier(obj: Object, tree: NodeTree, inputs: dict[str, Any]) -> Modifier
def link_instances_collection(name: str, objs: list[Object]) -> Collection   # hidden collection holding instance sources
```

**6. `blender/lib/render.py`.** Engine, colour, compositor and compatibility helpers.

```python
def blender_version() -> tuple[int, int, int]
def engine_id_eevee() -> str                                 # 'BLENDER_EEVEE_NEXT' (4.2–4.5) or 'BLENDER_EEVEE' (5.x) from enum items
def principled_input(node: Node, name: str) -> NodeSocket    # tolerant to renamed sockets
def configure_cycles_device() -> Literal["OPTIX","CUDA","HIP","METAL","ONEAPI","CPU"]   # prefer OPTIX>CUDA>HIP>METAL>ONEAPI, enable all GPUs, else CPU
def apply_quality(scene: Scene, quality: str, *, transparent: bool = False, resolution: tuple[int, int] | None = None) -> None
    # draft: 960×540, EEVEE (TAA 32, raytracing off, shadows on, volume samples 32) or Cycles 16 spp if EEVEE unavailable
    # final: 1920×1080, Cycles 96 spp, adaptive 0.01, OIDN (albedo+normal, GPU if available), light tree on,
    #        bounces total 8 / diffuse 3 / glossy 4 / transmission 6 / volume 1, clamp indirect 8, filter 1.5 px,
    #        persistent data on, seed 0, PNG RGB 8-bit compression 15 (RGBA for sprites)
def setup_color_management(scene: Scene) -> None             # view 'AgX', look containing 'Medium High Contrast', exposure −0.2, gamma 1
def compositor_tree(scene: Scene) -> NodeTree                # 4.x scene.node_tree / 5.x compositing_node_group
def setup_glare(scene: Scene, enabled: bool = True) -> None  # Glare BLOOM (4.2+) else FOG_GLOW; threshold 1.2, size 7, mix −0.85 → "slight bloom"
def set_glare(node: Node, **kwargs) -> None                  # property-or-socket setter
def kelvin_to_rgb(kelvin: float) -> RGB                      # Tanner Helland fit → linear; used for every light (EEVEE ignores Blackbody node on lights)
def frame_path(root: Path, step: int, local_index: int) -> Path   # .../stepN/f_0001.png
def is_frame_done(path: Path, min_bytes: int = 4096) -> bool # resume test: exists, size, PNG header + IEND
class ProgressLog:                                           # prints "step 3 · 57/120 · 6.2 s/f · ETA 0:04:13"
    def __init__(self, total: int, label: str) -> None
    def tick(self, seconds: float) -> None                   # EMA(α=0.15) for ETA
```

**7. `blender/lib/qa.py`.** Image statistics and QA stills.

```python
def image_stats(path: Path) -> dict   # numpy over bpy.data.images.load(): mean luminance, R/B ratio, % clipped (≥0.995 all channels), highlight hue (99th-pct luminance pixels), black-void % (luma<0.004)
def assert_warm(stats: dict) -> list[str]   # mean luma 0.10–0.38; R/B ≥ 1.45; clipped ≤ 0.1%; highlight hue 20°–55°; void ≤ 8% → list of failures
def qa_cameras(layout: dict) -> dict[str, Matrix]   # "establishing" (finale end pose), "step1", "step9" (Phase 1 only; camera.py supersedes)
def render_stills(scene: Scene, views: dict[str, Matrix], out_dir: Path, quality: str) -> list[Path]
def contact_sheet(paths: list[Path], cols: int, out: Path, thumb: int = 384) -> Path   # numpy tiling into one PNG
def alpha_report(path: Path) -> dict   # used in Phase 4: border alpha, islands, fringe ΔL
```

**8. `blender/lib/materials.py`.** Shader node setups. All base colours come from `Palette`.

```python
def get(key: str, **variant) -> Material                     # memoised factory dispatch
def clay_gloss() -> Material      # M_ClayGloss — the doll shader (D24)
def face_paint_group() -> NodeTree      # NG_FacePaint
def zari_group() -> NodeTree            # NG_Zari
def brush_strokes_group() -> NodeTree   # NG_Brush
def silk(color_key: str) -> Material    # M_Silk_<key>
def brass() -> Material; def gold() -> Material; def silver() -> Material
def teak() -> Material; def red_oxide() -> Material; def temple_wall() -> Material; def granite() -> Material
def rice_flour() -> Material; def terracotta() -> Material; def flame(kind: Literal["ghee","camphor","agal"]) -> Material
def marigold(color_key: str) -> Material; def jasmine() -> Material; def mango_leaf() -> Material
def banana_leaf() -> Material; def banana_stem() -> Material
def powder(color_key: str) -> Material       # kumkum / turmeric / vibhuti mounds on plates
def haze_volume() -> Material
def world(cfg: GoluConfig) -> World
def food(kind: str) -> Material              # chickpea, coconut, curry_leaf, mustard, pongal_rice, cashew, raisin, ghee_film, tamarind_rice, peanut, curd_rice, pomegranate, sambar_rice, veg_drumstick, veg_carrot, camphor
```

Shader recipes the executor must implement exactly:

- **M_ClayGloss**
  - Base Color: `Attribute(paint)`, multiplied by NG_Brush (Wave bands, scale 22, distortion 5, detail 3, on object coords rotated by `Object Info.Random·π`; ±5% value), then mixed through NG_Zari when `pbr.z==1`, then through NG_FacePaint when `pbr.z==0`.
  - Metallic: `pbr.x`. Roughness: `pbr.y + (Noise(scale 60) − 0.5)·0.08`.
  - **Coat Weight 0.6** (SPEC), Coat Roughness 0.06, Coat IOR 1.5. Normal: Bump(NG_Brush height, strength 0.03). Coat Normal stays flat geometry, so the varnish reads smooth over the brush strokes.
  - `pbr.z==4` (wood): Wave rings along Z with Noise distortion (Marapachi). `pbr.z==7` (scales and shell): Voronoi F1 rings.
- **NG_FacePaint** works in face space `p = (ObjectCoord − head_center) / head_radius`, rotated by `face_yaw`. All features are signed-distance shapes, masked to the front-facing hemisphere (`p.y < −0.2`):
  - Almond eyes: the intersection of two circles, width 0.30, centres x = ±0.33, z = +0.05. White sclera, black iris disc r = 0.085, kajal outline 0.035 thick, extended into a wing toward the temple.
  - Brows: arc band, thickness 0.03, radius 0.42, centred at z = −0.18.
  - Lips: lens shape at z = −0.42, width 0.22, red `lip`.
  - Forehead mark by `mark_type`:
    - namam: white U-band (outer r 0.16, inner r 0.10, upper half removed below z = 0.30) plus a red centre stripe 0.035 wide.
    - vibhuti: three horizontal white bands 0.035 tall at z = 0.36 / 0.44 / 0.52, plus a kumkum dot r = 0.035.
    - tilak_dot: kumkum dot r = 0.05 at z = 0.30.
    - tilak_vertical: red drop 0.04 × 0.14.

  Feature sizes are deliberately oversized (golu style) so the face reads at 40 px head height. `face_kind` swaps the layouts: elephant eyes are small and set wide at x = ±0.55; lion and boar heads use round eyes and a painted muzzle.
- **M_Silk_<key>** (step drapes)
  - Principled with Base from palette, Roughness 0.32, **Anisotropic 0.65**. Tangent: Tangent node (UV map, warp along u). Sheen Weight 0.45, Sheen Roughness 0.28, Sheen Tint = base lifted +25% value.
  - Weave micro-bump: Wave X × Wave Y at scale 900, strength 0.008.
  - Butta motifs: Voronoi (scale 18, randomness 0.3) distance < 0.08, gold.
  - **Zari border:** `UV.v > 0.9` gives Gold Principled (metallic 1, roughness 0.25) with a twill pattern (Wave scale 400 × Checker); a 0.012 contrast "kattam" line sits just inside it.
- **M_Brass:** metallic 1, base `brass`, roughness 0.26 + Noise(scale 40) × 0.12. Hammered bump: Voronoi F1, scale 70, strength 0.015. Patina: Ambient Occlusion (16 cm) inverted → mix toward dark olive-brown in crevices at 35%.
- **M_RedOxide:** base `red-oxide` with Noise mottling (scale 2.5, ±12% value); roughness 0.22–0.35; Coat 0.35. Joints: Brick texture 0.6 m with 2 mm mortar → bump 0.004 and darker line.
- **M_RiceFlour:** base `rice-flour`, roughness 0.95. Alpha breaks up at the ribbon edges (`|garment_uv.v − 0.5|·2 > 0.75 + Noise(scale 300)·0.3` makes it transparent). Bump: Noise(scale 900), strength 0.2.
- **M_Flame:** Emission. Colour: Gradient along the object's Z through a ColorRamp from flame-base (0) to flame-mid (0.35) to flame-tip (0.85). Strength 25 (ghee) / 45 (camphor) / 18 (agal). Mixed with Transparent by Layer Weight Facing^2 for a soft rim. The flame is invisible to shadow rays.
- **M_Marigold:** base from palette, with hue/value jitter from `Object Info.Random` (±0.03 hue, ±10% value; this works on GN instances). Subsurface Weight 0.25, radius petal-tinted. Roughness 0.55. Bump: Voronoi distance-to-edge, scale 35, for petal ruffles.
- **M_MangoLeaf / M_BananaLeaf:** UV-based midrib and veins (Wave across u), glossy roughness 0.35; mixed 15% with Translucent BSDF.
- **M_HazeVolume:** Principled Volume, density 0.035 falling off via a Gradient box mask, anisotropy 0.65, colour from `door_glow` kelvin.
- **World:** Background `world` colour at strength 0.6. No HDRI.

**9. `blender/lib/props.py`, environment section.** The doll-scale props are added in Phases 2–4.

```python
def build_kuthuvilakku(name: str, height: float, rng: Random, collection: Collection) -> tuple[Object, list[Light]]
    # Lathe (Screw) from a profile curve: stepped round base (Ø 0.30·H/1.25), stem with 3 knops, oil bowl Ø 0.18;
    # 5 V-spouts made in bmesh by pulling rim vertices in 5 angular windows outward/upward;
    # crown (prabhai) stacked lathe tiers + annam (hamsa) finial from metaballs; wicks = curved cylinders;
    # each wick → build_flame(); brass material
def build_flame(loc: Vector, height: float, kind: str, rng: Random, collection, power_w: float) -> tuple[Object, Light]
    # teardrop lathe r(t)=k·sin(πt)^0.75·(1−t)^0.35; lean ±6°; point light radius 0.012 m, color kelvin(flame), power_w;
    # seeded flicker: F-curve Noise modifier on light energy (±6%) and object scale (±3%), phase from rng (D28)
def build_agal_vilakku(loc: Vector, rng: Random, collection, lit: bool = True) -> Object   # terracotta lathe bowl + pinched spout (bmesh pull) + wick + flame (0.4 W)
def make_marigold_head(variant: int, color_key: str, rng: Random) -> Object   # icosphere(subdiv 3, r 0.016) + Displace(Voronoi, 0.004) + scale z 0.8 (SPEC)
def make_jasmine_bud(variant: int, rng: Random) -> Object                     # UV sphere scaled (0.35,0.35,1)·0.008, tapered, green calyx cone
def build_garland(name: str, path: list[Vector], rng: Random, collection, pattern: str = "M6J3") -> Object
    # curve along path → GN: Curve to Points (spacing 0.022) → index pattern (6 marigold : 3 jasmine) → Instance on Points
    # (Collection Info of 4 marigold + 3 jasmine variants, Pick Instance by Random Integer) → random rotation about tangent,
    # scale 0.9–1.1 (D21)
def build_thoranam(name: str, p0: Vector, p1: Vector, rng: Random, collection) -> Object
    # sagging string (catenary sag 0.06) + mango leaves every 0.07 m via GN; leaf = lanceolate outline mesh, folded on midrib
    # (Simple Deform BEND 25°), curved (BEND 30° along length); a marigold every 5th leaf
def build_banana_stem(name: str, height: float, rng: Random, collection) -> Object
    # pseudo-stem: lathe with sheath bands (Wave along Z), 5 leaves (parametric outline 1.2 m, midrib, droop via Curve
    # modifier, edge tears = 6–10 random slits), small banana bunch + purple flower bud
def build_kolam(name: str, dots: int, spacing: float, rng: Random, collection, symmetry: str = "D4") -> Object
    # mirror-curve (sikku) kolam (D22): diamond dot layout → seeded D4 mirror set → trace closed loops (reflections pulled toward their dot) →
    # Catmull-Rom smoothing → flat ribbon (width 0.007) via Curve to Mesh → garment_uv.v across width → M_RiceFlour;
    # pulli dots = small flattened discs at grid points
def kolam_loops(dots: int, mirrors: set[tuple[int, int, str]]) -> list[list[tuple[float, float]]]   # pure function, unit-tested in Blender python
```

**10. `blender/lib/environment.py`**

```python
@dataclass class StepHandle: n: int; width: float; z_top: float; y_front: float; depth: float; tread_obj: Object; cloth_obj: Object
@dataclass class EnvironmentHandles: steps: list[StepHandle]; lamps: list[Object]; lights: list[Light]; flame_points: list[Object]; collection: Collection
def build_environment(cfg: GoluConfig, quality: str) -> EnvironmentHandles
def build_room(cfg) -> Collection          # floor 9×9 m red oxide; back wall at y=+0.05; side walls; ceiling beams (teak); front wall with doorway at y=−6.0 (used by doors, D30)
def build_niche_wall(cfg, rows: int = 2, cols: int = 9, rng: Random = ...) -> list[Object]
    # modular niche tiles: horseshoe-arch (kudu) niche profile extruded 0.12 m, pilasters with pothigai bracket capitals
    # (stacked boxes + bevel), cornice band; temple_wall + granite; one agal vilakku per niche (lit)
def build_steps(cfg) -> list[StepHandle]   # 9 teak boxes per §1.1 (bevel 3 mm)
def build_cloth_drape(step: StepHandle, color_key: str, rng: Random) -> Object
    # grid 240×64 covering tread + front riser + side overhang; vertex group "hang" (0 at tread back → 1 at hem);
    # Displace A: Wave (bands along X, scale 9, distortion 3) strength 0.012 weighted by "hang" → vertical folds;
    # Displace B: Clouds noise 0.004 → softness; hem scallop by Wave on Z; Solidify 0.002; Subsurf 1; UV u along width,
    # v=1 at hem → zari band (D23)
def build_brass_trim(step: StepHandle) -> Object      # rounded rod along tread front edge (curve bevel r 0.004), brass
def build_decorations(cfg, steps) -> list[Object]     # garlands per tread edge (swags every 0.42 m, sag 0.06, plus 0.10 m drops at hooks), thoranam across top tier + 0.45 m, banana stems at x=±(w_1/2+0.75)
def place_kuthuvilakku(cfg, steps) -> tuple[list[Object], list[Light]]
def build_lighting(cfg, quality) -> list[Light]
    # Key: area 3.0×2.0 m at (−2.6, −4.2, 3.4) aimed at golu centroid, kelvin 2700, 450 W
    # Rim L/R: area 1.2×0.6 m at (±1.9, +0.4, 2.9) aimed down-forward, 2500 K, 120 W, diffuse 0.6/specular 1.2
    # Fill: area 2×2 m at (+2.8, −3.5, 1.4), 3000 K, 60 W
    # Practicals: kuthuvilakku 5 × 3.0 W each, agal 0.4 W each
def setup_world(cfg) -> None
```

**11. `blender/build_scene.py`**

```python
def main(argv: list[str]) -> int
def reset_scene() -> Scene                  # read_factory_settings(use_empty=True); metric units; fps from config
def build(cfg: GoluConfig, args: CliArgs) -> BuildResult   # Phase 1: environment only when --empty
def save(scene: Scene, path: Path, cfg_hash: str) -> None  # scene["config_hash"]; relative paths
def verify(cfg, result: BuildResult) -> list[str]          # Phase 1: tier dims/order, 9 drapes, 2 lamps × 5 flames, ≥ 9 garlands; extended in Phases 2–3
if __name__ == "__main__": sys.exit(main(sys.argv))
```

Phase 1 CLI: `--empty --qa-stills` renders `renders/qa/phase1_{establishing,step1,step9}.png` using `qa_cameras`.

**12. `blender/check_iconography.py`**

```python
def parse_rules(md_path: Path) -> list[Rule]       # finds the table under "## 1. Rules table"; columns as in ICONOGRAPHY.md
def matches(rule: Rule, doll: DollSpec, step: StepSpec) -> bool   # archetype list, exact id, or step:N
def check(cfg: GoluConfig, rules: list[Rule]) -> list[str]        # skin, arms, must_hold ⊆ attributes∪extras, vahana, forehead (doll or archetype default), attire colour; step rules
def main(argv) -> int                                              # prints PASS/FAIL table; exit 1 on violation
```

**13. `scripts/lib/common.sh`.** Shell helpers.

```bash
find_blender()        # $BLENDER → PATH → C:/Program Files/Blender Foundation/Blender 4.*/ → /Applications/Blender.app → /usr/bin
blender_version_ok()  # parse "Blender X.Y" ≥ 4.2
run_blender()         # "$BLENDER" -b --factory-startup --python-exit-code 1 -P "$script" -- "$@"
log() / die()         # timestamped to stderr and renders/logs/<date>.log
```

### 2.2 Phase 1 verification

| Acceptance: "Draft render of the empty Golu looks warm, temple-like and correctly lit" | How |
|---|---|
| Config is valid | `run_blender blender/check_iconography.py -- --config content/golu.config.json`, which runs `validate_config` then the rules. Expect 0 errors and 40 rules PASS. |
| Builds headless and deterministically | Run `blender -b -P blender/build_scene.py -- --config content/golu.config.json --empty --quality draft --qa-stills` twice. The `.blend` object counts and `qa_stills` PNG hashes must match. |
| Structure | `--verify` prints tiers 2.60 → 1.40 m in 0.15 m steps, 9 drapes with zari, 9 brass trims, ≥ 9 garlands, 1 thoranam, 2 banana stems, 2 kuthuvilakku × 5 lit wicks, ≥ 18 lit agal niches, 1 kolam. Expect 0 errors. |
| Warm and correctly lit (objective) | `qa.assert_warm` on all three stills: mean luminance 0.10–0.38, R/B ≥ 1.45, clipped ≤ 0.1%, highlight hue 20°–55°, black void ≤ 8%. |
| Warm and temple-like (visual) | Open the three PNGs and check: silk shows anisotropic sheen and folds; zari catches light; brass trim glints; marigold/jasmine alternation visible; thoranam leaves read as mango; kolam is crisp white on red oxide; lamp flames have bloom; niches glow; no pure-white hotspots; shadows go to warm brown, not grey or black. |
| Commit | `Phase 1: config, materials library, environment` |

---

## 3. Phase 2: doll factory, attributes, vahanas

**Goal:** `make_doll(spec) -> Object` builds any config entry as a stylised, hand-painted, varnished clay golu bommai, and the 6-doll QA turntable passes.

### 3.1 `blender/lib/doll_factory.py`

```python
@dataclass class ArchetypeTemplate: base_cm: float; head_ratio: float; build: str; shoulder_slope_deg: float; crown: str; default_mark: str; jewellery: str; hair: str; head_kind: str; lower_body: str; age: str; pedestal: str
ARCHETYPES: dict[str, ArchetypeTemplate]            # table §3.2
POSES: dict[str, PoseDef]                           # table §3.3
@dataclass class FigureParams: spec: DollSpec; tpl: ArchetypeTemplate; H: float; head_r: float; seed: int; palette: Palette
@dataclass class Joint: name: str; pos: Vector; frame: Matrix
@dataclass class Skeleton: joints: dict[str, Joint]; hands: list[HandFrame]; lap: Matrix; head_top: Vector; seat_height: float
@dataclass class HandFrame: index: int; side: Literal["R","L"]; pair: int; shoulder: Vector; elbow: Vector; wrist: Vector; grip: Matrix

def make_doll(spec: DollSpec, cfg: GoluConfig, collection: Collection) -> Object     # SPEC entry point; dispatches below; returns one joined object
def build_figure(params: FigureParams) -> Object                                     # human/deity path, steps 1–12 below
def resolve_params(spec: DollSpec, cfg: GoluConfig) -> FigureParams
def build_skeleton(params: FigureParams) -> Skeleton                                 # pure maths: proportions × POSES[pose]
def arm_fan(params: FigureParams, skel: Skeleton, n_arms: int) -> list[HandFrame]    # symmetric fan (below)
def body_metaballs(params, skel, name: str) -> Object                                # capsules/ellipsoids per bone, pot belly, nose bump, ears
def finish_body(obj: Object, params) -> None                                         # voxel remesh (H/170) → smooth ×2 → set attributes (skin) → subsurf (1 viewport / 1 render; 2 for H ≥ 0.25 m)
def special_head(kind: str, params, skel) -> Object                                  # elephant | lion | boar
def lower_body(kind: str, params, skel) -> Object                                    # fish | tortoise
def build_attire(params, skel, attire: AttireSpec) -> list[Object]                   # garment shells (below)
def build_hair(params, skel) -> list[Object]                                         # kondai, andal_kondai, braids, jata, kudumi, sikha, hair_knot, white_hair_bun, shaven
def build_crown(kind: str, params, skel) -> Object | None                            # kireedam | karanda_makuta | jata_makuta | turban_cloth | peacock_feather_crown
def build_jewellery(params, skel) -> list[Object]                                    # earrings, necklaces (torus chains), armlets, bangles, waist belt, anklets, nose ring
def build_jasmine(params, skel, around: str) -> Object                               # bud string instanced along a curve around the bun/braid
def attach_hands(params, skel, tokens: list[str]) -> list[Object]                    # mudra hand shapes + attribute placement (two-handed tokens consume a pair)
def attach_extras(params, skel, extras: list[str]) -> list[Object]                   # non-held items (§3.5)
def build_pedestal(params, seat: str) -> Object                                      # pedestal | peetam | lotus_seat | white_lotus_seat | water_pedestal | cloud_pedestal | pillar_throne | none (story seats come from dioramas)
def write_face_props(obj: Object, params, skel) -> None                              # §1.3 custom props
def finalize(parts: list[Object], spec: DollSpec) -> Object                          # join, origin bottom-centre, apply transforms, custom props, M_ClayGloss
def doll_footprint(obj: Object) -> tuple[float, float]                               # x/y extents for diorama spacing
def parameter_sweep(cfg: GoluConfig, out: Path) -> list[Path]                        # QA: arms 2/4/6/8/10 on one goddess; every skin; every vahana (incl. Garuda)
```

**Build steps inside `build_figure`.** These are the key techniques:

1. **Skeleton.** Joint positions come from `H` and the template. Shoulders are lowered by `shoulder_slope_deg` (18–24°) for the sloped golu silhouette. Hips and knees follow the pose.
2. **Body.**
   - Metaballs, with unique base name `mb_<id>`: an ELLIPSOID head (omitted for special heads), CAPSULE neck, two ELLIPSOID torso masses (chest, belly; the belly is scaled 1.6 for `pot_belly` and for Ganesha), and a pelvis.
   - Arms and legs are CAPSULE chains of radius 0.045·H (upper) tapering to 0.03·H.
   - Hands are mitten-like flattened ellipsoids, a golu convention. Fingers are painted.
   - The nose is a small ELLIPSOID (SPEC: "slightly modeled nose"). Ears are flattened ellipsoids.
3. **Mesh.** `metaball_to_mesh`, then **Voxel Remesh** at H/170 (about 1.3 mm), Laplacian smooth ×2, and **Subdivision Surface**. This gives soft sculpted clay forms. Write the skin attributes.
4. **Arm fan** for `n = arms`, in pairs p = 0…n/2−1:
   - Pair 0 is front: elbows forward, hands at chest or waist.
   - Pairs ≥ 1 pivot from a point 0.02·H behind and 0.015·H above the front shoulder. Elevation `θ_p = −5° + p·(70°/(n/2−1))` and outward splay `φ_p = 18° + p·10°`, mirrored left and right.
   - Upper arms of back pairs are shortened 8% per pair so the fan stays compact, as on real dolls.
   - Hands of back pairs face forward, holding emblems upright.
5. **Special heads.**
   - **Elephant (Ganesha, D11):** dome cranium with twin frontal bosses (kumbha). The trunk is a curve with tapered bevel curling to his left, ending at the modak in L1. Fan ears are cupped discs (Solidify 0.004) with pink inner paint. The left tusk is a full curved cone. The **right tusk** is a 30% stump, and its piece is the `danta` held in R1. Small eyes.
   - **Lion (Narasimha, lion vahana):** short muzzle, open mouth with red tongue and four fangs, nose pad. The mane is two rings of flame-shaped tufts (instanced flattened cones) around the face, painted orange-gold.
   - **Boar (Varaha):** elongated snout with a disc nose, two upturned tusks, small upright ears.
6. **Lower bodies.**
   - **Fish (Matsya):** from the waist, a metaball chain along an S-curve tapering to a forked tail fin (solidified shell). Scales use `pbr.z = 7` with Voronoi rings in the shader, blue-green to silver.
   - **Tortoise (Kurma):** a carapace dome (lathe) with a hex scute pattern (Voronoi), plastron, four flippers. The human torso rises from the front opening.
7. **Garments** as shaped shells (SPEC), all painted with `paint` = silk colour, `garment_uv` and the `zari` id:
   - `saree`: lathe "bell" from waist radius to hem radius. Its profile comes from hip and knee joints, and seated poses use the lap drape below. Front pleats (kosuvam) come from a Wave modifier on the front 60° sector. The pallu is a ribbon curve from the right hip, across the chest, over the left shoulder and down the back. Zari id 2 (hem plus pallu end).
   - `veshti` / `veshti_short` / `panchakacham`: tube from waist to ankle (or knee). Panchakacham adds a pleated front fold and a kachcham tuck between the legs. Zari id 1.
   - `pavadai` / `half_saree`: flared lathe skirt to the ankle, plus a half-saree ribbon over the left shoulder.
   - `angavastram` / `shawl` / `towel_shoulder`: ribbon over both shoulders, ends falling in front. Zari id 3.
   - `blouse` / `shirt` / `deerskin` / `sash`: painted onto the torso skin region (`pbr.z = 1` on the corners above the waist inside the sleeve mask). Deerskin adds a spotted pattern.
   - `trousers` / `shorts`: twin tubes.
   - Lap drape for seated poses: a subdivided plane shrink-wrapped over the folded-leg capsules with 2 mm offset, then Solidify.
8. **Hair and crowns.**
   - **Kireedam:** stacked lathe profile, meaning a band, three tiers of flared rings, a tapering spire and a knob finial. Small side ornaments are flattened metaball scrolls.
   - **Karanda makuta:** stacked bowls (goddesses).
   - **Jata:** coiled tubes (sages).
   - **Kondai:** sphere bun. Andal's `andal_kondai` is tilted 35° to her left and wrapped in jasmine.
   - **Kudumi / sikha:** a tuft.
9. **Jewellery** (gold paint, metal = 1, rough 0.28): makara-kundala earrings (torus plus drop); two necklaces as **torus chains** along catenaries with a pendant; keyura armlets; bangles; oddiyanam waist belt with a medallion; anklets; nose ring.
   - The `jewellery` level sets the counts: `simple` = 1 necklace, `royal` = 2 plus armlets, `divine` = 3 plus a yajnopavita (sacred thread) and a vanamala garland.
   - **Jasmine** is added for every goddess, consort and bride (SPEC).
10. **Hands.** For each token in `attributes`:
    - Mudras shape the mitten: abhaya (palm forward, fingers up), varada (palm forward, fingers down), kati (on hip), anjali (front pair meets at the sternum), chin and hridaya (hand at the heart), lola (hanging), point_up (index raised), and `abhaya_coins` / `varada_coins` (mudra plus a coin stream).
    - Otherwise `attributes.build(token, size)` is aligned so its grip frame matches `HandFrame.grip`. A two-handed token sets its secondary anchor at the partner hand: veena, flute, bow+arrow pair, garland, nadaswaram, churning rope, potters_wheel, laptop.
11. **Pedestal.** Every doll gets one (SPEC):
    - `pedestal`: oval two-step plinth 0.015·H tall, painted `pedestal` maroon with a gold edge line.
    - `lotus_seat`: two rings of 12 and 16 cupped lotus petals (instanced), pink to white, plus a seed disc.
    - `peetam`: stepped square throne 0.12·H with a gold band.
    - `water_pedestal`: blue wave-painted oval.
    - `pillar_throne`: a broken pillar stump behind Narasimha.
    - `cloud_pedestal`: lumpy white metaball cloud.
12. **Finalize.** Join all parts into one object, origin at the pedestal bottom, `M_ClayGloss`, face props, hotspot point. Assert the head-height ratio is within ±0.02 of the template.

### 3.2 Archetype parameter table

`H cm` is the standing-equivalent height before `scale`. Seated poses fold to about 0.72·H.

| archetype | H cm | head | build | crown / hair | default mark | jewellery | special |
|---|---|---|---|---|---|---|---|
| deity_vishnu_form | 24 | 0.20 | divine-slim | kireedam | namam | divine | — |
| avatar_matsya | 24 | 0.20 | divine-slim | kireedam | namam | divine | lower: fish |
| avatar_kurma | 22 | 0.20 | divine-slim | kireedam | namam | divine | lower: tortoise |
| avatar_varaha | 24 | 0.21 | divine-broad | kireedam | namam | divine | head: boar |
| avatar_narasimha | 24 | 0.22 | divine-broad | kireedam | namam | divine | head: lion |
| vamana_vatu | 24 | 0.24 | child | kudumi | namam | none | — |
| sage_warrior | 24 | 0.20 | athletic | jata | namam | simple + rudraksha | — |
| prince | 23 | 0.20 | slim | kireedam | namam | royal | — |
| king | 23 | 0.20 | portly | kireedam | namam | royal | moustache or beard |
| sage | 23 | 0.20 | lean-elder | jata + beard | per doll | rudraksha | — |
| musician | 22 | 0.20 | average | none | vibhuti | simple | — |
| goddess / goddess_consort / goddess_warrior | 22 | 0.20 | feminine | karanda_makuta or kondai | tilak_dot | divine | jasmine |
| deity_murugan | 23 | 0.20 | youthful | kireedam | vibhuti | divine | — |
| deity_ganesha | 22 | 0.24 | stout | kireedam | vibhuti | divine | head: elephant; pot belly |
| tribal_girl | 21 | 0.20 | feminine | loose bun + wild flowers | tilak_dot | bead | — |
| village_woman / village_man | 21 / 22 | 0.20 | average | kondai / turban cloth | tilak_dot / vibhuti | simple | — |
| chettiar | 22 | 0.20 | stout | bald-ish crown | vibhuti | gold chain | pot belly, moustache |
| modern_woman / modern_man | 21 / 22 | 0.19 | average | kondai+jasmine / short hair | tilak_dot / none | simple | spectacles, badge |
| schoolchild_girl / schoolchild_boy | 15 | 0.24 | child | braids / short hair | tilak_dot / none | none | — |
| saint_vaishnava / saint_andal | 22 | 0.20 | lean | sikha / andal_kondai | namam | tulasi mala / divine | — |
| saint_shaiva / child_saint | 22 | 0.20 / 0.26 | lean / child | shaven / child curls | vibhuti | rudraksha | — |
| poet_sage | 22 | 0.20 | lean-elder | hair knot + beard | none | none | — |
| elder_woman | 20 | 0.20 | stooped | white bun | vibhuti | rudraksha | — |
| infant_krishna / child_krishna | 22 | 0.30 / 0.24 | infant / child | curls + peacock feather | namam | waist chain, anklets | — |
| marapachi | 16 | 0.22 | carved-cylinder | carved bun or turban | per doll | none | face_kind 4, wood (D12) |

### 3.3 Pose library (`POSES`)

Each pose sets joint angles and seat height. `riding` places the pelvis on the vahana saddle anchor.

`standing`, `standing_tribhanga` (three-bend hip sway 8°), `standing_crossed_legs` (Venugopala), `standing_lifted_knee` (Varaha, left foot on a rock), `standing_offering` (garland raised), `standing_playing`, `standing_slinging`, `standing_lifting` (left arm overhead), `standing_stooped`, `standing_rigid` (Marapachi), `seated_throne`, `seated_lalitasana` (one leg pendant), `seated_padmasana`, `seated_cross_legged`, `seated_floor` (children), `seated_veena`, `seated_writing`, `seated_churning`, `seated_squat_vending`, `seated_squat_wheel`, `seated_cart`, `bending_kolam`, `crawling`, `dancing_child` (Sambandar), `dancing_one_leg` (Kaliya), `riding`, `upright_tail` (Matsya), `upright_shell` (Kurma).

### 3.4 `blender/lib/attributes.py`

```python
@dataclass class AttributeDef: builder: Callable[[float, Palette, Random], Object]; hands: int; grip: Matrix; size_ratio: float; paint: str
REGISTRY: dict[str, AttributeDef]
def build_attribute(token: str, doll_H: float, palette: Palette, rng: Random) -> Object   # origin = grip point, +Z = grip axis, +Y = facing
def is_mudra(token: str) -> bool
```

| token | technique |
|---|---|
| shankha | Valampuri conch: spiral lathe via Screw with offset (3 turns), flared lip, gold band (metal = 1) |
| chakra | Sudarshana: torus rim, 8 spokes, hub, **flame edges** = 16 instanced flattened teardrops round the rim (gold/orange) |
| gada | lathe mace: grip, fluted head (8 radial Wave bulges), finial |
| padma / nilotpala | 2–3 rings of cupped petals (instanced), pink or blue, on a curved stalk |
| vel | shaft plus leaf-shaped (rhombic-lens) blade with central ridge, gold, vibhuti stripe painted on the blade |
| bow / arrow / bow_arrow | recurved bow from a tapered-bevel curve plus a string curve; arrow shaft, head and fletching |
| veena | Saraswati veena: carved resonator (kudam, lathe), neck (dandi) with 24 frets, top gourd, curved yali-head scroll, 4 + 3 strings; two-handed |
| tambura, chipla | Narada's single-gourd tambura; small paired wooden clappers |
| parashu | crescent axe blade (extruded profile) on a haft |
| hala, musala | plough (curved beam with share), pestle-club |
| khadga, shield | curved sword with hilt; round shield with boss |
| trishula | shaft, three prongs (side prongs curved), damaru knot |
| butter_pot, butter_ball | small clay pot (lathe) with a white butter mound and drips; butter lump |
| flute | slim tube with painted holes; two-handed |
| kalasam | brass lathe pot, 5 mango leaves (fanned instances), coconut (displaced sphere, coir noise, three eyes, turmeric smear), kumkum dots |
| ankusha, pasha, modaka, danta | goad; noose (torus loop plus tail); modak (pleated lathe, Wave pleats); broken tusk |
| chatra, kamandalu | palm-leaf umbrella (cone with ribs); spouted water pot |
| palm_leaf, stylus, peacock_quill | bundled olai leaves with cord; ezhuthani; peacock feather (eye shader shared with vahanas) |
| parrot | small green metaball bird with red beak (Andal) |
| garland | thick wedding garland: torus path with instanced roses, jasmine and marigold; two-handed |
| japa_mala, rudraksha (extra), tulasi_mala (extra) | torus-chain beads |
| milk_cup | small gold cup |
| walking_stick, danda, goad_stick, reins | tapered sticks; rope curve |
| sling | Valli's kavan: rope curve with a pouch and stone |
| thavil_stick, thavil_thimble | drum stick; thimbled fingers (the drum itself is the `thavil_drum_on_strap` extra) |
| nadaswaram | long conical wooden bore plus metal bell (lathe); two-handed |
| churning_rope | Yashoda's churn: rod with star dasher plus rope wraps (the pot is an extra) |
| potters_wheel | ground-anchored wheel disc with a clay pot mid-throw; two-handed |
| weighing_scale, ledger, measure_padi | balance with two pans; cloth-bound book; brass measure |
| kolam_pinch, kolam_bowl | fingers pinched with powder; small bowl of rice flour |
| laptop | hinged box pair; screen emission 0.6 showing a soft orbit graphic (no text or logos) |
| clipboard, point | board with paper; pointing hand |
| paddy_sheaf, sugarcane, banana_bunch | instanced grains on stalks; segmented cane; bunch |
| infant | mini figure built by `build_figure` recursively (archetype infant_krishna proportions, peach, holding a padma), lap-anchored |
| bhudevi | small seated goddess on Varaha's left arm, built recursively |
| serpent_tail, lift_hill_finger | grip anchors only (geometry is from Kaliya / Govardhana story props) |
| pot_on_head_hold | hand raised to steady the pot (the pot is an extra) |
| flag | Adi Lakshmi's red pennant on a staff |

### 3.5 `extras` handled by `attach_extras`

| extra | what it adds |
|---|---|
| jasmine | bud string round the bun or braid |
| id_badge | lanyard and card |
| spectacles | torus rims |
| braids | twin braids with ribbon |
| kudumi, sikha, jata, hair_knot, white_hair_bun, shaven_head, andal_kondai, turban_cloth | hair / crown overrides |
| sacred_thread, sacred_thread_serpent | yajnopavita curve, or a small serpent for Ganesha |
| rudraksha, tulasi_mala, bead_necklace, gold_chain | beads |
| kireedam, karanda_makuta, peacock_feather_crown | crown override |
| moustache, beard | painted moustache; metaball beard |
| pot_belly | belly scale 1.6 |
| quiver | quiver on the back |
| groom_garland | garland already worn by the groom |
| bridal_jewellery, royal_jewellery | jewellery level up |
| nose_ring | gold nose ring |
| bow_on_shoulder | bow carried on the shoulder |
| hiranyakashipu_on_lap | stylised reclining figure across the lap, no gore |
| infant_on_lap | lap anchor for the `infant` token |
| coin_pile | gold-coin heap at the seat (GN scatter of discs) |
| vegetable_basket | wicker basket (Wave weave) with instanced brinjal, tomato, chilli, drumstick, greens |
| churning_pot | tall curd pot |
| pot_on_head | pot balanced on a head cushion |
| mini_kolam | `build_kolam(dots=5)` patch on the tread |
| thavil_drum_on_strap | barrel drum with tension straps |
| uzhavarappadai_on_shoulder | small hoe against the left shoulder |
| golden_cymbals_at_feet | pair of cymbals at Sambandar's feet |
| anklets, waist_chain | jewellery |
| wild_flowers_hair, flowers_hair | flowers in the hair |
| garland_on_shoulder | Andal's garland |

### 3.6 `blender/lib/vahanas.py`

```python
def build_vahana(kind: str, size: float, palette: Palette, rng: Random, pose: str = "standing") -> tuple[Object, Matrix | None]   # returns (mesh, rider saddle anchor or None)
def peacock(size, palette, rng, pose) -> Object   # metaball body/neck/head + crest (instanced stalks), wings; fanned tail: 150 eye-feathers on 5 concentric arcs (GN Instance on Points, radial Align Euler to Vector); feather shader = radial ocellus ColorRamp (navy→royal blue→turquoise→bronze→green) + Wave barbs + Thin Film 380 nm iridescence
def lion(size, palette, rng) -> Object            # quadruped skeleton + metaballs, curly mane (instanced tufts), tufted tail, saddle anchor for Durga
def mouse(size, palette, rng) -> Object           # mooshika holding a modak, curve tail
def swan(size, palette, rng) -> Object            # hamsa/annam: white body, S-neck, ornamental scroll tail, orange beak
def garuda(size, palette, rng) -> Object          # kneeling figure, eagle beak, spread wings, anjali; built only by the parameter sweep (no doll uses it)
def elephant(size, palette, rng, pose) -> Object  # charging (trunk raised, ears spread) or standing; caparison optional
def gaja_pair(size, palette, rng) -> Object       # two small elephants flanking, trunks raised holding kalashas over the goddess
def cow(size, palette, rng, variant: Literal["cow","calf","bullock"]) -> Object   # white-cream; painted horns; neck bell; kumkum forehead; bullock = Kangayam hump
def bullock_pair(size, palette, rng) -> Object    # two bullocks yoked (used by the cart)
def horse(size, palette, rng) -> Object           # white horse, rearing front leg, red caparison with zari, saddle anchor for Kalki
def kaliya_anchor(...)                            # Kaliya geometry lives in dioramas (SPEC §4.4); returns the dance anchor only
def quadruped_skeleton(body_len, height, neck, head, pose) -> Skeleton   # shared
```

Vahana sizes, as height in cm at the shoulder or body: elephant 20, peacock 18 (tail span 24), cow 14, calf 9, horse 15, lion 13, mouse 4, swan 9, gaja_pair 9 each, bullock 13, garuda 18.

### 3.7 `blender/render_qa.py`

```python
def main(argv) -> int     # --dolls s9_ganesha,s2_rama,s3_sita,s4_murugan,s2_narasimha,s5_chettiar (default) --angles 24 --quality draft|final --sweep
def turntable_scene(cfg) -> Scene   # neutral warm studio: 2700 K key + 2 rims, maroon silk sweep backdrop, same AgX/glare as the main scene
def render_turntable(doll: Object, out_dir: Path, angles: int, quality: str) -> list[Path]   # 768×768; 15° steps; camera at doll eye height ×1.1, 50 mm
def thumbnails(paths, out: Path, px: int = 160) -> Path   # small-size legibility sheet (front view only)
```

The QA set is the SPEC six. "Rama" is **s2_rama** (four arms, shankha and chakra, bow and arrow), which exercises the most factory features. "Sita" is s3_sita. Murugan renders with s4_peacock beside him.

Outputs:
- `renders/qa/turntable/<id>/f_01…24.png`
- `renders/qa/turntable_<id>.png`: 8-view contact sheet
- `renders/qa/thumbs.png`: front views at 160 px tall
- `renders/qa/sweep.png`: arms 2/4/6/8/10, every skin, every vahana including Garuda

### 3.8 Phase 2 verification

| Acceptance: "QA turntable of 6 dolls reads clearly as traditional painted clay golu bommai with correct iconography" | How |
|---|---|
| Config iconography | `check_iconography.py` passes all 40 rules (runs again; the config may have changed). |
| Structural asserts | `render_qa.py` logs for each doll: arms count = spec, every attribute token has geometry within 2 cm of its hand, vahana present, pedestal present, head ratio within ±0.02, single mesh object, `M_ClayGloss` only. Any failure exits 1. |
| Clay look | On the contact sheets: a sharp varnish highlight (coat) on the cheeks and silk; brush-stroke variation visible up close; soft remeshed forms (no faceting, no metaball lumps); a visible pedestal; painted rather than modelled faces. |
| Faces at small size | `thumbs.png` at 160 px: eyes, kajal, brows, lips and forehead mark distinguishable on all six. |
| Iconography (visual) | Tick the ICONOGRAPHY.md §2 "T" column for each of the six. Ganesha: right tusk broken, trunk to modak, mouse. Rama: four arms, chakra R2, shankha L2, bow and arrow. Sita: jasmine, saree pallu, garland. Murugan: vel, vibhuti, peacock tail fanned. Narasimha: mane, fangs, namam. Chettiar: moustache, gold chain, scales. |
| Parameter coverage | `sweep.png` shows 2/4/6/8/10-arm fans symmetric without interpenetration, all 7 skins, and all 8 SPEC vahanas plus gaja_pair and bullock. |
| Commit | `Phase 2: doll factory, attributes, vahanas` |

### 3.9 Doll parameter spec, every doll in the config

This table is generated from `content/golu.config.json`; regenerate it if the config changes. `H cm` = archetype or species base × `scale` (standing-equivalent for figures; overall height for objects; for animals, shoulder or body height). Hands are listed as `[R1, L1, R2, L2, …]` (D17). `x` is normalised across the usable step width (D18).

#### Step 1 — Technology & Modern India (cloth: maroon; story props: rocket_gantry, lunar_patch, rail_track, metro_viaduct)

| slot | id | archetype | H cm | skin | arms | attire (lower/upper · color/accent · zari) | hands [R1,L1,R2,L2,…] | extras | vahana | seat | pose | mark | x · row · turn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s1_pslv | object:pslv | 46.0 | none | 0 | — | — | — | — | launch_pad | static | — | -0.86 · back · 6° |
| 2 | s1_dish | object:satellite_dish | 16.0 | none | 0 | — | — | — | — | plinth | static | — | -0.64 · back · 14° |
| 3 | s1_scientist_woman | modern_woman | 21.0 | wheat | 2 | saree/blouse · kumkum/turmeric · gold | anjali, anjali | jasmine, id_badge | — | pedestal | standing | tilak_dot | -0.46 · front · 8° |
| 4 | s1_scientist_man | modern_man | 22.0 | wheat | 2 | trousers/shirt · shirt-blue/khaki · none | point, clipboard | id_badge, spectacles | — | pedestal | standing | none | -0.31 · front · -4° |
| 5 | s1_chandrayaan | object:chandrayaan3 | 10.0 | none | 0 | — | — | — | — | lunar_patch | static | — | -0.09 · front · 0° |
| 6 | s1_child_girl | schoolchild_girl | 15.0 | wheat | 2 | pavadai/blouse · parrot-green/turmeric · gold | laptop, laptop | jasmine, braids | — | pedestal | seated_floor | tilak_dot | 0.11 · front · 10° |
| 7 | s1_child_boy | schoolchild_boy | 15.0 | wheat | 2 | shorts/shirt · school-white/khaki · none | point, lola | — | — | pedestal | seated_floor | none | 0.24 · front · -16° |
| 8 | s1_vande_bharat | object:vande_bharat | 9.0 | none | 0 | — | — | — | — | rail_track | static | — | 0.52 · back · -12° |
| 9 | s1_metro | object:metro_coach | 8.0 | none | 0 | — | — | — | — | metro_viaduct | static | — | 0.86 · front · -8° |

#### Step 2 — Dasavataram (cloth: kumkum; story props: none)

| slot | id | archetype | H cm | skin | arms | attire (lower/upper · color/accent · zari) | hands [R1,L1,R2,L2,…] | extras | vahana | seat | pose | mark | x · row · turn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s2_matsya | avatar_matsya | 24.0 | blue | 4 | none/sash · pitambara/kumkum · gold | abhaya, varada, chakra, shankha | — | — | water_pedestal | upright_tail | namam | -0.9 · front · 4° |
| 2 | s2_kurma | avatar_kurma | 22.0 | blue | 4 | none/sash · pitambara/kumkum · gold | abhaya, varada, chakra, shankha | — | — | water_pedestal | upright_shell | namam | -0.7 · front · 3° |
| 3 | s2_varaha | avatar_varaha | 24.0 | blue | 4 | panchakacham/angavastram · pitambara/kumkum · gold | abhaya, bhudevi, chakra, shankha | — | — | pedestal | standing_lifted_knee | namam | -0.5 · front · 2° |
| 4 | s2_narasimha | avatar_narasimha | 24.0 | blue | 4 | panchakacham/angavastram · pitambara/kumkum · gold | abhaya, varada, chakra, shankha | hiranyakashipu_on_lap | — | pillar_throne | seated_throne | namam | -0.3 · front · 1° |
| 5 | s2_vamana | vamana_vatu | 17.3 | blue | 2 | veshti_short/deerskin · ivory/deerskin · none | chatra, kamandalu | sacred_thread, kudumi | — | pedestal | standing | namam | -0.1 · front · 0° |
| 6 | s2_parasurama | sage_warrior | 24.0 | blue | 4 | veshti/bare · saffron/deerskin · gold | parashu, kati, chakra, shankha | sacred_thread, jata, rudraksha | — | pedestal | standing | namam | 0.1 · front · 0° |
| 7 | s2_rama | deity_vishnu_form | 24.0 | blue | 4 | panchakacham/angavastram · pitambara/kumkum · gold | arrow, bow, chakra, shankha | quiver | — | pedestal | standing_tribhanga | namam | 0.3 · front · -1° |
| 8 | s2_balarama | deity_vishnu_form | 24.0 | peach | 4 | panchakacham/angavastram · nilambara/pitambara · gold | musala, hala, chakra, shankha | — | — | pedestal | standing | namam | 0.5 · front · -2° |
| 9 | s2_krishna | deity_vishnu_form | 24.0 | blue | 4 | panchakacham/angavastram · pitambara/peacock-blue · gold | flute, flute, chakra, shankha | peacock_feather_crown | — | pedestal | standing_crossed_legs | namam | 0.7 · front · -3° |
| 10 | s2_kalki | deity_vishnu_form | 24.0 | blue | 4 | panchakacham/angavastram · pitambara/kumkum · gold | khadga, shield, chakra, shankha | — | horse | pedestal | riding | namam | 0.9 · front · -5° |

#### Step 3 — Sita Kalyanam (cloth: turmeric; story props: wedding_mandapam)

| slot | id | archetype | H cm | skin | arms | attire (lower/upper · color/accent · zari) | hands [R1,L1,R2,L2,…] | extras | vahana | seat | pose | mark | x · row · turn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s3_thavil | musician | 22.0 | wheat | 2 | veshti/angavastram · white/maroon · gold | thavil_stick, thavil_thimble | thavil_drum_on_strap | — | pedestal | standing_playing | vibhuti | -0.9 · front · 14° |
| 2 | s3_nadaswaram | musician | 22.0 | wheat | 2 | veshti/angavastram · white/kumkum · gold | nadaswaram, nadaswaram | — | — | pedestal | standing_playing | vibhuti | -0.73 · front · 16° |
| 3 | s3_vasishta | sage | 23.0 | wheat | 2 | veshti/angavastram · saffron/ivory · none | abhaya, kamandalu | jata, beard, rudraksha, sacred_thread | — | pedestal | standing | namam | -0.56 · back · 12° |
| 4 | s3_dasaratha | king | 24.2 | wheat | 2 | panchakacham/angavastram · maroon/pitambara · gold | abhaya, kati | moustache, royal_jewellery, kireedam | — | pedestal | standing | namam | -0.4 · front · 14° |
| 5 | s3_lakshmana | prince | 22.3 | peach | 2 | panchakacham/angavastram · parrot-green/pitambara · gold | anjali, anjali | bow_on_shoulder, kireedam | — | pedestal | standing | namam | -0.25 · front · 16° |
| 6 | s3_rama | prince | 24.2 | blue | 2 | panchakacham/angavastram · pitambara/kumkum · gold | garland, garland | kireedam, groom_garland | — | pedestal | standing_offering | namam | -0.07 · front · 32° |
| 7 | s3_sita | goddess_consort | 21.6 | peach | 2 | saree/blouse · kumkum/turmeric · gold | garland, garland | jasmine, bridal_jewellery, nose_ring | — | pedestal | standing_offering | tilak_dot | 0.09 · front · -32° |
| 8 | s3_janaka | king | 24.2 | wheat | 2 | panchakacham/angavastram · ivory/maroon · gold | varada, abhaya | beard, royal_jewellery, kireedam | — | pedestal | standing | namam | 0.3 · front · -14° |
| 9 | s3_vishwamitra | sage | 23.0 | wheat | 2 | veshti/angavastram · saffron/deerskin · none | abhaya, danda | jata, beard, rudraksha, sacred_thread | — | pedestal | standing | vibhuti | 0.5 · back · -12° |
| 10 | s3_dhanush | object:shiva_dhanush_broken | 6.0 | none | 0 | — | — | — | — | none | static | — | 0.76 · front · -20° |

#### Step 4 — Murugan Valli Kalyanam (cloth: maroon; story props: thinai_field, paran_platform)

| slot | id | archetype | H cm | skin | arms | attire (lower/upper · color/accent · zari) | hands [R1,L1,R2,L2,…] | extras | vahana | seat | pose | mark | x · row · turn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s4_valli | tribal_girl | 19.9 | wheat | 2 | half_saree/blouse · parrot-green/kumkum · gold | sling, lola | wild_flowers_hair, bead_necklace | — | paran_platform | standing_slinging | tilak_dot | -0.8 · back · 18° |
| 2 | s4_elephant | animal | 20.0 | elephant-grey | 0 | — | — | — | elephant | pedestal | charging | none | -0.42 · front · -38° |
| 3 | s4_murugan | deity_murugan | 24.8 | peach | 2 | panchakacham/angavastram · kumkum/pitambara · gold | abhaya, vel | kireedam, rudraksha | — | pedestal | standing | vibhuti | 0.02 · front · -20° |
| 4 | s4_peacock | animal | 18.0 | none | 0 | — | — | — | peacock | pedestal | fanned | none | 0.24 · back · -10° |
| 5 | s4_deivanai | goddess_consort | 21.6 | peach | 2 | saree/blouse · turmeric/rani-pink · gold | lola, nilotpala | jasmine, karanda_makuta, nose_ring | — | pedestal | standing_tribhanga | tilak_dot | 0.48 · front · -14° |
| 6 | s4_narada | sage | 21.8 | peach | 2 | veshti/angavastram · ivory/saffron · none | tambura, chipla | sikha, tulasi_mala, sacred_thread | — | cloud_pedestal | standing | namam | 0.8 · front · -18° |

#### Step 5 — Village Life & Chettiar Set (cloth: kumkum; story props: chettiar_shop, drying_pots)

| slot | id | archetype | H cm | skin | arms | attire (lower/upper · color/accent · zari) | hands [R1,L1,R2,L2,…] | extras | vahana | seat | pose | mark | x · row · turn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s5_chettiar | chettiar | 22.0 | wheat | 2 | veshti/angavastram · white/turmeric · gold | weighing_scale, ledger | moustache, gold_chain, pot_belly | — | shop_counter | seated_cross_legged | vibhuti | -0.6 · back · 10° |
| 2 | s5_chettichi | village_woman | 19.9 | wheat | 2 | saree/blouse · brinjal/turmeric · gold | measure_padi, lola | jasmine, nose_ring, gold_chain | — | shop_counter | seated_cross_legged | tilak_dot | -0.4 · back · 4° |
| 3 | s5_vendor | village_woman | 19.9 | wheat | 2 | saree/blouse · mango-green/kumkum · none | lola, lola | vegetable_basket, flowers_hair | — | pedestal | seated_squat_vending | tilak_dot | -0.14 · front · 8° |
| 4 | s5_kolam_woman | village_woman | 19.9 | wheat | 2 | saree/blouse · turmeric/maroon · gold | kolam_pinch, kolam_bowl | jasmine, mini_kolam | — | pedestal | bending_kolam | tilak_dot | 0.06 · front · 0° |
| 5 | s5_potter | village_man | 22.0 | wheat | 2 | veshti_short/towel_shoulder · ivory/kumkum · none | potters_wheel, potters_wheel | turban_cloth | — | pedestal | seated_squat_wheel | vibhuti | 0.3 · front · -6° |
| 6 | s5_cow | animal | 14.0 | none | 0 | — | — | — | cow | pedestal | standing | none | 0.52 · back · -18° |
| 7 | s5_calf | animal | 9.0 | none | 0 | — | — | — | calf | none | suckling | none | 0.6 · front · 30° |
| 8 | s5_bullock_cart | object:bullock_cart | 14.0 | none | 0 | — | — | — | bullock_pair | none | static | — | 0.84 · back · -24° |
| 9 | s5_cart_driver | village_man | 20.9 | wheat | 2 | veshti_short/bare · white/kumkum · none | goad_stick, reins | turban_cloth, moustache | — | cart_yoke | seated_cart | vibhuti | 0.86 · back · -24° |

#### Step 6 — Saints & Devotees (cloth: turmeric; story props: none)

| slot | id | archetype | H cm | skin | arms | attire (lower/upper · color/accent · zari) | hands [R1,L1,R2,L2,…] | extras | vahana | seat | pose | mark | x · row · turn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s6_periyazhwar | saint_vaishnava | 22.0 | wheat | 2 | panchakacham/angavastram · white/saffron · none | anjali, anjali | sikha, tulasi_mala, sacred_thread | — | pedestal | standing | namam | -0.84 · front · 10° |
| 2 | s6_andal | saint_andal | 22.0 | peach | 2 | saree/blouse · parrot-green/kumkum · gold | padma, parrot | andal_kondai, jasmine, garland_on_shoulder | — | pedestal | standing_tribhanga | namam | -0.56 · front · 6° |
| 3 | s6_nammazhwar | saint_vaishnava | 20.2 | wheat | 2 | panchakacham/bare · white/saffron · none | chin, hridaya | sikha, tulasi_mala, sacred_thread | — | lotus_seat | seated_padmasana | namam | -0.28 · front · 3° |
| 4 | s6_thiruvalluvar | poet_sage | 22.0 | wheat | 2 | veshti/shawl · white/white · none | stylus, palm_leaf | beard, hair_knot | — | pedestal | seated_writing | none | 0 · front · 0° |
| 5 | s6_sambandar | child_saint | 15.4 | peach | 2 | veshti_short/bare · white/turmeric · gold | point_up, milk_cup | rudraksha, anklets, golden_cymbals_at_feet | — | pedestal | dancing_child | vibhuti | 0.28 · front · -3° |
| 6 | s6_appar | saint_shaiva | 22.0 | wheat | 2 | veshti/bare · white/saffron · none | anjali, anjali | uzhavarappadai_on_shoulder, rudraksha, shaven_head | — | pedestal | standing | vibhuti | 0.56 · front · -6° |
| 7 | s6_avvaiyar | elder_woman | 19.0 | wheat | 2 | saree/pallu_over_shoulders · white/ivory · none | walking_stick, palm_leaf | white_hair_bun, rudraksha | — | pedestal | standing_stooped | vibhuti | 0.84 · front · -10° |

#### Step 7 — Krishna Leela (cloth: maroon; story props: kaliya_pond, kaliya_hoods, govardhana_hill)

| slot | id | archetype | H cm | skin | arms | attire (lower/upper · color/accent · zari) | hands [R1,L1,R2,L2,…] | extras | vahana | seat | pose | mark | x · row · turn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s7_yashoda | village_woman | 20.6 | peach | 2 | saree/blouse · rani-pink/turmeric · gold | churning_rope, churning_rope | churning_pot, jasmine, nose_ring | — | pedestal | seated_churning | tilak_dot | -0.86 · back · 14° |
| 2 | s7_vennai_kannan | infant_krishna | 13.6 | blue | 2 | none/bare · pitambara/kumkum · gold | butter_ball, butter_pot | peacock_feather_crown, waist_chain, anklets | — | pedestal | crawling | namam | -0.66 · front · 10° |
| 3 | s7_gopi_pot | village_woman | 19.9 | peach | 2 | pavadai/half_saree · peacock-blue/turmeric · gold | pot_on_head_hold, kati | pot_on_head, jasmine | — | pedestal | standing_tribhanga | tilak_dot | -0.46 · back · 8° |
| 4 | s7_kaliya_krishna | child_krishna | 17.6 | blue | 2 | panchakacham/bare · pitambara/kumkum · gold | abhaya, serpent_tail | peacock_feather_crown, waist_chain, anklets | kaliya | kaliya_hoods | dancing_one_leg | namam | -0.12 · front · 0° |
| 5 | s7_govardhana_krishna | child_krishna | 19.8 | blue | 2 | panchakacham/bare · pitambara/peacock-blue · gold | flute, lift_hill_finger | peacock_feather_crown, waist_chain, anklets | — | pedestal | standing_lifting | namam | 0.46 · front · -4° |
| 6 | s7_gopi_shelter | village_woman | 19.3 | peach | 2 | pavadai/half_saree · lotus-pink/parrot-green · gold | anjali, anjali | jasmine | — | pedestal | standing | tilak_dot | 0.66 · back · -16° |
| 7 | s7_cow_shelter | animal | 11.9 | none | 0 | — | — | — | cow | none | standing | none | 0.84 · back · -28° |

#### Step 8 — Ashta Lakshmi (cloth: kumkum; story props: none)

| slot | id | archetype | H cm | skin | arms | attire (lower/upper · color/accent · zari) | hands [R1,L1,R2,L2,…] | extras | vahana | seat | pose | mark | x · row · turn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s8_adi | goddess | 22.0 | peach | 4 | saree/blouse · lotus-pink/turmeric · gold | abhaya, varada, padma, flag | karanda_makuta, jasmine, nose_ring | — | lotus_seat | seated_lalitasana | tilak_dot | -0.87 · front · 5° |
| 2 | s8_dhanya | goddess | 22.0 | peach | 8 | saree/blouse · parrot-green/turmeric · gold | abhaya, varada, padma, padma, gada, paddy_sheaf, sugarcane, banana_bunch | karanda_makuta, jasmine, nose_ring | — | lotus_seat | seated_lalitasana | tilak_dot | -0.62 · front · 4° |
| 3 | s8_dhairya | goddess | 22.0 | peach | 8 | saree/blouse · kumkum/pitambara · gold | abhaya, varada, chakra, shankha, arrow, bow, trishula, palm_leaf | karanda_makuta, jasmine, nose_ring | — | lotus_seat | seated_lalitasana | tilak_dot | -0.37 · front · 3° |
| 4 | s8_gaja | goddess | 22.0 | peach | 4 | saree/blouse · kumkum/parrot-green · gold | abhaya, varada, padma, padma | karanda_makuta, jasmine, nose_ring | gaja_pair | lotus_seat | seated_padmasana | tilak_dot | -0.12 · front · 1° |
| 5 | s8_santana | goddess | 22.0 | peach | 6 | saree/blouse · lotus-pink/peacock-blue · gold | abhaya, infant, khadga, shield, kalasam, kalasam | karanda_makuta, jasmine, nose_ring, infant_on_lap | — | lotus_seat | seated_lalitasana | tilak_dot | 0.12 · front · -1° |
| 6 | s8_vijaya | goddess | 22.0 | peach | 8 | saree/blouse · maroon/turmeric · gold | abhaya, varada, chakra, shankha, khadga, shield, padma, pasha | karanda_makuta, jasmine, nose_ring | — | lotus_seat | seated_lalitasana | tilak_dot | 0.37 · front · -3° |
| 7 | s8_vidya | goddess | 22.0 | peach | 4 | saree/blouse · kumkum/white · gold | abhaya, varada, palm_leaf, peacock_quill | karanda_makuta, jasmine, nose_ring | — | lotus_seat | seated_lalitasana | tilak_dot | 0.62 · front · -4° |
| 8 | s8_dhana | goddess | 22.0 | peach | 6 | saree/blouse · rani-pink/pitambara · gold | abhaya_coins, kalasam, chakra, shankha, padma, bow_arrow | karanda_makuta, jasmine, nose_ring, coin_pile | — | lotus_seat | seated_lalitasana | tilak_dot | 0.87 · front · -5° |

#### Step 9 — Main Deities (cloth: turmeric; story props: ganesha_peetam)

| slot | id | archetype | H cm | skin | arms | attire (lower/upper · color/accent · zari) | hands [R1,L1,R2,L2,…] | extras | vahana | seat | pose | mark | x · row · turn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | s9_durga | goddess_warrior | 24.2 | peach | 8 | saree/blouse · kumkum/pitambara · gold | trishula, shield, chakra, shankha, khadga, bow, arrow, padma | karanda_makuta, nose_ring | lion | pedestal | riding | tilak_vertical | -0.78 · front · 8° |
| 2 | s9_lakshmi | goddess | 24.2 | peach | 4 | saree/blouse · rani-pink/turmeric · gold | abhaya, varada_coins, padma, padma | kireedam, jasmine, nose_ring, coin_pile | — | lotus_seat | seated_lalitasana | tilak_dot | -0.4 · front · 4° |
| 3 | s9_ganesha | deity_ganesha | 28.6 | elephant-grey | 4 | panchakacham/angavastram · pitambara/kumkum · gold | danta, modaka, ankusha, pasha | kireedam, sacred_thread_serpent, pot_belly | mouse | peetam | seated_lalitasana | vibhuti | 0 · front · 0° |
| 4 | s9_saraswati | goddess | 24.2 | peach | 4 | saree/blouse · white/white · gold | veena, veena, japa_mala, palm_leaf | karanda_makuta, jasmine, nose_ring | swan | white_lotus_seat | seated_veena | tilak_dot | 0.38 · front · -4° |
| 5 | s9_kalasam | object:kalasam_amman | 20.0 | none | 0 | — | — | — | — | rice_mound | static | — | 0.62 · front · -6° |
| 6 | s9_marapachi_raja | marapachi | 16.0 | red-sanders | 2 | veshti/angavastram · pitambara/maroon · gold | lola, lola | turban_cloth | — | none | standing_rigid | namam | 0.8 · front · -8° |
| 7 | s9_marapachi_rani | marapachi | 15.0 | red-sanders | 2 | pavadai/half_saree · kumkum/parrot-green · gold | lola, lola | jasmine | — | none | standing_rigid | tilak_dot | 0.92 · front · -14° |

---

## 4. Phase 3: dioramas, camera, manifest

**Goal:** all 73 config entries are built and placed, the camera fly-through is keyed with exact frame ranges, `renders/manifest.json` is written, and the full draft fly-through renders.

### 4.1 `blender/lib/props.py`, story props and golu objects (added this phase)

```python
def build_golu_object(model: str, H: float, palette: Palette, rng: Random) -> Object   # dispatch for archetype "object" (called by make_doll)
def build_pslv(H, palette, rng) -> Object            # 4 stacked lathe stages, 6 strap-on boosters (radial instances), ogive fairing; white with black roll bands
def build_satellite_dish(H, palette, rng) -> Object  # paraboloid lathe, feed horn on 3 struts, yoke mount on a plinth
def build_chandrayaan3(H, palette, rng) -> Object    # Vikram: faceted box with gold-foil MLI (Voronoi crinkle, metallic 0.8) on 4 legs with footpads, ramp; Pragyan: 6-wheel rover with solar panel
def build_vande_bharat(H, palette, rng) -> Object    # 2 coaches, aerodynamic nose (lofted metaball → remesh), windows painted, white + blue band
def build_metro_coach(H, palette, rng) -> Object     # boxy coach, steel-grey + blue band, pantograph
def build_shiva_dhanush_broken(H, palette, rng) -> Object   # great recurved bow in two pieces, gold bands, splintered break
def build_kalasam_amman(H, palette, rng) -> Object   # attributes.kalasam scaled + gold Amman face (relief: metaball face, painted eyes, nose ring, kireedam) on the coconut, flower garland
def build_bullock_cart(H, palette, rng) -> Object    # two spoked wheels (torus + instanced spokes), bed, curved hood (thatch), yoke + vahanas.bullock_pair
def build_rocket_gantry(height: float, rng) -> Object          # lattice tower: columns + K-bracing (instanced struts), 4 platforms, umbilical arms; red-white
def build_launch_pad(...)-> Object; def build_lunar_patch(r, rng) -> Object   # grey regolith disc, Voronoi craters (bump + displace)
def build_rail_track(length) -> Object; def build_metro_viaduct(length) -> Object
def build_mandapam(width, depth, height, palette, rng) -> Object
    # four banana-stem pillars (build_banana_stem scaled, with leaves arching inward), canopy of maroon silk with
    # gold zari and tassels, marigold garlands on the beams, mango-leaf thoranam on the front beam
def build_thinai_field(width, depth, rng) -> Object  # soil patch + ~420 foxtail-millet stalks (GN instances of 4 variants: stalk + drooping bristly panicle)
def build_paran_platform(height, rng) -> Object      # raised bamboo watch platform with ladder and thatch shade
def build_chettiar_shop(width, rng) -> Object        # wooden stall: counter, 3 shelves with 30 tiny jars (lathe, 5 colours of contents), 6 open sacks (grain GN fills: rice, dal, red chilli, turmeric, tamarind), hanging scale, measures
def build_drying_pots(rng) -> Object                 # 7 terracotta pots of 3 shapes beside the potter
def build_kaliya(rng, palette) -> tuple[Object, Matrix]   # pond (glossy blue disc + ripple displacement); coiled serpent (spiral curve, tapered bevel, belly scales) rising to 5 spread hoods (cupped shells with painted hood mark); skin "dark"; returns dance anchor on the centre hood
def build_govardhana(rng) -> tuple[Object, Matrix]   # hill: icosphere displaced (Musgrave-like noise), flattened base, instanced tiny trees and rocks; returns the fingertip anchor
def build_ganesha_peetam(...) -> Object              # raised stepped throne for Step 9 centre
```

### 4.2 `blender/lib/dioramas.py`

```python
@dataclass class DioramaContext: cfg: GoluConfig; step: StepSpec; handle: StepHandle; dolls: dict[str, Object]; rng: Random; collection: Collection
def build_all(cfg, steps: list[StepHandle], dolls: dict[str, Object]) -> dict[int, list[Object]]
def slot_to_world(handle: StepHandle, pos: PositionSpec, footprint: tuple[float, float], rng: Random) -> Matrix
    # x = pos.x·usable/2 + jitter(±0.012); y = front line (+back_row_offset if back); z = tread top + cloth 2 mm;
    # yaw = pos.turn + jitter(±3°)  → dolls face the viewer, turned toward story partners (SPEC §4.4)
def resolve_overlaps(placed: list[tuple[Object, Matrix]], handle: StepHandle) -> None   # 1-D relaxation on x until bbox gaps ≥ 6 mm; never changes order
def anchor_to(obj: Object, anchor: Matrix) -> None   # place a doll on a story-prop anchor (seat values: launch_pad, lunar_patch, rail_track, metro_viaduct, paran_platform, shop_counter, cart_yoke, kaliya_hoods, rice_mound)
def step1_technology(ctx) -> list[Object]   # gantry + pad behind PSLV (x −0.86, back); lunar patch under Chandrayaan; 0.5 m track under Vande Bharat; viaduct under metro
def step2_dasavataram(ctx) -> list[Object]  # 10 evenly in avatar order L→R on a gentle arc (centre 2 cm back)
def step3_sita_kalyanam(ctx) -> list[Object]   # mandapam centred at x≈0 spanning Rama & Sita; groom side left, bride side right (D09); bow pieces on the tread before Janaka
def step4_valli_kalyanam(ctx) -> list[Object]  # thinai field x −1.0…−0.55 with paran; Valli on paran; elephant facing her
def step5_village(ctx) -> list[Object]      # shop x −0.75…−0.25 with Chettiar couple at counter; mini kolam before the kolam woman; drying pots by the potter; cart angled toward the viewer
def step6_saints(ctx) -> list[Object]
def step7_krishna_leela(ctx) -> list[Object]   # Kaliya pond at x −0.25…0.05; Govardhana hill spans x 0.25…0.95, held at Krishna's fingertip anchor
def step8_ashta_lakshmi(ctx) -> list[Object]
def step9_main_deities(ctx) -> list[Object]    # peetam under Ganesha at x 0; rice mound under kalasam
STEP_BUILDERS: dict[int, Callable[[DioramaContext], list[Object]]]
def verify_placement(cfg, steps, dolls, cam_rig) -> list[str]   # §4.5
```

### 4.3 `blender/lib/camera.py`

```python
@dataclass class StepShot: step: int; x0: float; x1: float; dist0: float; dist1: float; z: float; pitch: float; focus_y: float
@dataclass class Timeline: holds: list[tuple[int, int]]; transitions: list[tuple[int, int]]; finale: tuple[int, int]; total: int
def build_rig(cfg) -> tuple[Object, Object]           # camera (sensor 36 mm, lens from config) + DOF focus empty; scene.camera
def plan_shot(handle: StepHandle, dolls: list[Object], lens_mm: float) -> StepShot
    # distance so the step's doll bbox fills 78% of frame width at mid-dolly; lateral dolly x0→x1 = ±0.18·w_n (L→R, D28);
    # push-in 7% (dist0 → 0.93·dist0); camera z = mean doll eye height + 0.06 m; pitch −6°
def build_timeline(cfg) -> Timeline                   # §0.2 numbers
def key_hold(rig, shot: StepShot, start: int, n: int = 96) -> None
    # location/rotation keys at start and end, BEZIER with ease in/out on x and y; focus empty tracks the doll line; f/2.8
def key_transition(rig, a: StepShot, b: StepShot, start: int, n: int = 24) -> None
    # crane: z rises from a.z to b.z along a smooth S (ease in-out), x returns from a.x1 to b.x0, pitch eases;
    # focus distance animated from a to b; f-stop 2.8 throughout
def key_finale(rig, steps, start: int, n: int = 72) -> None
    # from step-9 end pose: pull back + down to establishing pose framing all 9 tiers + both kuthuvilakku + kolam edge;
    # lens 40→35 mm, f-stop 2.8→5.6, focus on tier 5
def write_manifest(path: Path, cfg, timeline, dolls: dict[str, Object], lamp_points: list[Object], scene, cam) -> dict
    # {version, fps, resolution, total, steps:[{id, dir, count, hold:[a,b], transition:[a,b]|null, finale:[a,b]|null,
    #   key_frame, hotspots:{doll_id:{every:8, t:[[x,y,vis],…]}}, flames:{every:8, t:[[[x,y],…]…]}}], doors:{count:72}}
    # projection via bpy_extras.object_utils.world_to_camera_view; y flipped to top-left origin;
    # vis = in-frame AND scene.ray_cast(cam→point) hits the doll itself (occlusion)
def project(scene, cam, co: Vector) -> tuple[float, float, float]
```

### 4.4 Render orchestration (introduced this phase)

**`blender/render_steps.py`**

```python
def main(argv) -> int
def ensure_built(args) -> Path        # open renders/golu_<q>.blend; rebuild via build_scene if missing or config_hash differs
def frames_for_step(manifest, step: int) -> list[tuple[int, int]]   # (global_frame, local_index) for hold + outgoing transition / finale
def render_step(scene, step: int, out_root: Path, args) -> None      # per frame: skip if is_frame_done (resume); scene.frame_set; render.filepath; bpy.ops.render.render(write_still=True); ProgressLog.tick
```

**`scripts/render_all.sh`**

```bash
usage(); parse_args()                 # --quality draft|final (required) --steps 1-9 [--doors] [--props] [--qa] [--all] [--yes] [--stride N] [--blender PATH]
build_if_stale()                      # run_blender blender/build_scene.py -- --config … --quality $Q --verify
estimate_and_confirm()                # final only: render_steps.py --probe → measured s/frame × remaining frames (+10 %); print table per segment; read -r "Proceed? [y/N]" unless --yes (SPEC §4.8)
render_steps_loop()                   # for N in steps: run_blender blender/render_steps.py -- --step N …  (resume built in)
render_doors(); render_props(); render_qa()
main "$@"
```

### 4.5 Phase 3 verification

| Acceptance: "Draft fly-through of all steps. Every doll in config is present and correctly placed" | How |
|---|---|
| Presence | `build_scene.py --verify` checks that the set of objects with `doll_id` equals the config ids (73), each built exactly once. |
| Placement | `verify_placement`. Each doll's base: within its tier tread bounds and ≥ 1 cm from the edge; x-order equals slot order; no pairwise bbox overlap above 5%; yaw within ±40° of facing the camera; story-seated dolls lie on their anchor (±5 mm). |
| Visible in its step | Manifest hotspots: every doll has `vis = 1` in ≥ 30% of its hold samples. |
| Timeline | `manifest.total == 1128`. Holds and transitions are contiguous with no gaps; step 9 includes the finale; `key_frame` is mid-hold (local 48). |
| Draft render | `scripts/render_all.sh --quality draft --steps 1-9` produces 1,128 PNGs. The resume test: interrupt it, re-run, and confirm only missing frames render. |
| Visual | Per step, a contact sheet of every 12th frame (`qa.contact_sheet`). Encode the full draft to `renders/draft/flythrough.mp4` with ffmpeg and watch it. Tick the "F" column of ICONOGRAPHY.md §2 for all 73. Check that the crane-ups are smooth, the finale shows both glowing kuthuvilakku, and Dasavataram reads Matsya→Kalki. |
| Commit | `Phase 3: dioramas, camera fly-through, manifest` |

---

## 5. Phase 4: doors, prop sprites, encode pipeline

### 5.1 `blender/render_doors.py`

```python
def main(argv) -> int
def build_door_scene(base: Path, cfg) -> Scene        # new scene "Doors" linking golu collections (D30) + door collection; camera CAM_Doors 40 mm at 1.55 m eye height, 3.2 m from doors
def build_doors(cfg, rng) -> tuple[Object, Object]   # two teak leaves: panels with carved relief (lathe rosettes, brick-pattern bevelled panels, Displace with Voronoi for carving depth),
                                                     # 7×4 grid of brass studs per leaf (instanced domes), a row of brass bells on the lintel (lathe + clapper),
                                                     # kumkum and turmeric marks painted on the frame (decals as small displaced discs), mango-leaf thoranam above,
                                                     # threshold stone with build_kolam(dots=9), kuthuvilakku each side (props.build_kuthuvilakku, lit)
def animate_doors(left, right, start=1, n=72) -> None   # hinge rotation 0 → 104° inward, F-curve ease in-out (cubic) with 2% settle; frames 1–6 static so f_0001 = poster (SPEC §4.6)
def add_glow_and_haze(scene, cfg) -> None            # area light 2300 K behind doors ramping 0 → 900 W over frames 8–60; doorway haze volume (M_HazeVolume) with density ramp; bloom via compositor glare
def render(scene, out_dir, quality, resume=True) -> None
```

### 5.2 `blender/render_props.py`

```python
SPRITES = ["aarthi_plate","camphor_plate","bowl_sundal","bowl_sakkarai_pongal","bowl_puliyodarai","bowl_curd_rice","bowl_sambar_rice","tray_banana_leaf","tray_composite","petal_marigold","petal_rose","flower_jasmine"]
def main(argv) -> int                                 # --only NAME  --verify
def sprite_scene(cfg) -> Scene                         # film transparent; 1024×1024 (petals 256); camera 45 mm, elevation 38°, azimuth 30° (top-down 3/4, SPEC §4.7); key 2700 K + rim; AgX; NO glare (clean alpha)
def build_aarthi_plate(cfg, rng) -> Object             # brass thattu (lathe with raised rim + embossed petal ring via Displace), small brass ghee lamp with UNLIT cotton wick (SPEC), kumkum + turmeric mounds (cones + noise, powder materials), marigold heads + rose petals + 3 jasmine buds
def build_camphor_plate(cfg, rng) -> Object            # small brass plate, one camphor tablet (rounded box, M_Camphor), unlit
def build_bowl(kind: Literal["brass","silver"], rng) -> Object   # lathe bowl with foot ring and rolled rim
def build_food(dish_id: str, bowl: Object, rng) -> Object       # mound surface (displaced dome inside the bowl) + GN scatter (Poisson, min distance ≈ item size, 2 layers):
    # sundal: chickpeas (3 variants, 2.2k inst) + coconut flakes + curry leaves + mustard seeds
    # sakkarai_pongal: jaggery-brown rice grains (6k) + cashews + raisins + ghee film (thin glossy layer, coat 0.8)
    # puliyodarai: tamarind-brown rice (6k) + peanuts + curry leaves + red chillies
    # curd_rice: white grains (6k) in creamy SSS base + pomegranate arils (transmission)
    # sambar_rice: orange-brown wet mash (displaced) + drumstick pieces + carrot cubes + curry leaves + ghee sheen
def build_banana_leaf_tray(cfg, rng) -> Object         # brass tray with a cut banana-leaf section (midrib, veins, slightly curled edges)
def shadow_catcher(scene) -> Object                    # plane with is_shadow_catcher (bowls + trays only, D31)
def composite_tray(cfg) -> Object                      # tray + 3 bowls of fixed dishes + config third_dish, arranged in an arc
def render_sprite(name, scene, out) -> Path
def verify(out_dir) -> list[str]                       # qa.alpha_report on every sprite (§5.4)
```

### 5.3 `scripts/encode_frames.sh` and `scripts/build_frames_json.mjs`

```bash
usage(); parse_args()      # --quality draft|final  --steps 1-9  [--force]
encode_seq() # src_dir dst_dir width quality  →  ffmpeg -hide_banner -y -i "$src/f_%04d.png" -vf "scale=$w:-2:flags=lanczos" \
             #   -c:v libwebp -quality $q -compression_level 6 -preset picture "$dst/f_%04d.webp"   (skip if counts match and dst newer unless --force)
encode_steps()   # desktop 1920w q75 → web/static/frames/stepN ; mobile 960w q70 → web/static/frames-mobile/stepN ; 4 steps in parallel (xargs -P 4)
encode_doors()   # WebP frames → web/static/doors/{desktop,mobile}/f_####.webp (1920w q75 / 960w q70);
                 # poster: f_0001 → doors/desktop/poster.webp (q82) + doors/mobile/poster.webp (q78); last frame kept for reduced motion;
                 # video (D35): -c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1 -pix_fmt yuv420p → doors/doors-1920.webm ; libx264 -crf 24 -preset slow -profile:v high -pix_fmt yuv420p -movflags +faststart → doors-1920.mp4 ; same at 960w
encode_props()   # -c:v libwebp -quality 90 -pix_fmt yuva420p (alpha lossless) → web/static/props/<name>.webp
write_json()     # node scripts/build_frames_json.mjs --manifest renders/manifest.json --static web/static --out web/src/lib/frames.json
```

```js
// build_frames_json.mjs
async function main(argv): Promise<void>
function countFrames(dir: string): number
function stepBytes(dir: string): number
function buildFramesJson(manifest, counts, bytes, version: string): FramesJson   // asserts counts == manifest per step & variant; copies hotspots/flames; version = sha1(manifest)[:10]
```

### 5.4 Phase 4 verification

| Acceptance: "WebP frames and frames.json generated. Sprites have clean transparent edges" | How |
|---|---|
| Frames exist | `encode_frames.sh --quality draft` produces `frames/step1…9` (120×8 + 168 = 1,128 files) and the same count in `frames-mobile`. `build_frames_json.mjs` exits 0 and its asserts pass. |
| Dimensions and quality | `ffprobe` spot-check of 10 random files per variant: 1920×1080 and 960×540, codec webp. Size report per step (desktop mean ≤ 160 KB). |
| frames.json | Vitest schema test (`web/tests/unit/frames.test.ts`, added Phase 5 but runnable now via `npx vitest run frames`): 9 steps, totals 1128, ranges contiguous, every config doll id has a hotspot track. |
| Doors | 72 WebP frames per variant, posters, two WebM and two MP4. `ffprobe` shows exactly 72 frames at 24 fps; file sizes within the D35 budget (desktop video ≤ 1.6 MB, mobile ≤ 0.6 MB). |
| Sprites, clean edges (automated) | `render_props.py --verify`. Each sprite needs: the 2-px border fully transparent (nothing clipped); exactly 1 alpha island above 50 px (no stray particles; petals allowed 1); fringe test, where for pixels with 0.05 < α < 0.95 the un-premultiplied luminance is within ±0.15 of the mean of the adjacent opaque pixels (no dark or white halo); contact shadow only on bowls and trays. |
| Sprites, clean edges (visual) | `renders/qa/sprites_on_bg.png`: each sprite composited over magenta, black and white, inspected at 200%. Check grains read individually, the ghee sheen on pongal, and the wick unlit. |
| Commit | `Phase 4: doors, prop sprites, encode pipeline` |

---

## 6. Phase 5: web entrance, frame scroller, overlays, navigator, audio

### 6.1 Scaffold

- **`web/package.json`**
  - deps: `@sveltejs/kit`, `svelte@5`, `@sveltejs/adapter-static`, `gsap@3.13` (ScrollTrigger, MotionPathPlugin, ScrollToPlugin), `howler@2.2`, `@fontsource/noto-serif-tamil`, `@fontsource/cormorant-garamond`.
  - dev: `typescript`, `vite`, `tailwindcss@4`, `@tailwindcss/vite`, `vitest`, `@playwright/test`, `@axe-core/playwright`, `lighthouse`, `svelte-check`.
  - scripts: `dev`, `build`, `preview`, `check`, `test:unit`, `test:e2e`, `lh`.
- **`svelte.config.js`:** adapter-static (`pages: build`, `assets: build`, `precompress: true`), `prerender.entries: ['*']`, `kit.alias: { $content: '../content' }`.
- **`vite.config.ts`:** `sveltekit()`, `tailwindcss()`, `server.fs.allow: ['..']`, `build.target: 'es2022'`, and manual chunks so GSAP and Howler load as their own chunk.
- **`tailwind.config.ts`:** colours from `config.palette.tokens`, fonts `ta` and `en` (D44). **`src/app.css`:** `@import "tailwindcss"; @config "../tailwind.config.ts";`, kolam-dot utility, brass panel utility, focus ring `outline: 2px solid var(--temple-gold)`.
- **`static/_headers`:** `/frames*/*`, `/doors/*` and `/props/*` get `Cache-Control: public, max-age=31536000, immutable`. URLs carry `?v=<frames.version>`.

### 6.2 Modules and signatures

```ts
// src/lib/config.ts
export type GoluConfig = …; export type Step = …; export type Doll = …; export type Dish = …   // mirror of the JSON schema
export const config: GoluConfig                               // import raw from '$content/golu.config.json'
export function prasadamTrio(cfg?: GoluConfig): [Dish, Dish, Dish]   // fixed two + third_dish (validated against options)
export function bilingual(en: string, ta: string): { en: string; ta: string }

// src/lib/frames.ts
export type FramesJson = …; export const frames: FramesJson
export function stepOfGlobal(g: number): { step: number; local: number }
export function globalOf(step: number, local: number): number
export function frameUrl(step: number, local: number, variant: 'desktop'|'mobile'): string   // /frames[-mobile]/stepN/f_0001.webp?v=
export function stepProgress(g: number): { step: number; p: number; phase: 'hold'|'transition'|'finale' }

// src/lib/engine/scrollMap.ts
export const FRAMES_PER_VH = 40                                // D45 (from config layout if overridden)
export function totalScrollPx(vh: number): number
export function progressToFrame(progress: number, total: number): number   // round(progress·(total−1)), clamped
export function stepStartProgress(step: number): number        // for navigator jumps (start + 0.10 of hold, so the title card is visible)

// src/lib/engine/coverFit.ts
export interface Rect { sx: number; sy: number; sw: number; sh: number; dx: number; dy: number; dw: number; dh: number }
export function coverFit(srcW: number, srcH: number, dstW: number, dstH: number, focusX = 0.5): Rect
export function portraitFocusX(hotspotXs: number[], cropW: number, p: number): number   // D37
export function frameToViewport(x: number, y: number, rect: Rect): [number, number]

// src/lib/engine/FrameCache.ts                                // D36 two-tier cache
export class FrameCache {
  constructor(opts: { variant: 'desktop'|'mobile'; decodeWindow: number; maxConcurrent?: number })
  preloadPlaceholders(): Promise<void>                         // step first frames (mobile size), resident bitmaps
  setPlayhead(global: number, direction: 1|-1): void           // reprioritise fetch queue (current step, then next) + decode window
  get(global: number): ImageBitmap | null
  nearest(global: number): ImageBitmap                         // nearest decoded → step placeholder → any placeholder (never null)
  evict(activeStep: number): void                              // drop blobs of steps > 2 away; close() bitmaps outside window
  stats(): { blobs: number; bitmaps: number; fallbacks: number; blankDraws: number }
}

// src/lib/engine/hotspots.ts
export function hotspotsAt(step: number, local: number): Array<{ id: string; x: number; y: number; vis: boolean }>   // linear interpolation of 8-frame samples
export function flamesAt(global: number): Array<[number, number]>

// src/lib/engine/scrollLock.ts
export function lockScroll(): () => void                       // saves scrollY, overflow hidden + touch-action none + key/wheel guard; returns unlock restoring position

// src/lib/stores.ts
export const activeStep: Writable<number>; export const globalFrame: Writable<number>
export const ritual: Writable<null|'aarthi'|'camphor'|'prasadam'>; export const entered: Writable<boolean>
export const reducedMotion: Readable<boolean>                  // from a11y/motion.ts

// src/lib/audio/audio.ts
export class AudioManager {
  constructor(cfg: GoluConfig['audio'])
  load(): Promise<{ missing: string[] }>                       // Howl per file (webm, mp3); onloaderror → mark missing → synth fallback
  unlock(): Promise<void>                                      // Howler.ctx.resume() inside the click handler
  bellLarge(): void; bellSmall(volume?: number): void
  startOm(): void                                              // fade 0 → 0.35 over 3 s (SPEC §5.1)
  duck(on: boolean): void                                      // 0.35 ↔ 0.20 over 0.6 s during rituals
  nadaswaram(step: number): void                               // D42
  startAmbientBells(): void; stopAmbientBells(): void          // random 20–40 s
  setMuted(m: boolean): void; setVolume(v: number): void       // persisted via try/catch localStorage
}
// src/lib/audio/synth.ts
export function synthBell(ctx: AudioContext, out: AudioNode, kind: 'large'|'small'): void
  // inharmonic partials (ratios 0.5, 1, 1.19, 1.56, 2.0, 2.51, 2.66, 3.01, 4.17) with amplitude 1/(k^0.7), exponential decays 1.2–6 s (large ×2), slight detune beat
export function synthOmDrone(ctx: AudioContext, out: AudioNode): { stop(): void }
  // 136.1 Hz fundamental + harmonics 2,3,4,5,6 (tanpura-like weights), slow swell LFO 0.11 Hz, soft waveshaper (jawari buzz), lowpass 1.8 kHz

// src/lib/a11y/motion.ts
export const prefersReducedMotion: Readable<boolean>
```

### 6.3 Components

| Component | Behaviour |
|---|---|
| `+page.svelte` | Mounts `Entrance` until `entered`, then `FrameScroller` (or `ReducedMotionView`), `StepTitleCard`, `Hotspots`, `StepNavigator`, `DustLayer`, `LampFlicker`, `RitualBar`, `AudioControls`. |
| `Entrance.svelte` | Full-screen poster (`fetchpriority=high`) and a brass-plaque button, "Enter Golu / கொலுவுக்குள் வாருங்கள்", disabled until preloading finishes. The preload starts after `load`: the door video as a Blob, plus `cache.preloadPlaceholders()`. `AgalLoader` shows progress. **On click:** 1. `audio.unlock()` 2. `bellLarge()` 3. play the door video, drawing each frame to the canvas (`requestVideoFrameCallback`, with a rAF fallback) for 72 frames at 24 fps, about 3 s; falls back to WebP frames if `canPlayType` fails 4. `startOm()` 5. golden bloom (radial gradient overlay plus brightness, 0.8 s), crossfade to the scroller, `entered = true`. Keyboard: Enter or Space. Focus moves to the step title. |
| `AgalLoader.svelte` | Inline SVG clay lamp with a CSS-animated flame; `aria-valuenow` progress (D43). |
| `FrameScroller.svelte` | Pinned full-viewport `<canvas role="img" aria-label=canvas_alt>`, DPR-aware (`min(devicePixelRatio, 2)`). ScrollTrigger on a spacer of `totalScrollPx` with `scrub: 0.5`; `onUpdate` sets the target frame. A single rAF loop draws only when the frame index or viewport changes: `cache.get(g) ?? cache.nearest(g)` (never blank), via `coverFit` with `portraitFocusX` when the viewport is portrait. Variant switches at 768 px. Updates `activeStep` and `globalFrame`. |
| `StepTitleCard.svelte` | Brass-bordered card with `title_ta` / `title_en` and `story_ta` / `story_en`. Opacity: 0 below 10% of the hold, then 1, then 0 from 85% (SPEC) with 4% ramps. `aria-live="polite"` announces the step title on change. |
| `Hotspots.svelte` | One `<button>` per visible doll at `frameToViewport(hotspotsAt(…))`: a 28 px brass ring with a soft pulse (static in reduced motion), `aria-label = name_ta / name_en`. Hidden during transitions. |
| `InfoCard.svelte` | Small brass card showing name_ta / name_en and info_ta / info_en. Focus is trapped while open; Escape or outside click closes it; it is positioned to stay within the viewport. |
| `StepNavigator.svelte` | Nine SVG diyas (bottom to top = steps 1 to 9). The active one glows (radial gradient plus flicker; static in reduced motion). Click or Enter does `gsap.to(window, {scrollTo: stepStartProgress·total, duration: 1.2, ease: 'power2.inOut'})`. `aria-current` marks the active diya. |
| `DustLayer.svelte` | Canvas of 60 (desktop) / 25 (mobile) motes drifting in a warm light cone, additive; pauses when the tab is hidden; off in reduced motion. |
| `LampFlicker.svelte` | Screen-blend glows at `flamesAt(g)`, with 1D noise flicker (D39); off in reduced motion. |
| `AudioControls.svelte` | Brass mute toggle and volume slider (`aria-valuetext`); state persisted. |
| `BrassPanel` / `BrassButton` | Shared chrome: brass gradient border, inner kolam-dot pattern (radial-gradient grid at 8% opacity), engraved text shadow. No flat buttons. |

### 6.4 Phase 5 verification

| Acceptance: "Smooth scrub with no blank frames on fast scroll. Audio starts on Enter" | How |
|---|---|
| Builds clean | `npm run check` (0 errors), `npm run build`, `npm run preview`. |
| Unit tests | Vitest: `coverFit` (cover maths, portrait pan bounds), `scrollMap` (0 → 0, 1 → 1127, monotonic), `frames` (schema, totals), `FrameCache.nearest` (never null after placeholders), `hotspots` interpolation. |
| No blank frames | `tests/e2e/scrub.spec.ts` (Playwright, Chromium, 1280×720 and 390×844, with and without "Fast 3G" throttling). Enter, then 40 random `scrollTo` jumps of up to the full length, 16 ms apart, then a 6 s wheel fling. A `requestAnimationFrame` probe reads 9 canvas sample pixels per frame; the test fails if all 9 are `(0,0,0,0)` on any frame. It also asserts `window.__golu.stats().blankDraws === 0` (dev and test builds only). |
| Smooth | Chrome performance trace with 4× CPU throttle on the mobile viewport: ≥ 95% of frames under 16.7 ms during a scripted 10 s scroll; long tasks under 50 ms. |
| Audio starts on Enter | e2e: before click `Howler.ctx.state === 'suspended'`; after click it is `'running'`; bell-large played; om volume reads ≥ 0.33 at t = 3.2 s. Repeated with the audio files removed: the synth fallback runs and the missing files are logged. |
| Visual | Manual run in desktop and phone emulation: doors open, the bloom transition, title cards fade at 10% and 85%, hotspots stay on the dolls, the navigator jumps. |
| Commit | `Phase 5: entrance, frame scroller, overlays, navigator, audio` |

---

## 7. Phase 6: rituals

```ts
// src/lib/rituals/ritualState.ts
export function startRitual(kind: 'aarthi'|'camphor'|'prasadam'): (() => void) | null   // null if one is running; locks scroll, ducks Om, disables other buttons
// src/lib/rituals/orbit.ts
export interface OrbitSpec { cw: number; ccw: number; secPerCircle: number; reversalEase: number; startDeg: number }
export function orbitAngle(t: number, s: OrbitSpec): number     // pure: degrees, screen space (clockwise positive, y down);
  // constant angular speed, except a smoothstep deceleration over the last `reversalEase` of circle cw
  // and an acceleration over the first `reversalEase` of the reverse; ∫ = +360·cw then back by 360·ccw
export function orbitDuration(s: OrbitSpec): number             // (cw+ccw)·secPerCircle + easing allowance
export function ellipsePoint(angleDeg: number, cx: number, cy: number, rx: number, ry: number): [number, number]
export function buildOrbitTimeline(el: HTMLElement, center: () => [number, number], s: OrbitSpec, onStrike: () => void): gsap.core.Timeline
  // MotionPathPlugin moves the plate along an SVG ellipse path (start at bottom); the path progress is driven by
  // orbitAngle(t)/360 (mod 1, direction-aware) so the turn count is exact; bell strike every 360/strikes_per_circle degrees of travel
// src/lib/rituals/flame.ts
export class FlameRenderer { constructor(canvas: HTMLCanvasElement, kind: 'ghee'|'camphor'); setAnchor(x: number, y: number): void; step(dt: number): void; extinguish(seconds: number): Promise<void>; freeze(): void }
  // teardrop core path (two Béziers), radial + linear gradient (ghee: #FF7A1A→#FFC64A→#FFF2C8 ; camphor: brighter white-yellow, 1.5× taller),
  // flicker = 1D value noise on height/lean/brightness (3 octaves), additive glow layers ('lighter')
// src/lib/rituals/smoke.ts     export class SmokeWisps { emit(x: number, y: number, n: number): void; step(dt: number): void }   // curl-noise drift, fading thin strokes
// src/lib/rituals/glow.ts      export function drawGlow(ctx, x, y, radius, color, intensity): void    // overlay canvas, CSS mix-blend-mode: screen
// src/lib/rituals/steam.ts     export class Steam { step(dt): void }
// src/lib/rituals/petals.ts    export class PetalShower { start(sprites: HTMLImageElement[], count: number): Promise<void> }   // sway + spin + gravity, 4 s
```

| Component | Behaviour |
|---|---|
| `RitualBar.svelte` | Three brass buttons from the config labels. Fixed bottom bar below 768 px, right side on desktop. `aria-disabled` while another ritual runs. |
| `PlateRitual.svelte` (aarthi, camphor) | The plate sprite rises in (0.8 s). `FlameRenderer` is anchored to the wick offset. The centre is the centroid of visible hotspots, or the viewport centre if there are none. The orbit runs 3 clockwise then 3 anticlockwise circles at 1.8 s each, eased at the reversal. A warm glow follows the plate with `mix-blend-mode: screen`. The small bell strikes 4 times per circle. Then the plate lowers and fades. **Camphor:** brighter, taller flame and smoke wisps; at the end the flame shrinks over 1.4 s and goes out, and a last wisp rises. **Reduced motion:** a static glowing plate at the centre, a frozen flame, no orbit, and a 4 s hold. |
| `Prasadam.svelte` | The banana-leaf tray slides up (0.9 s, power3.out) carrying three bowl sprites from `prasadamTrio()`, each with a bilingual label and soft steam. **Take / பெற்றுக்கொள்ளுங்கள்** lifts the bowls 12 px with a glow, starts the petal shower, and shows the blessing "அம்மன் அருள் உங்களுக்குக் கிடைக்கட்டும் — May the Goddess bless you" in an `aria-live="assertive"` region. It auto-closes after 6 s, or on Close or Escape (D41). Reduced motion: fades instead of slides, with no petal fall. |

### 7.1 Phase 6 verification

| Acceptance | How |
|---|---|
| **Exactly 3 clockwise + 3 anticlockwise circles** | Vitest `orbit.test.ts`: integrate `orbitAngle` at 1 ms steps. The cumulative signed angle peaks at exactly +1080° (±0.5°) and returns to 0° (±0.5°). The sign changes exactly once. The duration is ≈ 10.8 s plus easing. e2e: `window.__golu.ritualLog` records `{cwTurns: 3, ccwTurns: 3}` from the runtime angle accumulator. |
| Flame and glow look live | GIF recordings of both plate rituals at 1280×720 (gif_creator) inspected. Flicker is visibly non-periodic, the glow lights the dolls under the plate (screen blend), camphor is whiter and taller with rising wisps, and the extinguish leaves a last wisp. 60 fps check: the performance trace during the orbit, ≥ 95% of frames under 16.7 ms. |
| Prasadam flow complete | e2e `prasadam.spec.ts`: tray visible with 3 bowls; labels match the config trio. Switch `third_dish` to `curd_rice` and rebuild: the label and sprite change (D31). Take: blessing text present in the live region, petals spawn, auto-close at 6 s, scroll restored. |
| One at a time, scroll locked | e2e: clicking a second ritual mid-orbit is ignored; `scrollY` is unchanged during the ritual and restored after; wheel and touch are blocked. |
| Commit | `Phase 6: Aarthi, Camphor and Prasadam rituals` |

---

## 8. Phase 7: final render, polish, reduced motion, a11y, performance, docs

### 8.1 Work items, in order

1. **Final render.** Run `scripts/render_all.sh --quality final --all`. The probe estimate is printed and the script waits for confirmation (on this laptop expect 95–190 h for the fly-through; recommend a GPU host, §0.3). Then `encode_frames.sh --quality final`.
2. **`ReducedMotionView.svelte`** (SPEC §5.5). One `key_frame` image per step, stacked. Scroll position picks the step, and steps crossfade over 0.6 s. Hotspots use the key-frame projection. Rituals use static mode. The doors show the poster, then crossfade to the last door frame.
3. **Accessibility.**
   - Every control is a real `<button>` or `<input>` with a visible temple-gold focus ring.
   - Logical tab order: skip link, then step title, navigator, hotspots, rituals, audio.
   - `lang="ta"` / `lang="en"` spans on bilingual text.
   - Alt text and `aria-label`s from config (`canvas_alt`, step `alt_*`, doll names).
   - The blessing goes in `aria-live`.
   - Contrast ≥ 4.5:1 for card text (sandal on maroon or night).
4. **Performance.**
   - Inline critical CSS; preload the poster and fonts with `font-display: swap`.
   - Defer GSAP and Howler chunks until after first paint.
   - Preload doors and placeholders after `load`.
   - `content-visibility` on off-screen overlays; the canvas never exceeds DPR 2.
5. **Responsive.** Check 360 / 390 / 768 / 1024 / 1440 / 1920 / 3840 px widths. No horizontal scroll (`overflow-x: clip` on root; panels use `max-width: calc(100vw − 32px)`).
6. **Docs.**
   - `README.md`: prerequisites (Blender 4.5 LTS, ffmpeg, Node 20+, Git Bash on Windows), `BLENDER` env var, render draft and final, encode, `npm ci && npm run dev`, build, deploy (Netlify / Cloudflare Pages / any static host; `_headers`; LFS or release archive for frames, D46), troubleshooting (EEVEE on headless Linux needs a GPU or `xvfb-run`; Intel iGPU is CPU-only for Cycles).
   - `ASSETS_NEEDED.md`: `om-loop`, `bell-large`, `bell-small`, `nadaswaram-short` in webm and mp3, with duration, loudness (−16 LUFS), seamless-loop note and licence guidance (CC0 or self-recorded). What the synth fallback covers. Everything else is code-generated.
7. **Final report** per SPEC §7: what was built, final render settings and measured time, frames per step (120 ×8, 168), remaining `ASSETS_NEEDED.md` items, known limitations.

### 8.2 Phase 7 verification

| Quality bar | How |
|---|---|
| Final render complete | `render_all.sh` reports 1,128 + 72 + 12 outputs and 0 missing. `encode_frames.sh` asserts pass. Spot-check 20 final frames for fireflies and denoise artefacts. |
| Reduced motion | Playwright with `reducedMotion: 'reduce'`: no `<canvas>` frame scroller (key-frame view instead); 9 key images; ritual has no orbit transform (plate position constant over 3 s); no dust or flicker canvases running. |
| Accessibility | `@axe-core/playwright` on entrance, scroller, info card and each ritual: 0 serious or critical violations. Keyboard-only e2e: enter, navigate to step 4, open a hotspot card, run all three rituals, mute, all without a pointer. Visible focus ring is computed `outline-color` = temple-gold. |
| Initial load under 3 MB before Enter | e2e: sum `transferSize` of all resources until the Enter button becomes enabled. Must be < 3,000,000 bytes at 1920×1080 and at 390×844 (D35 budget about 2.2 / 1.3 MB). |
| 60 fps on mid-range Android | Real device if available (Chrome remote debugging, scripted scroll, FPS meter); otherwise a Chrome trace with 4× CPU and mobile emulation: ≥ 95% of frames under 16.7 ms; `FrameCache` bitmap memory ≤ 80 MB (`stats()`). |
| Lighthouse ≥ 85 | `npx lighthouse http://localhost:4173 --preset=perf` (mobile default) and `--preset=desktop`; both performance ≥ 85. Report saved to `renders/qa/lighthouse-*.html`. |
| Responsive | e2e at 360, 768, 1440 and 3840 widths: `document.documentElement.scrollWidth <= innerWidth`; screenshots inspected. |
| README works for a new person | Fresh clone into a temporary directory; follow README verbatim: draft render with `--stride 12`, encode, `npm ci`, `npm run build && npm run preview`, open, enter, scroll. Any step that needed knowledge outside README gets fixed in README. |
| Commit | `Phase 7: final render, polish, reduced motion, a11y, perf, docs` |

---

## 9. Acceptance traceability

| SPEC phase | Acceptance criterion | Verified by |
|---|---|---|
| 1 | Draft of empty Golu warm, temple-like, correctly lit | §2.2: `assert_warm` thresholds + visual checklist |
| 2 | QA turntable of 6 reads as painted clay golu with correct iconography | §3.8: structural asserts, `check_iconography.py`, thumbnails, ICONOGRAPHY "T" column |
| 3 | Draft fly-through; every doll present and correctly placed | §4.5: `verify_placement`, manifest visibility, ICONOGRAPHY "F" column |
| 4 | WebP + frames.json; clean sprite edges | §5.4: counts, ffprobe, schema test, `alpha_report` fringe test |
| 5 | Smooth scrub, no blank frames; audio on Enter | §6.4: pixel-probe e2e, `blankDraws == 0`, AudioContext state |
| 6 | Exactly 3 + 3 circles; live flame and glow; prasadam complete | §7.1: `orbitAngle` integral test, runtime log, GIF review, prasadam e2e |
| 7 | All quality bars; README sufficient | §8.2: Lighthouse, budget probe, axe, reduced-motion e2e, fresh-clone run |

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Final render takes 4–8 days on this laptop | Measured estimate and confirmation gate; resumable; recommend a GPU host (§0.3) |
| EEVEE shader compile on Intel iGPU is slow or unstable | A single doll material (D24); fall back to Cycles 16 spp for draft automatically if EEVEE init fails |
| Metaball family merging across dolls | Unique `mb_<id>` base names; convert and delete immediately |
| Blender API drift (4.2 / 4.5 / 5.x) | `render.py` compat helpers; CI-style smoke run of `build_scene --empty` on the installed version first |
| Memory blow-up from decoded bitmaps | Two-tier cache with `deviceMemory`-aware window (D36) |
| iOS Safari video-to-canvas quirks | `playsinline muted`, Blob URL, `requestVideoFrameCallback` with rAF fallback, WebP-frame fallback path (D35) |
| Iconography errors | Machine-checked rules table, turntable "T" column and fly-through "F" column sign-off |
| Tamil text shaping | Never rendered in Blender (D26); web fonts with full Tamil coverage |
