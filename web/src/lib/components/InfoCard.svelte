<script lang="ts">
  // Small brass info card: name_ta / name_en and info (SPEC §5.2). Esc or outside click closes; focus is kept inside.
  import { onMount } from 'svelte';
  import { config, type Doll } from '$lib/config';

  let { doll, x, y, onclose }: { doll: Doll; x: number; y: number; onclose: () => void } = $props();
  let card: HTMLDivElement;
  let closeBtn: HTMLButtonElement;
  let pos = $state({ left: 0, top: 0 });

  function place() {
    const w = card?.offsetWidth ?? 300;
    const h = card?.offsetHeight ?? 160;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let left = x + 22;
    if (left + w > vw - 16) left = x - w - 22;
    left = Math.max(16, Math.min(vw - w - 16, left));
    let top = y - h / 2;
    top = Math.max(16, Math.min(vh - h - 16, top));
    pos = { left, top };
  }

  $effect(() => {
    void x;
    void y;
    place();
  });

  onMount(() => {
    place();
    closeBtn?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onclose();
      if (e.key === 'Tab') {
        e.preventDefault();
        closeBtn?.focus();
      }
    };
    const click = (e: MouseEvent) => {
      if (card && !card.contains(e.target as Node) && !(e.target as HTMLElement).closest('.spot')) onclose();
    };
    window.addEventListener('keydown', key);
    window.addEventListener('pointerdown', click);
    return () => {
      window.removeEventListener('keydown', key);
      window.removeEventListener('pointerdown', click);
    };
  });
</script>

<div
  bind:this={card}
  class="brass-panel info"
  role="dialog"
  aria-modal="false"
  aria-labelledby="info-title"
  style:left="{pos.left}px"
  style:top="{pos.top}px"
>
  <div class="brass-inner inner">
    <h4 id="info-title"><span class="ta" lang="ta">{doll.name_ta}</span><span class="en" lang="en">{doll.name_en}</span></h4>
    <p class="ta" lang="ta">{doll.info_ta}</p>
    <p class="en" lang="en">{doll.info_en}</p>
    <button bind:this={closeBtn} type="button" class="close" onclick={onclose} aria-label={`${config.ui.close_ta} — ${config.ui.close_en}`}>✕</button>
  </div>
</div>

<style>
  .info {
    position: fixed;
    width: min(320px, calc(100vw - 32px));
    z-index: 30;
  }
  .inner {
    position: relative;
    padding: 0.85rem 2.4rem 0.9rem 1rem;
  }
  h4 {
    margin: 0 0 0.35rem;
    display: flex;
    flex-direction: column;
    color: #f6dfa0;
  }
  h4 .ta { font-family: var(--font-ta); font-size: 1.05rem; font-weight: 600; }
  h4 .en { font-family: var(--font-en); font-size: 1rem; font-weight: 600; color: var(--tok-sandal); }
  p { margin: 0.25rem 0 0; font-size: 0.88rem; line-height: 1.5; }
  p.ta { font-family: var(--font-ta); font-size: 0.84rem; }
  p.en { font-family: var(--font-en); font-style: italic; }
  .close {
    position: absolute;
    top: 0.45rem;
    right: 0.5rem;
    width: 1.8rem;
    height: 1.8rem;
    border-radius: 50%;
    border: 1px solid var(--tok-brass);
    background: color-mix(in srgb, var(--tok-maroon) 80%, black);
    color: var(--tok-sandal);
    cursor: pointer;
  }
  /* short landscape screens: a smaller card that leaves the dolls visible */
  @media (max-height: 520px) {
    .info { width: min(270px, calc(100vw - 32px)); }
    .inner { padding: 0.55rem 2.1rem 0.6rem 0.75rem; }
    h4 .ta { font-size: 0.92rem; }
    h4 .en { font-size: 0.86rem; }
    p { font-size: 0.76rem; line-height: 1.4; }
    p.ta { font-size: 0.74rem; }
  }
</style>
