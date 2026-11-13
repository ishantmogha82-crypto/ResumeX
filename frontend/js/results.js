/**
 * ResumeX — Results Dashboard & Report Viewer (results.js)
 */

document.addEventListener('DOMContentLoaded', async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const analysisId = urlParams.get('id');

  if (!analysisId) {
    showToast('No analysis ID provided. Redirecting to dashboard...', 'error');
    setTimeout(() => window.location.href = '/dashboard.html', 1500);
    return;
  }

  await loadAnalysisResults(analysisId);

  // Bind PDF Download Button
  const btnDownloadPdf = document.getElementById('btn-download-pdf');
  if (btnDownloadPdf) {
    btnDownloadPdf.addEventListener('click', () => {
      window.open(`${API_BASE}/reports/${analysisId}/pdf`, '_blank');
    });
  }
});

async function loadAnalysisResults(id) {
  const loader = document.getElementById('results-loader');
  const wrapper = document.getElementById('results-wrapper');

  try {
    const res = await fetch(`${API_BASE}/analyses/${id}`, { credentials: 'include' });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Unable to retrieve analysis report.');
    }

    const item = data.analysis;
    renderResults(item);

    if (loader) loader.style.display = 'none';
    if (wrapper) wrapper.style.display = 'block';

  } catch (err) {
    console.error('Failed to load analysis results:', err);
    if (loader) {
      loader.innerHTML = `
        <div style="color: #E2A1A1; text-align: center;">
          <h3>Failed to Load Evaluation</h3>
          <p style="margin: 12px 0 20px;">${escapeHtml(err.message)}</p>
          <a href="/dashboard.html" class="btn btn-secondary">Return to Dashboard</a>
        </div>
      `;
    }
  }
}

function renderResults(item) {
  // Title & Metadata
  const jobTitleEl = document.getElementById('res-job-title');
  const metaSubEl = document.getElementById('res-meta-sub');
  if (jobTitleEl) jobTitleEl.textContent = item.job_title || 'Untitled Target Role';
  if (metaSubEl) {
    const company = item.company_name ? `at ${item.company_name}` : '';
    metaSubEl.textContent = `Target: ${item.job_title} ${company} • Document: ${item.resume_filename || 'Uploaded Resume'}`;
  }

  // Scores
  const overall = Math.round(item.overall_score || 0);
  const skillScore = Math.round(item.skill_match_score || 0);
  const semanticScore = Math.round(item.similarity_score || 0);

  const overallEl = document.getElementById('overall-score-val');
  const skillEl = document.getElementById('skill-score-val');
  const semanticEl = document.getElementById('semantic-score-val');
  const circle = document.getElementById('score-circle');

  if (overallEl) overallEl.textContent = `${overall}%`;
  if (skillEl) skillEl.textContent = `${skillScore}%`;
  if (semanticEl) semanticEl.textContent = `${semanticScore}%`;

  if (circle) {
    const deg = Math.round((overall / 100) * 360);
    circle.style.setProperty('--score-deg', `${deg}deg`);
  }

  // Matched Skills
  const matchedSkills = item.matched_skills || [];
  const matchedCountVal = document.getElementById('matched-count-val');
  const matchedPill = document.getElementById('matched-pill');
  const matchedContainer = document.getElementById('matched-skills-container');

  if (matchedCountVal) matchedCountVal.textContent = matchedSkills.length;
  if (matchedPill) matchedPill.textContent = `${matchedSkills.length} Verified`;

  if (matchedContainer) {
    if (matchedSkills.length === 0) {
      matchedContainer.innerHTML = `<span style="color: var(--text-muted); font-size: 13px;">No direct required skills detected from the job description.</span>`;
    } else {
      matchedContainer.innerHTML = matchedSkills.map(s => `
        <span class="skill-tag matched">
          <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
          </svg>
          ${escapeHtml(s)}
        </span>
      `).join('');
    }
  }

  // Missing Skills
  const missingSkills = item.missing_skills || [];
  const missingPill = document.getElementById('missing-pill');
  const missingContainer = document.getElementById('missing-skills-container');

  if (missingPill) missingPill.textContent = `${missingSkills.length} Detected Gaps`;

  if (missingContainer) {
    if (missingSkills.length === 0) {
      missingContainer.innerHTML = `<span style="color: var(--text-secondary); font-size: 13px;">No critical skill gaps identified! Great alignment.</span>`;
    } else {
      missingContainer.innerHTML = missingSkills.map(s => `
        <span class="skill-tag missing">
          <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          ${escapeHtml(s)}
        </span>
      `).join('');
    }
  }

  // All Resume Skills
  const resumeSkills = item.resume_skills || [];
  const totalResumeSkillsPill = document.getElementById('total-resume-skills-pill');
  const resumeSkillsContainer = document.getElementById('resume-skills-container');

  if (totalResumeSkillsPill) totalResumeSkillsPill.textContent = `${resumeSkills.length} Total Extracted`;
  if (resumeSkillsContainer) {
    if (resumeSkills.length === 0) {
      resumeSkillsContainer.innerHTML = `<span style="color: var(--text-muted); font-size: 13px;">No standardized skills catalogued.</span>`;
    } else {
      resumeSkillsContainer.innerHTML = resumeSkills.map(s => `
        <span class="skill-tag neutral">${escapeHtml(s)}</span>
      `).join('');
    }
  }

  // Section Quality Audit (6 Sections)
  const sections = item.section_analysis || {};
  const sectionGrid = document.getElementById('section-grid');

  const sectionDefinitions = [
    { key: 'contact_info', name: 'Contact Information', hint: 'Email, phone, location, LinkedIn' },
    { key: 'education', name: 'Education & Academics', hint: 'Degrees, universities, graduation dates' },
    { key: 'experience', name: 'Work Experience', hint: 'Employment history, job roles, metrics' },
    { key: 'projects', name: 'Technical Projects', hint: 'Key deliverables, repositories, impact' },
    { key: 'skills', name: 'Skills Section', hint: 'Dedicated technical & soft skills block' },
    { key: 'certifications', name: 'Certifications', hint: 'Industry accreditations and credentials' }
  ];

  if (sectionGrid) {
    sectionGrid.innerHTML = sectionDefinitions.map(def => {
      const isDetected = !!sections[def.key];
      return `
        <div class="section-status-card">
          <div class="section-info">
            <h4>${escapeHtml(def.name)}</h4>
            <p>${escapeHtml(def.hint)}</p>
          </div>
          <span class="status-indicator ${isDetected ? 'detected' : 'not-detected'}">
            ${isDetected ? '✓ Detected' : '✕ Missing'}
          </span>
        </div>
      `;
    }).join('');
  }

  // Actionable Improvement Recommendations
  const recs = item.recommendations || [];
  const recsList = document.getElementById('recommendations-list');

  if (recsList) {
    if (recs.length === 0) {
      recsList.innerHTML = `<p style="color: var(--text-secondary);">Your resume strongly mirrors the target job posting!</p>`;
    } else {
      recsList.innerHTML = recs.map((rec, idx) => `
        <div class="rec-item">
          <div class="rec-number">${String(idx + 1).padStart(2, '0')}</div>
          <div class="rec-content">
            <h5>${escapeHtml(rec.title || 'Optimization Opportunity')}</h5>
            <p>${escapeHtml(rec.description || rec)}</p>
          </div>
        </div>
      `).join('');
    }
  }
}
