<script lang="ts">
  // Live flicker glows over the rendered lamp flames so the Golu stays alive when scrolling stops (DECISIONS D39).
  import { onMount } from 'svelte';
  import { frames } from '$lib/frames';
  import { frameToViewport } from '$lib/engine/coverFit';
  import { flamesAt } from '$lib/engine/hotspots';
  import { view } from '$lib/engine/view';
  import { makeNoise } from '$lib/rituals/flame';

  let canvas: HTMLCanvasElement;

  onMount(() => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const noise = makeNoise(17);
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let raf = 0;
    const resize = () => {
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
    };
    resize();
    window.addEventListener('resize', resize);
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      if (document.hidden) return;
      const v = $view;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!v) return;
      const pts = flamesAt(frames, v.step, v.local);
      const t = now / 1000;
      ctx.globalCompositeOperation = 'lighter';
      pts.forEach(([fx, fy], i) => {
        const [x, y] = frameToViewport(fx, fy, v.rect, v.srcW, v.srcH);
        const k = 0.55 + 0.45 * noise(t * 5 + i * 13.1);
        const r = (14 + 10 * k) * dpr * (v.width / 1280);
        const g = ctx.createRadialGradient(x * dpr, y * dpr, 0, x * dpr, y * dpr, r);
        g.addColorStop(0, `rgba(255,200,110,${0.35 * k})`);
        g.addColorStop(1, 'rgba(255,140,40,0)');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(x * dpr, y * dpr, r, 0, Math.PI * 2);
        ctx.fill();
      });
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  });
</script>

<canvas bind:this={canvas} class="flicker" aria-hidden="true"></canvas>

<style>
  .flicker {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 1;
    mix-blend-mode: screen;
  }
</style>
