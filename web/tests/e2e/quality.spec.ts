// Phase 7 quality bars (SPEC §5.5): reduced motion, accessibility, initial payload, responsive layout.
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { config } from './content';
import { enterGolu } from './helpers';

test('initial load before Enter stays under 3 MB', async ({ page }) => {
  let bytes = 0;
  page.on('response', async (res) => {
    const len = Number(res.headers()['content-length'] ?? 0);
    if (len) bytes += len;
    else {
      try {
        bytes += (await res.body()).length;
      } catch {
        /* redirects / opaque */
      }
    }
  });
  await page.goto('/');
  await expect(page.getByRole('button', { name: /கொலுவுக்குள் வாருங்கள்/ })).toBeVisible({ timeout: 60_000 });
  await page.waitForTimeout(500);
  console.log(`pre-Enter transfer: ${(bytes / 1e6).toFixed(2)} MB`);
  expect(bytes).toBeLessThan(3_000_000);
});

test('reduced motion: key frames instead of the scrubbed canvas, static ritual', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce', viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();
  await enterGolu(page);
  await expect(page.locator('canvas.frame-canvas')).toHaveCount(0);
  await expect(page.locator('img.key')).toHaveCount(9);
  await page.getByRole('button', { name: new RegExp(config.rituals.aarthi.label_en) }).click();
  const plate = page.locator('.plate');
  await expect(plate).toBeVisible();
  await page.waitForTimeout(1200);
  const a = await plate.boundingBox();
  await page.waitForTimeout(1500);
  const b = await plate.boundingBox();
  expect(Math.abs((a?.x ?? 0) - (b?.x ?? 0))).toBeLessThan(1);
  await ctx.close();
});

test('no serious accessibility violations; blessing announced', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: /கொலுவுக்குள் வாருங்கள்/ })).toBeVisible({ timeout: 60_000 });
  let res = await new AxeBuilder({ page }).analyze();
  expect(res.violations.filter((v) => ['serious', 'critical'].includes(v.impact ?? ''))).toEqual([]);
  await page.getByRole('button', { name: /கொலுவுக்குள் வாருங்கள்/ }).click();
  await page.waitForFunction(() => !document.querySelector('.entrance'), undefined, { timeout: 20_000 });
  res = await new AxeBuilder({ page }).analyze();
  expect(res.violations.filter((v) => ['serious', 'critical'].includes(v.impact ?? ''))).toEqual([]);
});

test('keyboard-only: enter, navigate, open a doll card, run a ritual, mute', async ({ page }) => {
  await page.goto('/');
  const enter = page.getByRole('button', { name: /கொலுவுக்குள் வாருங்கள்/ });
  await expect(enter).toBeVisible({ timeout: 60_000 });
  await enter.focus();
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => !document.querySelector('.entrance'), undefined, { timeout: 20_000 });
  const diya = page.getByRole('button', { name: /Step 4/ });
  await diya.focus();
  await page.keyboard.press('Enter');
  await page.waitForTimeout(2000);
  const outline = await diya.evaluate((el) => getComputedStyle(el).outlineColor);
  expect(outline).not.toBe('');
  const spot = page.locator('button.spot').first();
  await spot.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  const mute = page.getByRole('button', { name: new RegExp(config.ui.mute_en) });
  await mute.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: new RegExp(config.ui.unmute_en) })).toBeVisible();
});

for (const width of [360, 768, 1440, 3840]) {
  test(`no horizontal scroll at ${width}px`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width, height: Math.round(width * (width < 768 ? 2.1 : 0.56)) } });
    const page = await ctx.newPage();
    await enterGolu(page);
    const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(over).toBeLessThanOrEqual(0);
    await ctx.close();
  });
}
