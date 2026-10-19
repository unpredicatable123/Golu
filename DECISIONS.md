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

## E. Decisions made during the build

**D48 · SvelteKit 2 line, pinned.** The newest majors (SvelteKit 3, Vite 8, TypeScript 6) require each other and were released after the period the executor can verify. The app pins the maintained SvelteKit 2.70 / Svelte 5.57 / Vite 7.3 / TypeScript 5.9 line, which covers every SPEC requirement. Upgrading later is a dependency bump.

**D49 · Dolls without subdivision.** Voxel remeshing at 1/175 of doll height plus Laplacian smoothing already gives the soft clay form. A subdivision level on 73 dolls raised the scene from about 3.5M to about 17M vertices, and with the occlusion ray casts it exhausted memory on the 16 GB build machine. QA renders with and without subdivision were indistinguishable.

**D50 · Hotspot occlusion by a static BVH.** `scene.ray_cast` evaluates subdivision for every object on each call. Only the camera moves, so one BVH tree over the base meshes of dolls, story props and tiers is built once and reused for all samples.

**D51 · Lighter EEVEE draft settings.** On an integrated GPU a full-quality EEVEE frame took about 80 s. Draft frames therefore use:
- 12 TAA samples;
- no screen-space raytracing or volumetric shadows;
- shadows at half resolution;
- no shadows from the small practical lights (agal lamps and wick flames).

Final renders use Cycles with every light casting shadows, so the final images are unaffected.

**D52 · Camera framing.** Each step's shot frames 75% of the step width and dollies until the end dolls sit about 30% inside the frame. The pitch is 10° down, which looks over tall props on the step below (the Govardhana hill, the gantry). This lets every doll pass the "visible in at least 30% of its hold" check.

**D53 · Scale tuning from the step lineups.** These are content values in the config:
- Step-1 models and children were scaled up so they read at camera distance: Chandrayaan-3 ×1.5, children ×1.25, trains ×1.15–1.2.
- The PSLV is ×0.8, with its gantry moved to its outer side, so it no longer screens Matsya on step 2.
- The wild elephant is ×0.7.
- The eight Ashta Lakshmis are ×0.9, so eight lotus seats fit one tread.
- The cart is ×0.8.

**D54 · Plate motion.** The aarthi and camphor plates follow an SVG ellipse sampled by GSAP's MotionPathPlugin, as SPEC's stack lists. The distance travelled along it comes from the orbit function, which unit tests check: exactly 3 clockwise and 3 anticlockwise turns, eased at the reversal. The plate's position along the path is therefore exact rather than tween-timed.

**D55 · Tall props versus the step above.** The steps rise 0.24 m, and from the 10° camera the sight line to the next tread's feet clears about 0.29 m above a step. Tall props were therefore sized to that limit:
- **Wedding mandapam:** the first version had a 0.43 m pyramid roof, which hid Murugan and Valli. It is now 0.267 m pillars under a near-flat silk canopy with a scalloped valance and a small finial. Every hanging edge stays above the camera ray to the couple's faces (the visibility check), and the canopy stays below step 4's sight line.
- **Govardhana hill:** it has to sit above Krishna's raised finger, so it cannot clear the step above. It was narrowed to 0.28 m and flattened instead. The manifest's occlusion test already tracks the step-8 hotspot it partly covers.

**D56 · Tread trinkets.** The Saints and Ashta Lakshmi steps have no story set, and their evenly spaced dolls left bare cloth between them. Every front-row gap wider than 0.1 m now holds a small brass pooja item just ahead of the dolls: a flower plate, a kumkum and turmeric cup pair, or a kindi. These are decoration, not dolls, so the doll checks ignore them.

**D57 · Matte painted terrain.** M_ClayGloss gains material kind 5: painted terrain (hill, rocks, trees) with a 0.1 clear-coat instead of 0.6. At full varnish the Govardhana hill read as glossy plastic, while golu terrain pieces are matte, poster-painted clay. The doll kinds are unchanged.

**D58 · "High" render tier and frame blending.** On the user's request for sharper, smoother frames before the final pass, a third quality tier sits between draft and final:
- **Settings:** EEVEE at 1920×1080, 16 samples, full-resolution shadows. Measured about 55 s per frame; 720p saved only about 10%, because the cost is dominated by samples and per-frame scene sync, so the user chose 1080p.
- **Scene:** it renders the same built scene as draft, so no rebuild is needed.
- **Why:** on this laptop (4-core CPU, integrated GPU), Cycles final quality would take days. The high tier gets a sharp finish in hours.
- **Player:** the frame player now blends each frame into the next by the fractional scroll position, and upscales with high-quality smoothing. Scrubbing glides between rendered frames instead of stepping.

**D59 · Half-rate final render with motion interpolation.** The user's submission deadline is the next day, and a full-rate render would not fit, so the 720p render covers only the odd global frames (`--stride 2`, 564 frames).
- **Interpolation:** `encode_frames.sh --interpolate` rebuilds the even frames with ffmpeg's motion-compensated `minterpolate` over the global sequence, so step boundaries interpolate across the continuous camera move. The doors are handled the same way.
- **Check:** on draft frames, an interpolated frame scores 29.2 dB PSNR against the true render, versus 24.4 dB for repeating the previous frame. Most of the remaining difference is the renderer's own frame-to-frame noise.
- **Search range:** the hold dolly moves about 40 px between rendered frames at 1080p, beyond ffmpeg's default 32 px motion search, which produced ghosting. `search_param=96` (EPZS) gives clean midpoints.
- **Fast moves are rendered at full rate:** between steps the camera rises quickly, and motion interpolation tears at those speeds. So every frame of the step transitions (24 per step), the finale (72) and the door swing (72) is rendered. The encoder copies real renders over interpolated frames, so interpolation fills only the slow holds: 432 of the 1,128 fly-through frames. In total, 696 fly-through frames and all 72 door frames are real renders.

**D60 · Encode quality.** Encoding at WebP q75, about 100 KB per 1080p frame, smoothed away the faces, jewellery and garland detail the high render had added, and the user read the result as low quality. Frames are now encoded with a light unsharp mask (5×5, 0.7) at q85 for desktop (about 150–200 KB per frame) and q78 for mobile. Desktop frames total about 220 MB. They stream one step at a time, so a step costs about 25 MB on desktop.

**D61 · Om recording.** The project owner supplied a 3½-minute Om chant recording (`om-chant.mp3.mpeg`).
- **Preparation:** trimmed of its 0.3 s lead-in silence, loudness-normalised to −16 LUFS, given 1.5 s fades so the loop point doesn't click, and encoded to Opus (1.9 MB) and MP3 (3.3 MB).
- **Streaming:** at that size, downloading it up front would break the 3 MB pre-Enter budget. So the Om is not preloaded: it streams (Howler `html5`) when it starts after Enter, during its 3 s fade-in. If streaming fails, it falls back to the synthesised drone.
- **Other audio:** the bells stay synthesised until recordings are supplied.

**D62 · Smooth scrubbing on this laptop.** The final-frame check in Chrome found two problems.
- **Fallback blending:** frames were blended with the next frame even when the current one was a stand-in (the nearest decoded frame during a fast scroll). During transitions that showed a doubled, see-through image. Blending now happens only between the two exact neighbours.
- **Downscaling cost:** every animation frame downscaled two full 1080p bitmaps on the main thread. Frames are now decoded straight to their cover-fit draw size (`createImageBitmap` resize, off the main thread), so drawing is a 1:1 copy.
- **Result** for a 6 s scripted scroll through three steps: frames over 20 ms fell from 49% to 5%, the 95th percentile from 67 to 32 ms, and stand-in frames from 177 to 0.

**D63 · Ritual alignment from the rendered sprites.**
- **Flame position:** the plate flame was placed by a guessed offset shared by both plates. It floated above the aarthi lamp and missed the camphor block. Each ritual now has a `flame_anchor` measured on its sprite: the wick tip on the lamp rim at (0.629, 0.461), and the camphor block's top at (0.391, 0.434).
- **Prasadam tray:** separate bowl sprites in a flat CSS row could not line up with the three-quarter-view banana leaf. The tray now shows `tray_composite`, the whole tray rendered in 3D with the configured trio. Names are listed below in the same order, and steam rises from the bowl centres measured on that sprite (`composite_bowls`). Changing the third dish therefore needs a sprite re-render (`render_props.py --only tray_composite`).

**D64 · Load performance.** Nothing animates behind the entrance any more: the flame-flicker and dust layers mount after Enter, and the frame player draws only after Enter. The entrance title is prerendered, and the woff2 fonts are preloaded from the head.
- **Desktop:** Lighthouse performance went from 68 to 92 (blocking time from 450 ms to 10 ms).
- **Mobile:** the simulated slow-4G, 4× CPU preset scores about 64–67, below the planned 85. Its LCP is the Tamil title text, and it is dominated by script and font arrival on that profile; it is recorded as a known limitation.

**D65 · Every frame is a real render; no blending (replaces the interpolation in D59 and the blending in D58).**
- **Interpolation:** checked at full size, the motion-interpolated hold frames were visibly damaged where dolls overlap (ghosted figures, smeared hands and emblems, warped garlands). The owner saw this as glitches and blur. A whole-frame PSNR audit had missed it, because the damage is local.
- **Blending:** crossfading neighbouring frames also showed a double image, because the hold dolly moves about 20 px per frame at 1080p.
- **Shipped:** the owner's deadline left no time to render the 432 remaining even hold frames (about 5½ h). The shipped encode holds each real hold frame for two frames (`--fill-gaps`), so every image shown is a crisp real render. The holds update at an effective 12 fps while scrubbing. Rendering those frames (`render_steps.py --quality high --frames 2,4,…,96`) and re-encoding without `--fill-gaps` is the upgrade path.
- **Player:** always draws exactly one whole frame.

**D66 · Hotspots on riders.** Riders (Kalki on his horse, Durga on her lion) are lifted onto the saddle after the skeleton is built, but the head centre was taken from the unlifted skeleton. Their hotspot dots, and the face-paint centre, sat about 0.15 of the doll height too low (Kalki's dot was on the saddle). The lift is now added to the head centre, and the manifest's hotspot tracks were regenerated. The shipped frames were rendered before this fix, so Kalki and Durga have no painted eyes in them. The next render picks the fix up; it needs whole steps 2 and 9 re-rendered so the faces stay consistent from frame to frame.

**D67 · Deploying on Vercel from git (supersedes D46's "frames are not in git").** The owner deploys by connecting the GitHub repository to Vercel, which builds from a clean clone. So the encoded web assets are committed: `web/static/frames*`, `doors`, `props`, `audio` and `web/src/lib/frames.json`, about 330 MB in 2,400 files, each well under GitHub's 100 MB file limit. The raw PNG renders stay git-ignored. A root `vercel.json` installs and builds in `web/` and serves `web/build`, with immutable caching for the frame, door, sprite and audio paths and for `_app/immutable`. Frame URLs carry `?v=<version>`, so a re-encode busts caches.

**D68 · Phone layout.**
- **Portrait band:** on a tall portrait phone, covering the screen with a 16:9 frame showed only about a quarter of its width, so most dolls on a step were off-screen at any moment, and the 960 px frames were upscaled about 4.5×. Portrait screens now show at least 55% of the frame width (`bandFit`): the frame fills the width as a band centred at 54% of the height, under the title card. Above and below is a darkened, blurred copy of the same frame with feathered edges. Hotspots, lamp flicker and the plate path use the band rectangle.
- **Phone frames:** phones load the full-HD frame set, which is 1:1 at that band width, unless data saver is on or the network is 2G/3G. The decode window is 8 frames (about 70 MB of bitmaps).
- **Short landscape screens** (height ≤ 520 px):
  - The title card shows titles only and is hidden during rituals.
  - The title card clears the navigator diyas, and on phones it sits below the audio control.
  - Ritual buttons and info cards are smaller.
  - The prasadam tray is sized to the screen height.
