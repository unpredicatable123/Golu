<script lang="ts">
  // Three fixed brass ritual buttons: bottom bar on mobile, right side on desktop (SPEC §5.3).
  import { config } from '$lib/config';
  import BrassButton from '$lib/components/BrassButton.svelte';
  import { ritual, type RitualKind } from '$lib/stores';

  let { onstart }: { onstart: (kind: RitualKind) => void } = $props();
  const items: Array<{ kind: RitualKind; ta: string; en: string }> = [
    { kind: 'aarthi', ta: config.rituals.aarthi.label_ta, en: config.rituals.aarthi.label_en },
    { kind: 'camphor', ta: config.rituals.camphor.label_ta, en: config.rituals.camphor.label_en },
    { kind: 'prasadam', ta: config.rituals.prasadam.label_ta, en: config.rituals.prasadam.label_en },
  ];
</script>

<div class="bar" role="toolbar" aria-label="Rituals">
  {#each items as it (it.kind)}
    <BrassButton size="sm" ta={it.ta} en={it.en} disabled={$ritual !== null} onclick={() => onstart(it.kind)} />
  {/each}
</div>

<style>
  .bar {
    position: fixed;
    right: max(12px, 1.6vw);
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
    z-index: 7;
  }
  @media (max-width: 767px) {
    .bar {
      top: auto;
      right: 0;
      left: 0;
      bottom: 0;
      transform: none;
      flex-direction: row;
      justify-content: space-around;
      gap: 0.3rem;
      padding: 0.5rem 8px max(0.5rem, env(safe-area-inset-bottom));
      background: linear-gradient(0deg, rgb(26 11 6 / 0.92), rgb(26 11 6 / 0.55) 70%, transparent);
    }
  }
</style>
