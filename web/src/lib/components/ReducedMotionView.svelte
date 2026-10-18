<script lang="ts">
  // prefers-reduced-motion (SPEC §5.5): one key frame per step, crossfaded as the reader scrolls between steps.
  import { onMount } from 'svelte';
  import { config } from '$lib/config';
  import { frameUrl, frames } from '$lib/frames';
  import { coverFit } from '$lib/engine/coverFit';
  import { view } from '$lib/engine/view';
  import { activeStep, globalFrame } from '$lib/stores';

  let mobile = $state(false);
  let current = $state(1);
  let sections: HTMLElement[] = [];

  onMount(() => {
    mobile = window.innerWidth < 768;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting && e.intersectionRatio > 0.5) {
            const id = Number((e.target as HTMLElement).dataset.step);
            current = id;
            activeStep.set(id);
            const s = frames.steps[id - 1];
            globalFrame.set(s.globalStart + s.keyFrame);
            const W = window.innerWidth;
            const H = window.innerHeight;
            const src = mobile ? frames.mobile : frames.desktop;
            const r = coverFit(src.width, src.height, W, H);
            view.set({ rect: { ...r, dw: W, dh: H }, srcW: src.width, srcH: src.height, width: W, height: H, step: id, local: s.keyFrame });
          }
        }
      },
      { threshold: [0.5, 0.75] }
    );
    sections.forEach((s) => s && io.observe(s));
    return () => io.disconnect();
  });
</script>

<div class="stage" aria-hidden="true">
  {#each frames.steps as s (s.id)}
    <img
      class="key"
      class:on={current === s.id}
      src={frameUrl(s.id, s.keyFrame, mobile ? 'mobile' : 'desktop')}
      alt=""
      loading={s.id <= 2 ? 'eager' : 'lazy'}
    />
  {/each}
</div>
{#each config.steps as s, i (s.id)}
  <section class="step-snap" data-step={s.id} bind:this={sections[i]} aria-label={`${s.title_ta} — ${s.title_en}`}>
    <span class="sr-only">{s.alt_ta} — {s.alt_en}</span>
  </section>
{/each}

<style>
  .stage { position: fixed; inset: 0; z-index: 0; background: var(--tok-night); }
  .key { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.6s ease !important; }
  .key.on { opacity: 1; }
  .step-snap { position: relative; height: 100vh; }
</style>
