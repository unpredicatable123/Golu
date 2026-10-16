# Decisions

Each entry records an ambiguity or conflict in SPEC.md, or a deviation from it, and how it was resolved. Where culture is involved, the most traditional and widely recognised form was chosen. The ids (D01…) are referenced from PLAN.md, ICONOGRAPHY.md and code comments.

## A. Cultural and iconographic choices

**D01 · Dasavataram uses the four-armed Vishnu-form convention.** SPEC §4.3 says "Vishnu forms: blue, with shankha + chakra", but several avatars are usually shown with their own emblems. Resolution: on Step 2, nine avatars are four-armed with chakra in R2 and shankha in L2, and their avatar emblems in the front hands (Rama: bow and arrow; Krishna: flute; Balarama: plough and pestle; Kalki: sword and shield on a white horse). This keeps all ten readable as forms of Vishnu, as South Indian Dasavatara panels do. Exceptions are listed in ICONOGRAPHY.md:
- **E1 Vamana** is the two-armed brahmachari boy with umbrella and water pot, blue and with the namam.
- **E2 Balarama** is fair-skinned and dressed in nilambara (blue silk), as the texts describe him.
- **E3** Rama (Step 3) and Kannan (Step 7) appear in their human, two-armed narrative forms.

**D02 · Six arms are allowed.** SPEC §4.3 allows 2, 4, 8 or 10 arms. Santana Lakshmi and Dhana Lakshmi are six-armed in the standard Ashta Lakshmi iconography, so `arms` also accepts 6 (E4). The fan layout already handles any even count.

**D03 · Ashta Lakshmi list and order.** The eight are Adi, Dhanya, Dhairya, Gaja, Santana, Vijaya, Vidya and Dhana, placed left to right in the order of the Ashtalakshmi Stotram. Arms, emblems and garment colours follow the Wikipedia iconography section. Two notes:
- Dhairya Lakshmi is sometimes shown on a lion, but SPEC says each sits on a lotus, so all eight have `seat: lotus_seat`.
- Vidya Lakshmi is given a red saree (the cited source) with a white accent, which keeps her distinct from Saraswati on Step 9.

**D04 · Step 9 layout.** SPEC lists Ganesha (centre), Saraswati, Lakshmi, Durga, the Kalasam and the Marapachi pair but no order. Left to right: Durga on lion, Lakshmi, **Ganesha at x = 0**, Saraswati, Kalasam, Marapachi groom and bride.
- The three goddesses read in Navaratri order (days 1–3 Durga, 4–6 Lakshmi, 7–9 Saraswati) with Ganesha centred between them.
- The Marapachi couple stays together, as tradition requires.
- Ganesha is centred by position rather than by slot count. The heavy Durga-and-lion group on the left balances the smaller kalasam and dolls on the right.

**D05 · Valli and Deivanai.** Valli stands on Murugan's right and Deivanai on his left, as at Tiruttani. Seen by the viewer, Valli (in her millet field) is left of Murugan and Deivanai is right of him. Narada is at the right end, and the elephant charges from between Valli and Murugan toward Valli.

**D06 · Which Azhwars and Nayanmars.** SPEC names "Azhwars" without saying which. Andal is herself an Azhwar, so Step 6 adds **Periyazhwar** (her father) and **Nammazhwar** (the foremost Azhwar). Nayanmars are Appar and Sambandar, as SPEC names. Layout left to right: Vaishnava saints, then Thiruvalluvar at the centre, then the Shaiva saints, then Avvaiyar.

**D07 · Thiruvalluvar has no forehead mark.** He wears white robes, following the Tamil Nadu government portrait in use since the 1960s. This avoids taking a side in a live dispute about his depiction (E5).

**D08 · Plural groups become individual dolls.** "ISRO scientists" becomes one woman and one man; "children with laptop" becomes a girl and a boy; "gopis" becomes two (one with a curd pot, one sheltering under Govardhana); "cows" becomes a cow and calf. A cow under Govardhana and a cart driver are added because the scenes don't make sense without them. Kaliya, the Govardhana hill, the mandapam, the thinai field, the shop and the gantry are story props built by `dioramas.py`, as SPEC §4.4 says. Total: **73 config entries** (65 figures and animals, 8 objects).

**D09 · Narrative order.** Step 7 reads chronologically left to right: butter thief, then Kaliya, then Govardhana. Step 3 puts the musicians and the groom's family on the left and the bride's family on the right. Sita stands on Rama's left (vama bhaga), which is the viewer's right. The broken bow lies before Janaka and Vishwamitra, in whose presence it was broken.

**D10 · Durga has eight arms.** Ashtabhuja is the common Tamil golu form. Ten arms remain supported and are tested in the Phase 2 parameter sweep.

**D11 · Ganesha details.** The right tusk is broken and its piece is held in R1. The trunk curls to his left (idampuri), toward the modak in L1. Ankusha is in R2 and pasha in L2. The mouse sits at the front of the peetam, and a serpent serves as his sacred thread.

**D12 · Marapachi dolls are wood, not clay.** Skin value `red-sanders` switches the doll shader from flat clay paint to a polished red-sanders grain under a thinner varnish. The dolls are dressed in silk "real cloth" shells, as families dress them each year.

**D13 · Skin tones.** `dark` is used only for Kaliya, as in SPEC. Village and modern figures use `wheat`, a warm medium brown, which is accurate for Tamil Nadu and avoids pale "default" figures. Consorts and goddesses use `peach`, the golu paint convention. All skin hexes live in `palette.skin` in the config.

**D14 · Vande Bharat livery.** The model uses the original white body with a blue band, the most recognised livery. The colours live in the config palette so a saffron-grey variant is a one-line change.

**D15 · Kalasam.** The kalasam is brass, set on a mound of raw rice, with five mango leaves, a turmeric-smeared coconut and a gold Amman face fixed to the coconut.

## B. Config schema

**D16 · Fields added to the doll schema.** All are optional unless stated.
- `id` (required): stable key for the manifest, hotspots and QA.
- `model`: object type, for `archetype: object`.
- `extras[]`: items that aren't held in a hand, such as jasmine, a child on the lap, or a pot on the head.
- `seat`: lotus seat, peetam, pedestal, platform and so on. A lotus is a seat, not a vahana.
- `forehead`: overrides the archetype's default mark.

Per step, `alt_en`/`alt_ta` (SPEC §5.5 asks for alt text from config) and `story_props[]` are added.

**D17 · `attributes[]` is ordered by hand.** The order is `[R1, L1, R2, L2, …]`. Mudras are tokens that shape an empty hand: `abhaya`, `varada`, `kati`, `anjali`, `chin`, `hridaya`, `lola`, `point_up`, `abhaya_coins` and `varada_coins`. A two-handed item fills both hands of a pair. The rule is documented in the config's `$comment`.

**D18 · `position` is `{slot, x, row, turn}`.** `slot` is the 1-based left-to-right order. `x` is normalised across the usable width (−1…1). `row` is front or back, and `turn` is the yaw in degrees toward a story partner. `dioramas.py` adds seeded jitter (±0.012 in x, ±3° in yaw) and resolves overlaps from the measured bounds.

**D19 · Everything colour-related lives in `palette`.** This covers design tokens, skin, silk, step cloth, material base colours and light temperatures (SPEC §3: "nothing is hardcoded elsewhere"). Shader structure stays in code. Golu dimensions (`layout`), camera timing, ritual timing and audio levels are also config values.

## C. Blender pipeline

**D20 · Blender version.** The tested target is **Blender 4.5 LTS**. The minimum is 4.2 LTS, as SPEC requires; 4.2's support window has ended, while 4.5 is still supported. `lib/render.py` has compatibility shims for the 4.2-to-5.x API changes: the EEVEE engine id, the 5.x compositor node-group API, Glare node sockets, AgX look names and Principled socket names.

**D21 · "Particle instancing" means Geometry Nodes instancing.** Marigold garlands, the thoranam, food grains, the millet field, peacock feathers and gold coins all use Distribute Points on Faces or Curve to Points, then Instance on Points with seeded Random Value. This gives Poisson-disk spacing (no overlapping grains) and the same seed every run, with no particle cache. Legacy hair particles are not used.

**D22 · Kolam.** SPEC asks for a "procedural pattern texture". A real sikku kolam is one continuous line looping around a dot grid, which node textures can't express faithfully. So `props.build_kolam` generates the line with the mirror-curve algorithm on a classic diamond dot layout (11 dots across: 1-3-5-…-11-…-5-3-1), using a seeded, D4-symmetric mirror layout. At each reflection the line is pulled 38% back toward the dot it turns round, so loops part instead of touching, as in a hand-drawn sikku kolam. It becomes a flat ribbon mesh via Curve to Mesh, shaded with a procedural rice-flour material (noise-broken edges, granular bump). No image files are involved.

**D23 · Silk folds use Displace, not cloth simulation.** Each drape uses a Wave plus Noise displacement weighted toward the hanging edge. It is faster and has no simulation drift between runs.

**D24 · Dolls use one clay-gloss shader.** All dolls share `M_ClayGloss`, driven by mesh attributes: `paint` colour, `pbr` (metal, roughness, kind) and `garment_uv`. Garments are painted clay shells, as on real golu bommai, with the gold zari band computed in the shader from `garment_uv`. Jewellery is metallic gold paint under the varnish. The anisotropic silk shader is used for the step drapes only. One material means one EEVEE shader compile, which matters on integrated GPUs.

**D25 · Faces are painted in object space.** Eyes, kajal, brows, lips and forehead marks are drawn from object-space coordinates relative to per-object attributes (`head_center`, `head_radius`, `mark_type`, …). No UVs are needed on the voxel-remeshed body, and features stay crisp at any render size.

**D26 · No text inside renders.** Blender text objects don't shape Tamil script, so vowel signs would render wrongly. All Tamil and English text lives in the web overlay. The shop has no signboard.

**D27 · Frame layout on disk.** `stepN/` holds that step's 96 hold frames followed by its 24 outgoing transition frames (120 frames). `step9/` holds 96 hold frames plus the 72-frame finale (168 frames). Total: 8 × 120 + 168 = **1,128 frames**. Files are numbered 1-based (`f_0001`); `frames.json` uses 0-based indices.

**D28 · Camera.** Each step's dolly runs left to right as seen by the viewer, so the Dasavataram reads in avatar order. Each crane-up therefore also travels back left. Other settings:
- No motion blur: any frame can be a resting frame when the user stops scrolling.
- Fixed Cycles seed, so re-renders match (SPEC §4.1).
- Lamp flames carry a subtle seeded flicker (±6% power, ±3% scale), so scrubbing feels alive.

**D29 · Adaptive sampling.** Final quality is 96 samples maximum with adaptive sampling (threshold 0.01), plus OpenImageDenoise, light tree and persistent data. Converged pixels can stop early, so this is an optimisation within SPEC's "96 samples", not a deviation.

**D30 · Doors share the Golu scene.** `render_doors.py` adds a "Doors" scene to the built .blend. It links the Golu collections behind a front wall with a doorway, and adds the door assembly, a warm glow light and a doorway haze volume. The glimpse of the Golu is the real scene, softened by f/2.8 depth of field and haze.

**D31 · Sprites.**
- Bowls and the empty tray are rendered over a shadow catcher, so they carry a soft contact shadow in alpha. The plates float when waved, so they have no catcher.
- All three third-dish options are rendered, so switching `prasadam.third_dish` needs no re-render.
- The "banana-leaf tray composite" is rendered as both an empty tray (the web lifts bowls off it) and a full composite (used for reduced motion and social previews).
- Three tiny petal sprites (marigold, rose, jasmine) feed the petal shower.

**D32 · Development flag `--stride N`.** `render_all.sh --stride N` renders every Nth frame at draft quality for quick placement checks. It is never used for acceptance renders.

**D33 · Files added beyond SPEC §2.** All of these support required behaviour:
- `blender/lib/config.py`, `blender/lib/render.py`, `blender/lib/mesh_utils.py` and `blender/lib/qa.py`: shared loading, render setup, geometry helpers and image checks.
- `blender/render_qa.py`: the §4.3 QA turntable.
- `blender/check_iconography.py`: the §4.3 check of every doll against ICONOGRAPHY.md.
- `scripts/build_frames_json.mjs`: writes `frames.json`. Bash has no JSON tool on Windows, and Node is already required for the web app.
- `scripts/lib/common.sh`: shared shell helpers.
- Web test files.

**D34 · Shell scripts.** The `.sh` scripts run in Git Bash on Windows and in bash on macOS and Linux. Blender is found via `$BLENDER`, then `PATH`, then the standard install directories.

## D. Web app

**D35 · Pre-Enter budget versus preloading the door frames.** SPEC requires both "preload the door frames before enabling the button" and "initial load under 3 MB before Enter". Seventy-two independent 1920-wide WebP frames are about 6–8 MB, so both can't hold.

Resolution:
- The 72 rendered door frames are also encoded as one short video, VP9 WebM first and H.264 MP4 as fallback, about 1.2 MB desktop and 0.45 MB mobile. It is preloaded as a Blob and drawn frame by frame to the entrance canvas.
- Frame 1 is a separate high-quality WebP poster, which is also the static entrance background (SPEC §4.6).
- The 72 WebP door frames are still produced. They are used if the video can't play and for reduced-motion mode (first and last frame).
- The nine "first frame of each step" images are preloaded at 960w and double as low-resolution placeholders.

Budget: desktop ≈ 0.45 MB app + 0.16 MB poster + 1.2 MB door video + 0.36 MB step frames ≈ **2.2 MB**. Mobile ≈ **1.3 MB**.

**D36 · "Load" versus "decode".** Decoded 1920×1080 bitmaps are 8.3 MB each. Holding the current and next step decoded (240 frames) would need about 2 GB. So `FrameCache` keeps two tiers:
- **Fetch tier:** compressed WebP Blobs for the current and next step, as SPEC says. Steps more than 2 away are freed.
- **Decode tier:** `createImageBitmap` for a window of ±8 frames on devices with 4 GB or less (`navigator.deviceMemory`), ±16 otherwise, biased in the scroll direction. Evicted bitmaps are `close()`d.

The nine step-first-frame bitmaps stay resident as the last fallback, so the canvas is never blank.

**D37 · Portrait phones.** Cover-fitting 16:9 frames to a 9:19.5 portrait screen shows only the centre 26% of each frame. To keep it cover-fit while still showing every doll, the crop window pans horizontally across each step as it scrolls. The pan is driven by the left and right extents of that frame's visible hotspots. Landscape and desktop views don't pan.

**D38 · Hotspot tracks.** `camera.py` projects each doll's head point every 8 frames of its step's hold, plus the lamp flame points, into `renders/manifest.json`. `build_frames_json.mjs` copies them into `web/src/lib/frames.json` (about 6 KB gzipped). The web interpolates linearly between samples and hides hotspots during transitions.

**D39 · Live lamp flicker.** SPEC §0 promises "live flame… on top". When scrolling stops, the rendered kuthuvilakku flames freeze, so a light canvas overlay adds a flicker glow (screen blend) at their projected positions. Reduced-motion mode turns it off.

**D40 · Ritual direction and rhythm.** "Clockwise" means clockwise on screen as the viewer sees it, because the viewer is the one offering the aarthi. The plate starts at the bottom of the ellipse, nearest the viewer's hand, and ends there. The small bell strikes four times per circle (24 strikes over the six circles).

**D41 · Prasadam ending and scroll lock.** SPEC doesn't say when the prasadam ritual ends. It closes 6 seconds after the blessing appears, or at once on Close or Escape, and scroll is restored then. The blessing stays in the `aria-live` region.

**D42 · Nadaswaram plays once per visit to Step 3 or 4.** It plays when the step becomes active and won't repeat for the same step until another step has been active for at least 10 seconds.

**D43 · Loading indicator.** The agal-vilakku loader is inline SVG with a CSS and canvas flame, not a render, so it appears in the first paint at about 2 KB.

**D44 · Fonts and styling.**
- Noto Serif Tamil (400/600) for Tamil and Cormorant Garamond (500/600) for English, self-hosted via Fontsource with unicode-range subsets (about 200 KB total).
- Tailwind v4 uses a JS config (`@config`) that reads the design tokens from the config palette.

**D45 · Scroll pace.** 40 frames per viewport height of scroll, so a full pass is about 28 viewport heights. A step is 2.4 screens.

**D46 · Generated assets stay out of git.** `renders/`, `web/static/{frames,frames-mobile,doors,props}` and `web/src/lib/frames.json` are gitignored, because the final WebPs are about 150–200 MB. README documents render → encode → build → deploy, and suggests Git LFS or a release archive for sharing a finished render.

**D47 · Repository root.** SPEC §2 names the root `golu-darshan/`. This repository's root (`Golu/`) plays that role and is not renamed.
