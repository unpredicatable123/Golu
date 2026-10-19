<script lang="ts">
  // Scroll-driven frame player (SPEC §5.2): one full-viewport DPR-aware canvas, cover-fit, ScrollTrigger scrub 0.5,
  // drawing in rAF only when the frame (or the viewport) changes. Never blank (FrameCache placeholders).
  import { onDestroy, onMount, tick } from 'svelte';
  import { config } from '$lib/config';
  import { frames, stepOfGlobal, stepProgress } from '$lib/frames';
  import { FrameCache, decodeWindowFor } from '$lib/engine/FrameCache';
  import { MIN_VISIBLE_WIDTH, bandFit, cropWidthFraction, portraitFocusX } from '$lib/engine/coverFit';
  import { hotspotsAt } from '$lib/engine/hotspots';
  import { totalScrollPx } from '$lib/engine/scrollMap';
  import { view } from '$lib/engine/view';
  import { activeStep, entered, globalFrame } from '$lib/stores';

  let { cache }: { cache: FrameCache } = $props();

  let canvas: HTMLCanvasElement;
  let spacer: HTMLDivElement;
  let ctx: CanvasRenderingContext2D | null = null;
  let raf = 0;
  let lastDrawn = -1;
  let lastBitmap: ImageBitmap | null = null;
  let target = 0;
  let prevTarget = 0;
  let dirty = true;
  let killScroll: (() => void) | null = null;
  let refreshScroll: (() => void) | null = null;
  let isEntered = false;
  let scrollPx = $state(0);

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(window.innerWidth * dpr);
    canvas.height = Math.round(window.innerHeight * dpr);
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    if (ctx) {                                  // resizing the canvas resets its context state
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
    }
    scrollPx = totalScrollPx(frames.totalFrames, window.innerHeight);
    // decode size = what the frame is drawn at (in portrait the band shows MIN_VISIBLE_WIDTH of the frame width)
    const crop = cropWidthFraction(16, 9, canvas.width, canvas.height);
    const visible = Math.max(crop, MIN_VISIBLE_WIDTH);
    cache.setDrawSize(Math.round(canvas.width / Math.min(1, visible)), Math.round((canvas.width / Math.min(1, visible)) * 9 / 16) || canvas.height);
    dirty = true;
    tick().then(() => refreshScroll?.());     // re-measure once the spacer has its new height
  }

  // portrait band: the space above and below is a soft, darkened blur of the same frame (a tiny copy stretched
  // up is a cheap blur), feathered into the band's edges
  let blurCanvas: HTMLCanvasElement | null = null;
  function drawBackdrop(bmp: ImageBitmap, r: { dy: number; dh: number }, W: number, H: number) {
    if (!ctx) return;
    blurCanvas ??= Object.assign(document.createElement('canvas'), { width: 32, height: 18 });
    const b = blurCanvas.getContext('2d') as CanvasRenderingContext2D;
    b.drawImage(bmp, 0, 0, 32, 18);
    const cw = (H * 16) / 9;
    ctx.drawImage(blurCanvas, 0, 0, 32, 18, (W - cw) / 2, 0, cw, H);
    ctx.fillStyle = 'rgba(20, 8, 4, 0.55)';
    ctx.fillRect(0, 0, W, H);
    const f = Math.min(r.dy, H * 0.06);
    if (f > 1) {
      const top = ctx.createLinearGradient(0, r.dy, 0, r.dy + f);
      top.addColorStop(0, 'rgba(20, 8, 4, 0.9)');
      top.addColorStop(1, 'rgba(20, 8, 4, 0)');
      const bot = ctx.createLinearGradient(0, r.dy + r.dh - f, 0, r.dy + r.dh);
      bot.addColorStop(0, 'rgba(20, 8, 4, 0)');
      bot.addColorStop(1, 'rgba(20, 8, 4, 0.9)');
      featherTop = top;
      featherBottom = bot;
      featherSize = f;
    } else {
      featherTop = featherBottom = null;
    }
  }
  let featherTop: CanvasGradient | null = null;
  let featherBottom: CanvasGradient | null = null;
  let featherSize = 0;

  function draw() {
    raf = requestAnimationFrame(draw);
    if (!ctx || !isEntered) return;          // nothing to draw behind the entrance doors
    const g = Math.round(target);
    if (g !== lastDrawn && isEntered) {      // no frame streaming behind the entrance (pre-Enter budget < 3 MB)
      cache.setPlayhead(g, g >= prevTarget ? 1 : -1);
      prevTarget = g;
    }
    // always one whole rendered frame: crossfading neighbours ~20 px apart reads as a double, blurred image (D65)
    const bmp = cache.get(g) ?? cache.nearest(g);
    if (!bmp) return;
    if (g === lastDrawn && bmp === lastBitmap && !dirty) return;
    const { step, local } = stepOfGlobal(g);
    const W = canvas.width;
    const H = canvas.height;
    const srcW = bmp.width;
    const srcH = bmp.height;
    let focus = 0.5;
    const crop = Math.max(cropWidthFraction(srcW, srcH, W, H), MIN_VISIBLE_WIDTH);
    if (crop < 0.98) {
      const sp = stepProgress(g);
      const xs = hotspotsAt(frames, step, Math.min(local, frames.steps[step - 1].hold[1])).map((h) => h.x);
      focus = portraitFocusX(xs, crop, sp.phase === 'hold' ? sp.p : sp.phase === 'finale' ? 0.5 : 1);
    }
    const r = bandFit(srcW, srcH, W, H, focus);
    if (r.dh < H - 1) drawBackdrop(bmp, r, W, H);
    ctx.drawImage(bmp, r.sx, r.sy, r.sw, r.sh, r.dx, r.dy, r.dw, r.dh);
    if (r.dh < H - 1 && featherTop && featherBottom) {
      ctx.fillStyle = featherTop;
      ctx.fillRect(0, r.dy, W, featherSize);
      ctx.fillStyle = featherBottom;
      ctx.fillRect(0, r.dy + r.dh - featherSize, W, featherSize);
    }
    lastDrawn = g;
    lastBitmap = bmp;
    dirty = false;
    const css = 1 / Math.min(window.devicePixelRatio || 1, 2);
    view.set({ rect: { ...r, dx: r.dx * css, dy: r.dy * css, dw: r.dw * css, dh: r.dh * css }, srcW, srcH,
               width: W * css, height: H * css, step, local });
    globalFrame.set(g);
    activeStep.set(step);
  }

  onMount(() => {
    ctx = canvas.getContext('2d', { alpha: false });
    if (ctx) {
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';     // frames are upscaled on large or high-DPI screens
    }
    resize();
    window.addEventListener('resize', resize);
    raf = requestAnimationFrame(draw);
    let cancelled = false;
    (async () => {
      const { gsap } = await import('gsap');
      const { ScrollTrigger } = await import('gsap/ScrollTrigger');
      await tick();                           // the spacer must have its height before ScrollTrigger measures it
      if (cancelled) return;
      gsap.registerPlugin(ScrollTrigger);
      const proxy = { frame: 0 };
      const tween = gsap.to(proxy, {
        frame: frames.totalFrames - 1,
        ease: 'none',
        scrollTrigger: {
          trigger: spacer,
          start: 'top top',
          end: () => `+=${Math.max(1, spacer.offsetHeight - window.innerHeight)}`,
          invalidateOnRefresh: true,
          scrub: 0.5,
        },
        onUpdate: () => {
          target = proxy.frame;
        },
      });
      killScroll = () => {
        tween.scrollTrigger?.kill();
        tween.kill();
      };
      refreshScroll = () => ScrollTrigger.refresh();
      refreshScroll();
    })();
    if (import.meta.env.DEV || import.meta.env.MODE === 'test') {
      const w = window as Window;
      w.__golu = w.__golu ?? { stats: () => cache.stats(), ritualLog: [], audio: () => ({ state: 'none', om: 0, missing: [] }) };
      w.__golu.stats = () => cache.stats();
    }
    // the entrance overlay is removed on Enter: re-measure so the scrub range matches the final layout
    const unsubEntered = entered.subscribe((v) => {
      isEntered = v;
      if (!v) return;
      cache.setPlayhead(Math.floor(target), 1);   // start streaming the current and next step now
      tick().then(() => refreshScroll?.());
    });
    return () => {
      cancelled = true;
      unsubEntered();
    };
  });

  onDestroy(() => {
    if (typeof window === 'undefined') return;
    cancelAnimationFrame(raf);
    window.removeEventListener('resize', resize);
    killScroll?.();
  });
</script>

<div class="frame-wrap" role="img" aria-label={`${config.ui.canvas_alt_ta} — ${config.ui.canvas_alt_en}`}>
  <canvas bind:this={canvas} class="frame-canvas" aria-hidden="true"></canvas>
</div>
<div bind:this={spacer} class="spacer" style:height="{scrollPx}px" aria-hidden="true"></div>

<style>
  .frame-canvas {
    position: fixed;
    inset: 0;
    display: block;
    background: var(--tok-night);
    z-index: 0;
  }
  .spacer {
    position: relative;
    width: 1px;
    pointer-events: none;
  }
</style>
