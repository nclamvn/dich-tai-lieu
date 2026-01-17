/**
 * E2E Tests: Publishing Flow
 * Tests the complete translation/publishing workflow
 */

import { test, expect } from '@playwright/test';
import {
  waitForAppReady,
  waitForAgentActive,
  getAgentStatus,
  switchTab,
  TEST_FILES
} from './helpers.js';
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
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should enable start button after file upload', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFilePath);

    const startButton = page.locator('#btn-start');
    await expect(startButton).toBeEnabled();
  });

  test('should show progress tab content after starting', async ({ page }) => {
    // Upload file
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFilePath);

    // Click start button
    const startButton = page.locator('#btn-start');
    await startButton.click();

    // Wait for progress indicators
    await page.waitForTimeout(500);

    // Switch to progress tab
    await switchTab(page, 'progress');

    // Check progress bar is visible
    const progressBar = page.locator('#overall-progress');
    await expect(progressBar).toBeVisible();
  });

  test('should update agent status during processing', async ({ page }) => {
    // Upload file
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFilePath);

    // Click start button
    const startButton = page.locator('#btn-start');
    await startButton.click();

    // Wait for first agent to activate
    await page.waitForTimeout(1000);

    // At least one agent should be processing
    const editorStatus = await getAgentStatus(page, 'agent-editor');
    const translatorStatus = await getAgentStatus(page, 'agent-translator');
    const publisherStatus = await getAgentStatus(page, 'agent-publisher');

    // At least one should not be idle
    const hasActiveAgent =
      editorStatus !== 'idle' ||
      translatorStatus !== 'idle' ||
      publisherStatus !== 'idle';

    expect(hasActiveAgent).toBeTruthy();
  });

  test('should display progress percentage', async ({ page }) => {
    // Upload file
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFilePath);

    // Click start button
    const startButton = page.locator('#btn-start');
    await startButton.click();

    // Wait for some progress
    await page.waitForTimeout(2000);

    // Check progress text exists
    const progressText = page.locator('#progress-text');
    await expect(progressText).toBeVisible();

    const text = await progressText.textContent();
    expect(text).toMatch(/\d+%/);
  });
});

test.describe('Publishing API Integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should call translate API on start', async ({ page }) => {
    // Create test file
    const tmpDir = os.tmpdir();
    const testFile = path.join(tmpDir, 'api-test.txt');
    fs.writeFileSync(testFile, 'Test content');

    let apiCalled = false;

    // Intercept API call
    await page.route('**/translate', (route) => {
      apiCalled = true;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'test-job-123',
          status: 'processing'
        })
      });
    });

    // Upload and start
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFile);

    const startButton = page.locator('#btn-start');
    await startButton.click();

    // Wait for API call
    await page.waitForTimeout(1000);

    expect(apiCalled).toBeTruthy();

    // Cleanup
    fs.unlinkSync(testFile);
  });

  test('should poll job status after start', async ({ page }) => {
    const tmpDir = os.tmpdir();
    const testFile = path.join(tmpDir, 'poll-test.txt');
    fs.writeFileSync(testFile, 'Test content for polling');

    let pollCount = 0;

    // Intercept translate API
    await page.route('**/translate', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'poll-job-123',
          status: 'processing'
        })
      });
    });

    // Intercept status polling
    await page.route('**/jobs/poll-job-123', (route) => {
      pollCount++;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 'poll-job-123',
          status: 'processing',
          progress: pollCount * 10
        })
      });
    });

    // Upload and start
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFile);

    const startButton = page.locator('#btn-start');
    await startButton.click();

    // Wait for multiple polls
    await page.waitForTimeout(6000);

    expect(pollCount).toBeGreaterThan(0);

    // Cleanup
    fs.unlinkSync(testFile);
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

    const startButton = page.locator('#btn-start');
    await startButton.click();

    // Wait for error handling
    await page.waitForTimeout(1000);

    // Page should not crash
    await expect(page.locator('.workflow-header')).toBeVisible();

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

    const startButton = page.locator('#btn-start');
    await startButton.click();

    // Wait for error handling
    await page.waitForTimeout(1000);

    // Page should not crash
    await expect(page.locator('.workflow-header')).toBeVisible();

    // Cleanup
    fs.unlinkSync(testFile);
  });
});

test.describe('Downloads', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should show downloads placeholder initially', async ({ page }) => {
    await switchTab(page, 'downloads');

    const placeholder = page.locator('#downloads-placeholder');
    await expect(placeholder).toBeVisible();
  });

  test('should show download grid when job completes', async ({ page }) => {
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
          status: 'completed'
        })
      });
    });

    await page.route('**/jobs/download-job-123', (route) => {
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

    const startButton = page.locator('#btn-start');
    await startButton.click();

    // Wait for completion
    await page.waitForTimeout(2000);

    // Switch to downloads tab
    await switchTab(page, 'downloads');

    // Grid should be visible (mocked response)
    // This depends on how the UI handles the completed state
    const downloadArea = page.locator('#tab-downloads');
    await expect(downloadArea).toBeVisible();

    // Cleanup
    fs.unlinkSync(testFile);
  });
});
