/**
 * Proofreading Studio Logic
 * Handles the Split-View Editor and API interactions.
 */

const Editor = {
    currentJobId: null,

    init() {
        // Find elements
        this.overlay = document.getElementById('editor-overlay');
        this.container = document.getElementById('editor-segments-container');
        this.closeBtn = document.getElementById('editor-close-btn');
        this.titleEl = document.getElementById('editor-job-title');

        // Bind events
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
        }
    },

    async open(jobId, jobName) {
        this.currentJobId = jobId;
        this.titleEl.textContent = jobName || 'Proofreading Studio';

        // Show overlay
        this.overlay.classList.remove('hidden');
        // Small delay to allow display:block to apply before opacity transition
        requestAnimationFrame(() => {
            this.overlay.classList.add('active');
        });

        // Load data
        await this.loadSegments(jobId);
    },

    close() {
        this.overlay.classList.remove('active');
        setTimeout(() => {
            this.overlay.classList.add('hidden');
            this.container.innerHTML = ''; // Clear memory
            this.currentJobId = null;
        }, 300);
    },

    async loadSegments(jobId) {
        this.container.innerHTML = '<div class="loading-spinner"></div>';

        try {
            const response = await fetch(`/api/editor/jobs/${jobId}/segments`);
            if (!response.ok) throw new Error('Failed to load segments');

            const data = await response.json();
            this.renderSegments(data.segments);

        } catch (error) {
            console.error('Editor load error:', error);
            this.container.innerHTML = `<div class="error-message">Could not load editor: ${error.message}</div>`;
        }
    },

    renderSegments(segments) {
        this.container.innerHTML = '';

        segments.forEach(seg => {
            const card = document.createElement('div');
            card.className = 'segment-card';
            card.dataset.id = seg.chunk_id;

            card.innerHTML = `
                <div class="segment-source">${this.escapeHtml(seg.source)}</div>
                <div class="segment-target-wrapper">
                    <textarea class="segment-target-textarea">${this.escapeHtml(seg.translated)}</textarea>
                    <div class="save-indicator" id="save-indicator-${seg.chunk_id}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        Saved
                    </div>
                </div>
                <div class="segment-meta">
                    <span class="segment-id">#${seg.chunk_id}</span>
                    <span class="confidence-score">Quality: ${(seg.quality_score * 100).toFixed(0)}%</span>
                </div>
            `;

            // Auto-save logic
            const textarea = card.querySelector('textarea');
            let debounceTimer;

            textarea.addEventListener('input', () => {
                const indicator = document.getElementById(`save-indicator-${seg.chunk_id}`);
                indicator.classList.remove('saved');

                // Auto resize
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';

                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.saveSegment(seg.chunk_id, textarea.value);
                }, 1000); // Save after 1 second of inactivity
            });

            // Initial resize
            setTimeout(() => {
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            }, 0);

            this.container.appendChild(card);
        });
    },

    async saveSegment(chunkId, newText) {
        if (!this.currentJobId) return;

        try {
            const indicator = document.getElementById(`save-indicator-${chunkId}`);

            const response = await fetch(`/api/editor/jobs/${this.currentJobId}/segments/${chunkId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ translated_text: newText })
            });

            if (response.ok) {
                indicator.classList.add('saved');
            } else {
                console.error('Save failed');
            }
        } catch (e) {
            console.error('Save error', e);
        }
    },

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.innerText = text;
        return div.innerHTML;
    }
};

// Export to global scope
window.Editor = Editor;
