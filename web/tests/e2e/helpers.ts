import { expect, type Page } from '@playwright/test';

/** Wait for the Enter plaque (preloading done) and enter the Golu. */
export async function enterGolu(page: Page): Promise<void> {
  await page.goto('/');
  const enter = page.getByRole('button', { name: /கொலுவுக்குள் வாருங்கள்/ });
  await expect(enter).toBeVisible({ timeout: 60_000 });
  await enter.click();
  await expect(page.locator('main#golu-main')).toBeVisible();
  await page.waitForFunction(() => !document.querySelector('.entrance'), undefined, { timeout: 20_000 });
}

/** Sample 9 points of the frame canvas; true if every sample is fully black/transparent (a blank frame). */
export async function canvasIsBlank(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const c = document.querySelector('canvas.frame-canvas') as HTMLCanvasElement | null;
    if (!c) return true;
    const ctx = c.getContext('2d');
    if (!ctx) return true;
    for (const fx of [0.2, 0.5, 0.8]) {
      for (const fy of [0.2, 0.5, 0.8]) {
        const d = ctx.getImageData(Math.floor(c.width * fx), Math.floor(c.height * fy), 1, 1).data;
        if (d[0] + d[1] + d[2] > 3) return false;
      }
    }
    return true;
  });
}

export async function scrollMax(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight);
}
