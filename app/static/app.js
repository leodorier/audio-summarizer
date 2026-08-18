// Audio Summarizer Client Logic with Better Auth Integration
let currentUser = null;
let currentTimeframe = 'all';
let currentSearch = '';
let selectedFile = null;
let currentActiveRecord = null;
let activeModalTab = 'summary';

// Global 401 fetch interceptor
const _originalFetch = window.fetch;
window.fetch = async function(...args) {
    // Default to credentials include if options provided or empty
    if (args.length > 1 && typeof args[1] === 'object') {
        if (!args[1].credentials) {
            args[1].credentials = 'include';
        }
    }
    const res = await _originalFetch.apply(this, args);
    if (res.status === 401 && typeof args[0] === 'string' && !args[0].includes('/api/auth/')) {
        showLoginScreen();
    }
    return res;
};

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    setupEventListeners();
    checkAuth();
});

async function checkAuth() {
    try {
        const res = await fetch('/api/auth/me', { credentials: 'include' });
        const data = await res.json();
        if (data.authenticated && data.user) {
            currentUser = data.user;
            showDashboard();
        } else {
            showLoginScreen();
        }
    } catch (e) {
        showLoginScreen();
    }
}

function showLoginScreen() {
    const loginScreen = document.getElementById('login-screen');
    const mainDashboard = document.getElementById('main-dashboard');
    if (loginScreen) loginScreen.classList.remove('hidden');
    if (mainDashboard) mainDashboard.classList.add('hidden');
    currentUser = null;
    lucide.createIcons();
}

function showDashboard() {
    const loginScreen = document.getElementById('login-screen');
    const mainDashboard = document.getElementById('main-dashboard');
    const userEmailText = document.getElementById('user-email-text');

    if (loginScreen) loginScreen.classList.add('hidden');
    if (mainDashboard) mainDashboard.classList.remove('hidden');
    
    if (userEmailText && currentUser) {
        const displayName = currentUser.name || currentUser.username || (currentUser.email ? currentUser.email.split('@')[0] : 'User');
        userEmailText.textContent = displayName;
    }

    lucide.createIcons();
    fetchStats();
    fetchRecords();
}

async function handleLogin(e) {
    if (e && e.preventDefault) e.preventDefault();
    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');
    const loginError = document.getElementById('login-error');
    const loginErrorText = document.getElementById('login-error-text');
    const btnLoginSubmit = document.getElementById('btn-login-submit');
    const btnLoginText = document.getElementById('btn-login-text');

    const email = emailInput ? emailInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value : '';

    if (!email || !password) return;

    if (loginError) loginError.classList.add('hidden');
    if (btnLoginSubmit) btnLoginSubmit.disabled = true;
    if (btnLoginText) btnLoginText.textContent = 'Verifying...';

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (btnLoginSubmit) btnLoginSubmit.disabled = false;
        if (btnLoginText) btnLoginText.textContent = 'Sign In';

        if (res.ok && data.success) {
            currentUser = data.user || { email, name: email.split('@')[0] };
            showDashboard();
        } else {
            if (loginErrorText) loginErrorText.textContent = data.error || 'Invalid email or password.';
            if (loginError) loginError.classList.remove('hidden');
            lucide.createIcons();
        }
    } catch (err) {
        if (btnLoginSubmit) btnLoginSubmit.disabled = false;
        if (btnLoginText) btnLoginText.textContent = 'Sign In';
        if (loginErrorText) loginErrorText.textContent = 'Connection error. Ensure Second Brain API is reachable.';
        if (loginError) loginError.classList.remove('hidden');
        lucide.createIcons();
    }
}

async function handleLogout() {
    if (!confirm('Are you sure you want to sign out?')) return;
    try {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    } catch (e) {}
    currentUser = null;
    showLoginScreen();
}

// Expose globally
window.handleLogin = handleLogin;
window.handleLogout = handleLogout;

function setupEventListeners() {
    // Drop zone handling
    const dropZone = document.getElementById('drop-zone');
    const audioInput = document.getElementById('audio-input');
    const selectedFileDisplay = document.getElementById('selected-file-display');
    const selectedFilename = document.getElementById('selected-filename');
    const btnProcess = document.getElementById('btn-process');

    if (dropZone) {
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
    }

    if (audioInput) {
        audioInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });
    }

    function handleFileSelection(file) {
        selectedFile = file;
        selectedFilename.textContent = `${file.name} (${formatBytes(file.size)})`;
        selectedFileDisplay.classList.remove('hidden');
        selectedFileDisplay.classList.add('flex');
    }

    // Process button click
    if (btnProcess) {
        btnProcess.addEventListener('click', async () => {
            if (!selectedFile) {
                alert('Please select or drop an audio file first.');
                return;
            }
            await processAudioUpload();
        });
    }

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
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentSearch = e.target.value;
                fetchRecords();
            }, 300);
        });
    }

    // Modal controls
    document.getElementById('btn-close-modal')?.addEventListener('click', closeModal);
    document.getElementById('detail-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'detail-modal') closeModal();
    });

    // Modal tab switches
    const tabBtnSummary = document.getElementById('tab-btn-summary');
    const tabBtnTranscript = document.getElementById('tab-btn-transcript');
    const paneSummary = document.getElementById('pane-summary');
    const paneTranscript = document.getElementById('pane-transcript');

    if (tabBtnSummary && tabBtnTranscript) {
        tabBtnSummary.addEventListener('click', () => {
            activeModalTab = 'summary';
            tabBtnSummary.className = 'tab-btn px-4 py-3 text-sm font-semibold text-emerald-400 border-b-2 border-emerald-500 flex items-center gap-2 cursor-pointer';
            tabBtnTranscript.className = 'tab-btn px-4 py-3 text-sm font-medium text-slate-400 hover:text-slate-200 flex items-center gap-2 cursor-pointer';
            paneSummary.classList.remove('hidden');
            paneTranscript.classList.add('hidden');
        });

        tabBtnTranscript.addEventListener('click', () => {
            activeModalTab = 'transcript';
            tabBtnTranscript.className = 'tab-btn px-4 py-3 text-sm font-semibold text-emerald-400 border-b-2 border-emerald-500 flex items-center gap-2 cursor-pointer';
            tabBtnSummary.className = 'tab-btn px-4 py-3 text-sm font-medium text-slate-400 hover:text-slate-200 flex items-center gap-2 cursor-pointer';
            paneTranscript.classList.remove('hidden');
            paneSummary.classList.add('hidden');
        });
    }

    // Copy Content button
    const btnCopy = document.getElementById('btn-copy-active');
    if (btnCopy) {
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
    }

    // Delete record from modal
    document.getElementById('btn-modal-delete')?.addEventListener('click', async () => {
        if (!currentActiveRecord) return;
        if (confirm(`Are you sure you want to permanently delete "${currentActiveRecord.title}"?`)) {
            await deleteRecord(currentActiveRecord.id);
            closeModal();
        }
    });
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats', { credentials: 'include' });
        if (res.status === 401) {
            showLoginScreen();
            return;
        }
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
        const res = await fetch(url, { credentials: 'include' });
        if (res.status === 401) {
            showLoginScreen();
            return;
        }
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
        const res = await fetch(`/api/files/${recordId}`, { credentials: 'include' });
        if (res.status === 401) {
            showLoginScreen();
            return;
        }
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

    const customKey = (localStorage.getItem('custom_gemini_api_key') || '').trim();
    const isUserOwner = currentUser && (currentUser.is_owner === true || (currentUser.name || '').toLowerCase() === 'dragstonium');

    if (!customKey && !isUserOwner) {
        openSettingsModal();
        showSettingsAlert("⚠️ Action required: Please configure your personal Google Gemini API key to transcribe and summarize audio files.", "error");
        return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (titleInput.value.trim()) {
        formData.append('title', titleInput.value.trim());
    }
    if (customKey) {
        formData.append('api_key', customKey);
    }

    btnProcess.disabled = true;
    indicator.classList.remove('hidden');

    try {
        const headers = customKey ? { 'X-Gemini-Api-Key': customKey } : {};
        const res = await fetch('/api/upload', {
            method: 'POST',
            credentials: 'include',
            headers: headers,
            body: formData
        });

        if (res.status === 428) {
            openSettingsModal();
            showSettingsAlert("⚠️ Google Gemini API key required. Please enter your personal key below to continue.", "error");
            throw new Error("Gemini API key required.");
        }

        if (res.status === 401) {
            showLoginScreen();
            return;
        }

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
        const res = await fetch(`/api/files/${recordId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        if (res.status === 401) {
            showLoginScreen();
            return;
        }
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


// ==========================================
// Settings Modal & API Key Management
// ==========================================

function openSettingsModal() {
    const modal = document.getElementById('settingsModal');
    const userEmailEl = document.getElementById('settingsUserEmail');
    const keyInput = document.getElementById('settingsGeminiKeyInput');
    
    const displayName = (currentUser && (currentUser.name || currentUser.username)) || 'User';
    const email = (currentUser && currentUser.email) || '';
    if (userEmailEl) {
        userEmailEl.textContent = `Signed in as: ${displayName}${email ? ' (' + email + ')' : ''}`;
    }
    
    hideSettingsAlert();
    const savedKey = localStorage.getItem('custom_gemini_api_key') || '';
    if (keyInput) keyInput.value = savedKey;
    updateGeminiKeyBadge(savedKey);
    
    if (modal) modal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function closeSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.add('hidden');
}

function closeSettingsModalOnOverlay(e) {
    if (e.target.id === 'settingsModal') {
        closeSettingsModal();
    }
}

function showSettingsAlert(msg, type = 'success') {
    const alert = document.getElementById('settingsAlert');
    if (!alert) return;
    alert.classList.remove('hidden', 'bg-emerald-950/60', 'border-emerald-800', 'text-emerald-300', 'bg-red-950/60', 'border-red-800', 'text-red-300', 'bg-sky-950/60', 'border-sky-800', 'text-sky-300');
    
    if (type === 'success') {
        alert.classList.add('bg-emerald-950/60', 'border-emerald-800', 'text-emerald-300');
    } else if (type === 'error') {
        alert.classList.add('bg-red-950/60', 'border-red-800', 'text-red-300');
    } else {
        alert.classList.add('bg-sky-950/60', 'border-sky-800', 'text-sky-300');
    }
    alert.innerHTML = msg;
}

function hideSettingsAlert() {
    const alert = document.getElementById('settingsAlert');
    if (alert) alert.classList.add('hidden');
}

function updateGeminiKeyBadge(key) {
    const badge = document.getElementById('geminiKeyStatusBadge');
    const deleteBtn = document.getElementById('btnDeleteKey');
    if (!badge) return;
    if (key && key.trim()) {
        badge.textContent = '✨ Custom Key Active';
        badge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-950 text-emerald-300 border border-emerald-800';
        if (deleteBtn) deleteBtn.classList.remove('hidden');
    } else {
        badge.textContent = '⚙️ Server Default';
        badge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-800 text-slate-400 border border-slate-700';
        if (deleteBtn) deleteBtn.classList.add('hidden');
    }
}

function toggleGeminiKeyVisibility() {
    const input = document.getElementById('settingsGeminiKeyInput');
    const btn = document.getElementById('btnToggleKeyVis');
    if (!input || !btn) return;
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🔒';
    } else {
        input.type = 'password';
        btn.textContent = '👁️';
    }
}

async function testGeminiKey() {
    const input = document.getElementById('settingsGeminiKeyInput');
    const testBtn = document.getElementById('btnTestKey');
    const key = input ? input.value.trim() : '';
    
    showSettingsAlert('⏳ Testing connection to Google Gemini API...', 'info');
    if (testBtn) testBtn.disabled = true;
    
    try {
        const res = await fetch('/api/settings/verify-gemini', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key || undefined })
        });
        const data = await res.json();
        if (res.ok && data.valid) {
            showSettingsAlert('✅ Connection verified! Gemini API key is working perfectly.', 'success');
        } else {
            showSettingsAlert('❌ Verification failed: ' + (data.error || 'Invalid API key.'), 'error');
        }
    } catch (err) {
        showSettingsAlert('❌ Error testing key: ' + err.message, 'error');
    } finally {
        if (testBtn) testBtn.disabled = false;
    }
}

function saveGeminiKey() {
    const input = document.getElementById('settingsGeminiKeyInput');
    const key = input ? input.value.trim() : '';
    if (key) {
        localStorage.setItem('custom_gemini_api_key', key);
        showSettingsAlert('💾 Custom Gemini API key saved successfully for your session!', 'success');
    } else {
        localStorage.removeItem('custom_gemini_api_key');
        showSettingsAlert('ℹ️ Custom key removed. System will use server default configuration.', 'info');
    }
    updateGeminiKeyBadge(key);
}

function deleteGeminiKey() {
    localStorage.removeItem('custom_gemini_api_key');
    const input = document.getElementById('settingsGeminiKeyInput');
    if (input) input.value = '';
    updateGeminiKeyBadge('');
    showSettingsAlert('🗑️ Custom Gemini API key removed. Reverted to server configuration.', 'info');
}
