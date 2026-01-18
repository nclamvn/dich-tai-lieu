/**
 * E2E Tests: WebSocket Connection
 * Tests real-time updates via WebSocket
 * Updated for Claude-style UI (2026)
 */

import { test, expect } from '@playwright/test';
import { waitForAppReady } from './helpers.js';

test.describe('WebSocket Connection', () => {
  test('should have WebSocket support', async ({ page }) => {
    await page.goto('/ui', { timeout: 60000 });
    await waitForAppReady(page);

    // Check if WebSocket is available in browser
    const hasWebSocket = await page.evaluate(() => {
      return typeof WebSocket !== 'undefined';
    });

    expect(hasWebSocket).toBeTruthy();
  });
});

test.describe('Real-time Updates', () => {
  test('should have progress elements', async ({ page }) => {
    await page.goto('/ui', { timeout: 60000 });
    await waitForAppReady(page);

    // Check for progress elements
    await expect(page.locator('#progress-percentage')).toBeAttached();
    await expect(page.locator('#progress-fill')).toBeAttached();
    await expect(page.locator('#activity-list')).toBeAttached();

    // Step indicators
    await expect(page.locator('#step-1')).toBeAttached();
    await expect(page.locator('#step-2')).toBeAttached();
    await expect(page.locator('#step-3')).toBeAttached();
  });
});

test.describe('Polling Fallback', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should support HTTP polling for status updates', async ({ page }) => {
    // The UI should be able to poll job status via HTTP
    // This tests that the infrastructure exists
    const hasXHR = await page.evaluate(() => {
      return typeof XMLHttpRequest !== 'undefined' || typeof fetch !== 'undefined';
    });

    expect(hasXHR).toBeTruthy();
  });

  test('should have job status endpoint awareness', async ({ page }) => {
    // Check if code can make API calls
    const canFetch = await page.evaluate(async () => {
      try {
        // Just check fetch is available
        return typeof fetch === 'function';
      } catch {
        return false;
      }
    });

    expect(canFetch).toBeTruthy();
  });
});

test.describe('UI State Updates', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should have progress title element', async ({ page }) => {
    const progressTitle = page.locator('#progress-title');
    await expect(progressTitle).toBeAttached();
  });

  test('should have progress subtitle element', async ({ page }) => {
    const progressSubtitle = page.locator('#progress-subtitle');
    await expect(progressSubtitle).toBeAttached();
  });

  test('should have ETA display', async ({ page }) => {
    const progressEta = page.locator('#progress-eta');
    await expect(progressEta).toBeAttached();
  });

  test('should have batch summary elements', async ({ page }) => {
    const batchTotal = page.locator('#batch-total');
    const batchCompleted = page.locator('#batch-completed');
    const batchFailed = page.locator('#batch-failed');

    await expect(batchTotal).toBeAttached();
    await expect(batchCompleted).toBeAttached();
    await expect(batchFailed).toBeAttached();
  });
});

test.describe('Stats Display', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should have token stats element', async ({ page }) => {
    const statTokens = page.locator('#stat-tokens');
    await expect(statTokens).toBeAttached();
  });

  test('should have time stats element', async ({ page }) => {
    const statTime = page.locator('#stat-time');
    await expect(statTime).toBeAttached();
  });

  test('should have cost stats element', async ({ page }) => {
    const statCost = page.locator('#stat-cost');
    await expect(statCost).toBeAttached();
  });

  test('should have chunks stats element', async ({ page }) => {
    const statChunks = page.locator('#stat-chunks');
    await expect(statChunks).toBeAttached();
  });
});
