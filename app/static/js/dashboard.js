// Developer Dashboard Logic

let currentTheme = 'dark';
let activeEventSource = null;

document.addEventListener('DOMContentLoaded', () => {
    fetchDashboardStats();
    fetchLogs();
    fetchHealthAndVersion();
    setInterval(fetchDashboardStats, 3000);
});

function toggleTheme() {
    const html = document.documentElement;
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', currentTheme);
    const icon = document.getElementById('themeIcon');
    icon.className = currentTheme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
}

function showToast(message) {
    document.getElementById('toastMessage').innerText = message;
    const toastEl = document.getElementById('liveToast');
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

function copyToClipboard(elementId) {
    const input = document.getElementById(elementId);
    if (!input) return;
    navigator.clipboard.writeText(input.value).then(() => {
        showToast('Copied to clipboard!');
    });
}

function copyCodeSnippet(elementId) {
    const code = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(code).then(() => {
        showToast('Code snippet copied to clipboard!');
    });
}

function toggleSecretVisibility() {
    const input = document.getElementById('cred-secret-key');
    const icon = document.getElementById('secretEyeIcon');
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'bi bi-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'bi bi-eye';
    }
}

async function fetchDashboardStats() {
    try {
        const res = await fetch('/api/v1/dashboard/stats');
        const data = await res.json();

        document.getElementById('stat-active').innerText = data.active_downloads || 0;
        document.getElementById('stat-completed').innerText = data.completed_jobs || 0;
        document.getElementById('stat-disk-percent').innerText = `${data.storage.percent_used}%`;
        document.getElementById('stat-disk-human').innerText = `${data.storage.free_human} Free`;

        // Update jobs table
        const tbody = document.getElementById('jobs-table-body');
        if (!data.running_jobs_list || data.running_jobs_list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No download jobs currently recorded.</td></tr>`;
        } else {
            tbody.innerHTML = data.running_jobs_list.map(job => {
                const statusBadge = job.status === 'completed'
                    ? '<span class="badge bg-success">Completed</span>'
                    : job.status === 'failed'
                    ? '<span class="badge bg-danger">Failed</span>'
                    : '<span class="badge bg-primary">Processing</span>';

                return `
                    <tr>
                        <td class="ps-4 font-monospace small">${job.job_id.substring(0, 8)}...</td>
                        <td><span class="badge bg-secondary text-uppercase">${job.type}</span></td>
                        <td class="small fw-semibold">${job.current_step || 'Processing'}</td>
                        <td style="width: 25%;">
                            <div class="progress" style="height: 6px;">
                                <div class="progress-bar ${job.status === 'completed' ? 'bg-success' : 'bg-primary'}" style="width: ${job.progress || 0}%"></div>
                            </div>
                            <span class="extra-small text-muted">${job.progress || 0}%</span>
                        </td>
                        <td class="small font-monospace">${job.speed_human || '0 B/s'} (${job.eta_human || '0s'})</td>
                        <td class="pe-4 text-end">
                            ${job.file_path ? `<a href="/api/v1/files/${job.job_id}" class="btn btn-sm btn-outline-success py-0 px-2"><i class="bi bi-download"></i> Get File</a>` : ''}
                        </td>
                    </tr>
                `;
            }).join('');
        }

        // Fetch metrics for gauges
        const mRes = await fetch('/api/v1/metrics');
        const metrics = await mRes.json();
        document.getElementById('cpu-bar').style.width = `${metrics.cpu.percent_used}%`;
        document.getElementById('cpu-val').innerText = `${metrics.cpu.percent_used}%`;
        document.getElementById('cpu-cores').innerText = `Cores: ${metrics.cpu.core_count}`;

        document.getElementById('ram-bar').style.width = `${metrics.memory.percent_used}%`;
        document.getElementById('ram-val').innerText = `${metrics.memory.percent_used}%`;
        document.getElementById('ram-human').innerText = `${metrics.memory.used_human} / ${metrics.memory.total_human}`;

        const sRes = await fetch('/api/v1/status');
        const sData = await sRes.json();
        document.getElementById('stat-uptime').innerText = sData.uptime_human || '0s';

    } catch (e) {
        console.error('Stats fetch error', e);
    }
}

async function runPlaygroundTest() {
    const url = document.getElementById('play-url').value;
    const action = document.getElementById('play-action').value;
    const quality = document.getElementById('play-quality').value;
    const format = document.getElementById('play-format').value;
    const apiKey = document.getElementById('cred-api-key').value;
    const btn = document.getElementById('btn-run-playground');
    const responseBox = document.getElementById('play-response-body');
    const statusBadge = document.getElementById('play-status-code');

    if (!url) {
        alert('Please enter a valid video URL.');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Processing...`;
    responseBox.innerText = '// Sending API Request to Download Engine...';

    let endpoint = '/api/v1/download/video';
    let bodyData = { url, quality, format };

    if (action === 'metadata') {
        endpoint = '/api/v1/metadata';
        bodyData = { url };
    } else if (action === 'audio') {
        endpoint = '/api/v1/download/audio';
        bodyData = { url, format: 'mp3', bitrate: '192' };
    } else if (action === 'thumbnail') {
        endpoint = '/api/v1/download/thumbnail';
        bodyData = { url };
    }

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify(bodyData)
        });

        statusBadge.innerText = `HTTP ${res.status}`;
        statusBadge.className = res.ok ? 'badge bg-success font-monospace' : 'badge bg-danger font-monospace';

        const json = await res.json();
        responseBox.innerText = JSON.stringify(json, null, 2);

        if (json.job_id && (action === 'video' || action === 'audio')) {
            startLiveEventStream(json.job_id);
        }

        fetchDashboardStats();
    } catch (e) {
        responseBox.innerText = `// Error: ${e.message}`;
        statusBadge.innerText = 'HTTP Error';
        statusBadge.className = 'badge bg-danger font-monospace';
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="bi bi-send-fill me-1"></i> Send Request`;
    }
}

function startLiveEventStream(jobId) {
    if (activeEventSource) {
        activeEventSource.close();
    }

    const container = document.getElementById('live-stream-container');
    container.innerHTML = `<div class="alert alert-info small"><i class="bi bi-broadcast me-1"></i> Connecting to SSE live event stream for Job ID: <strong>${jobId}</strong>...</div>`;

    activeEventSource = new EventSource(`/api/v1/jobs/${jobId}/events`);
    activeEventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            const card = document.createElement('div');
            card.className = 'card border-0 shadow-sm bg-body-tertiary rounded-3 p-3';

            const statusClass = data.status === 'completed' ? 'text-success' : data.status === 'failed' ? 'text-danger' : 'text-primary';

            card.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-bold ${statusClass}"><i class="bi bi-arrow-right-circle me-1"></i> ${data.current_step || 'Update'}</span>
                    <span class="badge bg-secondary font-monospace">${data.progress || 0}%</span>
                </div>
                <div class="progress mb-2" style="height: 6px;">
                    <div class="progress-bar bg-primary" style="width: ${data.progress || 0}%"></div>
                </div>
                <div class="d-flex justify-content-between extra-small text-muted font-monospace">
                    <span>Speed: ${data.speed_human || '0 B/s'}</span>
                    <span>Downloaded: ${data.downloaded_bytes_human || '0 B'} / ${data.total_bytes_human || '0 B'}</span>
                    <span>ETA: ${data.eta_human || '0s'}</span>
                </div>
            `;
            container.prepend(card);

            if (['completed', 'failed', 'cancelled'].includes(data.status)) {
                activeEventSource.close();
            }
        } catch (e) {}
    };
}

async function fetchLogs() {
    const category = document.getElementById('log-category-filter').value;
    const container = document.getElementById('logs-container');
    try {
        const res = await fetch(`/api/v1/dashboard/logs?category=${category}&limit=100`);
        const json = await res.json();
        if (!json.logs || json.logs.length === 0) {
            container.innerHTML = `<div class="text-muted">// No logs recorded yet.</div>`;
            return;
        }
        container.innerHTML = json.logs.map(l => {
            const lvlColor = l.level === 'ERROR' ? 'text-danger' : l.level === 'WARN' ? 'text-warning' : 'text-info';
            return `<div><span class="text-muted">[${l.timestamp}]</span> <span class="${lvlColor}">[${l.level}]</span> <span class="text-secondary">[${l.category}]</span> ${l.message}</div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = `<div class="text-danger">// Error fetching logs: ${e.message}</div>`;
    }
}

async function fetchHealthAndVersion() {
    try {
        const hRes = await fetch('/api/v1/health');
        const hData = await hRes.json();
        document.getElementById('health-details-container').innerHTML = `
            <ul class="list-group list-group-flush small">
                <li class="list-group-item bg-transparent d-flex justify-content-between"><span>Status:</span> <strong class="text-success">${hData.status.toUpperCase()}</strong></li>
                <li class="list-group-item bg-transparent d-flex justify-content-between"><span>API Engine:</span> <span>${hData.components.api_server}</span></li>
                <li class="list-group-item bg-transparent d-flex justify-content-between"><span>yt-dlp Core:</span> <span>${hData.components.yt_dlp_engine}</span></li>
                <li class="list-group-item bg-transparent d-flex justify-content-between"><span>Storage Status:</span> <span>${hData.components.storage.status} (${hData.components.storage.percent_used}%)</span></li>
            </ul>
        `;

        const vRes = await fetch('/api/v1/version');
        const vData = await vRes.json();
        document.getElementById('version-details-container').innerHTML = `
            <ul class="list-group list-group-flush small">
                <li class="list-group-item bg-transparent d-flex justify-content-between"><span>API Version:</span> <strong>v${vData.version}</strong></li>
                <li class="list-group-item bg-transparent d-flex justify-content-between"><span>yt-dlp Core Version:</span> <span>${vData.yt_dlp_version}</span></li>
                <li class="list-group-item bg-transparent d-flex justify-content-between"><span>Python Environment:</span> <span>v${vData.python_version}</span></li>
                <li class="list-group-item bg-transparent d-flex justify-content-between"><span>OS Platform:</span> <span>${vData.os_platform}</span></li>
            </ul>
        `;
    } catch (e) {}
}

async function saveSettings(e) {
    e.preventDefault();
    const sig = document.getElementById('set-enforce-sig').checked;
    const ttl = parseInt(document.getElementById('set-ttl').value);
    const rate = parseInt(document.getElementById('set-rate-limit').value);
    const maxW = parseInt(document.getElementById('set-max-workers').value);
    const webhook = document.getElementById('set-webhook').value;

    try {
        const res = await fetch('/api/v1/dashboard/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                enforce_signature: sig,
                temp_file_ttl: ttl,
                rate_limit: rate,
                max_concurrent: maxW,
                webhook_url: webhook
            })
        });
        const json = await res.json();
        showToast(json.message || 'Settings saved successfully!');
    } catch (e) {
        alert(`Failed to save settings: ${e.message}`);
    }
}
