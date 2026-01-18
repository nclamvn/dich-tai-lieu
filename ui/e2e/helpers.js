/**
 * E2E Test Helpers
 * Common utilities for Playwright tests
 * Updated for Claude-style UI (2026)
 */

/**
 * Wait for the application to be fully loaded
 * @param {import('@playwright/test').Page} page
 */
export async function waitForAppReady(page) {
  // Wait for Lucide icons to be initialized
  await page.waitForFunction(() => {
    return typeof lucide !== 'undefined';
  }, { timeout: 10000 });

  // Wait for main content to be visible
  await page.waitForSelector('.main-content', { state: 'visible', timeout: 10000 });
}

/**
 * Upload a file to the dropzone
 * @param {import('@playwright/test').Page} page
 * @param {string} filePath - Path to the file to upload
 */
export async function uploadFile(page, filePath) {
  const fileInput = page.locator('#file-input');
  await fileInput.setInputFiles(filePath);
}

/**
 * Create a test file with content
 * @param {import('@playwright/test').Page} page
 * @param {string} content - File content
 * @param {string} filename - File name
 */
export async function uploadTestContent(page, content, filename = 'test.txt') {
  const dataTransfer = await page.evaluateHandle((data) => {
    const dt = new DataTransfer();
    const file = new File([data.content], data.filename, { type: 'text/plain' });
    dt.items.add(file);
    return dt;
  }, { content, filename });

  const dropzone = page.locator('#upload-zone');
  await dropzone.dispatchEvent('drop', { dataTransfer });
}

/**
 * Wait for job to complete or fail
 * @param {import('@playwright/test').Page} page
 * @param {number} timeout - Max wait time in ms
 */
export async function waitForJobCompletion(page, timeout = 120000) {
  await page.waitForFunction(
    () => {
      const progressText = document.querySelector('#progress-percentage');
      return progressText && progressText.textContent === '100%';
    },
    { timeout }
  );
}

/**
 * Get current step status
 * @param {import('@playwright/test').Page} page
 * @param {number} stepNum - Step number (1, 2, or 3)
 */
export async function getStepStatus(page, stepNum) {
  const step = page.locator(`#step-${stepNum}`);
  return step.getAttribute('class');
}

/**
 * Wait for specific step to be active
 * @param {import('@playwright/test').Page} page
 * @param {number} stepNum - Step number (1, 2, or 3)
 */
export async function waitForStepActive(page, stepNum) {
  await page.waitForSelector(`#step-${stepNum}.active`, { timeout: 30000 });
}

/**
 * Switch to a specific preview tab
 * @param {import('@playwright/test').Page} page
 * @param {string} tabName - Tab name
 */
export async function switchPreviewTab(page, tabName) {
  const tabButton = page.locator(`.preview-tab:has-text("${tabName}")`);
  await tabButton.click();
}

/**
 * Get all download links
 * @param {import('@playwright/test').Page} page
 */
export async function getDownloadLinks(page) {
  const links = await page.locator('#download-section .download-card a').all();
  return Promise.all(links.map(link => link.getAttribute('href')));
}

/**
 * Check if WebSocket is connected
 * @param {import('@playwright/test').Page} page
 */
export async function isWebSocketConnected(page) {
  return page.evaluate(() => {
    return typeof WebSocketClient !== 'undefined' && WebSocketClient.isConnected();
  });
}

/**
 * Wait for WebSocket connection
 * @param {import('@playwright/test').Page} page
 * @param {number} timeout
 */
export async function waitForWebSocket(page, timeout = 10000) {
  await page.waitForFunction(
    () => typeof WebSocketClient !== 'undefined' && WebSocketClient.isConnected(),
    { timeout }
  );
}

/**
 * Mock API response
 * @param {import('@playwright/test').Page} page
 * @param {string} urlPattern - URL pattern to intercept
 * @param {object} response - Response data
 */
export async function mockApiResponse(page, urlPattern, response) {
  await page.route(urlPattern, (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response)
    });
  });
}

/**
 * Create sample test files
 */
export const TEST_FILES = {
  simple: {
    content: 'Hello World. This is a simple test document.',
    filename: 'simple.txt'
  },
  multiline: {
    content: `Chapter 1: Introduction

This is the first paragraph of the introduction. It contains multiple sentences.

Chapter 2: Methods

We used the following approach to solve the problem.`,
    filename: 'multiline.txt'
  },
  academic: {
    content: `Abstract

This paper presents a novel approach to document translation using AI models.

Keywords: AI, Translation, NLP

1. Introduction

The field of natural language processing has seen remarkable advances in recent years.`,
    filename: 'academic.txt'
  }
};
