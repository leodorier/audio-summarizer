// Audio Summarizer Client Logic
let currentTimeframe = 'all';
let currentSearch = '';
let selectedFile = null;
let currentActiveRecord = null;
let activeModalTab = 'summary';

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    fetchStats();
    fetchRecords();
    setupEventListeners();
});

function setupEventListeners() {
    // Drop zone handling
    const dropZone = document.getElementById('drop-zone');
    const audioInput = document.getElementById('audio-input');
    const selectedFileDisplay = document.getElementById('selected-file-display');
    const selectedFilename = document.getElementById('selected-filename');
    const btnProcess = document.getElementById('btn-process');

    dropZone.addEventListener('click', () => audioInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('border-emerald-500', 'bg-slate-900');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('border-emerald-500', 'bg-slate-900');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    audioInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    function handleFileSelection(file) {
        selectedFile = file;
        selectedFilename.textContent = `${file.name} (${formatBytes(file.size)})`;
        selectedFileDisplay.classList.remove('hidden');
        selectedFileDisplay.classList.add('flex');
    }

    // Process button click
    btnProcess.addEventListener('click', async () => {
        if (!selectedFile) {
            alert('Please select or drop an audio file first.');
            return;
        }
        await processAudioUpload();
    });

    // Timeframe filter buttons
    document.querySelectorAll('.tf-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tf-btn').forEach(b => {
                b.classList.remove('bg-emerald-500', 'text-white');
                b.classList.add('text-slate-400');
            });
            btn.classList.add('bg-emerald-500', 'text-white');
            btn.classList.remove('text-slate-400');
            currentTimeframe = btn.getAttribute('data-timeframe');
            fetchRecords();
        });
    });

    // Search input with debounce
    let searchTimeout = null;
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentSearch = e.target.value;
            fetchRecords();
        }, 300);
    });

    // Modal controls
    document.getElementById('btn-close-modal').addEventListener('click', closeModal);
    document.getElementById('detail-modal').addEventListener('click', (e) => {
        if (e.target.id === 'detail-modal') closeModal();
    });

    // Modal tab switches
    const tabBtnSummary = document.getElementById('tab-btn-summary');
    const tabBtnTranscript = document.getElementById('tab-btn-transcript');
    const paneSummary = document.getElementById('pane-summary');
    const paneTranscript = document.getElementById('pane-transcript');

    tabBtnSummary.addEventListener('click', () => {
        activeModalTab = 'summary';
        tabBtnSummary.className = 'tab-btn px-4 py-3 text-sm font-semibold text-emerald-400 border-b-2 border-emerald-500 flex items-center gap-2';
        tabBtnTranscript.className = 'tab-btn px-4 py-3 text-sm font-medium text-slate-400 hover:text-slate-200 flex items-center gap-2';
        paneSummary.classList.remove('hidden');
        paneTranscript.classList.add('hidden');
    });

    tabBtnTranscript.addEventListener('click', () => {
        activeModalTab = 'transcript';
        tabBtnTranscript.className = 'tab-btn px-4 py-3 text-sm font-semibold text-emerald-400 border-b-2 border-emerald-500 flex items-center gap-2';
        tabBtnSummary.className = 'tab-btn px-4 py-3 text-sm font-medium text-slate-400 hover:text-slate-200 flex items-center gap-2';
        paneTranscript.classList.remove('hidden');
        paneSummary.classList.add('hidden');
    });

    // Copy Content button
    const btnCopy = document.getElementById('btn-copy-active');
    btnCopy.addEventListener('click', () => {
        if (!currentActiveRecord) return;
        const textToCopy = activeModalTab === 'summary' 
            ? currentActiveRecord.summary_text 
            : currentActiveRecord.raw_transcript;
        
        navigator.clipboard.writeText(textToCopy).then(() => {
            const btnText = document.getElementById('copy-btn-text');
            btnText.textContent = 'Copied!';
            setTimeout(() => btnText.textContent = 'Copy Content', 2000);
        });
    });

    // Delete record from modal
    document.getElementById('btn-modal-delete').addEventListener('click', async () => {
        if (!currentActiveRecord) return;
        if (confirm(`Are you sure you want to permanently delete "${currentActiveRecord.title}"?`)) {
            await deleteRecord(currentActiveRecord.id);
            closeModal();
        }
    });
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        if (res.ok) {
            const stats = await res.json();
            document.getElementById('stat-files').textContent = stats.total_files;
            const minutes = Math.round(stats.total_duration_seconds / 60);
            document.getElementById('stat-duration').textContent = `${minutes}m`;
            document.getElementById('stats-badge').classList.remove('hidden');
        }
    } catch (e) {
        console.error('Failed to fetch stats', e);
    }
}

async function fetchRecords() {
    const container = document.getElementById('records-container');
    const emptyState = document.getElementById('empty-state');
    
    let url = `/api/files?timeframe=${encodeURIComponent(currentTimeframe)}`;
    if (currentSearch.trim()) {
        url += `&search=${encodeURIComponent(currentSearch.trim())}`;
    }

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch files');
        const data = await res.json();

        if (data.items.length === 0) {
            container.innerHTML = '';
            emptyState.classList.remove('hidden');
            return;
        }

        emptyState.classList.add('hidden');
        container.innerHTML = data.items.map(item => renderRecordCard(item)).join('');
        lucide.createIcons();

        // Attach card click handlers
        document.querySelectorAll('.record-card').forEach(card => {
            card.addEventListener('click', () => {
                const recordId = card.getAttribute('data-id');
                openRecordModal(recordId);
            });
        });
    } catch (e) {
        console.error('Failed to load records', e);
    }
}

function renderRecordCard(item) {
    const dateFormatted = new Date(item.created_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
    const durationFormatted = formatDuration(item.duration_seconds);
    const topicsBadges = (item.topics || []).slice(0, 3).map(t => 
        `<span class="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded-md border border-slate-700 font-mono">${escapeHtml(t)}</span>`
    ).join('');

    return `
    <div data-id="${item.id}" class="record-card bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-emerald-500/40 rounded-2xl p-5 shadow-lg transition-all duration-200 cursor-pointer flex flex-col justify-between space-y-4 group">
        <div class="space-y-2">
            <div class="flex items-center justify-between text-xs">
                <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${escapeHtml(item.language)}</span>
                <span class="text-slate-400">${dateFormatted} • ${durationFormatted}</span>
            </div>
            <h3 class="text-base font-bold text-white group-hover:text-emerald-400 transition-colors line-clamp-2">
                ${escapeHtml(item.title)}
            </h3>
            <p class="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                ${escapeHtml(item.summary_preview)}
            </p>
        </div>

        <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between">
            <div class="flex items-center gap-1.5 flex-wrap">
                ${topicsBadges}
            </div>
            <div class="text-slate-400 group-hover:text-emerald-400 text-xs font-semibold flex items-center gap-1">
                <span>View</span>
                <i data-lucide="chevron-right" class="w-4 h-4"></i>
            </div>
        </div>
    </div>
    `;
}

async function openRecordModal(recordId) {
    try {
        const res = await fetch(`/api/files/${recordId}`);
        if (!res.ok) throw new Error('Failed to load record');
        const record = await res.json();
        currentActiveRecord = record;

        document.getElementById('modal-title').textContent = record.title;
        document.getElementById('modal-lang-badge').textContent = record.language.toUpperCase();
        document.getElementById('modal-date').textContent = new Date(record.created_at).toLocaleString();
        document.getElementById('modal-duration').textContent = formatDuration(record.duration_seconds);

        // Audio Player
        const player = document.getElementById('modal-audio-player');
        player.src = `/api/files/${record.id}/audio`;

        // Markdown summary render
        document.getElementById('modal-summary-content').innerHTML = marked.parse(record.summary_text || '');

        // Key Points
        const keyPointsList = document.getElementById('modal-key-points');
        keyPointsList.innerHTML = (record.key_points || []).map(p => `<li>${escapeHtml(p)}</li>`).join('') || '<li class="text-slate-500 italic">None recorded</li>';

        // Action Items
        const actionItemsList = document.getElementById('modal-action-items');
        actionItemsList.innerHTML = (record.action_items || []).map(a => `<li>${escapeHtml(a)}</li>`).join('') || '<li class="text-slate-500 italic">None recorded</li>';

        // Tags
        const tagsContainer = document.getElementById('modal-tags');
        tagsContainer.innerHTML = (record.topics || []).map(t => 
            `<span class="text-xs bg-slate-800 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700">${escapeHtml(t)}</span>`
        ).join('') || '<span class="text-xs text-slate-500 italic">None</span>';

        // Transcript
        document.getElementById('modal-transcript-text').textContent = record.raw_transcript;

        // Download links
        document.getElementById('btn-download-transcript').href = `/api/files/${record.id}/transcript?format=txt`;
        document.getElementById('btn-download-summary').href = `/api/files/${record.id}/summary`;

        document.getElementById('detail-modal').classList.remove('hidden');
        lucide.createIcons();
    } catch (e) {
        alert('Could not open record details: ' + e.message);
    }
}

function closeModal() {
    document.getElementById('detail-modal').classList.add('hidden');
    const player = document.getElementById('modal-audio-player');
    player.pause();
    player.src = '';
    currentActiveRecord = null;
}

async function processAudioUpload() {
    const btnProcess = document.getElementById('btn-process');
    const indicator = document.getElementById('processing-indicator');
    const titleInput = document.getElementById('custom-title-input');

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (titleInput.value.trim()) {
        formData.append('title', titleInput.value.trim());
    }

    btnProcess.disabled = true;
    indicator.classList.remove('hidden');

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Upload failed');
        }

        const newRecord = await res.json();
        selectedFile = null;
        titleInput.value = '';
        document.getElementById('selected-file-display').classList.add('hidden');
        document.getElementById('audio-input').value = '';

        await fetchStats();
        await fetchRecords();
        openRecordModal(newRecord.id);
    } catch (e) {
        alert('Processing Error: ' + e.message);
    } finally {
        btnProcess.disabled = false;
        indicator.classList.add('hidden');
    }
}

async function deleteRecord(recordId) {
    try {
        const res = await fetch(`/api/files/${recordId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete');
        await fetchStats();
        await fetchRecords();
    } catch (e) {
        alert('Delete failed: ' + e.message);
    }
}

function formatDuration(seconds) {
    if (!seconds || seconds <= 0) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs}s`;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
