/**
 * ResumeX — Dashboard & History Controller (dashboard.js)
 */

document.addEventListener('DOMContentLoaded', async () => {
  const isDashboardPage = !!document.getElementById('recent-analyses-body');
  const isHistoryPage = !!document.getElementById('history-table-body');

  if (isDashboardPage) {
    loadDashboardData();
  }

  if (isHistoryPage) {
    loadHistoryData();
  }
});

/**
 * Fetch and populate dashboard summary stats and recent analyses
 */
async function loadDashboardData() {
  const statTotal = document.getElementById('stat-total');
  const statAvg = document.getElementById('stat-avg');
  const statResumes = document.getElementById('stat-resumes');
  const tbody = document.getElementById('recent-analyses-body');

  try {
    // 1. Fetch Analyses
    const analysesRes = await fetch(`${API_BASE}/analyses`, { credentials: 'include' });
    const analysesData = await analysesRes.json();
    const analyses = analysesData.analyses || [];

    // 2. Fetch Resumes Count
    const resumesRes = await fetch(`${API_BASE}/resumes`, { credentials: 'include' });
    const resumesData = await resumesRes.json();
    const resumes = resumesData.resumes || [];

    // Compute metrics
    if (statTotal) statTotal.textContent = analyses.length;
    if (statResumes) statResumes.textContent = resumes.length;

    if (statAvg) {
      if (analyses.length > 0) {
        const sum = analyses.reduce((acc, a) => acc + (a.overall_score || 0), 0);
        const avg = Math.round(sum / analyses.length);
        statAvg.textContent = `${avg}%`;
      } else {
        statAvg.textContent = '0%';
      }
    }

    // Render Recent Analyses (up to 5)
    if (tbody) {
      if (analyses.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="6" class="empty-state">
              <p>No analyses performed yet.</p>
              <a href="/analyze.html" class="btn btn-primary btn-sm">Analyze Your First Resume</a>
            </td>
          </tr>
        `;
        return;
      }

      const recent = analyses.slice(0, 5);
      tbody.innerHTML = recent.map(item => `
        <tr>
          <td style="font-weight: 500; color: var(--text-primary);">${escapeHtml(item.job_title || 'Untitled Role')}</td>
          <td>${escapeHtml(item.company_name || '—')}</td>
          <td>
            <span class="score-badge ${getScoreClass(item.overall_score)}">
              ${Math.round(item.overall_score)}%
            </span>
          </td>
          <td>${escapeHtml(item.resume_filename || 'Resume Document')}</td>
          <td>${formatDate(item.created_at)}</td>
          <td>
            <a href="/results.html?id=${item.id}" class="btn btn-outline btn-sm">View Insights</a>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load dashboard statistics:', err);
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-state" style="color: #E2A1A1;">
            Failed to load analysis history. Please refresh the page.
          </td>
        </tr>
      `;
    }
  }
}

/**
 * Fetch and populate complete historical record list
 */
async function loadHistoryData() {
  const tbody = document.getElementById('history-table-body');
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/analyses`, { credentials: 'include' });
    const data = await res.json();
    const analyses = data.analyses || [];

    if (analyses.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-state">
            <p>You have not conducted any resume evaluations yet.</p>
            <a href="/analyze.html" class="btn btn-primary btn-sm">Run First Evaluation</a>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = analyses.map(item => `
      <tr>
        <td style="font-weight: 500; color: var(--text-primary);">${escapeHtml(item.job_title || 'Untitled Role')}</td>
        <td>${escapeHtml(item.company_name || '—')}</td>
        <td>
          <span class="score-badge ${getScoreClass(item.overall_score)}">
            ${Math.round(item.overall_score)}%
          </span>
        </td>
        <td>${escapeHtml(item.resume_filename || 'Document')}</td>
        <td>${formatDate(item.created_at)}</td>
        <td style="display: flex; gap: 8px;">
          <a href="/results.html?id=${item.id}" class="btn btn-outline btn-sm">View</a>
          <button onclick="deleteAnalysisRecord(${item.id})" class="btn btn-danger btn-sm" title="Delete Analysis">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('History load error:', err);
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="empty-state" style="color: #E2A1A1;">
          Failed to load historical evaluations.
        </td>
      </tr>
    `;
  }
}

/**
 * Delete an analysis record
 */
async function deleteAnalysisRecord(id) {
  if (!confirm('Are you sure you want to delete this analysis record? This cannot be undone.')) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/analyses/${id}`, {
      method: 'DELETE',
      credentials: 'include'
    });

    if (res.ok) {
      showToast('Record deleted successfully.', 'success');
      loadHistoryData();
    } else {
      const err = await res.json();
      showToast(err.error || 'Failed to delete record.', 'error');
    }
  } catch (err) {
    console.error('Delete error:', err);
    showToast('Failed to connect to server.', 'error');
  }
}

/**
 * Return CSS score tier badge
 */
function getScoreClass(score) {
  if (score >= 70) return 'score-high';
  if (score >= 45) return 'score-mid';
  return 'score-low';
}

