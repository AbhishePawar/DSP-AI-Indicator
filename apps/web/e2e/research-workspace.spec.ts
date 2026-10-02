import { test, expect } from '@playwright/test';

test.describe('Stage 3 Research Workspace QA & Parity Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to /analysis
    await page.goto('/analysis');
  });

  test('Selection Screen: toggles between Simple and Buffett Flagship modes', async ({ page }) => {
    await expect(page.locator('text=Flagship Analysis')).toBeVisible();
    await expect(page.locator('text=Simple')).toBeVisible();
    
    // Check mode toggle buttons
    const simpleBtn = page.getByRole('button', { name: /Simple/i });
    await simpleBtn.click();
    await expect(simpleBtn).toBeVisible();

    const flagshipBtn = page.getByRole('button', { name: /Flagship/i });
    await flagshipBtn.click();
    await expect(flagshipBtn).toBeVisible();
  });

  test('Keyboard Navigation: Tab order, TOC activation and active ScrollSpy', async ({ page }) => {
    // Start analysis with benchmark shortcut
    const tcsShortcut = page.getByRole('button', { name: /TCS/i });
    if (await tcsShortcut.isVisible()) {
      await tcsShortcut.click();
    }
    
    const runBtn = page.getByRole('button', { name: /Run Analysis/i });
    await runBtn.click();

    // Verify TOC sidebar is accessible via keyboard
    const tocNav = page.locator('aside[role="navigation"]');
    await expect(tocNav).toBeVisible({ timeout: 15000 });

    const summaryItem = tocNav.getByRole('button', { name: /Summary/i });
    await summaryItem.focus();
    await expect(summaryItem).toBeFocused();
    await page.keyboard.press('Enter');

    // Section 1 should be active
    await expect(summaryItem).toHaveAttribute('aria-current', 'true');
  });

  test('Research Chat Drawer: focus entry, Escape dismissal, and focus restoration', async ({ page }) => {
    const runBtn = page.getByRole('button', { name: /Run Analysis/i });
    await runBtn.click();

    const askDspBtn = page.getByRole('button', { name: /Ask DSP/i }).first();
    await expect(askDspBtn).toBeVisible({ timeout: 15000 });
    await askDspBtn.focus();
    await expect(askDspBtn).toBeFocused();
    await page.keyboard.press('Enter');

    // Drawer should open and focus input
    const drawer = page.locator('div[role="dialog"]');
    await expect(drawer).toBeVisible();
    const input = drawer.getByRole('textbox', { name: /Ask DSP Copilot/i });
    await expect(input).toBeFocused();

    // Press Escape to dismiss
    await page.keyboard.press('Escape');
    await expect(drawer).not.toBeVisible();

    // Focus restored to trigger
    await expect(askDspBtn).toBeFocused();
  });

  test('Data State Safety: Missing financial series renders structured unavailable state', async ({ page }) => {
    const runBtn = page.getByRole('button', { name: /Run Analysis/i });
    await runBtn.click();

    // Verify financials section
    const financials = page.locator('#s04');
    await expect(financials).toBeVisible({ timeout: 15000 });

    // Should indicate awaiting filing data when server series is missing
    const awaitingText = page.locator('text=awaiting filing data from backend').first();
    await expect(awaitingText).toBeVisible();
  });

  test('Accessibility: Table semantics and ARIA captions', async ({ page }) => {
    const runBtn = page.getByRole('button', { name: /Run Analysis/i });
    await runBtn.click();

    const buffettTable = page.locator('table[role="table"]');
    await expect(buffettTable).toBeVisible({ timeout: 15000 });
    const caption = buffettTable.locator('caption');
    await expect(caption).toHaveText(/Evaluation of 10 core Buffett investment criteria/i);
  });
});
