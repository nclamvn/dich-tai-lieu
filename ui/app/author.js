/**
 * Author Mode Logic (Commercial Refactor)
 * Handles the "Author Studio" Workspace.
 * managed by: ViewManager.js
 */

const AuthorApp = {
    state: {
        activeProject: null,
        activeChapter: null,
        isAIProcessing: false
    },

    init() {
        console.log('AuthorApp: Initialized (Commercial Mode)');
        this.bindEvents();
        // Projects are loaded by ViewManager.onMountAuthor, but we can load here too if needed.
        // To avoid double-loading in strict mode, we'll let ViewManager handle the data refresh 
        // or just do an initial check.
    },

    bindEvents() {
        // Project Management
        document.getElementById('btn-new-project')?.addEventListener('click', () => {
            this.createNewProject();
        });

        document.getElementById('btn-back-projects')?.addEventListener('click', () => {
            this.showProjectList();
        });

        // Editor Toolbar (Formatting)
        document.querySelectorAll('.tool-btn[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const action = btn.dataset.action;
                // Standard ContentEditable commands
                document.execCommand(action, false, null);

                // Specific Header overrides if needed
                if (action === 'h1') document.execCommand('formatBlock', false, 'H1');
                if (action === 'h2') document.execCommand('formatBlock', false, 'H2');
            });
        });

        // AI Propose
        document.getElementById('btn-ai-propose')?.addEventListener('click', () => {
            this.triggerAIPropose();
        });

        // AI Chat
        document.getElementById('btn-ai-send')?.addEventListener('click', () => {
            this.handleInfoChat();
        });
    },

    // --- Project Management ---

    async loadProjects() {
        // Mock Data for Commercial Demo
        const projects = [
            { id: 'p1', title: 'The Silent Space', status: 'In Progress', words: 12400, lastEdit: '2h ago' },
            { id: 'p2', title: 'AI Engineering Handbook', status: 'Draft', words: 4500, lastEdit: '1d ago' },
            { id: 'p3', title: 'Zero to One (Translation)', status: 'Review', words: 32000, lastEdit: '5d ago' }
        ];
        this.renderProjectList(projects);
    },

    renderProjectList(projects) {
        const list = document.getElementById('author-project-list');
        if (!list) return; // Guard clause

        if (projects.length === 0) {
            list.innerHTML = '<div class="empty-state" style="padding:20px; color:#666; text-align:center;">No active projects</div>';
            return;
        }

        // Renders using the new .project-card CSS class
        list.innerHTML = projects.map(p => `
            <div class="project-card" onclick="AuthorApp.openProject('${p.id}', '${p.title}')">
                <div class="card-header">
                    <span class="project-title">${p.title}</span>
                </div>
                <div class="card-meta">
                    <span class="status-badge">${p.status}</span>
                    <span class="word-count">${p.words} words</span>
                </div>
                <div class="card-footer">
                    Edited ${p.lastEdit}
                </div>
            </div>
        `).join('');
    },

    createNewProject() {
        const title = prompt("New Project Title:");
        if (title) {
            // Mock creation
            alert(`Project "${title}" created (Mock).`);
            // In real app, re-fetch list
            this.loadProjects();
        }
    },

    openProject(id, title) {
        this.state.activeProject = id;

        // Switch Views: Project List -> Editor
        document.querySelector('.author-project-list').classList.add('hidden');
        document.getElementById('author-chapter-nav').classList.remove('hidden');

        // Update Context
        const titleEl = document.getElementById('current-project-title');
        if (titleEl) titleEl.textContent = title;

        // Mock Chapters
        const chapters = [
            { id: 1, title: 'Chapter 1: The Beginning' },
            { id: 2, title: 'Chapter 2: The Awakening' },
            { id: 3, title: 'Chapter 3: Resolution' }
        ];

        const list = document.getElementById('chapter-list');
        if (list) {
            list.innerHTML = chapters.map(c => `
                <li onclick="AuthorApp.openChapter(${c.id})">
                    <span class="chapter-num">${c.id}</span>
                    <span class="chapter-name">${c.title}</span>
                </li>
            `).join('');
        }

        // Open first chapter by default
        this.openChapter(1);
    },

    showProjectList() {
        this.state.activeProject = null;
        document.querySelector('.author-project-list').classList.remove('hidden');
        document.getElementById('author-chapter-nav').classList.add('hidden');
    },

    openChapter(id) {
        this.state.activeChapter = id;

        // Visual Active State
        document.querySelectorAll('#chapter-list li').forEach(li => li.classList.remove('active'));
        // In real app, find specific LI by ID. For now, just clear all.

        const editor = document.getElementById('author-editor');
        if (editor) {
            editor.innerHTML = `<h1>Chapter ${id}</h1><p>Start writing your masterpiece here...</p><p>The quick brown fox jumps over the lazy dog.</p>`;
        }
    },

    // --- AI Logic ---

    async triggerAIPropose() {
        const editor = document.getElementById('author-editor');
        if (!editor) return;

        const text = editor.innerText;
        const lastContext = text.slice(-500);

        if (this.state.isAIProcessing) return;
        this.state.isAIProcessing = true;

        const btn = document.getElementById('btn-ai-propose');
        const originalContent = btn ? btn.innerHTML : 'AI Propose';

        if (btn) btn.innerHTML = '<i data-lucide="loader-2" class="animate-spin"></i> Thinking...';

        try {
            // Mock API Call
            await new Promise(r => setTimeout(r, 1200)); // Simulate delay
            const suggestion = " suddenly, the atmosphere shifted. The lights flickered, casting long, dancing shadows across the room.";
            this.insertTextAtCursor(suggestion);

        } catch (e) {
            console.error(e);
            alert("AI Error: Failed to generate");
        } finally {
            this.state.isAIProcessing = false;
            if (btn) btn.innerHTML = originalContent;
            if (window.lucide) window.lucide.createIcons();
        }
    },

    insertTextAtCursor(text) {
        const editor = document.getElementById('author-editor');
        if (!editor) return;

        editor.focus();
        document.execCommand('insertText', false, text);
    },

    handleInfoChat() {
        const input = document.getElementById('ai-chat-input');
        if (!input) return;

        const text = input.value.trim();
        if (!text) return;

        const container = document.getElementById('ai-chat-container');
        if (container) {
            container.innerHTML += `<div class="ai-message user">${text}</div>`;
            input.value = '';

            // Auto-scroll
            container.scrollTop = container.scrollHeight;

            // Mock Reply
            setTimeout(() => {
                container.innerHTML += `<div class="ai-message system">I am analyzing "${text}"... (AI Assistant)</div>`;
                container.scrollTop = container.scrollHeight;
            }, 800);
        }
    }
};

// Auto-run init
document.addEventListener('DOMContentLoaded', () => {
    AuthorApp.init();
});
