// IIFE to avoid polluting the global namespace
(function () {
  "use strict";

  // UTILITY FUNCTIONS
  const byId = (id) => document.getElementById(id);
  const query = (selector) => document.querySelector(selector);
  const queryAll = (selector) => document.querySelectorAll(selector);

  async function fetchJson(url, options = {}) {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `Request failed with status ${response.status}` }));
        throw new Error(errorData.error || `Request failed`);
      }
      return response.json();
    } catch (error) {
      console.error(`Fetch error for ${url}:`, error);
      throw error;
    }
  }

  const formatBytes = (bytes) => {
    bytes = Number(bytes);
    if (!bytes || bytes === 0) return "0 B";
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  };

  const generateProgressBar = (percent, barLength = 20) => {
    const p = Math.max(0, Math.min(100, percent));
    const filled = Math.round(barLength * (p / 100));
    let bar = "";
    if (filled === 0) {
      bar = ">" + " ".repeat(barLength - 1);
    } else if (filled === barLength) {
      bar = "=".repeat(barLength);
    } else {
      bar = "=".repeat(filled - 1) + ">" + " ".repeat(barLength - filled);
    }
    return `[${bar}] ${p}%`;
  };


  // --- PATH PREVIEW ---

  function updateOutputPathPreview() {
    const form = byId("job-form");
    if (!form) return;
    const outputName = byId("output-name");
    const gpuCountInput = byId("gpu-count");
    const gpuAvailableLabel = byId("gpu-available");
    const gpuAvailableCount = byId("gpu-available-count");
    const previewList = byId("output-path-preview-list");
    if (!previewList) return;

    const country = byId("country")?.value || "<country>";
    const yearSuffix = byId("year-suffix")?.value || "<year>";
    const selectedStates = Array.from(form.querySelectorAll("input[name='states']:checked")).map(el => el.value);
    const stateSample = selectedStates[0] || "<state>";
    const cropSample = (byId("target-crops")?.value.split(',')[0].trim() || "<crop>");

    const root = form.dataset.outputRoot || "";
    const name = outputName.value.trim();
    const base = name ? `${root}/${name}` : root;

    previewList.innerHTML = `
      <li class="list-group-item"><strong>Input Root:</strong><br><small class="text-muted">${form.dataset.inputRoot || "Not Set"}</small></li>
      <li class="list-group-item"><strong>Output Root:</strong><br><small class="text-muted">${base}</small></li>
      <li class="list-group-item">
        <strong>Inference Tiles:</strong><br>
        <small class="text-muted">${base}/inference_tiles/${yearSuffix}/${country}/${stateSample}/${cropSample}/<...>.tif</small>
      </li>
      <li class="list-group-item">
        <strong>Merged Masks:</strong><br>
        <small class="text-muted">${base}/merged_cropmasks/${yearSuffix}/${country}/${stateSample}/${cropSample}/<...>.tif</small>
      </li>
      <li class="list-group-item">
        <strong>Area CSV:</strong><br>
        <small class="text-muted">${base}/calculate_area/${yearSuffix}_${country}_${cropSample}.csv</small>
      </li>
    `;
  }

  // --- DASHBOARD AND JOB FORM ---

  function handleJobForm() {
    const form = byId("job-form");
    if (!form) return;

    const yearSelect = byId("year-suffix");
    const countrySelect = byId("country");
    const statesContainer = byId("states");
    const pipelineSelect = byId("pipeline-config");
    const targetCrops = byId("target-crops");
    const outputName = byId("output-name");
    const selectAllBtn = byId("select-all-states");
    const deselectAllBtn = byId("deselect-all-states");

    async function updateStates() {
      if (!yearSelect.value || !countrySelect.value) {
        statesContainer.innerHTML = `<small class="text-muted">Select a country and year first.</small>`;
        return;
      }
      try {
        const states = await fetchJson(`/core/input/states/?year_suffix=${yearSelect.value}&country=${countrySelect.value}`);
        statesContainer.innerHTML = "";
        if (!states.items || !states.items.length) {
            statesContainer.innerHTML = `<small class="text-muted">No states found for this selection.</small>`;
            return;
        }
        states.items.forEach((state) => {
            const div = document.createElement("div");
            div.className = "form-check";
            div.innerHTML = `
                <input class="form-check-input" type="checkbox" value="${state}" id="state-${state}" name="states" checked>
                <label class="form-check-label" for="state-${state}">${state}</label>
            `;
            statesContainer.appendChild(div);
        });
        updateOutputPathPreview();
      } catch (error) {
        statesContainer.innerHTML = `<small class="text-danger">Failed to load states.</small>`;
      }
    }

    async function updateYears() {
        if (!countrySelect.value) {
            yearSelect.innerHTML = "";
            return;
        }
        try {
            const years = await fetchJson(`/core/input/years/?country=${countrySelect.value}`);
            yearSelect.innerHTML = '<option value="">-- Select Year/Suffix --</option>';
            (years.items || []).forEach(item => {
                yearSelect.innerHTML += `<option value="${item}">${item}</option>`;
            });
            updateStates();
        } catch (error) {
            yearSelect.innerHTML = '<option value="">-- Error --</option>';
        }
    }

    async function initializeSelectors() {
        try {
            const countryData = await fetchJson("/core/input/countries/");
            countrySelect.innerHTML = '<option value="">-- Select Country --</option>';
            (countryData.items || []).forEach(item => {
                countrySelect.innerHTML += `<option value="${item}">${item}</option>`;
            });
            updateYears();
        } catch (error) {
            countrySelect.innerHTML = '<option value="">-- Error --</option>';
        }
    }

    async function loadAvailableGpus() {
        const gpuAvailableLabel = byId("gpu-available");
        const gpuAvailableCount = byId("gpu-available-count");
        const gpuCountInput = byId("gpu-count");

        if (!gpuAvailableLabel || !gpuAvailableCount) return;
        try {
            const data = await fetchJson("/core/gpu/available/");
            const available = Number(data.available || 0);
            gpuAvailableLabel.textContent = `/ ${available}`;
            gpuAvailableCount.textContent = `${available}`;
            if (gpuCountInput) {
                gpuCountInput.max = String(available);
                if (gpuCountInput.value && Number(gpuCountInput.value) > available) {
                    gpuCountInput.value = String(available);
                }
            }
        } catch (error) {
            gpuAvailableLabel.textContent = "/ 0";
            gpuAvailableCount.textContent = "0";
            if (gpuCountInput) {
                gpuCountInput.max = "0";
            }
        }
    }

    const gpuCountInput = byId("gpu-count");
    gpuCountInput?.addEventListener("input", () => {
        const value = Number(gpuCountInput.value);
        if (value === -1) {
            return;
        }
        const max = Number(gpuCountInput.max || "0");
        if (value > max) {
            gpuCountInput.value = String(max);
        }
    });

    selectAllBtn?.addEventListener('click', () => {
        statesContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = true);
        updateOutputPathPreview();
    });

    deselectAllBtn?.addEventListener('click', () => {
        statesContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        updateOutputPathPreview();
    });

    countrySelect?.addEventListener("change", () => {
        updateYears();
        updateOutputPathPreview();
        const countryCode = countrySelect.value;
        const options = Array.from(pipelineSelect.options);
        options.forEach(option => {
            if (!option.value) { // The "-- Manual --" option
                option.hidden = false;
                return;
            }
            const optionCountry = option.getAttribute("data-country") || "";
            option.hidden = !!countryCode && optionCountry && optionCountry !== countryCode;
        });
        if (pipelineSelect.value && options.find(o => o.value === pipelineSelect.value)?.hidden) {
            pipelineSelect.value = "";
            pipelineSelect.dispatchEvent(new Event('change'));
        }
    });

    yearSelect?.addEventListener("change", () => {
        updateStates();
        updateOutputPathPreview();
    });

    statesContainer.addEventListener('change', (e) => {
        if (e.target.type === 'checkbox') {
            updateOutputPathPreview();
        }
    });

    outputName?.addEventListener("input", updateOutputPathPreview);
    targetCrops?.addEventListener("input", updateOutputPathPreview);


    pipelineSelect?.addEventListener("change", () => {
      const option = pipelineSelect.options[pipelineSelect.selectedIndex];
      const crops = option ? option.getAttribute("data-crops") : "";
      if (crops) {
        targetCrops.value = crops;
        targetCrops.readOnly = true;
      } else {
        targetCrops.readOnly = false;
      }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submitButton = form.querySelector("button[type='submit']");
        if (submitButton.disabled) return;
        submitButton.disabled = true;

        const selectedStates = Array.from(statesContainer.querySelectorAll("input[name='states']:checked")).map(el => el.value);
        const resultBox = byId("job-result");

        const payload = {
            year_suffix: yearSelect.value,
            country: countrySelect.value,
            states: selectedStates,
            target_crops: targetCrops.value,
            output_name: byId("output-name").value,
            skip_inference: byId("skip-inference")?.checked,
            skip_merge: byId("skip-merge")?.checked,
            skip_area: byId("skip-area")?.checked,
            pipeline_config_id: pipelineSelect.value || null,
            schedule_at: byId("schedule-at").value || null,
            gpu_count: gpuCountInput?.value || null,
        };

        try {
            const data = await fetchJson("/core/jobs/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            resultBox.className = 'alert alert-success';
            resultBox.textContent = `Job ${data.job_id} created successfully. Redirecting...`;
            resultBox.hidden = false;
            window.location.href = `/core/jobs/${data.job_id}/`;
        } catch (error) {
            resultBox.className = 'alert alert-danger';
            resultBox.textContent = error.message || "Failed to create job.";
            resultBox.hidden = false;
            submitButton.disabled = false;
        }
    });

    if (countrySelect) {
      initializeSelectors();
      loadAvailableGpus();
      updateOutputPathPreview();
    }
  }

  // --- JOB DASHBOARD PAGE ---

  function handleJobDashboard() {
    const jobListBody = byId("job-list-body");
    if (!jobListBody) return;

    const getStatusClass = (status) => ({
      "PENDING": "bg-secondary",
      "RUNNING": "bg-info",
      "SUCCESS": "bg-success",
      "FAILED": "bg-danger",
      "CANCELLED": "bg-warning",
    }[status] || "bg-dark");

    const pollJobStatuses = async () => {
        const rows = queryAll("#job-list-body .job-row");
        const jobIds = Array.from(rows).map(row => row.dataset.jobId);
        if (jobIds.length === 0) return;

        for (const row of rows) {
            const jobId = row.dataset.jobId;
            try {
                const info = await fetchJson(`/core/jobs/${jobId}/info/`);
                const status = info.status || 'UNKNOWN';
                const statusBadge = row.querySelector(".job-status .badge");
                statusBadge.className = `badge rounded-pill ${getStatusClass(status)}`;
                statusBadge.textContent = `${status}${info.current_step ? ' (' + info.current_step + ')' : ''}`;

                const progressBar = row.querySelector(".job-progress .progress-bar");
                const percent = info.progress_percent || 0;
                progressBar.style.width = `${percent}%`;
                progressBar.textContent = `${percent}%`;
                progressBar.setAttribute("aria-valuenow", percent);

                if (status !== 'RUNNING') {
                    progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                } else if (!progressBar.classList.contains('progress-bar-animated')) {
                     progressBar.classList.add('progress-bar-animated', 'progress-bar-striped');
                }

            } catch (error) {
                 const statusBadge = row.querySelector(".job-status .badge");
                 statusBadge.className = 'badge rounded-pill bg-dark';
                 statusBadge.textContent = 'UNKNOWN';
            }
        }
    };

    jobListBody.addEventListener("click", (e) => {
        const row = e.target.closest("tr.job-row");
        if (row && row.dataset.href) {
            window.location.href = row.dataset.href;
        }
    });

    pollJobStatuses();
    setInterval(pollJobStatuses, 5000);
  }


  // --- JOB DETAIL PAGE ---

  function handleJobDetailPage() {
    const statusBadge = byId("job-status-badge");
    if (!statusBadge) return;

    const jobId = statusBadge.dataset.jobId;
    if(!jobId) return;

    const statusText = byId("job-status-text");
    const progressBar = byId("job-progress-bar");
    const errorBox = byId("error-box");
    const progressLog = byId("progress-log");
    const outputsContainer = byId("output-steps");
    const celeryStatusBox = byId("celery-status-box");
    const cancelBtn = byId("cancel-job");
    const retryBtn = byId("retry-job");

    const getStatusClass = (status, element) => {
      const isBadge = element === 'badge';
      const mapping = {
          "PENDING": { badge: "bg-secondary", text: "text-muted" },
          "RUNNING": { badge: "bg-info", text: "text-primary" },
          "SUCCESS": { badge: "bg-success", text: "text-success" },
          "FAILED": { badge: "bg-danger", text: "text-danger" },
          "CANCELLED": { badge: "bg-warning", text: "text-warning" },
      };
      return (mapping[status] || {badge: 'bg-dark', text: 'text-dark'})[element];
    };

    const pollJobInfo = async () => {
        try {
            const info = await fetchJson(`/core/jobs/${jobId}/info/`);
            const status = info.status || 'UNKNOWN';
            const percent = info.progress_percent || 0;

            statusBadge.className = `badge rounded-pill ${getStatusClass(status, 'badge')}`;
            statusBadge.textContent = status;

            statusText.className = `card-text ${getStatusClass(status, 'text')}`;
            statusText.textContent = info.current_step ? `Current step: ${info.current_step}` : "Job is not running.";
            if (status === 'SUCCESS') statusText.textContent = 'Job completed successfully.';

            progressBar.style.width = `${percent}%`;
            progressBar.textContent = `${percent}%`;
            progressBar.setAttribute("aria-valuenow", percent);

            if (status !== 'RUNNING') {
                progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
            } else if (!progressBar.classList.contains('progress-bar-animated')) {
                progressBar.classList.add('progress-bar-animated', 'progress-bar-striped');
            }

            if (info.error) {
                errorBox.textContent = info.error;
                errorBox.hidden = false;
            } else {
                errorBox.hidden = true;
            }
        } catch (error) {
            errorBox.textContent = `Failed to poll job info: ${error.message}`;
            errorBox.hidden = false;
        }
    };

    const pollProgressLog = async () => {
        try {
            const progress = await fetchJson(`/core/jobs/${jobId}/progress/`);
            progressLog.innerHTML = '';
            const allSteps = Object.values(progress.steps || {}).flat();
            if (allSteps.length === 0) {
                 progressLog.innerHTML = '<div class="text-muted">Waiting for progress updates...</div>';
                 return;
            }
            allSteps.forEach(p => {
                if (p.message) {
                    const time = new Date().toLocaleTimeString();
                    const entry = document.createElement('div');
                    entry.className = 'log-entry';
                    const progressBarHtml = generateProgressBar(Number(p.percent || 0));
                    entry.innerHTML = `<span class="log-time">${time}</span> ${progressBarHtml} ${p.message}`;
                    progressLog.appendChild(entry);
                }
            });
            progressLog.scrollTop = progressLog.scrollHeight;
        } catch (error) {
            console.error("Failed to poll progress log:", error);
        }
    };

    const pollOutputs = async () => {
        try {
            const outputs = await fetchJson(`/core/jobs/${jobId}/outputs/`);
            outputsContainer.innerHTML = '';
            const steps = outputs.steps || {};
            const logs = outputs.logs || [];
            if (Object.keys(steps).length === 0 && logs.length === 0) {
                 outputsContainer.innerHTML = '<div class="text-muted">No outputs generated yet.</div>';
                 return;
            }

            const downloadAllButton = `
                <div class="d-flex justify-content-end mb-3">
                    <a href="/core/jobs/${jobId}/outputs/download-zip/" class="btn btn-success">
                        <i class="bi bi-archive-fill"></i> Download All as ZIP
                    </a>
                </div>
            `;
            outputsContainer.innerHTML = downloadAllButton;

            const accordion = document.createElement('div');
            accordion.className = 'accordion';
            accordion.id = 'outputs-accordion';

            const logsExpanded = logs.length > 0 && Object.keys(steps).length === 0;
            const logsBody = logs.length > 0
                ? `<ul class="list-group list-group-flush">
                        ${logs.map(file => `
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <span>
                                    <i class="bi bi-file-earmark-text"></i>
                                    ${file.name}
                                    <small class="text-muted d-block">${formatBytes(file.size_bytes)}</small>
                                </span>
                                <a href="/core/jobs/${jobId}/logs/download/?name=${encodeURIComponent(file.name)}" class="btn btn-sm btn-outline-primary">
                                    <i class="bi bi-download"></i>
                                </a>
                            </li>
                        `).join('')}
                    </ul>`
                : `<div class="p-3 text-muted">No log files available yet.</div>`;

            const logsItem = document.createElement('div');
            logsItem.className = 'accordion-item';
            logsItem.innerHTML = `
                <h2 class="accordion-header" id="heading-logs">
                    <button class="accordion-button ${logsExpanded ? '' : 'collapsed'}" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-logs" aria-expanded="${logsExpanded}" aria-controls="collapse-logs">
                        Logs <span class="badge bg-secondary ms-2">${logs.length}</span>
                    </button>
                </h2>
                <div id="collapse-logs" class="accordion-collapse collapse ${logsExpanded ? 'show' : ''}" aria-labelledby="heading-logs" data-bs-parent="#outputs-accordion">
                    <div class="accordion-body p-0">
                        ${logsBody}
                    </div>
                </div>
            `;
            accordion.appendChild(logsItem);

            Object.entries(steps).forEach(([step, files], index) => {
                if (files.length === 0) return;
                const stepId = `step-${step}`;
                const item = document.createElement('div');
                item.className = 'accordion-item';

                const stepDownloadButton = `
                    <div class="d-flex justify-content-end p-2">
                        <a href="/core/jobs/${jobId}/outputs/download-zip/?step=${step}" class="btn btn-sm btn-outline-success">
                            <i class="bi bi-archive"></i> Download Step ZIP
                        </a>
                    </div>
                `;

                item.innerHTML = `
                    <h2 class="accordion-header" id="heading-${stepId}">
                        <button class="accordion-button ${index > 0 ? 'collapsed' : ''}" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-${stepId}" aria-expanded="${index === 0}" aria-controls="collapse-${stepId}">
                            ${step} <span class="badge bg-secondary ms-2">${files.length}</span>
                        </button>
                    </h2>
                    <div id="collapse-${stepId}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}" aria-labelledby="heading-${stepId}" data-bs-parent="#outputs-accordion">
                        <div class="accordion-body output-list">
                            ${stepDownloadButton}
                            <ul class="list-group">
                            ${files.map(file => `
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    <span>
                                        <i class="bi bi-file-earmark-text"></i>
                                        ${file.relative_path}
                                        <small class="text-muted d-block">${formatBytes(file.size_bytes)}</small>
                                    </span>
                                    <a href="/core/jobs/${jobId}/outputs/download/?path=${encodeURIComponent(file.relative_path)}" class="btn btn-sm btn-outline-primary">
                                        <i class="bi bi-download"></i>
                                    </a>
                                </li>
                            `).join('')}
                            </ul>
                        </div>
                    </div>
                `;
                accordion.appendChild(item);
            });
            outputsContainer.appendChild(accordion);

        } catch (error) {
            // silent fail
        }
    };

     const pollCeleryStatus = async () => {
        try {
            const status = await fetchJson(`/core/jobs/${jobId}/task-status/`);
            celeryStatusBox.textContent = JSON.stringify(status, null, 2);
        } catch (error) {
            celeryStatusBox.textContent = `Failed to load Celery status: ${error.message}`;
        }
    };

    cancelBtn?.addEventListener("click", async () => {
      if (confirm('Are you sure you want to cancel this job?')) {
        await fetchJson(`/core/jobs/${jobId}/cancel/`, { method: "POST" });
        pollJobInfo();
        setTimeout(() => window.location.reload(), 1000);
      }
    });

    retryBtn?.addEventListener("click", async () => {
        if (confirm('Are you sure you want to retry this job?')) {
            const payload = {
                skip_inference: byId("retry-skip-inference")?.checked,
                skip_merge: byId("retry-skip-merge")?.checked,
                skip_area: byId("retry-skip-area")?.checked,
            };
            await fetchJson(`/core/jobs/${jobId}/retry/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            pollJobInfo();
            setTimeout(() => window.location.reload(), 1000);
        }
    });

    // Initial polls
    pollJobInfo();
    pollProgressLog();
    pollOutputs();
    pollCeleryStatus();

    // Setup intervals
    setInterval(pollJobInfo, 5000);
    setInterval(pollProgressLog, 7000);
    setInterval(pollOutputs, 30000);
    setInterval(pollCeleryStatus, 30000);
  }

  function handleJobDetailMap() {
    const mapContainer = byId("job-detail-map");
    if (!mapContainer) return;

    const statusBadge = byId("job-status-badge");
    const jobId = statusBadge?.dataset.jobId;
    if (!jobId) return;

    let map;
    let overlayLayers = [];
    let layerControl;
    const mapTab = byId('maps-tab');
    mapTab.addEventListener('shown.bs.tab', async event => {
        if (!map) {
            map = L.map(mapContainer).setView([0, 0], 2);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
        }
        map.invalidateSize();

        if (overlayLayers.length > 0) {
            overlayLayers.forEach(layer => map.removeLayer(layer));
            overlayLayers = [];
        }
        if (layerControl) {
            map.removeControl(layerControl);
            layerControl = null;
        }

        try {
            const outputs = await fetchJson(`/core/jobs/${jobId}/outputs/`);
            const thumbnails = outputs.steps?.mask_thumbnails || [];
            
            if (thumbnails.length === 0) {
                mapContainer.innerHTML = '<div class="text-muted">No map thumbnails available yet.</div>';
                return;
            }
            
            let firstOverlay = true;
            const overlays = {};
            thumbnails.forEach(thumb => {
                if (thumb.bounds && thumb.bounds.length === 2) {
                    const imageUrl = `/core/jobs/${jobId}/outputs/download/?path=${encodeURIComponent(thumb.relative_path)}`;
                    const imageBounds = thumb.bounds; // [[north, west], [south, east]]
                    const layerName = thumb.relative_path.split('/').pop();
                    const overlay = L.imageOverlay(imageUrl, imageBounds);
                    overlays[layerName] = overlay;
                    overlayLayers.push(overlay);
                    overlay.addTo(map);

                    if (firstOverlay) {
                        map.fitBounds(imageBounds);
                        firstOverlay = false;
                    }
                }
            });
            if (Object.keys(overlays).length > 0) {
                layerControl = L.control.layers(null, overlays, { collapsed: true }).addTo(map);
            }

        } catch (error) {
            mapContainer.innerHTML = `<div class="alert alert-danger">Failed to load map data: ${error.message}</div>`;
        }
    });
  }

  // --- JOB OUTPUTS PAGE ---
  function handleJobOutputsPage() {
    const downloadButtons = queryAll(".js-download-outputs");
    if (downloadButtons.length > 0) {
        queryAll('.output-select-all').forEach(selectAll => {
            selectAll.addEventListener('change', (e) => {
                const step = e.target.dataset.step;
                const table = e.target.closest('.card, .tab-pane');
                table.querySelectorAll(`.output-checkbox`).forEach(checkbox => {
                    checkbox.checked = e.target.checked;
                });
            });
        });

        downloadButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const step = e.target.dataset.step;
                const table = e.target.closest('.card, .tab-pane');
                const selected = Array.from(table.querySelectorAll('.output-checkbox:checked')).map(cb => cb.dataset.path);

                if (selected.length === 0) {
                    alert('Please select files to download.');
                    return;
                }

                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/core/outputs/zip/`;
                selected.forEach(path => {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'paths';
                    input.value = path;
                    form.appendChild(input);
                });
                document.body.appendChild(form);
                form.submit();
                form.remove();
            });
        });
    }

    const mapContainer = byId("job-outputs-map");
    if (mapContainer) {
        let map;
        let overlayLayers = [];
        let layerControl;
        const mapTab = byId('out-maps-tab');
        mapTab.addEventListener('shown.bs.tab', async event => {
            if (map) return;

            map = L.map(mapContainer).setView([0, 0], 2);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            const urlParams = new URLSearchParams(window.location.search);
            const country = urlParams.get('country') || '';
            const year_suffix = urlParams.get('year_suffix') || '';
            const output_name = urlParams.get('output_name') || '';

            try {
                const data = await fetchJson(`/core/outputs/filtered/?country=${country}&year_suffix=${year_suffix}&output_name=${output_name}`);
                const thumbnails = data.items || [];

                if (thumbnails.length === 0) {
                    mapContainer.innerHTML = '<div class="text-muted">No map thumbnails found for the selected filters.</div>';
                    return;
                }

                const allBounds = [];
                const overlays = {};
                thumbnails.forEach(thumb => {
                    if (thumb.bounds && thumb.bounds.length === 2) {
                        const imageUrl = `/core/jobs/${thumb.job_id}/outputs/download/?path=${encodeURIComponent(thumb.relative_path)}`;
                        const imageBounds = thumb.bounds;
                        const layerName = thumb.relative_path.split('/').pop();
                        const overlay = L.imageOverlay(imageUrl, imageBounds);
                        overlays[`${thumb.job_id}-${layerName}`] = overlay;
                        overlayLayers.push(overlay);
                        allBounds.push(L.latLngBounds(imageBounds));
                    }
                });
                const overlayNames = Object.keys(overlays);
                if (overlayNames.length > 0) {
                    overlayNames.forEach(name => overlays[name].addTo(map));
                    layerControl = L.control.layers(null, overlays, { collapsed: true }).addTo(map);
                }

                if (allBounds.length > 0) {
                    const groupBounds = allBounds.reduce((bounds, b) => bounds.extend(b), allBounds[0]);
                    map.fitBounds(groupBounds);
                }

            } catch (error) {
                mapContainer.innerHTML = `<div class="alert alert-danger">Failed to load map data: ${error.message}</div>`;
            }
        });
    }
  }

  // --- SETTINGS PAGE ---
  function handleSettingsPage() {
      const settingsForm = byId("settings-form");
      if(!settingsForm) return;

      const messageBox = byId("root-settings-message");

      async function loadRoots() {
        const data = await fetchJson("/core/root-settings/");
        const inputSelect = byId("input-root-select");
        const outputSelect = byId("output-root-select");
        const logsSelect = byId("logs-root-select");
        const inputActive = byId("input-root-active");
        const outputActive = byId("output-root-active");
        const logsActive = byId("logs-root-active");

        const populate = (select, items) => {
            select.innerHTML = "";
            items.forEach(item => {
                const option = document.createElement("option");
                option.value = item.id;
                option.textContent = item.path;
                select.appendChild(option);
            });
        };
        populate(inputSelect, data.input || []);
        populate(outputSelect, data.output || []);
        populate(logsSelect, data.logs || []);

        const activeInput = (data.input || []).find(i => i.is_active);
        const activeOutput = (data.output || []).find(i => i.is_active);
        const activeLogs = (data.logs || []).find(i => i.is_active);

        if (activeInput) {
            inputActive.textContent = `Active: ${activeInput.path}`;
            inputSelect.value = activeInput.id;
        } else {
            inputActive.textContent = "Active: Not Set";
        }
        if (activeOutput) {
            outputActive.textContent = `Active: ${activeOutput.path}`;
            outputSelect.value = activeOutput.id;
        } else {
            outputActive.textContent = "Active: Not Set";
        }
        if (activeLogs) {
            logsActive.textContent = `Active: ${logsActive.path}`;
            logsSelect.value = activeLogs.id;
        } else {
            logsActive.textContent = "Active: Not Set";
        }
      }

      const setMessage = (text, isError) => {
        messageBox.hidden = false;
        messageBox.textContent = text;
        messageBox.className = isError ? 'alert alert-danger' : 'alert alert-success';
      }

      settingsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const action = e.submitter.dataset.action;
        const type = e.submitter.dataset.type;
        if(!action || !type) return;

        const pathInput = byId(`${type}-root-path`);
        const select = byId(`${type}-root-select`);
        let payload = { action, type };

        if (action === 'add') {
            if(!pathInput.value) {
                setMessage("New path cannot be empty.", true);
                return;
            }
            payload.path = pathInput.value.trim();
            payload.activate = true;
        } else if (action === 'activate') {
            if(!select.value) {
                setMessage("Please select a path to activate.", true);
                return;
            }
            payload.id = select.value;
        }

        try {
            await fetchJson('/core/root-settings/', {
                method: 'POST',
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            setMessage(`Successfully ${action}ed ${type} root. Reloading...`, false);
            await loadRoots();
        } catch(error) {
            setMessage(error.message, true);
        }
      });

      loadRoots();
  }


  // --- INITIALIZATION ---

  document.addEventListener("DOMContentLoaded", () => {
    // Format file sizes on all pages
    queryAll('[data-bytes]').forEach(el => {
        el.textContent = formatBytes(el.dataset.bytes);
    });

    handleJobForm();
    handleJobDashboard();
    handleJobDetailPage();
    handleJobDetailMap();
    handleJobOutputsPage();
    handleSettingsPage();
  });

})();
