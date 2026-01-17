/**
 * E2E Tests: WebSocket Connection
 * Tests real-time updates via WebSocket
 */

import { test, expect } from '@playwright/test';
import { waitForAppReady, waitForWebSocket, isWebSocketConnected } from './helpers.js';

test.describe('WebSocket Connection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should initialize WebSocket client', async ({ page }) => {
    // Check WebSocketClient is defined
    const hasClient = await page.evaluate(() => {
      return typeof WebSocketClient !== 'undefined';
    });

    expect(hasClient).toBeTruthy();
  });

  test('should attempt WebSocket connection on load', async ({ page }) => {
    // Wait for connection attempt
    await page.waitForTimeout(2000);

    // Check connection state (may be connected or attempting)
    const state = await page.evaluate(() => {
      if (typeof WebSocketClient === 'undefined') return 'undefined';
      return WebSocketClient.state.isConnected ? 'connected' : 'attempting';
    });

    expect(['connected', 'attempting']).toContain(state);
  });

  test('should have reconnection capability', async ({ page }) => {
    const hasReconnect = await page.evaluate(() => {
      return typeof WebSocketClient !== 'undefined' &&
             typeof WebSocketClient.reconnect === 'function';
    });

    expect(hasReconnect).toBeTruthy();
  });

  test('should have event handler registration', async ({ page }) => {
    const hasEventHandlers = await page.evaluate(() => {
      return typeof WebSocketClient !== 'undefined' &&
             typeof WebSocketClient.on === 'function' &&
             typeof WebSocketClient.off === 'function';
    });

    expect(hasEventHandlers).toBeTruthy();
  });

  test('should support job subscription', async ({ page }) => {
    const hasSubscription = await page.evaluate(() => {
      return typeof WebSocketClient !== 'undefined' &&
             typeof WebSocketClient.subscribeToJob === 'function' &&
             typeof WebSocketClient.unsubscribeFromJob === 'function';
    });

    expect(hasSubscription).toBeTruthy();
  });

  test('should have heartbeat configuration', async ({ page }) => {
    const config = await page.evaluate(() => {
      if (typeof WebSocketClient === 'undefined') return null;
      return WebSocketClient.config;
    });

    expect(config).toBeTruthy();
    expect(config.heartbeatInterval).toBeDefined();
    expect(config.reconnectInterval).toBeDefined();
    expect(config.maxReconnectAttempts).toBeDefined();
  });
});

test.describe('WebSocket Fallback', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should have polling fallback capability', async ({ page }) => {
    const hasFallback = await page.evaluate(() => {
      return typeof WebSocketClient !== 'undefined' &&
             typeof WebSocketClient.isUsingPolling === 'function';
    });

    expect(hasFallback).toBeTruthy();
  });

  test('should track fallback state', async ({ page }) => {
    const fallbackState = await page.evaluate(() => {
      if (typeof WebSocketClient === 'undefined') return null;
      return WebSocketClient.state.fallbackToPolling;
    });

    // Initially should not be in fallback mode
    expect(fallbackState).toBe(false);
  });
});

test.describe('WebSocket Message Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should have message handlers map', async ({ page }) => {
    const hasHandlers = await page.evaluate(() => {
      return typeof WebSocketClient !== 'undefined' &&
             WebSocketClient.state.messageHandlers instanceof Map;
    });

    expect(hasHandlers).toBeTruthy();
  });

  test('should register and unregister handlers', async ({ page }) => {
    const result = await page.evaluate(() => {
      if (typeof WebSocketClient === 'undefined') return null;

      let received = false;

      // Register handler
      const unsubscribe = WebSocketClient.on('test_event', (data) => {
        received = true;
      });

      // Check handler is registered
      const handlerCount = WebSocketClient.state.messageHandlers.get('test_event')?.length || 0;

      // Unsubscribe
      unsubscribe();

      // Check handler is removed
      const afterCount = WebSocketClient.state.messageHandlers.get('test_event')?.length || 0;

      return { handlerCount, afterCount };
    });

    expect(result.handlerCount).toBe(1);
    expect(result.afterCount).toBe(0);
  });

  test('should dispatch events to handlers', async ({ page }) => {
    const result = await page.evaluate(() => {
      if (typeof WebSocketClient === 'undefined') return null;

      let receivedData = null;

      // Register handler
      WebSocketClient.on('test_dispatch', (data) => {
        receivedData = data;
      });

      // Dispatch event
      WebSocketClient.dispatchEvent('test_dispatch', { test: 'value' });

      return receivedData;
    });

    expect(result).toEqual({ test: 'value' });
  });
});

test.describe('WebSocket with Job Updates', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ui');
    await waitForAppReady(page);
  });

  test('should track current job ID', async ({ page }) => {
    const result = await page.evaluate(() => {
      if (typeof WebSocketClient === 'undefined') return null;

      // Subscribe to job
      WebSocketClient.subscribeToJob('test-job-123');

      const jobId = WebSocketClient.state.currentJobId;

      // Unsubscribe
      WebSocketClient.unsubscribeFromJob();

      const afterJobId = WebSocketClient.state.currentJobId;

      return { jobId, afterJobId };
    });

    expect(result.jobId).toBe('test-job-123');
    expect(result.afterJobId).toBe(null);
  });

  test('should handle job progress events', async ({ page }) => {
    const result = await page.evaluate(() => {
      if (typeof WebSocketClient === 'undefined') return null;

      let progressData = null;

      WebSocketClient.on('job_progress', (data) => {
        progressData = data;
      });

      // Simulate receiving job progress
      WebSocketClient.dispatchEvent('job_progress', {
        event: 'job_progress',
        job_id: 'test-123',
        progress: 50
      });

      return progressData;
    });

    expect(result.progress).toBe(50);
    expect(result.job_id).toBe('test-123');
  });

  test('should handle job completion events', async ({ page }) => {
    const result = await page.evaluate(() => {
      if (typeof WebSocketClient === 'undefined') return null;

      let completedData = null;

      WebSocketClient.on('job_completed', (data) => {
        completedData = data;
      });

      // Simulate job completion
      WebSocketClient.dispatchEvent('job_completed', {
        event: 'job_completed',
        job_id: 'test-123',
        outputs: { docx: '/output.docx' }
      });

      return completedData;
    });

    expect(result.event).toBe('job_completed');
    expect(result.outputs).toBeDefined();
  });

  test('should handle job failure events', async ({ page }) => {
    const result = await page.evaluate(() => {
      if (typeof WebSocketClient === 'undefined') return null;

      let failedData = null;

      WebSocketClient.on('job_failed', (data) => {
        failedData = data;
      });

      // Simulate job failure
      WebSocketClient.dispatchEvent('job_failed', {
        event: 'job_failed',
        job_id: 'test-123',
        error: 'Translation failed'
      });

      return failedData;
    });

    expect(result.event).toBe('job_failed');
    expect(result.error).toBe('Translation failed');
  });
});
