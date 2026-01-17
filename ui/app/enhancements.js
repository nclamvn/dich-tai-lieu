/**
 * AI Publisher Pro - UI Enhancements
 * Phase 1: Accessibility, Loading, Error Handling
 * Phase 2: Dark Mode, Keyboard Shortcuts, Offline Support
 */

const UIEnhancements = {
    // ============================================
    // INITIALIZATION
    // ============================================
    init() {
        this.initTheme();
        this.initKeyboardShortcuts();
        this.initOfflineDetection();
        this.initAccessibility();
        this.initErrorBoundary();
        console.log('[UI Enhancements] Initialized');
    },

    // ============================================
    // PHASE 2: DARK MODE
    // ============================================
    initTheme() {
        // Check saved preference or system preference
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        } else if (systemPrefersDark) {
            // Don't set attribute, let CSS handle system preference
        }

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                // Only auto-switch if user hasn't set a preference
                this.updateThemeUI();
            }
        });

        // Setup toggle button if exists
        this.setupThemeToggle();
    },

    setupThemeToggle() {
        const toggleBtn = document.getElementById('theme-toggle');
        if (!toggleBtn) return;

        toggleBtn.addEventListener('click', () => this.toggleTheme());
    },

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        let newTheme;
        if (currentTheme === 'dark') {
            newTheme = 'light';
        } else if (currentTheme === 'light') {
            newTheme = 'dark';
        } else {
            // No explicit theme set, toggle from system preference
            newTheme = systemPrefersDark ? 'light' : 'dark';
        }

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        this.updateThemeUI();

        // Announce to screen readers
        this.announce(`Theme changed to ${newTheme} mode`);
    },

    updateThemeUI() {
        const theme = document.documentElement.getAttribute('data-theme') ||
                      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

        // Update toggle button icons
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            const sunIcon = toggleBtn.querySelector('.icon-sun');
            const moonIcon = toggleBtn.querySelector('.icon-moon');
            if (sunIcon && moonIcon) {
                sunIcon.style.display = theme === 'dark' ? 'block' : 'none';
                moonIcon.style.display = theme === 'light' ? 'block' : 'none';
            }
        }
    },

    // ============================================
    // PHASE 2: KEYBOARD SHORTCUTS
    // ============================================
    shortcuts: {
        'ctrl+enter': { action: 'startPublishing', description: 'Start Publishing' },
        'ctrl+o': { action: 'openFile', description: 'Open File' },
        'ctrl+s': { action: 'saveEdit', description: 'Save Edit' },
        'ctrl+z': { action: 'undo', description: 'Undo' },
        'ctrl+shift+z': { action: 'redo', description: 'Redo' },
        'ctrl+d': { action: 'toggleTheme', description: 'Toggle Dark Mode' },
        'escape': { action: 'closeModal', description: 'Close Modal' },
        '?': { action: 'showShortcuts', description: 'Show Shortcuts' },
    },

    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger shortcuts when typing in inputs
            if (e.target.matches('input, textarea, [contenteditable]')) {
                // Allow Ctrl+S in editor
                if (!(e.ctrlKey && e.key === 's')) return;
            }

            const key = this.getShortcutKey(e);
            const shortcut = this.shortcuts[key];

            if (shortcut) {
                e.preventDefault();
                this.executeShortcut(shortcut.action);
            }
        });
    },

    getShortcutKey(e) {
        const parts = [];
        if (e.ctrlKey || e.metaKey) parts.push('ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');
        parts.push(e.key.toLowerCase());
        return parts.join('+');
    },

    executeShortcut(action) {
        switch (action) {
            case 'startPublishing':
                const startBtn = document.getElementById('btn-start');
                if (startBtn && !startBtn.disabled) startBtn.click();
                break;
            case 'openFile':
                const fileInput = document.getElementById('file-input');
                if (fileInput) fileInput.click();
                break;
            case 'saveEdit':
                // Trigger save in editor if open
                if (window.Editor && window.Editor.currentJobId) {
                    this.showToast('Saving...', 'info');
                }
                break;
            case 'undo':
                if (window.EditorHistory) window.EditorHistory.undo();
                break;
            case 'redo':
                if (window.EditorHistory) window.EditorHistory.redo();
                break;
            case 'toggleTheme':
                this.toggleTheme();
                break;
            case 'closeModal':
                this.closeAllModals();
                break;
            case 'showShortcuts':
                this.showShortcutsPanel();
                break;
        }
    },

    showShortcutsPanel() {
        // Check if panel already exists
        let panel = document.getElementById('shortcuts-help');
        if (panel) {
            panel.classList.toggle('visible');
            return;
        }

        // Create shortcuts panel
        panel = document.createElement('div');
        panel.id = 'shortcuts-help';
        panel.className = 'shortcuts-help';
        panel.innerHTML = `
            <div class="shortcuts-panel" role="dialog" aria-labelledby="shortcuts-title">
                <div class="shortcuts-header">
                    <h2 id="shortcuts-title">Keyboard Shortcuts</h2>
                    <button class="shortcuts-close" aria-label="Close">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="shortcuts-list">
                    ${Object.entries(this.shortcuts).map(([key, { description }]) => `
                        <div class="shortcut-item">
                            <span class="shortcut-label">${description}</span>
                            <div class="shortcut-keys">
                                ${key.split('+').map(k => `<kbd class="kbd">${this.formatKey(k)}</kbd>`).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        document.body.appendChild(panel);

        // Show with animation
        requestAnimationFrame(() => panel.classList.add('visible'));

        // Close handlers
        panel.querySelector('.shortcuts-close').addEventListener('click', () => {
            panel.classList.remove('visible');
        });
        panel.addEventListener('click', (e) => {
            if (e.target === panel) panel.classList.remove('visible');
        });
    },

    formatKey(key) {
        const keyMap = {
            'ctrl': navigator.platform.includes('Mac') ? '⌘' : 'Ctrl',
            'shift': '⇧',
            'alt': navigator.platform.includes('Mac') ? '⌥' : 'Alt',
            'enter': '↵',
            'escape': 'Esc',
        };
        return keyMap[key] || key.toUpperCase();
    },

    closeAllModals() {
        // Close shortcuts panel
        const shortcutsPanel = document.getElementById('shortcuts-help');
        if (shortcutsPanel) shortcutsPanel.classList.remove('visible');

        // Close editor overlay
        if (window.Editor) window.Editor.close();

        // Close any open dropdowns
        document.querySelectorAll('.profile-dropdown:not(.hidden), .provider-dropdown:not([style*="none"])').forEach(el => {
            el.classList.add('hidden');
        });
    },

    // ============================================
    // PHASE 2: OFFLINE DETECTION
    // ============================================
    initOfflineDetection() {
        // Create indicators
        this.createOfflineIndicator();
        this.createOnlineIndicator();

        // Initial check
        this.updateOnlineStatus();

        // Listen for changes
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
    },

    createOfflineIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'offline-indicator';
        indicator.className = 'offline-indicator';
        indicator.setAttribute('role', 'status');
        indicator.setAttribute('aria-live', 'polite');
        indicator.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="1" y1="1" x2="23" y2="23"></line>
                <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"></path>
                <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"></path>
                <path d="M10.71 5.05A16 16 0 0 1 22.58 9"></path>
                <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"></path>
                <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
                <line x1="12" y1="20" x2="12.01" y2="20"></line>
            </svg>
            <span>You're offline. Some features may be unavailable.</span>
        `;
        document.body.appendChild(indicator);
    },

    createOnlineIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'online-indicator';
        indicator.className = 'online-indicator';
        indicator.setAttribute('role', 'status');
        indicator.setAttribute('aria-live', 'polite');
        indicator.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12.55a11 11 0 0 1 14.08 0"></path>
                <path d="M1.42 9a16 16 0 0 1 21.16 0"></path>
                <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
                <line x1="12" y1="20" x2="12.01" y2="20"></line>
            </svg>
            <span>Connection restored!</span>
        `;
        document.body.appendChild(indicator);
    },

    updateOnlineStatus() {
        if (!navigator.onLine) {
            this.handleOffline();
        }
    },

    handleOffline() {
        const indicator = document.getElementById('offline-indicator');
        if (indicator) {
            indicator.classList.add('visible');
        }
        this.announce('You are now offline. Some features may be unavailable.');
    },

    handleOnline() {
        // Hide offline indicator
        const offlineIndicator = document.getElementById('offline-indicator');
        if (offlineIndicator) {
            offlineIndicator.classList.remove('visible');
        }

        // Show online indicator briefly
        const onlineIndicator = document.getElementById('online-indicator');
        if (onlineIndicator) {
            onlineIndicator.classList.add('visible');
            setTimeout(() => {
                onlineIndicator.classList.remove('visible');
            }, 3000);
        }

        this.announce('Connection restored!');
    },

    // ============================================
    // PHASE 1: ACCESSIBILITY
    // ============================================
    initAccessibility() {
        // Add skip link
        this.addSkipLink();

        // Ensure ARIA labels
        this.ensureAriaLabels();

        // Setup focus trap for modals
        this.setupFocusTrap();
    },

    addSkipLink() {
        // Check if skip link already exists
        if (document.querySelector('.skip-link')) return;

        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-link';
        skipLink.textContent = 'Skip to main content';
        document.body.insertBefore(skipLink, document.body.firstChild);

        // Add main content ID if not exists
        const mainContent = document.querySelector('main, .bento-grid, .admin-main');
        if (mainContent && !mainContent.id) {
            mainContent.id = 'main-content';
        }
    },

    ensureAriaLabels() {
        // Add labels to buttons without text
        document.querySelectorAll('button:not([aria-label])').forEach(btn => {
            if (!btn.textContent.trim()) {
                const icon = btn.querySelector('svg');
                if (icon) {
                    // Try to infer label from class or data attributes
                    const label = btn.dataset.tooltip ||
                                  btn.title ||
                                  btn.className.match(/btn-(\w+)/)?.[1] ||
                                  'Button';
                    btn.setAttribute('aria-label', label);
                }
            }
        });

        // Ensure dropzone is accessible
        const dropzone = document.querySelector('.dropzone');
        if (dropzone) {
            dropzone.setAttribute('role', 'button');
            dropzone.setAttribute('tabindex', '0');
            dropzone.setAttribute('aria-label', 'Upload area. Click or drag files here.');

            // Handle keyboard activation
            dropzone.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const fileInput = document.getElementById('file-input');
                    if (fileInput) fileInput.click();
                }
            });
        }
    },

    setupFocusTrap() {
        // Will be called when modals open
        this.focusTrapActive = false;
        this.focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    },

    trapFocus(container) {
        const focusable = container.querySelectorAll(this.focusableElements);
        const firstFocusable = focusable[0];
        const lastFocusable = focusable[focusable.length - 1];

        container.addEventListener('keydown', (e) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        });

        // Focus first element
        if (firstFocusable) firstFocusable.focus();
    },

    // Screen reader announcements
    announce(message, priority = 'polite') {
        let announcer = document.getElementById('sr-announcer');
        if (!announcer) {
            announcer = document.createElement('div');
            announcer.id = 'sr-announcer';
            announcer.className = 'sr-only';
            announcer.setAttribute('aria-live', priority);
            announcer.setAttribute('aria-atomic', 'true');
            document.body.appendChild(announcer);
        }

        // Clear and set new message
        announcer.textContent = '';
        setTimeout(() => {
            announcer.textContent = message;
        }, 100);
    },

    // ============================================
    // PHASE 1: ERROR BOUNDARY
    // ============================================
    initErrorBoundary() {
        // Global error handler
        window.addEventListener('error', (e) => {
            console.error('[Error Boundary]', e.error);
            this.showErrorBoundary(e.error?.message || 'An unexpected error occurred');
        });

        // Unhandled promise rejection
        window.addEventListener('unhandledrejection', (e) => {
            console.error('[Error Boundary] Unhandled Promise:', e.reason);
            this.showErrorBoundary(e.reason?.message || 'An unexpected error occurred');
        });
    },

    showErrorBoundary(message, container = null) {
        const errorHTML = `
            <div class="error-boundary">
                <div class="error-boundary-icon">
                    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                </div>
                <h3>Something went wrong</h3>
                <p>${this.escapeHtml(message)}</p>
                <div class="error-boundary-actions">
                    <button class="btn-retry" onclick="location.reload()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="23 4 23 10 17 10"></polyline>
                            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                        </svg>
                        Reload Page
                    </button>
                </div>
            </div>
        `;

        if (container) {
            container.innerHTML = errorHTML;
        } else {
            // Show toast for non-critical errors
            this.showToast(message, 'error');
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // ============================================
    // PHASE 1: LOADING SKELETONS
    // ============================================
    showSkeleton(container, type = 'default') {
        const skeletons = {
            default: `
                <div class="loading-skeleton">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text"></div>
                </div>
            `,
            preview: `
                <div class="preview-skeleton">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text"></div>
                </div>
            `,
            agent: `
                <div class="agent-card-skeleton">
                    <div class="skeleton skeleton-avatar"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text sm"></div>
                </div>
            `,
            file: `
                <div class="file-skeleton">
                    <div class="skeleton skeleton-icon"></div>
                    <div class="skeleton-content">
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text sm"></div>
                    </div>
                </div>
            `,
        };

        if (container) {
            container.innerHTML = skeletons[type] || skeletons.default;
        }
    },

    hideSkeleton(container) {
        if (container) {
            const skeleton = container.querySelector('.loading-skeleton, .preview-skeleton, .agent-card-skeleton, .file-skeleton');
            if (skeleton) skeleton.remove();
        }
    },

    // ============================================
    // UTILITY: TOAST
    // ============================================
    showToast(message, type = 'info', duration = 4000) {
        // Use existing toast system if available
        if (window.PublisherApp && window.PublisherApp.showToast) {
            window.PublisherApp.showToast(message, type);
            return;
        }

        // Fallback toast
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const icons = {
            success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
            error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
            info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>',
            warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
        };

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            ${icons[type] || icons.info}
            <span class="toast-message">${this.escapeHtml(message)}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'toastIn 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },
};

// ============================================
// PHASE 2: EDITOR HISTORY (Undo/Redo)
// ============================================
const EditorHistory = {
    history: [],
    currentIndex: -1,
    maxHistory: 50,

    push(state) {
        // Remove any future states
        this.history = this.history.slice(0, this.currentIndex + 1);

        // Add new state
        this.history.push(state);

        // Limit history size
        if (this.history.length > this.maxHistory) {
            this.history.shift();
        } else {
            this.currentIndex++;
        }

        this.updateButtons();
    },

    undo() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.restoreState(this.history[this.currentIndex]);
            this.updateButtons();
            UIEnhancements.announce('Undo');
        }
    },

    redo() {
        if (this.currentIndex < this.history.length - 1) {
            this.currentIndex++;
            this.restoreState(this.history[this.currentIndex]);
            this.updateButtons();
            UIEnhancements.announce('Redo');
        }
    },

    restoreState(state) {
        if (state && state.chunkId && state.text) {
            const textarea = document.querySelector(`[data-chunk-id="${state.chunkId}"] textarea`);
            if (textarea) {
                textarea.value = state.text;
                // Trigger save
                textarea.dispatchEvent(new Event('input'));
            }
        }
    },

    updateButtons() {
        const undoBtn = document.getElementById('btn-undo');
        const redoBtn = document.getElementById('btn-redo');

        if (undoBtn) undoBtn.disabled = this.currentIndex <= 0;
        if (redoBtn) redoBtn.disabled = this.currentIndex >= this.history.length - 1;
    },

    clear() {
        this.history = [];
        this.currentIndex = -1;
        this.updateButtons();
    }
};

// ============================================
// BATCH DOWNLOAD
// ============================================
const BatchDownload = {
    async downloadAll(files) {
        if (!files || files.length === 0) {
            UIEnhancements.showToast('No files to download', 'warning');
            return;
        }

        UIEnhancements.showToast('Preparing download...', 'info');

        // For single file, direct download
        if (files.length === 1) {
            window.location.href = files[0].url;
            return;
        }

        // For multiple files, download sequentially
        for (const file of files) {
            await this.downloadFile(file.url, file.name);
            await this.delay(500); // Small delay between downloads
        }

        UIEnhancements.showToast('All files downloaded!', 'success');
    },

    downloadFile(url, filename) {
        return new Promise((resolve) => {
            const link = document.createElement('a');
            link.href = url;
            link.download = filename || 'download';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            resolve();
        });
    },

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

// Export to global scope
window.UIEnhancements = UIEnhancements;
window.EditorHistory = EditorHistory;
window.BatchDownload = BatchDownload;

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => UIEnhancements.init());
} else {
    UIEnhancements.init();
}
