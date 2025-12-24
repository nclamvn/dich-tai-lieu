/**
 * Simple Authentication System for AI Translator Pro
 *
 * SECURITY FEATURES:
 * - Credentials stored as SHA-256 hash (never plain text)
 * - Session stored in localStorage with expiry
 * - Brute force protection (5 attempts, 15 min lockout)
 * - HTTPS enforcement in production
 * - For production, consider Firebase Auth, Auth0, or Supabase
 */

// ========== SECURITY: Force HTTPS in production ==========
(function enforceHTTPS() {
  if (location.protocol !== 'https:' &&
      location.hostname !== 'localhost' &&
      location.hostname !== '127.0.0.1') {
    location.replace('https:' + location.href.substring(location.protocol.length));
  }
})();

const AUTH_CONFIG = {
  // Email for login
  VALID_EMAIL: 'nclamvn@gmail.com',

  // SHA-256 hash of password
  // Generate new hash at: /auth/generate-hash.html
  PASSWORD_HASH: '26fbe741c08222597eba163228603d34bdda63bd06a35ca0a382794cd6afa4f9',

  // Session settings
  SESSION_KEY: 'prismy_auth_session',
  SESSION_DURATION: 24 * 60 * 60 * 1000, // 24 hours

  // Brute force protection
  MAX_LOGIN_ATTEMPTS: 5,
  LOCKOUT_DURATION: 15 * 60 * 1000, // 15 minutes
  ATTEMPTS_KEY: 'prismy_login_attempts',
};

/**
 * Hash password using SHA-256
 */
async function hashPassword(password) {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
  const session = localStorage.getItem(AUTH_CONFIG.SESSION_KEY);
  if (!session) return false;

  try {
    const { expiry, email } = JSON.parse(session);
    if (Date.now() > expiry) {
      localStorage.removeItem(AUTH_CONFIG.SESSION_KEY);
      return false;
    }
    return email === AUTH_CONFIG.VALID_EMAIL;
  } catch {
    return false;
  }
}

/**
 * Get current user email
 */
function getCurrentUser() {
  if (!isAuthenticated()) return null;
  const session = JSON.parse(localStorage.getItem(AUTH_CONFIG.SESSION_KEY));
  return session?.email || null;
}

/**
 * Check if account is locked due to too many failed attempts
 */
function isAccountLocked() {
  const attemptsData = localStorage.getItem(AUTH_CONFIG.ATTEMPTS_KEY);
  if (!attemptsData) return { locked: false, remainingTime: 0 };

  try {
    const { count, lockUntil } = JSON.parse(attemptsData);
    if (lockUntil && Date.now() < lockUntil) {
      const remainingTime = Math.ceil((lockUntil - Date.now()) / 1000 / 60);
      return { locked: true, remainingTime };
    }
    // Lockout expired, reset attempts
    if (lockUntil && Date.now() >= lockUntil) {
      localStorage.removeItem(AUTH_CONFIG.ATTEMPTS_KEY);
    }
    return { locked: false, remainingTime: 0 };
  } catch {
    return { locked: false, remainingTime: 0 };
  }
}

/**
 * Record failed login attempt
 */
function recordFailedAttempt() {
  const attemptsData = localStorage.getItem(AUTH_CONFIG.ATTEMPTS_KEY);
  let attempts = { count: 0, lockUntil: null };

  if (attemptsData) {
    try {
      attempts = JSON.parse(attemptsData);
    } catch {
      attempts = { count: 0, lockUntil: null };
    }
  }

  attempts.count += 1;
  attempts.lastAttempt = Date.now();

  // Lock account if max attempts exceeded
  if (attempts.count >= AUTH_CONFIG.MAX_LOGIN_ATTEMPTS) {
    attempts.lockUntil = Date.now() + AUTH_CONFIG.LOCKOUT_DURATION;
  }

  localStorage.setItem(AUTH_CONFIG.ATTEMPTS_KEY, JSON.stringify(attempts));
  return AUTH_CONFIG.MAX_LOGIN_ATTEMPTS - attempts.count;
}

/**
 * Clear failed attempts on successful login
 */
function clearFailedAttempts() {
  localStorage.removeItem(AUTH_CONFIG.ATTEMPTS_KEY);
}

/**
 * Attempt login with brute force protection
 */
async function login(email, password) {
  // Check if account is locked
  const lockStatus = isAccountLocked();
  if (lockStatus.locked) {
    return {
      success: false,
      error: `Tài khoản bị khóa. Vui lòng thử lại sau ${lockStatus.remainingTime} phút.`,
      locked: true
    };
  }

  // Validate email
  if (email.toLowerCase() !== AUTH_CONFIG.VALID_EMAIL.toLowerCase()) {
    const remaining = recordFailedAttempt();
    if (remaining <= 0) {
      return {
        success: false,
        error: `Tài khoản bị khóa trong 15 phút do đăng nhập sai nhiều lần.`,
        locked: true
      };
    }
    return {
      success: false,
      error: `Email không đúng. Còn ${remaining} lần thử.`
    };
  }

  // Validate password hash
  const hashedInput = await hashPassword(password);
  if (hashedInput !== AUTH_CONFIG.PASSWORD_HASH) {
    const remaining = recordFailedAttempt();
    if (remaining <= 0) {
      return {
        success: false,
        error: `Tài khoản bị khóa trong 15 phút do đăng nhập sai nhiều lần.`,
        locked: true
      };
    }
    return {
      success: false,
      error: `Mật khẩu không đúng. Còn ${remaining} lần thử.`
    };
  }

  // Clear failed attempts on successful login
  clearFailedAttempts();

  // Create session
  const session = {
    email: email.toLowerCase(),
    expiry: Date.now() + AUTH_CONFIG.SESSION_DURATION,
    createdAt: Date.now(),
  };
  localStorage.setItem(AUTH_CONFIG.SESSION_KEY, JSON.stringify(session));

  return { success: true };
}

/**
 * Logout - clear session and redirect
 */
function logout() {
  localStorage.removeItem(AUTH_CONFIG.SESSION_KEY);
  window.location.href = '/landing/index.html';
}

/**
 * Protect page - redirect if not authenticated
 */
function requireAuth(redirectUrl = '/?login=required') {
  if (!isAuthenticated()) {
    window.location.href = redirectUrl;
    return false;
  }
  return true;
}

/**
 * Extend session if active
 */
function extendSession() {
  if (isAuthenticated()) {
    const session = JSON.parse(localStorage.getItem(AUTH_CONFIG.SESSION_KEY));
    session.expiry = Date.now() + AUTH_CONFIG.SESSION_DURATION;
    localStorage.setItem(AUTH_CONFIG.SESSION_KEY, JSON.stringify(session));
  }
}

// Export for global use
window.PrismyAuth = {
  isAuthenticated,
  getCurrentUser,
  login,
  logout,
  requireAuth,
  extendSession,
  hashPassword,
  isAccountLocked,
};

// Auto-extend session on activity
document.addEventListener('click', () => {
  if (isAuthenticated()) {
    extendSession();
  }
});
