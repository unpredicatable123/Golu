<script lang="ts">
  // Doll hotspots following the projected head points from the manifest (SPEC §5.2, DECISIONS D38).
  import { dollById } from '$lib/config';
  import { frames } from '$lib/frames';
  import { frameToViewport } from '$lib/engine/coverFit';
  import { hotspotsAt } from '$lib/engine/hotspots';
  import { view } from '$lib/engine/view';
  import { openDoll, reducedMotion, ritual } from '$lib/stores';
  import InfoCard from './InfoCard.svelte';

  let { keyFrameMode = false }: { keyFrameMode?: boolean } = $props();

  const spots = $derived.by(() => {
    const v = $view;
    if (!v || $ritual) return [];
    const s = frames.steps[v.step - 1];
    const local = keyFrameMode ? s.keyFrame : v.local;
    return hotspotsAt(frames, v.step, local)
      .filter((h) => h.vis)
      .map((h) => {
        const [x, y] = frameToViewport(h.x, h.y, v.rect, v.srcW, v.srcH);
        const doll = dollById(h.id);
        return { ...h, px: x, py: y, doll };
      })
      .filter((h) => h.doll && h.px > 8 && h.px < v.width - 8 && h.py > 8 && h.py < v.height - 8);
  });
  const open = $derived(spots.find((s) => s.id === $openDoll) ?? null);
</script>

<div class="hotspots" aria-label="Golu dolls">
  {#each spots as s (s.id)}
    <button
      type="button"
      class="spot"
      class:still={$reducedMotion}
      class:active={$openDoll === s.id}
      style:left="{s.px}px"
      style:top="{s.py}px"
      aria-label={`${s.doll?.name_ta} — ${s.doll?.name_en}`}
      aria-expanded={$openDoll === s.id}
      onclick={() => openDoll.set($openDoll === s.id ? null : s.id)}
    ><span class="ring"></span></button>
  {/each}
</div>
{#if open && open.doll}
  <InfoCard doll={open.doll} x={open.px} y={open.py} onclose={() => openDoll.set(null)} />
{/if}

<style>
  .hotspots {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 4;
  }
  .spot {
    position: absolute;
    width: 30px;
    height: 30px;
    margin: -15px 0 0 -15px;
    padding: 0;
    border: 0;
    background: transparent;
    pointer-events: auto;
    cursor: pointer;
  }
  .ring {
    position: absolute;
    inset: 6px;
    border-radius: 50%;
    border: 2px solid var(--tok-temple-gold);
    background: radial-gradient(circle, rgb(255 210 120 / 0.55) 0 30%, rgb(255 180 60 / 0.12) 55%, transparent 70%);
    box-shadow: 0 0 10px rgb(255 190 90 / 0.6);
    animation: pulse 2.4s ease-in-out infinite;
  }
  .still .ring { animation: none; }
  .active .ring { border-color: #fff1c4; }
  @keyframes pulse {
    0%, 100% { transform: scale(0.85); opacity: 0.75; }
    50% { transform: scale(1.1); opacity: 1; }
  }
</style>
