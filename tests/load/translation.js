/**
 * k6 Translation Flow Load Test
 * Tests the complete translation workflow under load
 *
 * Run: k6 run tests/load/translation.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { FormData } from 'https://jslib.k6.io/formdata/0.0.2/index.js';
import config from './k6.config.js';

// Custom metrics
const errorRate = new Rate('errors');
const jobsCreated = new Counter('jobs_created');
const jobsCompleted = new Counter('jobs_completed');
const jobsFailed = new Counter('jobs_failed');
const translationDuration = new Trend('translation_duration');
const uploadDuration = new Trend('upload_duration');

// Test options - use lighter load for translation tests
export const options = {
  stages: [
    { duration: '1m', target: 5 },   // Ramp up to 5 users
    { duration: '3m', target: 5 },   // Stay at 5 users
    { duration: '1m', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],  // Allow 5% error rate for heavy operations
    'http_req_duration{type:upload}': ['p(95)<5000'],  // 5s for uploads
    errors: ['rate<0.1'],  // Overall error rate
  },
};

const BASE_URL = config.baseUrl;

// Sample text content for testing
const SAMPLE_TEXTS = [
  'Hello World. This is a simple test document.',
  'The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet.',
  'Artificial Intelligence is transforming the way we work and live. Machine learning algorithms can now process natural language with remarkable accuracy.',
  `Chapter 1: Introduction

Natural language processing (NLP) is a field of artificial intelligence that focuses on the interaction between computers and human language. This document explores the fundamental concepts of NLP and its applications in modern software systems.

Chapter 2: Background

The history of NLP dates back to the 1950s when researchers first attempted to develop machine translation systems. Since then, the field has evolved significantly with the advent of deep learning and transformer architectures.`,
];

/**
 * Setup
 */
export function setup() {
  const res = http.get(`${BASE_URL}/health`);
  if (res.status !== 200) {
    throw new Error('Server not available');
  }
  return {
    startTime: new Date().toISOString(),
    testContent: SAMPLE_TEXTS[Math.floor(Math.random() * SAMPLE_TEXTS.length)],
  };
}

/**
 * Main test function
 */
export default function(data) {
  group('Translation Flow', function() {
    // Step 1: Upload file and start translation
    const jobId = startTranslation(data.testContent);

    if (jobId) {
      jobsCreated.add(1);

      // Step 2: Poll for status
      const completed = pollJobStatus(jobId);

      if (completed) {
        jobsCompleted.add(1);
      } else {
        jobsFailed.add(1);
      }
    }
  });

  // Wait before next iteration
  sleep(Math.random() * 3 + 2);
}

/**
 * Start a translation job
 */
function startTranslation(content) {
  // Create form data with file
  const fd = new FormData();

  // Create a blob-like structure for the file
  const fileData = {
    data: content,
    filename: `test-${Date.now()}.txt`,
    content_type: 'text/plain',
  };

  fd.append('file', http.file(fileData.data, fileData.filename, fileData.content_type));
  fd.append('profile', 'novel');  // Default profile
  fd.append('ai_provider', 'claude');

  const startTime = Date.now();

  const res = http.post(`${BASE_URL}/translate`, fd.body(), {
    headers: { 'Content-Type': `multipart/form-data; boundary=${fd.boundary}` },
    tags: { name: 'translate', type: 'upload' },
    timeout: '30s',
  });

  uploadDuration.add(Date.now() - startTime);

  const passed = check(res, {
    'upload status is 200': (r) => r.status === 200,
    'upload returns job_id': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data.job_id !== undefined;
      } catch {
        return false;
      }
    },
  });

  if (!passed) {
    errorRate.add(1);
    console.log(`Upload failed: ${res.status} - ${res.body}`);
    return null;
  }

  try {
    const data = JSON.parse(res.body);
    return data.job_id;
  } catch {
    return null;
  }
}

/**
 * Poll job status until completion or timeout
 */
function pollJobStatus(jobId, maxAttempts = 60, intervalMs = 2000) {
  const startTime = Date.now();

  for (let i = 0; i < maxAttempts; i++) {
    sleep(intervalMs / 1000);

    const res = http.get(`${BASE_URL}/jobs/${jobId}`, {
      tags: { name: 'job_status', type: 'api' },
    });

    if (res.status !== 200) {
      continue;
    }

    try {
      const data = JSON.parse(res.body);

      if (data.status === 'completed') {
        translationDuration.add(Date.now() - startTime);
        return true;
      }

      if (data.status === 'failed' || data.status === 'error') {
        console.log(`Job ${jobId} failed: ${data.error || 'Unknown error'}`);
        errorRate.add(1);
        return false;
      }

      // Still processing, continue polling
    } catch (e) {
      console.log(`Error parsing status: ${e}`);
    }
  }

  // Timeout
  console.log(`Job ${jobId} timed out after ${maxAttempts} attempts`);
  errorRate.add(1);
  return false;
}

/**
 * Teardown
 */
export function teardown(data) {
  console.log('='.repeat(50));
  console.log('Translation Load Test Summary');
  console.log('='.repeat(50));
  console.log(`Started: ${data.startTime}`);
  console.log(`Ended: ${new Date().toISOString()}`);
}
