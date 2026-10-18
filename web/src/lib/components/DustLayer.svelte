<script lang="ts">
  // Subtle dust motes drifting in a warm light cone (SPEC §5.2 ambient). Off in reduced motion; paused when hidden.
  import { onMount } from 'svelte';

  let canvas: HTMLCanvasElement;

  onMount(() => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let raf = 0;
    let last = performance.now();
    const mobile = window.innerWidth < 768;
    const n = mobile ? 25 : 60;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const motes = Array.from({ length: n }, () => ({
      x: Math.random(), y: Math.random(), r: 0.6 + Math.random() * 1.6, vx: (Math.random() - 0.5) * 0.004,
      vy: -0.002 - Math.random() * 0.004, ph: Math.random() * 6.28, a: 0.15 + Math.random() * 0.35,
    }));
    const resize = () => {
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
    };
    resize();
    window.addEventListener('resize', resize);
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      if (document.hidden) return;
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter';
      for (const m of motes) {
        m.ph += dt * 0.6;
        m.x += (m.vx + Math.sin(m.ph) * 0.002) * dt;
        m.y += m.vy * dt;
        if (m.y < -0.02) { m.y = 1.02; m.x = Math.random(); }
        if (m.x < -0.02) m.x = 1.02;
        if (m.x > 1.02) m.x = -0.02;
        // brighter inside the key-light cone (upper left → centre)
        const cone = Math.max(0, 1 - Math.abs(m.x - (0.25 + m.y * 0.35)) * 2.2);
        const a = m.a * (0.3 + 0.7 * cone) * (0.7 + 0.3 * Math.sin(m.ph * 2));
        ctx.fillStyle = `rgba(255,214,150,${a})`;
        ctx.beginPath();
        ctx.arc(m.x * W, m.y * H, m.r * dpr, 0, Math.PI * 2);
        ctx.fill();
      }
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  });
</script>

<canvas bind:this={canvas} class="dust" aria-hidden="true"></canvas>

<style>
  .dust {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 2;
    mix-blend-mode: screen;
    opacity: 0.8;
  }
</style>
