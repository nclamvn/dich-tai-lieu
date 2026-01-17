/**
 * Vitest Test Setup
 *
 * This file runs before each test file.
 * Sets up global mocks and utilities.
 */

import { vi, beforeEach, afterEach } from 'vitest';

// ============================================================================
// Global Mocks
// ============================================================================

// Mock fetch API
global.fetch = vi.fn();

// Mock localStorage
const localStorageMock = {
  store: {},
  getItem: vi.fn((key) => localStorageMock.store[key] || null),
  setItem: vi.fn((key, value) => {
    localStorageMock.store[key] = value.toString();
  }),
  removeItem: vi.fn((key) => {
    delete localStorageMock.store[key];
  }),
  clear: vi.fn(() => {
    localStorageMock.store = {};
  })
};
global.localStorage = localStorageMock;

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: vi.fn(),
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  // Keep error for debugging
  error: console.error
};

// ============================================================================
// DOM Setup
// ============================================================================

// Create basic DOM structure for tests
function setupDOM() {
  document.body.innerHTML = `
    <div id="app">
      <!-- File upload area -->
      <div id="dropzone"></div>
      <input type="file" id="file-input" />

      <!-- Language selectors -->
      <select id="source-lang">
        <option value="auto">Auto-detect</option>
        <option value="en">English</option>
        <option value="vi">Vietnamese</option>
        <option value="zh">Chinese</option>
      </select>
      <select id="target-lang">
        <option value="vi">Vietnamese</option>
        <option value="en">English</option>
      </select>

      <!-- Profile selector -->
      <div id="profiles-grid"></div>

      <!-- Settings -->
      <input type="checkbox" id="use-vision" />
      <div id="cost-mode-cards"></div>

      <!-- Progress area -->
      <div id="progress-area" class="hidden">
        <div id="progress-bar"></div>
        <div id="progress-percent">0%</div>
        <div id="current-task"></div>
      </div>

      <!-- Agent cards -->
      <div id="agent-1" class="agent-card">
        <div class="agent-status">idle</div>
        <div class="agent-progress"></div>
      </div>
      <div id="agent-2" class="agent-card">
        <div class="agent-status">idle</div>
        <div class="agent-progress"></div>
      </div>
      <div id="agent-3" class="agent-card">
        <div class="agent-status">idle</div>
        <div class="agent-progress"></div>
      </div>

      <!-- Results area -->
      <div id="downloads-grid" class="hidden"></div>
      <div id="dna-content" class="hidden"></div>

      <!-- Buttons -->
      <button id="start-btn" disabled>Start Publishing</button>

      <!-- Stats -->
      <div id="stat-time">--</div>
      <div id="stat-tokens">--</div>
      <div id="stat-cost">--</div>

      <!-- Toast container -->
      <div id="toast-container"></div>
    </div>
  `;
}

// ============================================================================
// Test Lifecycle
// ============================================================================

beforeEach(() => {
  // Reset DOM
  setupDOM();

  // Clear all mocks
  vi.clearAllMocks();

  // Reset localStorage
  localStorageMock.clear();
  localStorageMock.store = {};

  // Reset fetch mock
  global.fetch.mockReset();
});

afterEach(() => {
  // Cleanup
  vi.restoreAllMocks();
});

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Mock a successful fetch response
 */
global.mockFetchSuccess = (data, status = 200) => {
  global.fetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data))
  });
};

/**
 * Mock a fetch error
 */
global.mockFetchError = (error, status = 500) => {
  global.fetch.mockResolvedValueOnce({
    ok: false,
    status,
    json: () => Promise.resolve({ error: error.message || error }),
    text: () => Promise.resolve(error.message || error)
  });
};

/**
 * Create a mock File object
 */
global.createMockFile = (name, size, type) => {
  const content = new Array(size).fill('x').join('');
  return new File([content], name, { type });
};

/**
 * Wait for DOM updates
 */
global.waitForDOM = () => new Promise(resolve => setTimeout(resolve, 0));

/**
 * Simulate user input event
 */
global.simulateInput = (element, value) => {
  element.value = value;
  element.dispatchEvent(new Event('input', { bubbles: true }));
  element.dispatchEvent(new Event('change', { bubbles: true }));
};

// ============================================================================
// Export for ES modules
// ============================================================================

export {
  setupDOM,
  localStorageMock
};
