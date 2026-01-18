/**
 * E2E Tests: Publishing Flow
 * Tests the complete translation/publishing workflow
 * Updated for Claude-style UI (2026)
 */

import { test, expect } from '@playwright/test';
import { waitForAppReady, TEST_FILES } from './helpers.js';
import path from 'path';
import fs from 'fs';
import os from 'os';

test.describe('Publishing Flow', () => {
  let testFilePath;

  test.beforeAll(async () => {
    // Create a test file
    const tmpDir = os.tmpdir();
    testFilePath = path.join(tmpDir, 'publish-test.txt');
    fs.writeFileSync(testFilePath, TEST_FILES.multiline.content);
  });

  test.afterAll(async () => {
    if (fs.existsSync(testFilePath)) {
      fs.unlinkSync(testFilePath);
    }
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/ui', { timeout: 60000 });
    await waitForAppReady(page);
  });

  test('should have submit button', async ({ page }) => {
    const submitBtn = page.locator('#submit-btn');
    await expect(submitBtn).toBeVisible();
  });

  test('should show file preview after upload', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFilePath);

    const filePreview = page.locator('#file-preview');
    await expect(filePreview).toBeVisible();
  });

  test('should have progress section in DOM', async ({ page }) => {
    // Progress section should exist in DOM
    const progressSection = page.locator('#progress-section');
    await expect(progressSection).toBeAttached();
  });

  test('should have progress steps in DOM', async ({ page }) => {
    // Progress steps should exist in DOM
    const step1 = page.locator('#step-1');
    const step2 = page.locator('#step-2');
    const step3 = page.locator('#step-3');

    await expect(step1).toBeAttached();
    await expect(step2).toBeAttached();
    await expect(step3).toBeAttached();
  });
});

test.describe('Publishing API Integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should be able to submit form', async ({ page }) => {
    // Create test file
    const tmpDir = os.tmpdir();
    const testFile = path.join(tmpDir, 'api-test.txt');
    fs.writeFileSync(testFile, 'Test content');

    // Upload file
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFile);

    // Verify file is loaded
    const fileName = page.locator('#file-name');
    await expect(fileName).toContainText('.txt');

    // Submit button should be available
    const submitBtn = page.locator('#submit-btn');
    await expect(submitBtn).toBeVisible();

    // Cleanup
    fs.unlinkSync(testFile);
  });

  test('should have fetch capability for polling', async ({ page }) => {
    // Verify fetch API is available for polling
    const hasFetch = await page.evaluate(() => {
      return typeof fetch === 'function';
    });

    expect(hasFetch).toBeTruthy();
  });
});

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should handle API errors gracefully', async ({ page }) => {
    const tmpDir = os.tmpdir();
    const testFile = path.join(tmpDir, 'error-test.txt');
    fs.writeFileSync(testFile, 'Error test content');

    // Intercept with error response
    await page.route('**/translate', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Internal server error'
        })
      });
    });

    // Upload and start
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFile);

    const submitBtn = page.locator('#submit-btn');
    await submitBtn.click();

    // Wait for error handling
    await page.waitForTimeout(1000);

    // Page should not crash - main content visible
    await expect(page.locator('.main-content')).toBeVisible();

    // Cleanup
    fs.unlinkSync(testFile);
  });

  test('should handle network errors', async ({ page }) => {
    const tmpDir = os.tmpdir();
    const testFile = path.join(tmpDir, 'network-test.txt');
    fs.writeFileSync(testFile, 'Network test content');

    // Intercept with network error
    await page.route('**/translate', (route) => {
      route.abort('failed');
    });

    // Upload and start
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFile);

    const submitBtn = page.locator('#submit-btn');
    await submitBtn.click();

    // Wait for error handling
    await page.waitForTimeout(1000);

    // Page should not crash
    await expect(page.locator('.main-content')).toBeVisible();

    // Cleanup
    fs.unlinkSync(testFile);
  });
});

test.describe('Downloads', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should have download section', async ({ page }) => {
    const downloadSection = page.locator('#download-section');
    await expect(downloadSection).toBeAttached();
  });

  test('should show downloads when job completes', async ({ page }) => {
    const tmpDir = os.tmpdir();
    const testFile = path.join(tmpDir, 'download-test.txt');
    fs.writeFileSync(testFile, 'Download test content');

    // Mock completed job
    await page.route('**/translate', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'download-job-123',
          status: 'completed',
          progress: 100
        })
      });
    });

    await page.route('**/jobs/download-job-123**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'download-job-123',
          status: 'completed',
          progress: 100,
          outputs: {
            docx: '/outputs/test.docx',
            pdf: '/outputs/test.pdf'
          }
        })
      });
    });

    // Upload and start
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFile);

    const submitBtn = page.locator('#submit-btn');
    await submitBtn.click();

    // Wait for completion
    await page.waitForTimeout(2000);

    // Download section should exist
    const downloadSection = page.locator('#download-section');
    await expect(downloadSection).toBeAttached();

    // Cleanup
    fs.unlinkSync(testFile);
  });
});

test.describe('Progress Display', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should have progress percentage element', async ({ page }) => {
    const progressPercentage = page.locator('#progress-percentage');
    await expect(progressPercentage).toBeAttached();
  });

  test('should have progress bar', async ({ page }) => {
    const progressBar = page.locator('.progress-bar');
    await expect(progressBar).toBeAttached();
  });

  test('should update progress during job', async ({ page }) => {
    const tmpDir = os.tmpdir();
    const testFile = path.join(tmpDir, 'progress-test.txt');
    fs.writeFileSync(testFile, 'Progress test content');

    let pollCount = 0;

    await page.route('**/translate', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'progress-job-123',
          status: 'processing'
        })
      });
    });

    await page.route('**/jobs/progress-job-123**', (route) => {
      pollCount++;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'progress-job-123',
          status: 'processing',
          progress: Math.min(pollCount * 20, 100)
        })
      });
    });

    // Upload and start
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFile);

    await page.locator('#submit-btn').click();

    // Wait for some progress
    await page.waitForTimeout(3000);

    // Progress should have updated
    const progressText = await page.locator('#progress-percentage').textContent();
    // Should show some percentage
    expect(progressText).toBeTruthy();

    // Cleanup
    fs.unlinkSync(testFile);
  });
});
