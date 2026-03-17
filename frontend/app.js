/* ─────────────────────────────────────────────────────────────────────────
   AI Architecture Reviewer — Frontend Logic
   ───────────────────────────────────────────────────────────────────────── */

// ── CONFIG: Replace with your `terraform output api_url` value ──────────────
const API_BASE = 'https://qj9x1m7r6d.execute-api.us-east-1.amazonaws.com/dev';
// Example: 'https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev'
// ────────────────────────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 3000;
const MAX_POLLS = 60; // ~3 minutes max

// ── DOM refs ───────────────────────────────────────────────────────────────
const dropZone       = document.getElementById('drop-zone');
const fileInput      = document.getElementById('file-input');
const browseBtn      = document.getElementById('browse-btn');
const uploadSection  = document.getElementById('upload-section');
const progressCard   = document.getElementById('progress-card');
const uploadZone     = document.querySelector('.upload-zone');
const progressBar    = document.getElementById('progress-bar');
const progressLabel  = document.getElementById('progress-label');
const progressSteps  = document.getElementById('progress-steps');
const reportSection  = document.getElementById('report-section');
const newReviewBtn   = document.getElementById('new-review-btn');

// ── Drag & Drop ─────────────────────────────────────────────────────────────
dropZone.addEventListener('click', (e) => {
  if (e.target !== browseBtn) fileInput.click();
});
browseBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) processFile(file);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) processFile(fileInput.files[0]);
});

newReviewBtn.addEventListener('click', resetUI);

// ── Main Flow ────────────────────────────────────────────────────────────────
async function processFile(file) {
  showProgress('Requesting upload URL…', 10, 'Step 1 of 3');

  try {
    // 1. Get presigned URL
    const { uploadUrl, jobId } = await getPresignedUrl(file.type || 'image/png');
    showProgress('Uploading diagram to S3…', 40, 'Step 2 of 3');

    // 2. Upload directly to S3
    await uploadToS3(uploadUrl, file);
    showProgress('Analyzing with Amazon Bedrock…', 70, 'Step 3 of 3 — Claude is thinking…');

    // 3. Poll for report
    const report = await pollReport(jobId);
    renderReport(report);

  } catch (err) {
    console.error(err);
    showError(err.message || 'An unexpected error occurred.');
  }
}

// ── API Calls ────────────────────────────────────────────────────────────────
async function getPresignedUrl(fileType) {
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fileType }),
  });
  if (!res.ok) throw new Error(`Upload URL request failed (${res.status})`);
  return res.json();
}

async function uploadToS3(presignedUrl, file) {
  const res = await fetch(presignedUrl, {
    method: 'PUT',
    headers: { 'Content-Type': file.type || 'image/png' },
    body: file,
  });
  if (!res.ok) throw new Error(`S3 upload failed (${res.status})`);
}

async function pollReport(jobId) {
  for (let i = 0; i < MAX_POLLS; i++) {
    await sleep(POLL_INTERVAL_MS);
    const res = await fetch(`${API_BASE}/report/${jobId}`);
    const data = await res.json();

    if (res.status === 200 && data.status !== 'processing') {
      if (data.status === 'error') throw new Error(data.message || 'Analysis failed');
      return data;
    }

    // Animate the waiting message
    const dots = '.'.repeat((i % 3) + 1);
    showProgress(`Claude is analyzing your architecture${dots}`, 70 + Math.min(i * 0.5, 25), 'Step 3 of 3 — Claude is thinking…');
  }
  throw new Error('Analysis timed out. Please try again.');
}

// ── Progress UI ───────────────────────────────────────────────────────────────
function showProgress(label, percent, steps) {
  uploadZone.classList.add('hidden');
  progressCard.classList.remove('hidden');
  reportSection.classList.add('hidden');
  progressLabel.textContent = label;
  progressBar.style.width = `${percent}%`;
  progressSteps.textContent = steps;
}

function showError(msg) {
  progressCard.classList.add('hidden');
  uploadZone.classList.remove('hidden');
  uploadZone.querySelector('h3').textContent = '❌ ' + msg;
  setTimeout(() => { uploadZone.querySelector('h3').textContent = 'Drop your architecture diagram'; }, 4000);
}

function resetUI() {
  reportSection.classList.add('hidden');
  progressCard.classList.add('hidden');
  uploadZone.classList.remove('hidden');
  progressBar.style.width = '0%';
  fileInput.value = '';
}

// ── Report Renderer ──────────────────────────────────────────────────────────
function renderReport(r) {
  progressCard.classList.add('hidden');
  reportSection.classList.remove('hidden');

  // Risk badge
  const riskMap = { HIGH: '🔴', MEDIUM: '🟡', LOW: '🟢' };
  document.getElementById('risk-badge').textContent = riskMap[r.overallRisk] || '⚪';
  document.getElementById('report-summary-text').textContent = r.summary || '';

  // Detected services
  const chipsEl = document.getElementById('services-chips');
  chipsEl.innerHTML = '';
  (r.detectedServices || []).forEach(s => {
    const el = document.createElement('span');
    el.className = 'service-chip';
    el.textContent = s;
    chipsEl.appendChild(el);
  });

  // Pillar scores
  renderPillars(r.pillarScores || {});

  // Positives
  const positivesList = document.getElementById('positives-list');
  positivesList.innerHTML = '';
  (r.positives || []).forEach(p => {
    const li = document.createElement('li');
    li.textContent = p;
    positivesList.appendChild(li);
  });

  // Issues
  const issuesGrid = document.getElementById('issues-grid');
  issuesGrid.innerHTML = '';
  (r.issues || []).forEach(issue => issuesGrid.appendChild(buildIssueCard(issue)));

  // Recommendations
  const recsGrid = document.getElementById('recs-grid');
  recsGrid.innerHTML = '';
  (r.recommendations || []).forEach(rec => recsGrid.appendChild(buildRecCard(rec)));

  // WAF Risks
  const wafList = document.getElementById('waf-list');
  wafList.innerHTML = '';
  (r.wellArchitectedRisks || []).forEach(risk => wafList.appendChild(buildWafItem(risk)));

  // Scroll into view
  reportSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderPillars(scores) {
  const pillarNames = {
    operationalExcellence: 'Operational Excellence',
    security:              'Security',
    reliability:           'Reliability',
    performanceEfficiency: 'Performance Efficiency',
    costOptimization:      'Cost Optimization',
    sustainability:        'Sustainability',
  };
  const grid = document.getElementById('pillars-grid');
  grid.innerHTML = '';

  Object.entries(pillarNames).forEach(([key, label]) => {
    const data = scores[key] || { score: 0, comment: '' };
    const score = data.score || 0;
    const pct = (score / 5) * 100;
    const color = score >= 4 ? '#22c55e' : score >= 3 ? '#f59e0b' : '#ef4444';

    const div = document.createElement('div');
    div.className = 'pillar-item';
    div.innerHTML = `
      <div class="pillar-name">${label}</div>
      <div class="pillar-bar-track">
        <div class="pillar-bar-fill" style="width:0%;background:${color}" data-target="${pct}"></div>
      </div>
      <div class="pillar-meta">
        <span>${data.comment || ''}</span>
        <span>${score}/5</span>
      </div>`;
    grid.appendChild(div);
  });

  // Animate bars after a tick
  requestAnimationFrame(() => {
    document.querySelectorAll('.pillar-bar-fill').forEach(bar => {
      bar.style.width = bar.dataset.target + '%';
    });
  });
}

function buildIssueCard(issue) {
  const div = document.createElement('div');
  div.className = `issue-card ${issue.severity || 'MEDIUM'}`;
  div.innerHTML = `
    <div class="issue-header">
      <span class="severity-tag ${issue.severity || 'MEDIUM'}">${issue.severity || 'MEDIUM'}</span>
      <span class="pillar-tag">${issue.pillar || ''}</span>
    </div>
    <div class="issue-title">${issue.title || ''}</div>
    <div class="issue-desc">${issue.description || ''}</div>
    ${issue.impact ? `<div class="issue-impact"><strong>Impact:</strong> ${issue.impact}</div>` : ''}`;
  return div;
}

function buildRecCard(rec) {
  const div = document.createElement('div');
  div.className = `rec-card ${rec.priority || 'MEDIUM'}`;
  const services = (rec.awsServices || []).map(s => `<span class="service-tag">${s}</span>`).join('');
  div.innerHTML = `
    <div class="rec-header">
      <span class="priority-tag ${rec.priority || 'MEDIUM'}">${rec.priority || 'MEDIUM'} PRIORITY</span>
    </div>
    <div class="rec-title">${rec.title || ''}</div>
    <div class="rec-desc">${rec.description || ''}</div>
    ${services ? `<div class="rec-services">${services}</div>` : ''}`;
  return div;
}

function buildWafItem(risk) {
  const div = document.createElement('div');
  div.className = 'waf-item';
  div.innerHTML = `
    <div class="waf-risk-dot ${risk.risk || 'MEDIUM'}"></div>
    <div>
      <div class="waf-pillar">${risk.pillar || ''}</div>
      <div class="waf-finding">${risk.finding || ''}</div>
    </div>`;
  return div;
}

// ── Helpers ──────────────────────────────────────────────────────────────────
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
