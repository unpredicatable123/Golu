<script lang="ts">
  // Brass-plaque button (SPEC §5: no flat modern buttons). Bilingual label: Tamil above, English below.
  import type { Snippet } from 'svelte';

  let {
    ta,
    en,
    onclick,
    disabled = false,
    size = 'md',
    pressed,
    label,
    children,
  }: {
    ta?: string;
    en?: string;
    onclick?: (e: MouseEvent) => void;
    disabled?: boolean;
    size?: 'sm' | 'md' | 'lg';
    pressed?: boolean;
    label?: string;
    children?: Snippet;
  } = $props();
</script>

<button
  type="button"
  class="brass-btn {size}"
  {disabled}
  aria-disabled={disabled}
  aria-pressed={pressed}
  aria-label={label ?? (ta && en ? `${ta} — ${en}` : undefined)}
  {onclick}
>
  <span class="face kolam-dots">
    {#if children}{@render children()}{/if}
    {#if ta}<span class="ta" lang="ta">{ta}</span>{/if}
    {#if en}<span class="en" lang="en">{en}</span>{/if}
  </span>
</button>

<style>
  .brass-btn {
    border: 0;
    padding: 2px;
    border-radius: 999px;
    cursor: pointer;
    background: linear-gradient(135deg, #f6e3a6 0%, var(--tok-brass) 30%, #6e4a17 55%, var(--tok-temple-gold) 80%, #f0d48a 100%);
    box-shadow: 0 6px 18px rgb(0 0 0 / 0.55), inset 0 1px 0 rgb(255 240 200 / 0.5);
    transition: transform 0.15s ease, filter 0.2s ease;
    color: var(--tok-sandal);
  }
  .brass-btn:hover:not(:disabled) {
    filter: brightness(1.12);
    transform: translateY(-1px);
  }
  .brass-btn:active:not(:disabled) {
    transform: translateY(1px);
  }
  .brass-btn:disabled {
    cursor: default;
    filter: grayscale(0.4) brightness(0.7);
  }
  .face {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1px;
    border-radius: 999px;
    padding: 0.55em 1.25em;
    background-color: color-mix(in srgb, var(--tok-maroon) 88%, black);
    box-shadow: inset 0 0 0 1px rgb(255 220 150 / 0.22), inset 0 2px 6px rgb(0 0 0 / 0.6);
    text-shadow: 0 1px 0 rgb(0 0 0 / 0.7);
    line-height: 1.15;
  }
  .ta {
    font-family: var(--font-ta);
    font-weight: 600;
  }
  .en {
    font-family: var(--font-en);
    font-weight: 600;
    letter-spacing: 0.06em;
    font-size: 0.82em;
    opacity: 0.9;
  }
  .sm { font-size: 0.82rem; }
  .md { font-size: 0.95rem; }
  .lg { font-size: clamp(1.05rem, 2.6vw, 1.35rem); }
  .lg .face { padding: 0.8em 2em; }
</style>
