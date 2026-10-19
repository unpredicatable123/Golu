#!/usr/bin/env node
// Writes web/src/lib/frames.json from renders/manifest.json + the encoded WebP folders (SPEC §4.8, D27, D38).
// node scripts/build_frames_json.mjs --manifest renders/manifest.json --static web/static --out web/src/lib/frames.json
import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 2) out[argv[i].replace(/^--/, '')] = argv[i + 1];
  for (const k of ['manifest', 'static', 'out']) if (!out[k]) throw new Error(`missing --${k}`);
  return out;
}

export function countFrames(dir) {
  if (!existsSync(dir)) return 0;
  return readdirSync(dir).filter((f) => /^f_\d{4}\.webp$/.test(f)).length;
}

export function stepBytes(dir) {
  if (!existsSync(dir)) return 0;
  return readdirSync(dir)
    .filter((f) => f.endsWith('.webp'))
    .reduce((n, f) => n + statSync(join(dir, f)).size, 0);
}

export function listAudio(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((f) => /\.(webm|mp3|ogg|m4a)$/.test(f)).sort();
}

export function buildFramesJson(manifest, counts, bytes, version, audio = []) {
  const steps = manifest.steps.map((s) => {
    const c = counts[s.id];
    if (c.desktop !== s.count || c.mobile !== s.count) {
      throw new Error(`step ${s.id}: manifest has ${s.count} frames, desktop ${c.desktop}, mobile ${c.mobile}`);
    }
    return {
      id: s.id,
      dir: s.dir,
      count: s.count,
      globalStart: s.global_start,
      hold: s.hold,
      transition: s.transition,
      finale: s.finale,
      keyFrame: s.key_frame,
      sampleFrames: s.sample_frames,
      bytes: bytes[s.id],
      hotspots: s.hotspots,
      flames: s.flames,
    };
  });
  let expect = 0;
  for (const s of steps) {
    if (s.globalStart !== expect) throw new Error(`step ${s.id}: globalStart ${s.globalStart} != ${expect}`);
    expect += s.count;
  }
  if (expect !== manifest.total) throw new Error(`frame total ${expect} != manifest total ${manifest.total}`);
  return {
    version,
    fps: manifest.fps,
    totalFrames: manifest.total,
    desktop: { width: 1920, height: 1080, dir: 'frames' },
    mobile: { width: 960, height: 540, dir: 'frames-mobile' },
    doors: { count: manifest.doors.count },
    audio,
    steps,
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const raw = readFileSync(args.manifest, 'utf8');
  const manifest = JSON.parse(raw);
  const counts = {};
  const bytes = {};
  for (const s of manifest.steps) {
    const d = join(args.static, 'frames', s.dir);
    const m = join(args.static, 'frames-mobile', s.dir);
    counts[s.id] = { desktop: countFrames(d), mobile: countFrames(m) };
    bytes[s.id] = { desktop: stepBytes(d), mobile: stepBytes(m) };
  }
  // audio files actually present, so the app requests only those and synthesises the rest (no 404s)
  const audio = listAudio(join(args.static, 'audio'));
  // the version busts caches whenever the scene *or* the encoded frames change (re-encode at a new quality)
  const version = createHash('sha1').update(raw).update(JSON.stringify(bytes)).update(JSON.stringify(audio)).digest('hex').slice(0, 10);
  const json = buildFramesJson(manifest, counts, bytes, version, audio);
  mkdirSync(dirname(args.out), { recursive: true });
  writeFileSync(args.out, JSON.stringify(json));
  const mb = (k) => (Object.values(bytes).reduce((n, b) => n + b[k], 0) / 1e6).toFixed(1);
  console.log(`frames.json: ${json.totalFrames} frames, ${json.steps.length} steps, version ${version}, ` +
    `desktop ${mb('desktop')} MB, mobile ${mb('mobile')} MB`);
}

if (import.meta.url === `file://${process.argv[1].replace(/\\/g, '/')}` || process.argv[1]?.endsWith('build_frames_json.mjs')) {
  try {
    main();
  } catch (e) {
    console.error(`build_frames_json: ${e.message}`);
    process.exit(1);
  }
}
