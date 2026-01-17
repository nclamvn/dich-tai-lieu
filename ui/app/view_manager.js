/**
 * ViewManager - Commercial Architecture Controller
 * Handles switching between isolated Workspaces (Translator vs Author).
 */

const ViewManager = {
    init() {
        console.log('ViewManager: Initializing Commercial Architecture...');
        this.bindGlobalNav();

        // Auto-detect active workspace or default to translator
        // Check hash or localstorage
        const lastWorkspace = localStorage.getItem('active_workspace') || 'workspace-translator';
        this.switchWorkspace(lastWorkspace);
    },

    bindGlobalNav() {
        const tabs = document.querySelectorAll('.workspace-tab[data-target]');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const target = tab.dataset.target;
                this.switchWorkspace(target);
            });
        });
    },

    switchWorkspace(targetId) {
        // 1. Update Tabs
        document.querySelectorAll('.workspace-tab').forEach(tab => {
            if (tab.dataset.target === targetId) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // 2. Update Workspaces (The "Scene Change")
        document.querySelectorAll('.workspace').forEach(ws => {
            if (ws.id === targetId) {
                ws.classList.add('active');
                ws.classList.remove('hidden');
            } else {
                ws.classList.remove('active');
                ws.classList.add('hidden');
            }
        });

        // 3. Persist
        localStorage.setItem('active_workspace', targetId);

        // 4. Trigger specific Lifecycle hooks
        if (targetId === 'workspace-author') {
            this.onMountAuthor();
        }
    },

    onMountAuthor() {
        // Lazy load Author data if needed
        if (window.AuthorApp && window.AuthorApp.loadProjects) {
            window.AuthorApp.loadProjects(); // Reload projects
        }
    }
};

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
    ViewManager.init();
});
