// Phase 5 acceptance: smooth scrub with no blank frames on fast scroll; audio starts on Enter (SPEC §6).
import { expect, test } from '@playwright/test';
import { canvasIsBlank, enterGolu, scrollMax } from './helpers';

test('audio context starts on Enter and the Om fades in', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: /கொலுவுக்குள் வாருங்கள்/ })).toBeVisible({ timeout: 60_000 });
  const before = await page.evaluate(() => window.__golu?.audio().state ?? 'none');
  expect(['none', 'suspended']).toContain(before);
  await enterGolu(page);
  await expect.poll(() => page.evaluate(() => window.__golu?.audio().state)).toBe('running');
  await page.waitForTimeout(3300);
  const om = await page.evaluate(() => window.__golu?.audio().om ?? 0);
  expect(om).toBeGreaterThan(0.3);
});

test('never shows a blank canvas while scrubbing fast', async ({ page }) => {
  // 100 jumps, each with a canvas readback: headless Chromium decodes 1080p WebP in software (~200 ms/frame here)
  test.setTimeout(240_000);
  await enterGolu(page);
  const max = await scrollMax(page);
  let blanks = 0;
  for (let i = 0; i < 40; i++) {
    const y = Math.round(Math.random() * max);
    await page.evaluate((yy) => window.scrollTo(0, yy), y);
    await page.waitForTimeout(16);
    if (await canvasIsBlank(page)) blanks++;
  }
  for (let i = 0; i < 60; i++) {
    await page.mouse.wheel(0, 900);
    await page.waitForTimeout(16);
    if (await canvasIsBlank(page)) blanks++;
  }
  expect(blanks).toBe(0);
  const stats = await page.evaluate(() => window.__golu?.stats());
  expect(stats?.blankDraws).toBe(0);
});

test('step title card and hotspots appear inside a step', async ({ page }) => {
  await enterGolu(page);
  const max = await scrollMax(page);
  await page.evaluate((yy) => window.scrollTo(0, yy), Math.round(max * (120 + 50) / 1127));
  await page.waitForTimeout(1500);
  await expect(page.locator('.card-wrap')).toHaveCSS('opacity', '1');
  await expect(page.locator('button.spot').first()).toBeVisible();
  await page.locator('button.spot').first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});
