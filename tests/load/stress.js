/**
 * k6 Stress Test
 * Finds the breaking point of the system
 *
 * Run: k6 run tests/load/stress.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import config from './k6.config.js';

// Custom metrics
const errorRate = new Rate('errors');
const requestDuration = new Trend('request_duration');
const successfulRequests = new Counter('successful_requests');
const failedRequests = new Counter('failed_requests');

// Stress test stages - gradually increase load
export const options = {
  stages: config.stages.stress,
  thresholds: {
    http_req_failed: ['rate<0.1'],  // Allow up to 10% errors during stress
    http_req_duration: ['p(90)<3000'],  // 90% under 3 seconds
    errors: ['rate<0.15'],  // Overall error rate
  },
};

const BASE_URL = config.baseUrl;

// API endpoints to stress test
const ENDPOINTS = [
  { path: '/health', weight: 3, name: 'health' },
  { path: '/ui', weight: 2, name: 'ui' },
  { path: '/docs', weight: 1, name: 'docs' },
  { path: '/profiles', weight: 2, name: 'profiles' },
];

/**
 * Setup
 */
export function setup() {
  const res = http.get(`${BASE_URL}/health`);
  if (res.status !== 200) {
    throw new Error('Server not available for stress testing');
  }

  console.log('Starting stress test...');
  console.log(`Target URL: ${BASE_URL}`);

  return {
    startTime: Date.now(),
  };
}

/**
 * Main test function
 */
export default function(data) {
  // Select random endpoint based on weight
  const endpoint = selectEndpoint();

  const startTime = Date.now();
  const res = http.get(`${BASE_URL}${endpoint.path}`, {
    tags: { name: endpoint.name, type: 'stress' },
    timeout: '10s',
  });

  const duration = Date.now() - startTime;
  requestDuration.add(duration);

  const passed = check(res, {
    [`${endpoint.name} returns success`]: (r) => r.status >= 200 && r.status < 400,
    [`${endpoint.name} response time acceptable`]: (r) => r.timings.duration < 5000,
  });

  if (passed) {
    successfulRequests.add(1);
  } else {
    failedRequests.add(1);
    errorRate.add(1);

    // Log failures for debugging
    if (res.status >= 500) {
      console.log(`Server error on ${endpoint.path}: ${res.status}`);
    }
  }

  // Variable think time based on current stage
  const thinkTime = Math.random() * 0.5 + 0.1;
  sleep(thinkTime);
}

/**
 * Select endpoint based on weight
 */
function selectEndpoint() {
  const totalWeight = ENDPOINTS.reduce((sum, e) => sum + e.weight, 0);
  let random = Math.random() * totalWeight;

  for (const endpoint of ENDPOINTS) {
    random -= endpoint.weight;
    if (random <= 0) {
      return endpoint;
    }
  }

  return ENDPOINTS[0];
}

/**
 * Teardown
 */
export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;

  console.log('='.repeat(50));
  console.log('Stress Test Complete');
  console.log('='.repeat(50));
  console.log(`Total Duration: ${duration.toFixed(2)}s`);
}
