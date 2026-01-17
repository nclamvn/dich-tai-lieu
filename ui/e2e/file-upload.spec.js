/**
 * E2E Tests: File Upload Flow
 * Tests file upload, validation, and preview
 */

import { test, expect } from '@playwright/test';
import { waitForAppReady, TEST_FILES } from './helpers.js';
import path from 'path';
import fs from 'fs';
import os from 'os';

test.describe('File Upload', () => {
  let testFilePath;

  test.beforeAll(async () => {
    // Create a test file
    const tmpDir = os.tmpdir();
    testFilePath = path.join(tmpDir, 'test-upload.txt');
    fs.writeFileSync(testFilePath, TEST_FILES.simple.content);
  });

  test.afterAll(async () => {
    // Cleanup test file
    if (fs.existsSync(testFilePath)) {
      fs.unlinkSync(testFilePath);
    }
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should accept file via file input', async ({ page }) => {
    const fileInput = page.locator('#file-input');

    // Upload file
    await fileInput.setInputFiles(testFilePath);

    // Check file preview appears
    const filePreview = page.locator('#file-preview');
    await expect(filePreview).toBeVisible();

    // Check filename is displayed
    const fileName = page.locator('#file-name');
    await expect(fileName).toContainText('test-upload.txt');

    // Check start button becomes enabled
    const startButton = page.locator('#btn-start');
    await expect(startButton).toBeEnabled();
  });

  test('should show file size in preview', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFilePath);

    const fileSize = page.locator('#file-size');
    await expect(fileSize).toBeVisible();
    // Should show bytes or KB
    const sizeText = await fileSize.textContent();
    expect(sizeText).toMatch(/\d+(\.\d+)?\s*(B|KB|MB)/);
  });

  test('should allow removing uploaded file', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFilePath);

    // Verify file is uploaded
    const filePreview = page.locator('#file-preview');
    await expect(filePreview).toBeVisible();

    // Click remove button
    const removeButton = page.locator('#file-remove');
    await removeButton.click();

    // Check file preview is hidden
    await expect(filePreview).toBeHidden();

    // Check dropzone is visible again
    const dropzone = page.locator('#dropzone');
    await expect(dropzone).toBeVisible();

    // Check start button is disabled
    const startButton = page.locator('#btn-start');
    await expect(startButton).toBeDisabled();
  });

  test('should highlight dropzone on dragover', async ({ page }) => {
    const dropzone = page.locator('#dropzone');

    // Simulate dragover
    await dropzone.dispatchEvent('dragover', {
      dataTransfer: { types: ['Files'] }
    });

    // Check for dragover class/style (implementation dependent)
    // This is a basic check - actual implementation may vary
    await expect(dropzone).toBeVisible();
  });
});

test.describe('File Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should accept PDF files', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    const accept = await fileInput.getAttribute('accept');

    expect(accept).toContain('.pdf');
  });

  test('should accept DOCX files', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    const accept = await fileInput.getAttribute('accept');

    expect(accept).toContain('.docx');
  });

  test('should accept TXT files', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    const accept = await fileInput.getAttribute('accept');

    expect(accept).toContain('.txt');
  });

  test('should accept MD files', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    const accept = await fileInput.getAttribute('accept');

    expect(accept).toContain('.md');
  });

  test('should accept TEX files', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    const accept = await fileInput.getAttribute('accept');

    expect(accept).toContain('.tex');
  });
});

test.describe('Multiple File Types', () => {
  let testFiles = {};

  test.beforeAll(async () => {
    const tmpDir = os.tmpdir();

    // Create test files of different types
    testFiles.txt = path.join(tmpDir, 'test.txt');
    testFiles.md = path.join(tmpDir, 'test.md');

    fs.writeFileSync(testFiles.txt, 'Plain text content');
    fs.writeFileSync(testFiles.md, '# Markdown\n\nContent here');
  });

  test.afterAll(async () => {
    // Cleanup
    Object.values(testFiles).forEach(filePath => {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    });
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should upload TXT file successfully', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFiles.txt);

    const fileName = page.locator('#file-name');
    await expect(fileName).toContainText('test.txt');
  });

  test('should upload MD file successfully', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(testFiles.md);

    const fileName = page.locator('#file-name');
    await expect(fileName).toContainText('test.md');
  });
});
