<script lang="ts">
  // Bilingual step title + story; fades in at 10% of the step's hold and out at 85% (SPEC §5.2).
  import { config } from '$lib/config';
  import { stepProgress } from '$lib/frames';
  import { globalFrame } from '$lib/stores';

  const RAMP = 0.04;
  const info = $derived(stepProgress($globalFrame));
  const step = $derived(config.steps[info.step - 1]);
  const opacity = $derived.by(() => {
    if (info.phase !== 'hold') return 0;
    const p = info.p;
    if (p < 0.1 || p > 0.85) return 0;
    return Math.min(1, (p - 0.1) / RAMP, (0.85 - p) / RAMP);
  });
</script>

<section class="card-wrap" style:opacity={opacity} aria-hidden={opacity === 0}>
  <div class="brass-panel">
    <div class="brass-inner inner">
      <p class="eyebrow"><span lang="ta">{config.ui.step_label_ta} {step.id}</span> · <span lang="en">{config.ui.step_label_en} {step.id}</span></p>
      <h2 class="title-ta" lang="ta">{step.title_ta}</h2>
      <h3 class="title-en" lang="en">{step.title_en}</h3>
      <p class="story-ta" lang="ta">{step.story_ta}</p>
      <p class="story-en" lang="en">{step.story_en}</p>
    </div>
  </div>
</section>
<p class="sr-only" aria-live="polite">{step.title_ta} — {step.title_en}</p>

<style>
  .card-wrap {
    position: fixed;
    left: max(16px, 3vw);
    top: max(16px, 4vh);
    width: min(440px, calc(100vw - 32px));
    z-index: 5;
    pointer-events: none;
    transition: opacity 0.12s linear;
  }
  .inner {
    padding: 1rem 1.25rem 1.1rem;
  }
  .eyebrow {
    margin: 0 0 0.3rem;
    font-size: 0.78rem;
    letter-spacing: 0.12em;
    color: var(--tok-temple-gold);
    text-transform: uppercase;
  }
  .title-ta {
    margin: 0;
    font-family: var(--font-ta);
    font-weight: 600;
    font-size: clamp(1.25rem, 3.2vw, 1.7rem);
    color: #f6dfa0;
    line-height: 1.35;
  }
  .title-en {
    margin: 0.1rem 0 0.55rem;
    font-family: var(--font-en);
    font-weight: 600;
    font-size: clamp(1.05rem, 2.4vw, 1.3rem);
    color: var(--tok-sandal);
    letter-spacing: 0.03em;
  }
  .story-ta, .story-en {
    margin: 0.2rem 0 0;
    font-size: 0.95rem;
    line-height: 1.5;
    color: color-mix(in srgb, var(--tok-sandal) 92%, white);
  }
  .story-ta { font-family: var(--font-ta); font-size: 0.9rem; }
  .story-en { font-family: var(--font-en); font-style: italic; }
  @media (max-width: 767px) {
    .card-wrap { top: 12px; }
    .story-ta, .story-en { font-size: 0.82rem; }
  }
</style>
