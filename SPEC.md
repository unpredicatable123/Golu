# Navaratri Golu Darshan — Master Build Spec

> This file is the single source of truth. The planner (Fable) turns it into PLAN.md. The executor (Opus) builds it phase by phase. Do not skip sections or invent scope beyond it.

---

## 0. Mission

Build an immersive, devotional web experience of a 9-step (padi) Navaratri Golu, as found in Tamil homes and temples.

- **Every visual is created by code.** Blender Python scripts model, light and render the Golu, the dolls, the temple doors and the ritual props.
- **The web app plays those renders** as scroll-driven frame sequences, with live flame, light, sound and ritual interactions on top.

The feeling must be: *walking into a lamp-lit Tamil temple during Navaratri.* Use warm brass light, silk, marigold, kolam and the sound of bells and Om. It must never feel cartoonish, Western-fantasy, or like a generic website.

---

## 1. Deliverables

1. `blender/`: Python scripts (Blender 4.2 LTS or newer, run headless) that generate:
   - the full Golu scene
   - 50+ procedural clay dolls
   - the camera fly-through
   - the temple-door sequence
   - the ritual and prasadam props
2. `scripts/`: render orchestration plus ffmpeg conversion to WebP frame sequences, with an auto-generated `frames.json`.
3. `web/`: a SvelteKit app (static adapter) with the entrance, the scroll frame engine, overlays, rituals, prasadam and audio.
4. Docs:
   - `README.md`: setup, render, run and deploy
   - `ASSETS_NEEDED.md`: audio files or anything not code-generated
   - `DECISIONS.md`: any deviation from this spec, with the reason

---

## 2. Repository structure

```
golu-darshan/
├── SPEC.md  PLAN.md  README.md  ASSETS_NEEDED.md  DECISIONS.md
├── content/golu.config.json          # single source for steps, dolls, rituals, prasadam
├── blender/
│   ├── build_scene.py                # entry: builds the whole .blend from config
│   ├── lib/
│   │   ├── materials.py              # clay-gloss, brass, gold, silk+zari, wood, marigold, food
│   │   ├── doll_factory.py           # parametric doll builder (see §4.3)
│   │   ├── attributes.py             # shankha, chakra, gada, padma, vel, bow, veena, kalasam…
│   │   ├── vahanas.py                # peacock, lion, mouse, swan, Garuda, elephant, cow
│   │   ├── props.py                  # kuthuvilakku, garlands, thoranam, kolam, mandapam, plates, bowls
│   │   ├── environment.py            # room, steps, silk drape, back wall, lighting
│   │   ├── dioramas.py               # one function per step theme
│   │   └── camera.py                 # camera path + per-step markers
│   ├── render_steps.py               # renders golu fly-through frames
│   ├── render_doors.py               # renders entrance door-opening frames
│   └── render_props.py               # renders transparent ritual/prasadam sprites
├── scripts/
│   ├── render_all.sh                 # --quality draft|final --steps 1-9
│   └── encode_frames.sh              # PNG → WebP desktop (1920w) + mobile (960w) + frames.json
├── renders/                          # raw PNG output (gitignored)
└── web/                              # SvelteKit app
    └── static/{frames,frames-mobile,doors,props,audio}/
```

---

## 3. Content config: `content/golu.config.json`

Everything (titles, stories, doll lists, colors, prasadam dishes) lives here. **Both Blender and the web app read it**, and nothing is hardcoded elsewhere. Each step has:

- `id`, `title_en`, `title_ta`
- `story_en`, `story_ta` (1–2 lines)
- `cloth_color`
- `dolls[]`, where each doll has:
  - `name_en`, `name_ta`, `archetype`, `skin`, `arms`, `attire`
  - `attributes[]`, `vahana`, `pose`, `scale`
  - `position` (slot on the step)
  - `info_en`, `info_ta`

Step order runs bottom (1) to top (9). By tradition, the deities sit at the top.

| Step | Theme (EN / TA) | Dolls |
|---|---|---|
| 1 | Technology & Modern India / தொழில்நுட்பம் & நவீன இந்தியா | Chandrayaan lander + Pragyan rover, PSLV rocket on launch pad, Vande Bharat train, metro coach, satellite dish, ISRO scientists, children with laptop |
| 2 | Dasavataram / தசாவதாரம் | Matsya, Kurma, Varaha, Narasimha, Vamana, Parasurama, Rama, Balarama, Krishna, Kalki (in order, left→right) |
| 3 | Sita Kalyanam / சீதா கல்யாணம் | Rama & Sita exchanging garlands under a wedding mandapam, Lakshmana, Janaka, Dasaratha, Vishwamitra, Vasishta, broken Shiva dhanush, nadaswaram & thavil players |
| 4 | Murugan Valli Kalyanam / முருகன் வள்ளி கல்யாணம் | Murugan with vel, Valli in a thinai (millet) field, Deivanai, Narada, wild elephant (Ganesha), peacock |
| 5 | Village Life & Chettiar Set / கிராம வாழ்க்கை & செட்டியார் கடை | Chettiar couple with shop and tiny goods, vegetable vendor, potter at wheel, cows, bullock cart, woman drawing kolam |
| 6 | Saints & Devotees / அடியார்கள் | Andal, Thiruvalluvar, Azhwars, Nayanmars (Appar, Sambandar), Avvaiyar |
| 7 | Krishna Leela / கிருஷ்ண லீலை | Baby Krishna with butter pot, Yashoda, gopis, Kaliya Mardanam, Govardhana lift |
| 8 | Ashta Lakshmi / அஷ்ட லட்சுமி | Eight forms of Lakshmi, each on a lotus, with their distinct attributes |
| 9 | Main Deities / விநாயகர் & முப்பெரும் தேவியர் | Ganesha (center), Saraswati with veena, Lakshmi on lotus, Durga on lion, Kalasam (Amman face), Marapachi bommai pair |

Prasadam:

- Sundal / சுண்டல் (chickpea with coconut and curry leaves)
- Sakkarai Pongal / சர்க்கரைப் பொங்கல்
- Third dish, configurable, default Puliyodarai / புளியோதரை. Alternatives: Curd Rice / தயிர் சாதம், Sambar Rice / சாம்பார் சாதம்.

---

## 4. Part A: Blender pipeline

### 4.1 Environment rules

- Scripts must run headless: `blender -b -P blender/build_scene.py -- --config content/golu.config.json`.
- Use only the bundled Blender Python. No add-ons that need manual install.
- Everything is procedural: geometry, shader-node textures and modifiers. No downloaded models or textures.
- Make scripts deterministic: use fixed random seeds, so re-renders match.
- Use Cycles with GPU if available, otherwise CPU, with OpenImageDenoise. EEVEE is allowed for `draft` quality.

### 4.2 Environment: `environment.py`

- **Room:** warm interior with a back wall of carved temple-style niches holding small lit agal vilakku (clay lamps). The floor is red oxide with a white rice-flour kolam (procedural pattern texture) in front of the Golu.
- **Steps:** 9 wooden tiers, each wider at the bottom.
  - Each tier is draped in silk cloth with a gold zari border. Model the drape with folds (Displace + Wave/Noise, or a short cloth-sim bake frozen to mesh).
  - Silk shader: anisotropic sheen. Cloth colors alternate maroon, kumkum red and turmeric yellow according to the config.
  - Each step edge has a thin brass trim.
- **Decoration:**
  - Marigold garlands swag along each step edge. Use curves with instanced marigold heads (displaced icosphere, orange or yellow, slight color variation) alternating with jasmine.
  - Mango-leaf thoranam across the top.
  - Banana stems on both sides.
- **Kuthuvilakku:** Two tall brass lamps flank the Golu. Model them with Screw (lathe) from a profile curve, five-faced top with wicks. Each wick has a small emissive flame mesh plus a warm point light.
- **Lighting:**
  - Overall color temperature about 2700K.
  - Key: large soft warm area light from front-top-left.
  - Rim lights for doll separation.
  - Lamps add practical glow.
  - World: very dark warm brown.
  - Filmic/AgX view transform, slight bloom or glare. No harsh white light.

### 4.3 Doll factory: `doll_factory.py` (the most important module)

Real golu bommai are **stylized hand-painted clay dolls with a glossy varnish**. Recreate that style faithfully. Do not attempt photoreal humans. A well-crafted stylized clay doll *is* the realistic result here.

**`make_doll(spec) -> Object` builds:**

- **Body**
  - Build from metaballs or joined primitives, then Voxel Remesh, then Subdivision Surface + smooth shading, for soft sculpted clay forms.
  - Traditional golu proportions: large head (about 1/5 of height), sloped shoulders, seated or standing pose.
  - Every doll stands on a small painted pedestal base.
- **Face** (painted, not modeled)
  - Shader-painted elements: almond eyes with black kajal outline, arched brows, red lips, a slightly modeled nose.
  - Forehead mark by archetype: tilak, Vaishnava namam (U-shape) or vibhuti stripes.
  - The face must read clearly at small render size.
- **Skin tones**
  - `blue` (Vishnu, Rama, Krishna avatars)
  - `peach` and `wheat` (most figures)
  - `dark` (Kali / Kaliya forms)
  - `elephant-grey` (Ganesha)
- **Attire**
  - Saree / pavadai / veshti / angavastram as shaped shells over the body.
  - Silk colors per config, with a procedural gold zari border band.
- **Jewelry**
  - Gold metallic: kireedam crown (stacked lathe profile), earrings, necklaces (torus chains), armlets, waist belt.
  - Goddesses get jasmine in the hair.
- **Arms**
  - Parameter of 2, 4, 8 or 10 arms. Arrange multiple arms in a symmetrical fan, with hands in abhaya/varada mudra or holding attributes.
- **Attributes** (`attributes.py`)
  - shankha, chakra (with flame edges), gada, padma (lotus), vel, bow & arrow, veena, axe (Parasurama), plough (Balarama), sword (Kalki), butter pot, flute, trident, kalasam with mango leaves and coconut.
- **Vahanas** (`vahanas.py`)
  - peacock (with a fanned tail using instanced eye-feathers), lion, mouse, swan, Garuda, elephant, cow, horse (Kalki).
- **Animal-form avatars**
  - Matsya (fish lower body), Kurma (tortoise lower body), Varaha (boar head), Narasimha (lion head with mane).
- **Material:** clay-gloss shader. Painted base color, slight roughness variation, clear-coat 0.6 for the varnish shine, subtle hand-painted brush-stroke noise.

**Iconography accuracy:** each deity must carry its correct attributes and colors.

- Vishnu forms: blue, with shankha + chakra.
- Murugan: vel and peacock.
- Saraswati: white saree and veena.
- Lakshmi: red/pink saree, lotus, gold coins.
- Durga: lion and weapons.
- Ganesha: elephant head with one tusk broken, modak, mouse.

Write a short `ICONOGRAPHY.md` table and verify every doll against it.

**Quality check:** render a test turntable of 6 representative dolls (Ganesha, Rama, Sita, Murugan, Narasimha, a Chettiar figure) to `renders/qa/` before building the full scene.

### 4.4 Dioramas: `dioramas.py`

- Write one function per step that places that step's dolls and props from config, using slot positions, slight angle variation and natural spacing. Dolls should face the viewer, slightly turned toward each other in story scenes.
- Story props:
  - wedding mandapam with plantain pillars (step 3)
  - thinai field (step 4)
  - Chettiar shop with tiny jars and sacks (step 5)
  - Kaliya serpent hoods (step 7)
  - Govardhana hill (step 7)
  - rocket gantry (step 1)

### 4.5 Camera: `camera.py`

- 35–50mm lens, depth of field focused on the active step (f/2.8 look).
- Per step: a 96-frame segment (4s at 24fps). The camera drifts slowly along the step in a gentle lateral dolly with a slight push-in, framing that step's dolls.
- Between steps: a 24-frame smooth crane-up transition to the next step.
- Ending: a 72-frame pull-back revealing the entire 9-step Golu with both kuthuvilakku glowing.
- Write the frame ranges for each step into `renders/manifest.json` so the web app can map scroll to frames.

### 4.6 Entrance doors: `render_doors.py`

- Carved teak temple doors:
  - brass studs and bells
  - kumkum and turmeric marks
  - mango-leaf thoranam above
  - kolam on the threshold
  - a kuthuvilakku on each side
- 72 frames: the doors swing open inward (eased), and warm golden light and slight haze pour out, revealing a soft glimpse of the Golu.
- Frame 1 doubles as the static entrance background.

### 4.7 Ritual & prasadam sprites: `render_props.py`

Render with transparent film, 1024px, from a slightly top-down three-quarter view.

- **Aarthi plate:** brass thattu with a ghee lamp (wick unlit, since the flame is added live in the web app), kumkum, turmeric and flowers.
- **Camphor plate:** small brass plate with a camphor tablet (unlit).
- **Prasadam bowls** (three, each in a separate render, in brass or silver bowls, also one banana-leaf tray composite):
  - Sundal: chickpeas via particle instancing, coconut flakes, curry leaves, mustard seeds.
  - Sakkarai Pongal: glossy jaggery-brown rice grains (instanced), cashews, raisins, ghee sheen.
  - Third dish from config: Puliyodarai (tamarind-brown rice, peanuts, curry leaves), or curd rice (white, pomegranate) / sambar rice.

### 4.8 Render & encode

- `scripts/render_all.sh --quality draft|final --steps 1-9`
  - **draft:** 960×540, EEVEE or Cycles at 16 samples. For fast review.
  - **final:** 1920×1080, Cycles 96 samples + denoise, PNG 8-bit.
  - Supports resuming: skip frames already rendered. Logs progress and an ETA.
- `scripts/encode_frames.sh`
  - Converts PNGs to WebP: desktop 1920w q75, mobile 960w q70.
  - Copies to `web/static/frames*/stepN/f_0001.webp…`.
  - Writes `web/src/lib/frames.json` with per-step frame counts and transition ranges.
- Print the total estimated render time before the final render starts, and wait for confirmation.

---

## 5. Part B: Web app (`web/`)

**Stack:** SvelteKit + TypeScript + Tailwind (adapter-static), GSAP (ScrollTrigger, MotionPathPlugin), Howler.js. Fonts: a Tamil-supporting display font (e.g., Noto Serif Tamil / Hind Madurai) plus an elegant serif for English.

**Design tokens:**

| Token | Hex |
|---|---|
| kumkum | `#B3122E` |
| turmeric | `#E8A317` |
| temple-gold | `#C9A227` |
| brass | `#B5893A` |
| maroon | `#5C0A14` |
| sandal | `#E9D3A9` |
| night | `#1A0B06` |

UI chrome uses brass-bordered panels with subtle kolam-dot patterns. No flat modern buttons.

### 5.1 Entrance

- Full-screen first door frame, with the button **"Enter Golu / கொலுவுக்குள் வாருங்கள்"** styled as a brass plaque.
- On click:
  1. Unlock audio.
  2. Ring the large temple bell.
  3. Play the 72 door frames on canvas (about 3s).
  4. Fade the Om chant loop in to 35% over 3s.
  5. Golden light bloom, then transition into the scroll experience.
- Preload the door frames and the first frame of each step before enabling the button. Show an agal-vilakku loading indicator.

### 5.2 Scroll frame engine: `<FrameScroller>`

- One full-viewport canvas, DPR-aware, cover-fit.
- Scroll maps to a global frame index (ScrollTrigger, `scrub: 0.5`). Draw in rAF only when the frame changes.
- Mobile (<768px) loads `frames-mobile`.
- Loading:
  - Use `createImageBitmap`.
  - Load the current step plus the next.
  - Free steps more than 2 away.
  - If a frame is missing, draw the nearest loaded frame. **Never show a blank canvas.**
- **Overlays, synced to scroll:**
  - Bilingual step title card plus story: fades in at 10% of the step range and out at 85%.
  - Doll hotspots (positions from `manifest.json` / config, projected per step) open a small brass info card with `name_ta / name_en` and `info`.
- **Step navigator:** 9 small diyas on the side. The active one glows. Click to jump with a smooth scroll.
- **Ambient:** a subtle drifting dust-in-light particle layer, and an occasional soft small bell every 20–40s (random).

### 5.3 Ritual controls

Three fixed brass buttons, always reachable (bottom bar on mobile, right side on desktop):

**Show Aarthi / ஆரத்தி**
- The plate sprite rises in.
- A live flame (canvas particle flame: teardrop core, orange-yellow gradient, flicker noise, additive glow) sits on the wick.
- Motion path: an ellipse around the center of the active step. **3 full circles clockwise, then 3 anti-clockwise**, about 1.8s per circle, eased at the reversal.
- Light spill: a radial warm glow on an overlay canvas follows the plate with `mix-blend-mode: screen`, so the dolls appear lit.
- The small bell rings continuously in rhythm during the motion. The plate then lowers and fades.

**Show Camphor / கற்பூர ஆரத்தி**
- Same motion pattern.
- The flame is brighter, white-yellow and taller, with thin rising smoke wisps (particles with curl drift).
- At the end the flame shrinks and goes out, and a last wisp of smoke rises.

**Take Prasadam / பிரசாதம்**
- A banana-leaf tray slides up holding the three bowl sprites, with soft steam particles.
- Bilingual labels under each bowl. The third dish comes from config.
- The **"Take / பெற்றுக்கொள்ளுங்கள்"** button triggers:
  - bowls gently lift and glow
  - a falling-flower-petal shower
  - the blessing message **"அம்மன் அருள் உங்களுக்குக் கிடைக்கட்டும் — May the Goddess bless you"**

Only one ritual runs at a time. Scrolling is paused (locked) during a ritual and restored after.

### 5.4 Audio (Howler)

| File | Use |
|---|---|
| `om-loop` | Seamless loop at 35%, ducked to 20% during rituals |
| `bell-large` | Entrance |
| `bell-small` | Rituals and ambient rings |
| `nadaswaram-short` | Optional, plays softly when entering steps 3 and 4 (the weddings) |

- Global mute and volume control. The state persists in localStorage, wrapped in try/catch.
- **Fallback if files are missing:** synthesize the bell with Web Audio (inharmonic partials with exponential decay) and the Om with a low drone (tanpura-like 136.1Hz fundamental with harmonics, slow swell). Log what is missing in `ASSETS_NEEDED.md`.

### 5.5 Quality bars

- **Reduced motion** (`prefers-reduced-motion`): one key frame per step with crossfades. Rituals become a static glowing plate and no orbit.
- **Accessibility:** keyboard-operable controls, focus rings in temple-gold, alt text from config, `aria-live` for the blessing message.
- **Performance:**
  - Initial load under 3MB before Enter.
  - 60fps scroll on a mid-range Android.
  - Lighthouse performance ≥ 85.
- **Responsive:** 360px to 4K. No horizontal scroll.

---

## 6. Phases & acceptance criteria

| Phase | Work | Accept when |
|---|---|---|
| 1 | Config, materials library, environment (steps, cloth, lamps, garlands, lighting) | Draft render of the empty Golu looks warm, temple-like and correctly lit |
| 2 | Doll factory + attributes + vahanas | QA turntable of 6 dolls reads clearly as traditional painted clay golu bommai with correct iconography |
| 3 | All 9 dioramas + camera + manifest | Draft fly-through of all steps. Every doll in config is present and correctly placed |
| 4 | Doors + props sprites + encode pipeline | WebP frames and frames.json generated. Sprites have clean transparent edges |
| 5 | Web: entrance, frame scroller, overlays, navigator, audio | Smooth scrub with no blank frames on fast scroll. Audio starts on Enter |
| 6 | Web: Aarthi, Camphor, Prasadam | Exactly 3 clockwise + 3 anti-clockwise circles. Flame and glow look live. Prasadam flow complete |
| 7 | Final render, polish, reduced motion, a11y, perf, docs | All quality bars met. README lets a new person render and run everything |

After every phase:

1. Run it.
2. Visually inspect the renders or the browser.
3. Fix issues.
4. Commit `Phase N: <summary>`.

Write complete code only: no TODOs or stubs.

---

## 7. Final report

When done, report:

- what was built
- final render settings and time taken
- frame counts per step
- anything left in `ASSETS_NEEDED.md`
- known limitations
