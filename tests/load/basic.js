/**
 * k6 Basic Load Test
 * Tests fundamental API endpoints under load
 *
 * Run: k6 run tests/load/basic.js
 * With environment: k6 run -e BASE_URL=http://localhost:3001 tests/load/basic.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import config from './k6.config.js';

// Custom metrics
const errorRate = new Rate('errors');
const healthCheckDuration = new Trend('health_check_duration');
const apiDuration = new Trend('api_duration');

// Test options
export const options = {
  stages: config.stages.load,
  thresholds: config.thresholds,
  tags: config.tags,
};

const BASE_URL = config.baseUrl;

/**
 * Setup - runs once before tests
 */
export function setup() {
  // Verify server is running
  const res = http.get(`${BASE_URL}/health`);
  if (res.status !== 200) {
    throw new Error(`Server not available: ${res.status}`);
  }
  console.log('Server is ready for load testing');

  return { startTime: new Date().toISOString() };
}

/**
 * Main test function - runs for each virtual user
 */
export default function(data) {
  // Test 1: Health Check
  testHealthCheck();

  // Test 2: Load UI page
  testUIPage();

  // Test 3: API endpoints
  testAPIEndpoints();

  // Random think time between requests
  sleep(Math.random() * 2 + 1);
}

/**
 * Test health check endpoint
 */
function testHealthCheck() {
  const res = http.get(`${BASE_URL}/health`, {
    tags: { name: 'health', type: 'api' },
  });

  healthCheckDuration.add(res.timings.duration);

  const passed = check(res, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 100ms': (r) => r.timings.duration < 100,
    'health check returns valid JSON': (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch {
        return false;
      }
    },
  });

  errorRate.add(!passed);
}

/**
 * Test UI page load
 */
function testUIPage() {
  const res = http.get(`${BASE_URL}/ui`, {
    tags: { name: 'ui', type: 'page' },
  });

  const passed = check(res, {
    'UI page status is 200': (r) => r.status === 200,
    'UI page contains expected content': (r) => r.body.includes('Xưởng Xuất Bản'),
    'UI page response time < 500ms': (r) => r.timings.duration < 500,
  });

  errorRate.add(!passed);
}

/**
 * Test API endpoints
 */
function testAPIEndpoints() {
  // Test API docs
  const docsRes = http.get(`${BASE_URL}/docs`, {
    tags: { name: 'docs', type: 'page' },
  });

  check(docsRes, {
    'API docs accessible': (r) => r.status === 200,
  });

  // Test profiles endpoint
  const profilesRes = http.get(`${BASE_URL}/profiles`, {
    tags: { name: 'profiles', type: 'api' },
  });

  apiDuration.add(profilesRes.timings.duration);

  const passed = check(profilesRes, {
    'profiles endpoint status is 200': (r) => r.status === 200,
    'profiles returns array': (r) => {
      try {
        const data = JSON.parse(r.body);
        return Array.isArray(data);
      } catch {
        return false;
      }
    },
    'profiles response time < 200ms': (r) => r.timings.duration < 200,
  });

  errorRate.add(!passed);
}

/**
 * Teardown - runs once after tests
 */
export function teardown(data) {
  console.log(`Load test completed. Started at: ${data.startTime}`);
}
