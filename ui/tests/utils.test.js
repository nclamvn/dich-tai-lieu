/**
 * Utility Functions Tests
 *
 * Tests for pure utility functions in main.js
 * These are the easiest to test as they have no DOM dependencies.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// ============================================================================
// Import functions to test (extracted from main.js for testability)
// In production, these would be imported from a separate utils.js file
// ============================================================================

// Utility functions extracted from PublisherApp

/**
 * Format file size to human readable string
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size (e.g., "1.5 MB")
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Format duration from seconds to human readable string
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration (e.g., "2m 30s")
 */
function formatDuration(seconds) {
  if (!seconds || seconds < 0) return '--';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

/**
 * Format large numbers with K/M suffix
 * @param {number} num - Number to format
 * @returns {string} Formatted number (e.g., "1.5K", "2.3M")
 */
function formatNumber(num) {
  if (!num || num < 0) return '0';
  if (num < 1000) return num.toString();
  if (num < 1000000) return `${(num / 1000).toFixed(1)}K`;
  return `${(num / 1000000).toFixed(1)}M`;
}

/**
 * Detect language from text using regex patterns
 * @param {string} text - Text to analyze
 * @returns {object} { language: string, confidence: number }
 */
function detectLanguageFromText(text) {
  if (!text || text.trim().length === 0) {
    return { language: 'auto', confidence: 0 };
  }

  // Count characters in different scripts
  const cjkPattern = /[\u4e00-\u9fff]/g;      // Chinese
  const hiragana = /[\u3040-\u309f]/g;        // Japanese Hiragana
  const katakana = /[\u30a0-\u30ff]/g;        // Japanese Katakana
  const hangul = /[\uac00-\ud7af]/g;          // Korean
  const cyrillic = /[\u0400-\u04ff]/g;        // Russian/Cyrillic
  const vietnamese = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/gi;
  const latinExtended = /[a-zA-Z]/g;

  const totalChars = text.length;
  const cjkCount = (text.match(cjkPattern) || []).length;
  const hiraganaCount = (text.match(hiragana) || []).length;
  const katakanaCount = (text.match(katakana) || []).length;
  const hangulCount = (text.match(hangul) || []).length;
  const cyrillicCount = (text.match(cyrillic) || []).length;
  const vietnameseCount = (text.match(vietnamese) || []).length;
  const latinCount = (text.match(latinExtended) || []).length;

  // Calculate percentages
  const cjkPercent = cjkCount / totalChars;
  const japanesePercent = (hiraganaCount + katakanaCount) / totalChars;
  const koreanPercent = hangulCount / totalChars;
  const cyrillicPercent = cyrillicCount / totalChars;
  const vietnamesePercent = vietnameseCount / totalChars;
  const latinPercent = latinCount / totalChars;

  // Detection thresholds
  if (japanesePercent > 0.1 || (hiraganaCount > 0 && katakanaCount > 0)) {
    return { language: 'ja', confidence: Math.min(0.95, japanesePercent * 3 + 0.5) };
  }

  if (koreanPercent > 0.1) {
    return { language: 'ko', confidence: Math.min(0.95, koreanPercent * 3 + 0.5) };
  }

  if (cjkPercent > 0.1) {
    return { language: 'zh', confidence: Math.min(0.95, cjkPercent * 2 + 0.3) };
  }

  if (cyrillicPercent > 0.2) {
    return { language: 'ru', confidence: Math.min(0.95, cyrillicPercent * 2 + 0.3) };
  }

  if (vietnamesePercent > 0.05) {
    return { language: 'vi', confidence: Math.min(0.95, vietnamesePercent * 5 + 0.4) };
  }

  if (latinPercent > 0.5) {
    // Default to English for Latin text
    return { language: 'en', confidence: 0.6 };
  }

  return { language: 'auto', confidence: 0 };
}

/**
 * Calculate cost estimate based on file size and cost mode
 * @param {number} fileSize - File size in bytes
 * @param {string} costMode - 'economy', 'balanced', or 'quality'
 * @returns {object} { estimatedCost: number, estimatedTime: string, pages: number }
 */
function calculateCostEstimate(fileSize, costMode) {
  // Estimate pages (average 2KB per page for text content)
  const estimatedPages = Math.max(1, Math.ceil(fileSize / 2048));

  // Cost per page by mode
  const costPerPage = {
    economy: 0.001,    // Gemini Flash
    balanced: 0.004,   // GPT-4o-mini
    quality: 0.05      // Claude Sonnet
  };

  // Time per page (seconds)
  const timePerPage = {
    economy: 3,
    balanced: 5,
    quality: 8
  };

  const cost = estimatedPages * (costPerPage[costMode] || costPerPage.balanced);
  const timeSeconds = estimatedPages * (timePerPage[costMode] || timePerPage.balanced);

  return {
    estimatedCost: Math.round(cost * 100) / 100,  // Round to 2 decimal places
    estimatedTime: formatDuration(timeSeconds),
    pages: estimatedPages
  };
}

/**
 * Validate file type for upload
 * @param {File} file - File object
 * @returns {object} { valid: boolean, error?: string, icon?: string }
 */
function validateFileType(file) {
  const allowedTypes = {
    'application/pdf': { icon: 'file-text', name: 'PDF' },
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { icon: 'file-text', name: 'DOCX' },
    'text/plain': { icon: 'file-text', name: 'TXT' },
    'text/markdown': { icon: 'file-code', name: 'MD' },
    'application/x-tex': { icon: 'file-code', name: 'TEX' }
  };

  // Check by MIME type
  if (allowedTypes[file.type]) {
    return { valid: true, icon: allowedTypes[file.type].icon };
  }

  // Check by extension as fallback
  const ext = file.name.split('.').pop().toLowerCase();
  const extensionMap = {
    pdf: { icon: 'file-text', name: 'PDF' },
    docx: { icon: 'file-text', name: 'DOCX' },
    txt: { icon: 'file-text', name: 'TXT' },
    md: { icon: 'file-code', name: 'MD' },
    tex: { icon: 'file-code', name: 'TEX' }
  };

  if (extensionMap[ext]) {
    return { valid: true, icon: extensionMap[ext].icon };
  }

  return {
    valid: false,
    error: `Unsupported file type: ${file.type || ext}. Supported: PDF, DOCX, TXT, MD, TEX`
  };
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ============================================================================
// Tests
// ============================================================================

describe('formatFileSize', () => {
  it('should return "0 B" for 0 bytes', () => {
    expect(formatFileSize(0)).toBe('0 B');
  });

  it('should format bytes correctly', () => {
    expect(formatFileSize(500)).toBe('500 B');
    expect(formatFileSize(1023)).toBe('1023 B');
  });

  it('should format kilobytes correctly', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(102400)).toBe('100.0 KB');
  });

  it('should format megabytes correctly', () => {
    expect(formatFileSize(1024 * 1024)).toBe('1.0 MB');
    expect(formatFileSize(1.5 * 1024 * 1024)).toBe('1.5 MB');
    expect(formatFileSize(10 * 1024 * 1024)).toBe('10.0 MB');
  });
});

describe('formatDuration', () => {
  it('should return "--" for invalid input', () => {
    expect(formatDuration(null)).toBe('--');
    expect(formatDuration(undefined)).toBe('--');
    expect(formatDuration(-1)).toBe('--');
    expect(formatDuration(0)).toBe('--');
  });

  it('should format seconds correctly', () => {
    expect(formatDuration(1)).toBe('1s');
    expect(formatDuration(30)).toBe('30s');
    expect(formatDuration(59)).toBe('59s');
  });

  it('should format minutes correctly', () => {
    expect(formatDuration(60)).toBe('1m');
    expect(formatDuration(90)).toBe('1m 30s');
    expect(formatDuration(120)).toBe('2m');
    expect(formatDuration(3599)).toBe('59m 59s');
  });

  it('should format hours correctly', () => {
    expect(formatDuration(3600)).toBe('1h');
    expect(formatDuration(3660)).toBe('1h 1m');
    expect(formatDuration(7200)).toBe('2h');
    expect(formatDuration(7380)).toBe('2h 3m');
  });
});

describe('formatNumber', () => {
  it('should return "0" for invalid input', () => {
    expect(formatNumber(null)).toBe('0');
    expect(formatNumber(undefined)).toBe('0');
    expect(formatNumber(-1)).toBe('0');
  });

  it('should format small numbers as-is', () => {
    expect(formatNumber(0)).toBe('0');
    expect(formatNumber(1)).toBe('1');
    expect(formatNumber(999)).toBe('999');
  });

  it('should format thousands with K suffix', () => {
    expect(formatNumber(1000)).toBe('1.0K');
    expect(formatNumber(1500)).toBe('1.5K');
    expect(formatNumber(10000)).toBe('10.0K');
    expect(formatNumber(999999)).toBe('1000.0K');
  });

  it('should format millions with M suffix', () => {
    expect(formatNumber(1000000)).toBe('1.0M');
    expect(formatNumber(2500000)).toBe('2.5M');
    expect(formatNumber(10000000)).toBe('10.0M');
  });
});

describe('detectLanguageFromText', () => {
  it('should return auto for empty text', () => {
    expect(detectLanguageFromText('')).toEqual({ language: 'auto', confidence: 0 });
    expect(detectLanguageFromText('   ')).toEqual({ language: 'auto', confidence: 0 });
    expect(detectLanguageFromText(null)).toEqual({ language: 'auto', confidence: 0 });
  });

  it('should detect English text', () => {
    const result = detectLanguageFromText('This is a sample English text for testing purposes.');
    expect(result.language).toBe('en');
    expect(result.confidence).toBeGreaterThan(0.5);
  });

  it('should detect Vietnamese text', () => {
    const result = detectLanguageFromText('Đây là một đoạn văn bản tiếng Việt để kiểm tra.');
    expect(result.language).toBe('vi');
    expect(result.confidence).toBeGreaterThan(0.5);
  });

  it('should detect Chinese text', () => {
    const result = detectLanguageFromText('这是一段中文文本，用于测试语言检测功能。');
    expect(result.language).toBe('zh');
    expect(result.confidence).toBeGreaterThan(0.5);
  });

  it('should detect Japanese text', () => {
    const result = detectLanguageFromText('これは日本語のテキストです。テストに使います。');
    expect(result.language).toBe('ja');
    expect(result.confidence).toBeGreaterThan(0.5);
  });

  it('should detect Korean text', () => {
    const result = detectLanguageFromText('이것은 한국어 텍스트입니다. 테스트용입니다.');
    expect(result.language).toBe('ko');
    expect(result.confidence).toBeGreaterThan(0.5);
  });

  it('should detect Russian text', () => {
    const result = detectLanguageFromText('Это русский текст для проверки обнаружения языка.');
    expect(result.language).toBe('ru');
    expect(result.confidence).toBeGreaterThan(0.5);
  });
});

describe('calculateCostEstimate', () => {
  it('should calculate minimum 1 page for small files', () => {
    const result = calculateCostEstimate(100, 'balanced');
    expect(result.pages).toBe(1);
  });

  it('should estimate pages based on file size', () => {
    // 10KB = ~5 pages (2KB per page)
    const result = calculateCostEstimate(10240, 'balanced');
    expect(result.pages).toBe(5);
  });

  it('should calculate cost for economy mode', () => {
    const result = calculateCostEstimate(20480, 'economy');  // 10 pages
    expect(result.pages).toBe(10);
    expect(result.estimatedCost).toBe(0.01);  // 10 * 0.001
  });

  it('should calculate cost for balanced mode', () => {
    const result = calculateCostEstimate(20480, 'balanced');  // 10 pages
    expect(result.pages).toBe(10);
    expect(result.estimatedCost).toBe(0.04);  // 10 * 0.004
  });

  it('should calculate cost for quality mode', () => {
    const result = calculateCostEstimate(20480, 'quality');  // 10 pages
    expect(result.pages).toBe(10);
    expect(result.estimatedCost).toBe(0.5);  // 10 * 0.05
  });

  it('should estimate time based on mode', () => {
    const economyResult = calculateCostEstimate(4096, 'economy');    // 2 pages
    const qualityResult = calculateCostEstimate(4096, 'quality');    // 2 pages

    // Economy: 2 pages * 3s = 6s
    expect(economyResult.estimatedTime).toBe('6s');

    // Quality: 2 pages * 8s = 16s
    expect(qualityResult.estimatedTime).toBe('16s');
  });
});

describe('validateFileType', () => {
  it('should accept PDF files', () => {
    const file = { name: 'test.pdf', type: 'application/pdf' };
    const result = validateFileType(file);
    expect(result.valid).toBe(true);
    expect(result.icon).toBe('file-text');
  });

  it('should accept DOCX files', () => {
    const file = {
      name: 'test.docx',
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    };
    const result = validateFileType(file);
    expect(result.valid).toBe(true);
  });

  it('should accept TXT files', () => {
    const file = { name: 'test.txt', type: 'text/plain' };
    const result = validateFileType(file);
    expect(result.valid).toBe(true);
  });

  it('should accept files by extension when MIME type is missing', () => {
    const file = { name: 'test.md', type: '' };
    const result = validateFileType(file);
    expect(result.valid).toBe(true);
    expect(result.icon).toBe('file-code');
  });

  it('should reject unsupported file types', () => {
    const file = { name: 'test.exe', type: 'application/x-msdownload' };
    const result = validateFileType(file);
    expect(result.valid).toBe(false);
    expect(result.error).toContain('Unsupported file type');
  });

  it('should reject image files', () => {
    const file = { name: 'test.jpg', type: 'image/jpeg' };
    const result = validateFileType(file);
    expect(result.valid).toBe(false);
  });
});

describe('escapeHtml', () => {
  it('should return empty string for falsy input', () => {
    expect(escapeHtml('')).toBe('');
    expect(escapeHtml(null)).toBe('');
    expect(escapeHtml(undefined)).toBe('');
  });

  it('should escape HTML special characters', () => {
    expect(escapeHtml('<script>alert("xss")</script>')).toBe(
      '&lt;script&gt;alert("xss")&lt;/script&gt;'
    );
  });

  it('should escape ampersands', () => {
    expect(escapeHtml('Tom & Jerry')).toBe('Tom &amp; Jerry');
  });

  it('should escape quotes', () => {
    expect(escapeHtml('Say "Hello"')).toBe('Say "Hello"');
  });

  it('should handle plain text without changes', () => {
    expect(escapeHtml('Hello World')).toBe('Hello World');
  });
});
