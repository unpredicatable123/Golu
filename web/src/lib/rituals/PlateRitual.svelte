<script lang="ts">
  // Aarthi / camphor ritual (SPEC §5.3): the plate rises, a live flame sits on the wick, the plate circles the active
  // step 3× clockwise then 3× anticlockwise (eased at the reversal), a warm screen-blend glow follows it, the small
  // bell rings in rhythm; then the plate lowers and fades. Camphor: brighter, taller flame with smoke; goes out at the
  // end with a last wisp. Reduced motion: a static glowing plate, no orbit.
  import { onMount } from 'svelte';
  import { config, type PlateRitual } from '$lib/config';
  import { frames } from '$lib/frames';
  import type { AudioManager } from '$lib/audio/audio';
  import { frameToViewport } from '$lib/engine/coverFit';
  import { hotspotsAt } from '$lib/engine/hotspots';
  import { view } from '$lib/engine/view';
  import { reducedMotion } from '$lib/stores';
  import { FlameRenderer } from './flame';
  import { countTurns, ellipsePoint, orbitDuration, orbitTravel, type OrbitSpec } from './orbit';
  import { SmokeWisps, drawGlow } from './particles';
  import { logRitual } from './ritualState';

  let { kind, audio, ondone }: { kind: 'aarthi' | 'camphor'; audio: AudioManager | null; ondone: () => void } = $props();
  const R: PlateRitual = $derived(config.rituals[kind]);

  let fx: HTMLCanvasElement;
  let glow: HTMLCanvasElement;
  let plate: HTMLImageElement;
  let px = $state(0);
  let py = $state(0);
  let plateOpacity = $state(0);
  let plateW = $state(220);
  let announce = $state('');

  const spec: OrbitSpec = $derived({
    cw: R.motion.circles_clockwise,
    ccw: R.motion.circles_anticlockwise,
    secPerCircle: R.motion.seconds_per_circle,
    reversalEase: R.motion.reversal_ease_fraction,
    startDeg: R.motion.start_angle_deg,
  });

  function centreOfStep(w: number, h: number): [number, number] {
    const v = $view;
    if (!v) return [w / 2, h * 0.52];
    const pts = hotspotsAt(frames, v.step, Math.min(v.local, frames.steps[v.step - 1].hold[1]))
      .filter((s) => s.vis)
      .map((s) => frameToViewport(s.x, s.y, v.rect, v.srcW, v.srcH));
    if (!pts.length) return [w / 2, h * 0.52];
    const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length;
    const cy = pts.reduce((a, p) => a + p[1], 0) / pts.length;
    return [Math.min(w * 0.75, Math.max(w * 0.25, cx)), Math.min(h * 0.7, Math.max(h * 0.3, cy + h * 0.06))];
  }

  onMount(() => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = window.innerWidth;
    const H = window.innerHeight;
    for (const c of [fx, glow]) {
      c.width = W * dpr;
      c.height = H * dpr;
    }
    const fctx = fx.getContext('2d') as CanvasRenderingContext2D;
    const gctx = glow.getContext('2d') as CanvasRenderingContext2D;
    fctx.scale(dpr, dpr);
    gctx.scale(dpr, dpr);
    const portrait = W < H;
    plateW = Math.max(150, Math.min(300, Math.min(W, H) * 0.32));
    const rx = W * (portrait ? R.motion.ellipse_rx_vw_portrait : R.motion.ellipse_rx_vw);
    const ry = H * (portrait ? R.motion.ellipse_ry_vh_portrait : R.motion.ellipse_ry_vh);
    const [cx, cy] = centreOfStep(W, H);
    // MotionPathPlugin (SPEC stack) samples an SVG ellipse that starts at the bottom and runs clockwise on screen;
    // orbitTravel() decides how far along it the plate is, so the 3 + 3 turn count stays exact.
    let onPath: ((travelDeg: number) => [number, number]) | null = null;
    (async () => {
      const { gsap } = await import('gsap');
      const { MotionPathPlugin } = await import('gsap/MotionPathPlugin');
      gsap.registerPlugin(MotionPathPlugin);
      const d = `M ${cx} ${cy + ry} A ${rx} ${ry} 0 1 1 ${cx} ${cy - ry} A ${rx} ${ry} 0 1 1 ${cx} ${cy + ry} Z`;
      const raw = MotionPathPlugin.getRawPath(d);
      MotionPathPlugin.cacheRawPathMeasurements(raw);
      onPath = (travel) => {
        const frac = (((travel / 360) % 1) + 1) % 1;
        const p = MotionPathPlugin.getPositionOnPath(raw, frac);
        return [p.x, p.y];
      };
    })();
    const flame = new FlameRenderer(fctx, R.flame, kind === 'aarthi' ? 7 : 13);
    const smoke = new SmokeWisps(fctx);
    const still = $reducedMotion;
    if (still) flame.freeze();
    const rise = R.motion.rise_seconds;
    const lower = R.motion.lower_seconds;
    const orbit = orbitDuration(spec);
    const total = rise + (still ? 4 : orbit) + lower;
    const strikeEvery = 360 / R.bell.strikes_per_circle;
    let lastStrike = 0;
    const travelSamples: number[] = [];
    let start = performance.now();
    let last = start;
    let raf = 0;
    let finished = false;
    let extinguishing = false;
    announce = `${R.label_ta} — ${R.label_en}`;

    const finish = () => {
      if (finished) return;
      finished = true;
      cancelAnimationFrame(raf);
      const turns = countTurns(travelSamples.length ? travelSamples : [0]);
      logRitual(kind, turns.cwTurns, turns.ccwTurns);
      ondone();
    };

    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const t = (now - start) / 1000;
      let x = cx;
      let y = cy + ry;
      let alpha = 1;
      if (t < rise) {
        const k = t / rise;
        const e = 1 - (1 - k) * (1 - k);
        y = H + plateW * 0.6 - (H + plateW * 0.6 - (cy + ry)) * e;
        alpha = e;
      } else if (!still && t < rise + orbit) {
        const travel = orbitTravel(t - rise, spec);
        travelSamples.push(travel);
        [x, y] = onPath ? onPath(travel) : ellipsePoint(spec.startDeg + travel, cx, cy, rx, ry);
        if (Math.abs(travel - lastStrike) >= strikeEvery) {
          lastStrike = travel;
          audio?.bellSmall(R.bell.volume);
        }
      } else if (still && t < rise + 4) {
        y = cy;
      } else {
        if (!still && travelSamples.length && travelSamples[travelSamples.length - 1] !== orbitTravel(orbit, spec)) {
          travelSamples.push(orbitTravel(orbit, spec));
        }
        const k = Math.min(1, (t - rise - (still ? 4 : orbit)) / lower);
        y = (still ? cy : cy + ry) + k * k * (H * 0.5);
        alpha = 1 - k;
        if (kind === 'camphor' && !extinguishing) {
          extinguishing = true;
          flame.extinguish(R.extinguish_seconds ?? 1.4).then(() =>
            smoke.emit(x + (R.flame_anchor[0] - 0.5) * plateW, y + (R.flame_anchor[1] - 0.5) * plateW, 3, 3.4));
        }
      }
      px = x;
      py = y;
      plateOpacity = alpha;
      // the sprite is centred on (x, y) and square: map the measured flame anchor into the page
      const wickX = x + (R.flame_anchor[0] - 0.5) * plateW;
      const wickY = y + (R.flame_anchor[1] - 0.5) * plateW;
      fctx.clearRect(0, 0, W, H);
      gctx.clearRect(0, 0, W, H);
      flame.setAnchor(wickX, wickY, kind === 'camphor' ? plateW / 230 : plateW / 260);
      flame.step(dt);
      if (kind === 'camphor' && !still && flame.alive && Math.random() < dt * 9) smoke.emit(wickX, wickY - 40, 1);
      smoke.step(dt);
      drawGlow(gctx, wickX, wickY - 10, Math.min(W, H) * R.glow.radius_vmin, R.glow.color, R.glow.intensity * flame.intensity() * alpha);
      fctx.globalAlpha = alpha;
      flame.draw();
      smoke.draw();
      fctx.globalAlpha = 1;
      if (t >= total && !smoke.active) finish();
    };
    raf = requestAnimationFrame(tick);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') finish();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('keydown', onKey);
    };
  });
</script>

<div class="ritual" role="region" aria-label={`${R.label_ta} — ${R.label_en}`}>
  <canvas bind:this={glow} class="glow" aria-hidden="true"></canvas>
  <img
    bind:this={plate}
    class="plate"
    src={`/props/${R.sprite}.webp?v=${frames.version}`}
    alt={`${R.label_ta} — ${R.label_en}`}
    style:width="{plateW}px"
    style:left="{px}px"
    style:top="{py}px"
    style:opacity={plateOpacity}
  />
  <canvas bind:this={fx} class="fx" aria-hidden="true"></canvas>
  <p class="sr-only" aria-live="polite">{announce}</p>
</div>

<style>
  .ritual { position: fixed; inset: 0; z-index: 20; pointer-events: none; }
  .glow, .fx { position: absolute; inset: 0; width: 100vw; height: 100vh; }
  .glow { mix-blend-mode: screen; }
  .plate {
    position: absolute;
    transform: translate(-50%, -50%);
    filter: drop-shadow(0 12px 18px rgb(0 0 0 / 0.55));
    will-change: left, top;
  }
</style>
