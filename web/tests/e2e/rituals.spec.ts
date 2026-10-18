// Phase 6 acceptance: exactly 3 clockwise + 3 anticlockwise circles; prasadam flow complete; one ritual at a time.
import { expect, test } from '@playwright/test';
import { config } from './content';
import { enterGolu, scrollMax } from './helpers';

test.describe.configure({ timeout: 180_000 });

test('aarthi circles 3 + 3 and scroll is locked then restored', async ({ page }) => {
  await enterGolu(page);
  const max = await scrollMax(page);
  await page.evaluate((yy) => window.scrollTo(0, yy), Math.round(max * 0.3));
  await page.waitForTimeout(800);
  const y0 = await page.evaluate(() => window.scrollY);
  await page.getByRole('button', { name: new RegExp(config.rituals.aarthi.label_en) }).click();
  await page.mouse.wheel(0, 2000);
  await page.waitForTimeout(500);
  expect(await page.evaluate(() => window.scrollY)).toBe(y0);
  // a second ritual is refused while one runs
  await expect(page.getByRole('button', { name: new RegExp(config.rituals.camphor.label_en) })).toBeDisabled();
  await page.waitForFunction(() => (window.__golu?.ritualLog.length ?? 0) > 0, undefined, { timeout: 30_000 });
  const log = await page.evaluate(() => window.__golu?.ritualLog[0]);
  expect(log).toMatchObject({ kind: 'aarthi', cwTurns: 3, ccwTurns: 3 });
  await page.mouse.wheel(0, 600);
  await page.waitForTimeout(400);
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(y0);
});

test('camphor circles 3 + 3 and goes out', async ({ page }) => {
  await enterGolu(page);
  await page.getByRole('button', { name: new RegExp(config.rituals.camphor.label_en) }).click();
  await page.waitForFunction(() => (window.__golu?.ritualLog.length ?? 0) > 0, undefined, { timeout: 40_000 });
  expect(await page.evaluate(() => window.__golu?.ritualLog[0])).toMatchObject({ kind: 'camphor', cwTurns: 3, ccwTurns: 3 });
});

test('prasadam: tray with the configured trio, Take → blessing, auto close', async ({ page }) => {
  await enterGolu(page);
  await page.getByRole('button', { name: new RegExp(config.rituals.prasadam.label_en) }).click();
  const dialog = page.getByRole('dialog', { name: new RegExp(config.rituals.prasadam.label_en) });
  await expect(dialog).toBeVisible();
  const ids = [...config.prasadam.fixed, config.prasadam.third_dish];
  for (const id of ids) {
    const d = config.prasadam.dishes.find((x) => x.id === id)!;
    await expect(dialog.getByText(d.name_en)).toBeVisible();
    await expect(dialog.getByText(d.name_ta)).toBeVisible();
  }
  await dialog.getByRole('button', { name: new RegExp(config.rituals.prasadam.take_en) }).click();
  await expect(page.getByText(config.rituals.prasadam.blessing_ta)).toBeVisible();
  // SvelteKit's own route announcer is also assertive: target the blessing's live region
  await expect(page.locator('[aria-live="assertive"]:not(#svelte-announcer)')).toContainText(config.rituals.prasadam.blessing_en);
  await expect(dialog).toHaveCount(0, { timeout: (config.rituals.prasadam.auto_close_seconds + 4) * 1000 });
});
