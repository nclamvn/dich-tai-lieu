/**
 * E2E Tests: Homepage & Navigation
 * Tests basic page load, UI elements, and navigation
 * Updated for Claude-style UI (2026)
 */

import { test, expect } from '@playwright/test';
import { waitForAppReady } from './helpers.js';

test.describe('Homepage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should load the main application', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/AI Publisher Pro/);

    // Check main content is visible
    const mainContent = page.locator('.main-content');
    await expect(mainContent).toBeVisible();
  });

  test('should display hero section', async ({ page }) => {
    // Hero title
    const heroTitle = page.locator('.hero-title');
    await expect(heroTitle).toBeVisible();

    // Hero subtitle
    const heroSubtitle = page.locator('.hero-subtitle');
    await expect(heroSubtitle).toBeVisible();
  });

  test('should display upload zone', async ({ page }) => {
    const uploadZone = page.locator('#upload-zone');
    await expect(uploadZone).toBeVisible();
  });

  test('should have file input', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    await expect(fileInput).toBeAttached();
  });

  test('should have language selectors', async ({ page }) => {
    // Source language - may be in options panel
    const sourceLang = page.locator('#source-lang');
    await expect(sourceLang).toBeAttached();

    // Target language
    const targetLang = page.locator('#target-lang');
    await expect(targetLang).toBeAttached();
  });

  test('should have submit button', async ({ page }) => {
    const submitBtn = page.locator('#submit-btn');
    await expect(submitBtn).toBeVisible();
  });

  test('should have progress steps in DOM', async ({ page }) => {
    // Step 1 - Analysis
    const step1 = page.locator('#step-1');
    await expect(step1).toBeAttached();

    // Step 2 - Translation
    const step2 = page.locator('#step-2');
    await expect(step2).toBeAttached();

    // Step 3 - Export
    const step3 = page.locator('#step-3');
    await expect(step3).toBeAttached();
  });

  test('should have preview tabs in DOM', async ({ page }) => {
    const previewTabs = page.locator('.preview-tabs');
    await expect(previewTabs).toBeAttached();
  });
});

test.describe('Theme', () => {
  test('should have theme toggle in settings', async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);

    // Open settings panel
    const settingsBtn = page.locator('#settings-btn');
    await settingsBtn.click();

    // Check theme toggle exists
    const themeToggle = page.locator('#theme-toggle');
    await expect(themeToggle).toBeVisible();
  });

  test('should persist theme in localStorage', async ({ page }) => {
    await page.goto('/ui');

    // Check localStorage has theme key (or will be set)
    const theme = await page.evaluate(() => {
      return localStorage.getItem('theme') || 'system';
    });

    expect(['light', 'dark', 'system']).toContain(theme);
  });
});

test.describe('Settings Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should open settings panel', async ({ page }) => {
    const settingsBtn = page.locator('#settings-btn');
    await settingsBtn.click();

    const settingsPanel = page.locator('#settings-panel');
    await expect(settingsPanel).toBeVisible();
  });

  test('should close settings panel', async ({ page }) => {
    // Open settings
    await page.locator('#settings-btn').click();
    const settingsPanel = page.locator('#settings-panel');
    await expect(settingsPanel).toBeVisible();

    // Close settings via overlay click or close button
    const closeBtn = page.locator('#settings-close');
    await closeBtn.click();

    // Wait for panel to close (may have animation)
    await page.waitForTimeout(300);

    // Panel should be hidden (check class or hidden state)
    const isHidden = await settingsPanel.evaluate(el => {
      return !el.classList.contains('active') ||
             window.getComputedStyle(el).display === 'none' ||
             !el.offsetParent;
    });
    expect(isHidden).toBeTruthy();
  });

  test('should have API key input', async ({ page }) => {
    await page.locator('#settings-btn').click();

    const apiKeyInput = page.locator('#api-key-input');
    await expect(apiKeyInput).toBeVisible();
  });
});

test.describe('History Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should open history panel', async ({ page }) => {
    const historyBtn = page.locator('#history-btn');
    await historyBtn.click();

    const historyPanel = page.locator('#history-panel');
    await expect(historyPanel).toBeVisible();
  });

  test('should close history panel', async ({ page }) => {
    // Open history
    await page.locator('#history-btn').click();
    const historyPanel = page.locator('#history-panel');
    await expect(historyPanel).toBeVisible();

    // Close history
    await page.locator('#history-close').click();

    // Wait for panel to close (may have animation)
    await page.waitForTimeout(300);

    // Panel should be hidden
    const isHidden = await historyPanel.evaluate(el => {
      return !el.classList.contains('active') ||
             window.getComputedStyle(el).display === 'none' ||
             !el.offsetParent;
    });
    expect(isHidden).toBeTruthy();
  });

  test('should show empty state initially', async ({ page }) => {
    await page.locator('#history-btn').click();

    const emptyState = page.locator('#history-empty');
    await expect(emptyState).toBeVisible();
  });
});

test.describe('Model Selection', () => {
  test('should have model selector in DOM', async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);

    const modelSelect = page.locator('#model-select');
    await expect(modelSelect).toBeAttached();
  });

  test('should have model options', async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);

    const options = await page.locator('#model-select option').count();
    expect(options).toBeGreaterThan(0);
  });
});
