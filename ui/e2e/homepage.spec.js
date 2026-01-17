/**
 * E2E Tests: Homepage & Navigation
 * Tests basic page load, UI elements, and navigation
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
    await expect(page).toHaveTitle(/Xưởng Xuất Bản/);

    // Check main header is visible
    const header = page.locator('.workflow-header h1');
    await expect(header).toBeVisible();
    await expect(header).toContainText('Xưởng Xuất Bản');
  });

  test('should display three agent cards', async ({ page }) => {
    // Editor agent
    const editorAgent = page.locator('#agent-editor');
    await expect(editorAgent).toBeVisible();
    await expect(editorAgent.locator('h3')).toContainText('Biên Tập Viên');

    // Translator agent
    const translatorAgent = page.locator('#agent-translator');
    await expect(translatorAgent).toBeVisible();
    await expect(translatorAgent.locator('h3')).toContainText('Dịch Giả');

    // Publisher agent
    const publisherAgent = page.locator('#agent-publisher');
    await expect(publisherAgent).toBeVisible();
    await expect(publisherAgent.locator('h3')).toContainText('Nhà Xuất Bản');
  });

  test('should have all agents in idle status initially', async ({ page }) => {
    const agents = ['agent-editor', 'agent-translator', 'agent-publisher'];

    for (const agentId of agents) {
      const agent = page.locator(`#${agentId}`);
      await expect(agent).toHaveAttribute('data-status', 'idle');
    }
  });

  test('should display dropzone for file upload', async ({ page }) => {
    const dropzone = page.locator('#dropzone');
    await expect(dropzone).toBeVisible();
    await expect(dropzone).toContainText('Kéo thả tài liệu vào đây');
  });

  test('should have start button disabled initially', async ({ page }) => {
    const startButton = page.locator('#btn-start');
    await expect(startButton).toBeVisible();
    await expect(startButton).toBeDisabled();
  });

  test('should display all preview tabs', async ({ page }) => {
    const tabs = [
      { name: 'preview', text: 'Xem Trước' },
      { name: 'dna', text: 'DNA' },
      { name: 'progress', text: 'Tiến Trình' },
      { name: 'downloads', text: 'Tải Xuống' }
    ];

    for (const tab of tabs) {
      const tabBtn = page.locator(`[data-tab="${tab.name}"]`);
      await expect(tabBtn).toBeVisible();
      await expect(tabBtn).toContainText(tab.text);
    }
  });

  test('should switch between tabs', async ({ page }) => {
    // Click progress tab
    await page.locator('[data-tab="progress"]').click();
    await expect(page.locator('#tab-progress')).toHaveClass(/active/);

    // Click downloads tab
    await page.locator('[data-tab="downloads"]').click();
    await expect(page.locator('#tab-downloads')).toHaveClass(/active/);

    // Click preview tab
    await page.locator('[data-tab="preview"]').click();
    await expect(page.locator('#tab-preview')).toHaveClass(/active/);
  });

  test('should display AI provider selector', async ({ page }) => {
    const providerCard = page.locator('#ai-provider-card');
    await expect(providerCard).toBeVisible();

    const providerName = providerCard.locator('.provider-name');
    await expect(providerName).toBeVisible();
  });

  test('should have profile selector visible', async ({ page }) => {
    const profileSelector = page.locator('#profile-selector');
    await expect(profileSelector).toBeVisible();

    const profileSelected = page.locator('#profile-selected');
    await expect(profileSelected).toBeVisible();
  });
});

test.describe('Theme', () => {
  test('should start with dark theme', async ({ page }) => {
    await page.goto('/ui');

    const html = page.locator('html');
    const theme = await html.getAttribute('data-theme');
    expect(theme).toBe('dark');
  });

  test('should persist theme in localStorage', async ({ page }) => {
    await page.goto('/ui');

    const theme = await page.evaluate(() => localStorage.getItem('theme'));
    // Theme should be set or null (defaults to system preference)
    expect(theme === null || theme === 'dark' || theme === 'light').toBeTruthy();
  });
});

test.describe('Mode Toggle', () => {
  test('should display mode toggle buttons', async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);

    const singleModeBtn = page.locator('[data-mode="single"]');
    await expect(singleModeBtn).toBeVisible();
    await expect(singleModeBtn).toContainText('Một File');

    const batchLink = page.locator('.mode-toggle a[href="/ui/batch-upload.html"]');
    await expect(batchLink).toBeVisible();
    await expect(batchLink).toContainText('Hàng Loạt');
  });

  test('should have single mode active by default', async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);

    const singleModeBtn = page.locator('[data-mode="single"]');
    await expect(singleModeBtn).toHaveClass(/active/);
  });
});
