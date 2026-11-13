/**
 * ResumeX — Resume Upload & Analysis Controller (analyze.js)
 */

document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('resume-file');
  const filePreview = document.getElementById('file-preview');
  const fileNameDisplay = document.getElementById('file-name');
  const fileSizeDisplay = document.getElementById('file-size');
  const btnRemoveFile = document.getElementById('btn-remove-file');

  const analyzeForm = document.getElementById('analyze-form');
  const jobTitleInput = document.getElementById('job-title');
  const companyNameInput = document.getElementById('company-name');
  const jobDescInput = document.getElementById('job-description');
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnText = document.getElementById('btn-text');
  const errorBox = document.getElementById('analyze-error');

  let selectedFile = null;
  const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
  const ALLOWED_EXTS = ['.pdf', '.docx'];

  function showError(msg) {
    if (errorBox) {
      errorBox.textContent = msg;
      errorBox.style.display = 'block';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      showToast(msg, 'error');
    }
  }

  function clearError() {
    if (errorBox) {
      errorBox.textContent = '';
      errorBox.style.display = 'none';
    }
  }

  // ─────────────────────────────────────────────────────────────
  // FILE SELECTION & DRAG-AND-DROP
  // ─────────────────────────────────────────────────────────────
  if (dropzone && fileInput) {
    // Click to select
    dropzone.addEventListener('click', () => fileInput.click());

    // Drag events
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    // Handle Drop
    dropzone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0) {
        validateAndSetFile(files[0]);
      }
    });

    // Handle File Input Change
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        validateAndSetFile(fileInput.files[0]);
      }
    });
  }

  function validateAndSetFile(file) {
    clearError();

    // Check extension
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      showError(`Invalid format "${file.name}". Please upload a PDF or DOCX resume document.`);
      return;
    }

    // Check size limit (5MB)
    if (file.size > MAX_SIZE_BYTES) {
      showError(`File size exceeds 5MB limit (${formatBytes(file.size)}). Please upload a smaller file.`);
      return;
    }

    selectedFile = file;

    // Show preview UI
    if (dropzone) dropzone.style.display = 'none';
    if (filePreview) {
      fileNameDisplay.textContent = file.name;
      fileSizeDisplay.textContent = formatBytes(file.size);
      filePreview.style.display = 'flex';
    }
  }

  // Remove file handler
  if (btnRemoveFile) {
    btnRemoveFile.addEventListener('click', () => {
      selectedFile = null;
      if (fileInput) fileInput.value = '';
      if (filePreview) filePreview.style.display = 'none';
      if (dropzone) dropzone.style.display = 'flex';
      clearError();
    });
  }

  // ─────────────────────────────────────────────────────────────
  // FORM SUBMISSION & PIPELINE ORCHESTRATION
  // ─────────────────────────────────────────────────────────────
  if (analyzeForm) {
    analyzeForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearError();

      if (!selectedFile) {
        showError('Please upload a resume file (PDF or DOCX) to begin analysis.');
        return;
      }

      const jobTitle = jobTitleInput.value.trim();
      const companyName = companyNameInput.value.trim();
      const jobDescription = jobDescInput.value.trim();

      if (!jobTitle) {
        showError('Please provide a target job title.');
        return;
      }

      if (!jobDescription || jobDescription.length < 50) {
        showError('Please enter a comprehensive job description (at least 50 characters) to benchmark against.');
        return;
      }

      // Enter Loading State
      btnAnalyze.disabled = true;
      btnText.innerHTML = `<span class="spinner"></span> Step 1/2: Uploading & Parsing Document...`;

      try {
        // Step 1: Upload Resume Document
        const formData = new FormData();
        formData.append('resume', selectedFile);

        const uploadRes = await fetch(`${API_BASE}/resumes/upload`, {
          method: 'POST',
          credentials: 'include',
          body: formData
        });

        const uploadData = await uploadRes.json();
        if (!uploadRes.ok) {
          throw new Error(uploadData.error || 'Failed to parse and upload resume document.');
        }

        const resumeId = uploadData.resume.id;

        // Step 2: Trigger TF-IDF & Skill Matching Analysis
        btnText.innerHTML = `<span class="spinner"></span> Step 2/2: Computing Vector Match & Skill Audit...`;

        const analyzeRes = await fetch(`${API_BASE}/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            resume_id: resumeId,
            job_title: jobTitle,
            company_name: companyName,
            job_description: jobDescription
          })
        });

        const analyzeData = await analyzeRes.json();
        if (!analyzeRes.ok) {
          throw new Error(analyzeData.error || 'Analysis failed to execute.');
        }

        showToast('Evaluation complete! Redirecting to report...', 'success');
        setTimeout(() => {
          window.location.href = `/results.html?id=${analyzeData.analysis.id}`;
        }, 400);

      } catch (err) {
        console.error('Analysis workflow error:', err);
        showError(err.message || 'An unexpected error occurred during analysis.');
        btnAnalyze.disabled = false;
        btnText.textContent = 'Run Resume Analysis';
      }
    });
  }
});

