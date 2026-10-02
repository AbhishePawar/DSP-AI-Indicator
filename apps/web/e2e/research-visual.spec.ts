import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'laptop-1280', width: 1280, height: 800 },
  { name: 'tablet-landscape-1024', width: 1024, height: 768 },
  { name: 'tablet-portrait-768', width: 768, height: 1024 },
  { name: 'mobile-480', width: 480, height: 854 },
];

test.describe('Research Workspace Visual Regression Suite', () => {
  for (const vp of VIEWPORTS) {
    test.describe(`Viewport: ${vp.name} (${vp.width}x${vp.height})`, () => {
      test.use({ viewport: { width: vp.width, height: vp.height } });

      test('Selection Screen Baseline', async ({ page }) => {
        await page.goto('/analysis');
        await expect(page.locator('text=Flagship Analysis')).toBeVisible();
        await expect(page).toHaveScreenshot(`selection-screen-${vp.name}.png`, {
          fullPage: false,
          maxDiffPixelRatio: 0.02,
        });
      });

      test('Workspace Flagship & Summary Baseline', async ({ page }) => {
        await page.goto('/analysis');
        const runBtn = page.getByRole('button', { name: /Run Analysis/i });
        await runBtn.click();

        await expect(page.locator('#s01')).toBeVisible({ timeout: 15000 });
        await expect(page).toHaveScreenshot(`flagship-workspace-${vp.name}.png`, {
          fullPage: false,
          maxDiffPixelRatio: 0.02,
        });
      });

      test('Buffett 10-Criteria Assessment Baseline', async ({ page }) => {
        await page.goto('/analysis');
        const runBtn = page.getByRole('button', { name: /Run Analysis/i });
        await runBtn.click();

        const buffettSection = page.locator('#s02');
        await expect(buffettSection).toBeVisible({ timeout: 15000 });
        await buffettSection.scrollIntoViewIfNeeded();

        await expect(buffettSection).toHaveScreenshot(`buffett-assessment-${vp.name}.png`, {
          maxDiffPixelRatio: 0.02,
        });
      });

      test('Chat Drawer Baseline', async ({ page }) => {
        await page.goto('/analysis');
        const runBtn = page.getByRole('button', { name: /Run Analysis/i });
        await runBtn.click();

        const askDspBtn = page.getByRole('button', { name: /Ask DSP/i }).first();
        await expect(askDspBtn).toBeVisible({ timeout: 15000 });
        await askDspBtn.click();

        const drawer = page.locator('div[role="dialog"]');
        await expect(drawer).toBeVisible();

        await expect(drawer).toHaveScreenshot(`chat-drawer-${vp.name}.png`, {
          maxDiffPixelRatio: 0.02,
        });
      });
    });
  }
});
