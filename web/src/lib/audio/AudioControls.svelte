<script lang="ts">
  // Global mute + volume (SPEC §5.4); state persists via AudioManager (localStorage, try/catch).
  import { onMount } from 'svelte';
  import { config } from '$lib/config';
  import type { AudioManager } from './audio';

  let { audio }: { audio: AudioManager } = $props();
  let muted = $state(false);
  let volume = $state(1);

  onMount(() => {
    muted = audio.muted;      // persisted state (localStorage) loaded by AudioManager
    volume = audio.volume;
  });

  async function toggle() {
    muted = !muted;
    await audio.setMuted(muted);
  }

  async function onVolume(e: Event) {
    volume = Number((e.target as HTMLInputElement).value);
    await audio.setVolume(volume);
  }
</script>

<div class="audio brass-panel">
  <div class="brass-inner inner">
    <button
      type="button"
      class="mute"
      aria-pressed={muted}
      aria-label={muted ? `${config.ui.unmute_ta} — ${config.ui.unmute_en}` : `${config.ui.mute_ta} — ${config.ui.mute_en}`}
      onclick={toggle}
    >
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
        <path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor" />
        {#if muted}
          <path d="M16 9l5 6M21 9l-5 6" stroke="currentColor" stroke-width="2" fill="none" />
        {:else}
          <path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" stroke="currentColor" stroke-width="1.8" fill="none" />
        {/if}
      </svg>
    </button>
    <label class="sr-only" for="golu-volume">{config.ui.volume_ta} — {config.ui.volume_en}</label>
    <input
      id="golu-volume"
      type="range"
      min="0"
      max="1"
      step="0.05"
      value={volume}
      aria-valuetext={`${Math.round(volume * 100)}%`}
      oninput={onVolume}
    />
  </div>
</div>

<style>
  .audio {
    position: fixed;
    top: max(12px, 2vh);
    right: max(12px, 2vw);
    z-index: 8;
  }
  .inner {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.7rem;
  }
  .mute {
    border: 0;
    background: transparent;
    color: #f6dfa0;
    cursor: pointer;
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
  }
  input[type='range'] {
    width: 90px;
    accent-color: var(--tok-temple-gold);
  }
  @media (max-width: 767px) {
    input[type='range'] { width: 64px; }
  }
</style>
