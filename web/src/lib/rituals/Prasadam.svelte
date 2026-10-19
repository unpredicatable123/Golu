<script lang="ts">
  // Prasadam (SPEC §5.3, DECISIONS D41): banana-leaf tray slides up with three bowls (third dish from config) and steam;
  // "Take" lifts and lights the bowls, showers petals and announces the blessing; closes after 6 s or on Close/Esc.
  import { onMount } from 'svelte';
  import { config, prasadamTrio } from '$lib/config';
  import { frames } from '$lib/frames';
  import { reducedMotion } from '$lib/stores';
  import BrassButton from '$lib/components/BrassButton.svelte';
  import { PetalShower, Steam } from './particles';

  let { ondone }: { ondone: () => void } = $props();
  const P = config.rituals.prasadam;
  const trio = prasadamTrio();
  const v = frames.version;

  let fx: HTMLCanvasElement;
  let trayImg: HTMLImageElement;
  // the composite sprite is square with the tray in its middle band: the frame shows rows CROP_TOP … CROP_TOP+CROP_H
  const CROP_TOP = 0.3;
  const CROP_H = 0.5625;
  let shown = $state(false);
  let taken = $state(false);
  let blessing = $state('');
  let takeBtn: HTMLDivElement;
  let closing = $state(false);

  function close() {
    if (closing) return;
    closing = true;
    shown = false;
    setTimeout(ondone, $reducedMotion ? 150 : 700);
  }

  function take() {
    if (taken) return;
    taken = true;
    blessing = `${P.blessing_ta} — ${P.blessing_en}`;
    if (!$reducedMotion) startPetals();
    setTimeout(close, P.auto_close_seconds * 1000);
  }

  let petals: PetalShower | null = null;
  function startPetals() {
    petals?.start(window.innerWidth, window.innerWidth < 768 ? 60 : 120);
  }

  onMount(() => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    fx.width = window.innerWidth * dpr;
    fx.height = window.innerHeight * dpr;
    const ctx = fx.getContext('2d') as CanvasRenderingContext2D;
    ctx.scale(dpr, dpr);
    const sprites = P.petal_sprites.map((name) => {
      const img = new Image();
      img.src = `/props/${name}.webp?v=${v}`;
      return img;
    });
    petals = new PetalShower(ctx, sprites);
    // steam rises from each bowl as rendered in the composite tray (measured centres, mapped through the crop)
    const steam = new Steam(ctx, () => {
      if (!trayImg) return [];
      const r = trayImg.getBoundingClientRect();
      return P.composite_bowls.map(([u, v]) => [r.left + u * r.width, r.top + ((v - CROP_TOP) / CROP_H - 0.03) * r.height] as [number, number]);
    });
    requestAnimationFrame(() => (shown = true));
    setTimeout(() => takeBtn?.querySelector('button')?.focus(), 900);
    let last = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      if (!$reducedMotion && shown) {
        steam.step(dt);
        steam.draw();
      }
      if (petals?.active) {
        petals.step(dt, window.innerHeight);
        petals.draw();
      }
    };
    raf = requestAnimationFrame(tick);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('keydown', onKey);
    };
  });
</script>

<div class="prasadam" class:shown class:still={$reducedMotion} role="dialog" aria-modal="true" aria-label={`${P.label_ta} — ${P.label_en}`}>
  <div class="tray">
    <!-- the whole tray rendered in 3D (leaf, brass plate and the configured trio in their bowls), so every bowl sits
         on the leaf; the dish names follow in the same left-to-right order -->
    <div class="tray-frame" class:lift={taken}>
      <img class="tray-img" bind:this={trayImg} src={`/props/${P.composite_sprite}.webp?v=${v}`}
           alt={trio.map((d) => `${d.name_ta} — ${d.name_en}`).join(', ')} />
    </div>
    <ul class="names">
      {#each trio as d (d.id)}
        <li><span class="ta" lang="ta">{d.name_ta}</span><span class="en" lang="en">{d.name_en}</span></li>
      {/each}
    </ul>
    <div class="actions">
      <div bind:this={takeBtn}>
        <BrassButton size="md" ta={P.take_ta} en={P.take_en} disabled={taken} onclick={take} />
      </div>
      <button type="button" class="close" onclick={close} aria-label={`${config.ui.close_ta} — ${config.ui.close_en}`}>✕</button>
    </div>
  </div>
  <canvas bind:this={fx} class="fx" aria-hidden="true"></canvas>
  <p class="blessing" class:on={!!blessing} aria-live="assertive">
    {#if blessing}<span class="ta" lang="ta">{P.blessing_ta}</span><span class="en" lang="en">{P.blessing_en}</span>{/if}
  </p>
</div>

<style>
  .prasadam { position: fixed; inset: 0; z-index: 25; pointer-events: none; }
  .prasadam > * { pointer-events: auto; }
  .fx { position: absolute; inset: 0; width: 100vw; height: 100vh; pointer-events: none; }
  .tray {
    position: absolute;
    left: 50%;
    bottom: max(4vh, 24px);
    width: min(760px, calc(100vw - 32px));
    transform: translate(-50%, 115%);
    transition: transform 0.9s cubic-bezier(0.2, 0.9, 0.25, 1);
  }
  .shown .tray { transform: translate(-50%, 0); }
  .still .tray { transition: opacity 0.4s ease; transform: translate(-50%, 0); opacity: 0; }
  .still.shown .tray { opacity: 1; }
  .tray-frame {
    position: relative;
    width: 100%;
    aspect-ratio: 1024 / 576;               /* CROP_H of the square sprite */
    transition: transform 0.7s ease, filter 0.7s ease;
    filter: drop-shadow(0 14px 22px rgb(0 0 0 / 0.6));
  }
  .tray-img { width: 100%; height: 100%; display: block; object-fit: cover; object-position: 50% 68.6%; /* CROP_TOP */ }
  .tray-frame.lift { transform: translateY(-10px); filter: drop-shadow(0 0 22px rgb(255 200 110 / 0.8)) brightness(1.08); }
  .still .tray-frame.lift { transform: none; }
  .names {
    list-style: none; margin: 0.3rem 0 0; padding: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem;
    text-align: center; line-height: 1.25; text-shadow: 0 1px 4px rgb(0 0 0 / 0.9);
  }
  .names li { display: flex; flex-direction: column; }
  .names .ta { font-family: var(--font-ta); font-size: clamp(0.78rem, 2vw, 1rem); color: #f6dfa0; font-weight: 600; }
  .names .en { font-family: var(--font-en); font-size: clamp(0.76rem, 1.9vw, 0.95rem); color: var(--tok-sandal); }
  .actions { position: relative; display: flex; justify-content: center; align-items: center; gap: 0.8rem; margin-top: 0.6rem; padding-bottom: 2%; }
  .close {
    width: 2.2rem; height: 2.2rem; border-radius: 50%; border: 1px solid var(--tok-brass);
    background: color-mix(in srgb, var(--tok-maroon) 80%, black); color: var(--tok-sandal); cursor: pointer;
  }
  .blessing {
    position: absolute; left: 50%; top: 18vh; transform: translateX(-50%); width: min(680px, calc(100vw - 32px));
    margin: 0; text-align: center; display: flex; flex-direction: column; gap: 0.3rem; opacity: 0;
    transition: opacity 1.2s ease; text-shadow: 0 2px 14px rgb(0 0 0 / 0.95); pointer-events: none;
  }
  .blessing.on { opacity: 1; }
  .blessing .ta { font-family: var(--font-ta); font-weight: 600; font-size: clamp(1.15rem, 3.6vw, 2rem); color: #ffe6a8; }
  .blessing .en { font-family: var(--font-en); font-style: italic; font-size: clamp(1.05rem, 3vw, 1.6rem); color: var(--tok-sandal); }
</style>
