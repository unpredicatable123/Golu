// Typed view of content/golu.config.json — the single source for every string, colour and timing (SPEC §3).
import raw from '$content/golu.config.json';

export interface Position { slot: number; x: number; row: 'front' | 'back'; turn: number }
export interface Doll {
  id: string;
  name_en: string;
  name_ta: string;
  archetype: string;
  info_en: string;
  info_ta: string;
  position: Position;
}
export interface Step {
  id: number;
  title_en: string;
  title_ta: string;
  story_en: string;
  story_ta: string;
  alt_en: string;
  alt_ta: string;
  cloth_color: string;
  dolls: Doll[];
}
export interface Motion {
  circles_clockwise: number;
  circles_anticlockwise: number;
  seconds_per_circle: number;
  reversal_ease_fraction: number;
  rise_seconds: number;
  lower_seconds: number;
  ellipse_rx_vw: number;
  ellipse_ry_vh: number;
  ellipse_rx_vw_portrait: number;
  ellipse_ry_vh_portrait: number;
  start_angle_deg: number;
}
export interface PlateRitual {
  label_en: string;
  label_ta: string;
  sprite: string;
  /** flame base (the wick, or the camphor block's top) in the sprite, as fractions of its width/height */
  flame_anchor: [number, number];
  flame: 'ghee' | 'camphor';
  motion: Motion;
  bell: { strikes_per_circle: number; volume: number };
  glow: { color: string; radius_vmin: number; intensity: number };
  extinguish_seconds?: number;
}
export interface Dish {
  id: string;
  name_en: string;
  name_ta: string;
  desc_en: string;
  desc_ta: string;
  sprite: string;
  bowl: 'brass' | 'silver';
}
export interface AudioCue { file: string; volume: number; [k: string]: unknown }
export interface GoluConfig {
  meta: { title_en: string; title_ta: string; description_en: string; description_ta: string; fps: number };
  layout: { camera: { hold_frames: number; transition_frames: number; finale_frames: number; door_frames: number } };
  palette: { tokens: Record<string, string> };
  ui: Record<string, string>;
  steps: Step[];
  rituals: {
    aarthi: PlateRitual;
    camphor: PlateRitual;
    prasadam: {
      label_en: string;
      label_ta: string;
      take_en: string;
      take_ta: string;
      blessing_ta: string;
      blessing_en: string;
      tray_sprite: string;
      composite_sprite: string;
      /** centres of the trio's bowls in the composite sprite (fractions), left to right */
      composite_bowls: [number, number][];
      petal_sprites: string[];
      auto_close_seconds: number;
    };
  };
  prasadam: { dishes: Dish[]; fixed: string[]; third_dish: string; third_dish_options: string[] };
  audio: {
    om_loop: AudioCue & { ducked_volume: number; fade_in_seconds: number };
    bell_large: AudioCue;
    bell_small: AudioCue & { ambient_volume: number; ambient_min_seconds: number; ambient_max_seconds: number };
    nadaswaram_short: AudioCue & { steps: number[] };
    formats: string[];
    fallback: { om_fundamental_hz: number; om_swell_seconds: number };
  };
}

export const config = raw as unknown as GoluConfig;

/** The three prasadam bowls: the two fixed dishes plus the configurable third (SPEC §3). */
export function prasadamTrio(cfg: GoluConfig = config): [Dish, Dish, Dish] {
  const byId = new Map(cfg.prasadam.dishes.map((d) => [d.id, d]));
  const third = cfg.prasadam.third_dish_options.includes(cfg.prasadam.third_dish)
    ? cfg.prasadam.third_dish
    : cfg.prasadam.third_dish_options[0];
  const ids = [...cfg.prasadam.fixed, third];
  const dishes = ids.map((id) => {
    const d = byId.get(id);
    if (!d) throw new Error(`prasadam dish ${id} missing from config`);
    return d;
  });
  return [dishes[0], dishes[1], dishes[2]];
}

export function dollById(id: string, cfg: GoluConfig = config): Doll | undefined {
  for (const s of cfg.steps) for (const d of s.dolls) if (d.id === id) return d;
  return undefined;
}

/** CSS custom properties for the design tokens (rendered into <head> at prerender time). */
export function tokenCss(cfg: GoluConfig = config): string {
  return `:root{${Object.entries(cfg.palette.tokens)
    .map(([k, v]) => `--tok-${k}:${v}`)
    .join(';')}}`;
}
