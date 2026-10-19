<script lang="ts">
  // Entrance (SPEC §5.1, DECISIONS D35): poster = door frame 1; the door sequence plays on a canvas from a
  // preloaded video (WebP frames as fallback); Enter is enabled only after doors + step placeholders are loaded.
  import { onMount } from 'svelte';
  import { config } from '$lib/config';
  import { frames } from '$lib/frames';
  import type { AudioManager } from '$lib/audio/audio';
  import type { FrameCache } from '$lib/engine/FrameCache';
  import { coverFit } from '$lib/engine/coverFit';
  import { reducedMotion } from '$lib/stores';
  import AgalLoader from './AgalLoader.svelte';
  import BrassButton from './BrassButton.svelte';

  // cache/audio arrive after the app initialises; the entrance itself is in the prerendered HTML (fast LCP)
  let { cache, audio, onentered }: { cache: FrameCache | null; audio: AudioManager | null; onentered: () => void } = $props();
  let started = false;

  let canvas: HTMLCanvasElement;
  let ready = $state(false);
  let posterOk = $state(true);
  let progress = $state(0);
  let playing = $state(false);
  let bloom = $state(false);
  let leaving = $state(false);
  let videoUrl: string | null = null;
  let mobile = $state(false);

  const posterDesktop = `/doors/desktop/poster.webp?v=${frames.version}`;
  const posterMobile = `/doors/mobile/poster.webp?v=${frames.version}`;

  async function preload(cache: FrameCache) {
    const width = mobile ? 960 : 1920;
    const sources = [`/doors/doors-${width}.webm`, `/doors/doors-${width}.mp4`];
    const probe = document.createElement('video');
    const pick = sources.find((s) => probe.canPlayType(s.endsWith('.webm') ? 'video/webm; codecs="vp9"' : 'video/mp4; codecs="avc1.640028"'));
    let doorsDone = 0;
    let stepsDone = 0;
    const report = () => {
      progress = 0.6 * doorsDone + 0.4 * (stepsDone / frames.steps.length);
    };
    const doors = (async () => {
      if (!pick) return;
      try {
        const res = await fetch(`${pick}?v=${frames.version}`);
        if (!res.ok) throw new Error(String(res.status));
        videoUrl = URL.createObjectURL(await res.blob());
      } catch {
        videoUrl = null;     // falls back to the WebP door frames when playing
      }
      doorsDone = 1;
      report();
    })();
    const steps = cache.preloadPlaceholders((d) => {
      stepsDone = d;
      report();
    });
    await Promise.all([doors, steps.catch(() => undefined)]);
    progress = 1;
    ready = true;
  }

  function drawCover(ctx: CanvasRenderingContext2D, src: CanvasImageSource, w: number, h: number) {
    const r = coverFit(w, h, ctx.canvas.width, ctx.canvas.height);
    ctx.drawImage(src, r.sx, r.sy, r.sw, r.sh, 0, 0, ctx.canvas.width, ctx.canvas.height);
  }

  async function playDoorsVideo(ctx: CanvasRenderingContext2D): Promise<void> {
    const v = document.createElement('video');
    v.src = videoUrl as string;
    v.muted = true;
    v.playsInline = true;
    await v.play();
    await new Promise<void>((resolve) => {
      const rvfc = (v as HTMLVideoElement & { requestVideoFrameCallback?: (cb: () => void) => number }).requestVideoFrameCallback;
      const frame = () => {
        drawCover(ctx, v, v.videoWidth, v.videoHeight);
        if (v.ended) resolve();
        else if (rvfc) rvfc.call(v, frame);
        else requestAnimationFrame(frame);
      };
      v.onended = () => {
        drawCover(ctx, v, v.videoWidth, v.videoHeight);
        resolve();
      };
      frame();
    });
  }

  async function playDoorsFrames(ctx: CanvasRenderingContext2D): Promise<void> {
    const dir = mobile ? 'mobile' : 'desktop';
    const n = frames.doors.count;
    const load = async (i: number) => {
      const res = await fetch(`/doors/${dir}/f_${String(i + 1).padStart(4, '0')}.webp?v=${frames.version}`);
      if (!res.ok) throw new Error(`door frame ${i + 1}: ${res.status}`);
      return createImageBitmap(await res.blob());
    };
    const first = await load(0);           // probe one frame before requesting all of them
    const imgs = [first, ...(await Promise.all(Array.from({ length: n - 1 }, (_, i) => load(i + 1))))];
    const start = performance.now();
    await new Promise<void>((resolve) => {
      const tick = (now: number) => {
        const i = Math.min(n - 1, Math.floor(((now - start) / 1000) * frames.fps));
        drawCover(ctx, imgs[i], imgs[i].width, imgs[i].height);
        if (i < n - 1) requestAnimationFrame(tick);
        else resolve();
      };
      requestAnimationFrame(tick);
    });
    imgs.forEach((b) => b.close());
  }

  async function enter() {
    if (!ready || playing || !audio) return;
    playing = true;
    await audio.unlock().catch((e) => console.warn('[golu] audio unlock failed:', e));   // 1. unlock audio (inside the click)
    audio.bellLarge();                    // 2. large temple bell
    const ctx = canvas.getContext('2d');
    if (ctx) {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      try {
        if ($reducedMotion) {
          // reduced motion: crossfade poster → last door frame (no door swing)
          const res = await fetch(`/doors/${mobile ? 'mobile' : 'desktop'}/f_${String(frames.doors.count).padStart(4, '0')}.webp?v=${frames.version}`);
          if (!res.ok) throw new Error(`door frame: ${res.status}`);
          const last = await createImageBitmap(await res.blob());
          drawCover(ctx, last, last.width, last.height);
        } else if (videoUrl) {
          await playDoorsVideo(ctx).catch(() => playDoorsFrames(ctx));   // 3. the 72 door frames on canvas
        } else {
          await playDoorsFrames(ctx);
        }
      } catch (e) {
        // never strand the visitor at the doors: go straight to the bloom and the golu
        console.warn('[golu] door sequence unavailable, skipping:', e instanceof Error ? e.message : e);
      }
    }
    audio.startOm();                      // 4. Om fades in to 35 % over 3 s
    bloom = true;                         // 5. golden bloom, then into the scroll experience
    await new Promise((r) => setTimeout(r, $reducedMotion ? 300 : 900));
    leaving = true;
    onentered();
  }

  $effect(() => {
    if (cache && !started) {
      started = true;
      preload(cache);
    }
  });

  onMount(() => {
    mobile = window.innerWidth < 768;
    return () => {
      if (videoUrl) URL.revokeObjectURL(videoUrl);
    };
  });
</script>

<svelte:head>
  <link rel="preload" as="image" href={posterDesktop} media="(min-width: 768px)" fetchpriority="high" />
  <link rel="preload" as="image" href={posterMobile} media="(max-width: 767px)" fetchpriority="high" />
</svelte:head>

<section class="entrance" class:leaving aria-label={`${config.meta.title_ta} — ${config.meta.title_en}`}>
  {#if posterOk}
    <picture>
      <source media="(max-width: 767px)" srcset={posterMobile} />
      <img class="poster" src={posterDesktop} alt={`${config.meta.title_ta} — ${config.meta.title_en}`}
           fetchpriority="high" onerror={() => (posterOk = false)} />
    </picture>
  {/if}
  <canvas bind:this={canvas} class="doors" class:visible={playing} aria-hidden="true"></canvas>
  <div class="bloom" class:on={bloom} aria-hidden="true"></div>
  {#if !playing}
    <div class="center">
      <h1 class="title">
        <span class="ta" lang="ta">{config.meta.title_ta}</span>
        <span class="en" lang="en">{config.meta.title_en}</span>
      </h1>
      {#if ready}
        <BrassButton size="lg" ta={config.ui.enter_ta} en={config.ui.enter_en} onclick={enter} />
      {:else}
        <AgalLoader progress={progress} ta={config.ui.loading_ta} en={config.ui.loading_en} />
      {/if}
    </div>
  {/if}
</section>

<style>
  .entrance {
    position: fixed;
    inset: 0;
    z-index: 50;
    background: var(--tok-night);
    transition: opacity 0.9s ease;
  }
  .entrance.leaving { opacity: 0; pointer-events: none; }
  .poster, .doors {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .doors { opacity: 0; }
  .doors.visible { opacity: 1; }
  .bloom {
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 50% 48%, rgb(255 226 150 / 0.95), rgb(255 170 60 / 0.55) 35%, rgb(120 40 10 / 0) 75%);
    opacity: 0;
    transition: opacity 0.8s ease-in;
    mix-blend-mode: screen;
  }
  .bloom.on { opacity: 1; }
  .center {
    position: absolute;
    inset: auto 0 max(8vh, 40px) 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.4rem;
    padding: 0 16px;
    text-align: center;
  }
  .title {
    margin: 0;
    display: flex;
    flex-direction: column;
    text-shadow: 0 2px 12px rgb(0 0 0 / 0.85);
  }
  .title .ta { font-family: var(--font-ta); font-weight: 600; font-size: clamp(1.5rem, 4.6vw, 2.6rem); color: #f6dfa0; }
  .title .en { font-family: var(--font-en); font-weight: 600; font-size: clamp(1.1rem, 3vw, 1.7rem); color: var(--tok-sandal); letter-spacing: 0.08em; }
</style>
