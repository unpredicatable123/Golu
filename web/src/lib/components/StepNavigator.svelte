<script lang="ts">
  // Nine small diyas (bottom → top = steps 1 → 9); the active one glows; click jumps with a smooth scroll (SPEC §5.2).
  import { config } from '$lib/config';
  import { frames } from '$lib/frames';
  import { stepStartProgress, totalScrollPx } from '$lib/engine/scrollMap';
  import { activeStep, reducedMotion, ritual } from '$lib/stores';

  let { onjump }: { onjump?: (step: number) => void } = $props();

  async function jump(id: number) {
    if ($ritual) return;
    if (onjump) {
      onjump(id);
      return;
    }
    const s = frames.steps[id - 1];
    const p = stepStartProgress(s.globalStart, s.hold[1], frames.totalFrames);
    const total = totalScrollPx(frames.totalFrames, window.innerHeight) - window.innerHeight;
    const y = p * total;
    if ($reducedMotion) {
      window.scrollTo(0, y);
      return;
    }
    const { gsap } = await import('gsap');
    const { ScrollToPlugin } = await import('gsap/ScrollToPlugin');
    gsap.registerPlugin(ScrollToPlugin);
    gsap.to(window, { scrollTo: y, duration: 1.2, ease: 'power2.inOut' });
  }
</script>

<nav class="nav" aria-label={`${config.ui.navigator_ta} — ${config.ui.navigator_en}`}>
  {#each [...config.steps].reverse() as s (s.id)}
    <button
      type="button"
      class="diya"
      class:active={$activeStep === s.id}
      class:still={$reducedMotion}
      aria-current={$activeStep === s.id ? 'step' : undefined}
      aria-label={`${config.ui.step_label_ta} ${s.id}: ${s.title_ta} — ${config.ui.step_label_en} ${s.id}: ${s.title_en}`}
      title={`${s.title_ta} · ${s.title_en}`}
      onclick={() => jump(s.id)}
    >
      <svg viewBox="0 0 40 30" width="34" height="26" aria-hidden="true">
        <path class="flame" d="M20 2 C17 7 16.5 10 18.2 12.6 C19 13.6 21 13.6 21.8 12.6 C23.5 10 23 7 20 2 Z" />
        <path class="clay" d="M5 17 C9 26 31 26 35 17 C31 19.5 9 19.5 5 17 Z" />
        <ellipse cx="20" cy="17" rx="15" ry="2.2" class="rim" />
      </svg>
      <span class="num" aria-hidden="true">{s.id}</span>
    </button>
  {/each}
</nav>

<style>
  .nav {
    position: fixed;
    left: max(10px, 1.2vw);
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    flex-direction: column;
    gap: 2px;
    z-index: 6;
  }
  .diya {
    position: relative;
    border: 0;
    background: transparent;
    padding: 2px 4px;
    cursor: pointer;
    opacity: 0.62;
    transition: opacity 0.3s ease, filter 0.3s ease;
  }
  .diya:hover { opacity: 0.9; }
  .flame { fill: #ffb347; opacity: 0.35; transform-origin: 20px 13px; }
  .clay { fill: #9a4b22; }
  .rim { fill: #d9a441; opacity: 0.7; }
  .num {
    position: absolute;
    right: -6px;
    bottom: 0;
    font-size: 0.62rem;
    color: var(--tok-sandal);
    opacity: 0.6;
  }
  .active { opacity: 1; filter: drop-shadow(0 0 8px rgb(255 180 70 / 0.85)); }
  .active .flame { opacity: 1; fill: #ffd27a; animation: flick 1.1s ease-in-out infinite alternate; }
  .still.active .flame { animation: none; }
  @keyframes flick {
    from { transform: scale(0.94, 1.05); }
    to { transform: scale(1.04, 0.95); }
  }
  @media (max-width: 767px) {
    .nav { top: auto; bottom: 86px; transform: none; gap: 0; }
    .diya svg { width: 26px; height: 20px; }
  }
</style>
