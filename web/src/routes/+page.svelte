<script lang="ts">
  // Golu Darshan: entrance → scroll frame experience with overlays, navigator, ambience, rituals and audio.
  import { onMount } from 'svelte';
  import { config } from '$lib/config';
  import { AudioManager } from '$lib/audio/audio';
  import AudioControls from '$lib/audio/AudioControls.svelte';
  import { FrameCache, decodeWindowFor } from '$lib/engine/FrameCache';
  import DustLayer from '$lib/components/DustLayer.svelte';
  import Entrance from '$lib/components/Entrance.svelte';
  import FrameScroller from '$lib/components/FrameScroller.svelte';
  import Hotspots from '$lib/components/Hotspots.svelte';
  import LampFlicker from '$lib/components/LampFlicker.svelte';
  import ReducedMotionView from '$lib/components/ReducedMotionView.svelte';
  import StepNavigator from '$lib/components/StepNavigator.svelte';
  import StepTitleCard from '$lib/components/StepTitleCard.svelte';
  import PlateRitual from '$lib/rituals/PlateRitual.svelte';
  import Prasadam from '$lib/rituals/Prasadam.svelte';
  import RitualBar from '$lib/rituals/RitualBar.svelte';
  import { startRitual } from '$lib/rituals/ritualState';
  import { activeStep, entered, reducedMotion, ritual, type RitualKind } from '$lib/stores';

  let cache: FrameCache | null = $state(null);
  let audio: AudioManager | null = $state(null);
  let running: RitualKind | null = $state(null);
  let endRitual: (() => void) | null = null;
  let prevStep = 1;

  onMount(() => {
    const mobile = window.innerWidth < 768;
    const nav = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean; effectiveType?: string } };
    const mem = nav.deviceMemory;
    // phones show 55% of the frame width across ~1000+ device pixels in portrait (D68): the 960 px set would be
    // upscaled about 2x and look soft, so use the full-HD set unless data saver is on or the network is slow
    const lowData = !!nav.connection?.saveData || /(^|-)(2g|3g)$/.test(nav.connection?.effectiveType ?? '');
    const variant = !mobile || (!lowData && window.devicePixelRatio >= 1.5) ? 'desktop' : 'mobile';
    cache = new FrameCache({ variant, decodeWindow: decodeWindowFor(mem, mobile) });
    audio = new AudioManager(config.audio);
    audio.load();
    const w = window as Window;
    w.__golu = w.__golu ?? { stats: () => cache!.stats(), ritualLog: [], audio: () => audio!.state() };
    w.__golu.audio = () => audio!.state();
    const unsub = activeStep.subscribe((s) => {
      if ($entered && audio) audio.nadaswaram(s, prevStep);
      prevStep = s;
    });
    return () => {
      unsub();
      audio?.stopAmbientBells();
      cache?.dispose();
    };
  });

  function onEntered() {
    entered.set(true);
    audio?.startAmbientBells(() => $ritual !== null);
  }

  function begin(kind: RitualKind) {
    const end = startRitual(kind, audio);
    if (!end) return;
    endRitual = end;
    running = kind;
  }

  function done() {
    endRitual?.();
    endRitual = null;
    running = null;
  }
</script>

<a class="skip sr-only" href="#golu-main">{config.ui.navigator_ta} — {config.ui.navigator_en}</a>

{#if !$entered}
  <Entrance {cache} {audio} onentered={onEntered} />
{/if}
<!-- always in the static HTML: the skip link targets it; contents mount in the browser -->
<main id="golu-main" class:hidden={!$entered}>
  {#if cache && audio}
    {#if $reducedMotion}
      <ReducedMotionView />
    {:else}
      <FrameScroller {cache} />
      {#if $entered}
        <!-- full-screen animated overlays: only once the golu is visible (no main-thread work behind the doors) -->
        <LampFlicker />
        <DustLayer />
      {/if}
    {/if}
    {#if $entered}
      <StepTitleCard />
      <Hotspots keyFrameMode={$reducedMotion} />
      <StepNavigator />
      <RitualBar onstart={begin} />
      <AudioControls {audio} />
      {#if running === 'aarthi' || running === 'camphor'}
        <PlateRitual kind={running} {audio} ondone={done} />
      {:else if running === 'prasadam'}
        <Prasadam ondone={done} />
      {/if}
    {/if}
  {/if}
</main>

<style>
  main.hidden { visibility: hidden; }
  .skip:focus {
    position: fixed;
    top: 8px;
    left: 8px;
    width: auto;
    height: auto;
    clip: auto;
    padding: 0.5rem 0.8rem;
    background: var(--tok-maroon);
    color: var(--tok-sandal);
    z-index: 100;
  }
</style>
