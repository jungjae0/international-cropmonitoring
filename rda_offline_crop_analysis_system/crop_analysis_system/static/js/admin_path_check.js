function debounce(fn, wait) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function updatePreview(previewEl, resolved, exists) {
  if (!previewEl) {
    return;
  }
  const showStatus = previewEl.dataset.status !== "off";
  const status = exists ? "Exists" : "Missing";
  previewEl.textContent = resolved
    ? `Resolved: ${resolved}${showStatus ? ` (${status})` : ""}`
    : "";
  if (showStatus) {
    previewEl.classList.toggle("is-ok", !!resolved && exists);
    previewEl.classList.toggle("is-bad", !!resolved && !exists);
  } else {
    previewEl.classList.remove("is-ok", "is-bad");
  }
}

async function fetchValidation(pathValue) {
  const url = `/core/validate-path/?path=${encodeURIComponent(pathValue)}`;
  const response = await fetch(url, { credentials: "same-origin" });
  if (!response.ok) {
    return { resolved: "", exists: false };
  }
  return response.json();
}

function bindPathPreview(inputId, previewId) {
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  if (!input || !preview) {
    return;
  }
  const run = debounce(async () => {
    const value = input.value.trim();
    if (!value) {
      updatePreview(preview, "", false);
      return;
    }
    const data = await fetchValidation(value);
    updatePreview(preview, data.resolved || "", !!data.exists);
  }, 300);
  input.addEventListener("input", run);
  input.addEventListener("change", run);
  run();
}

document.addEventListener("DOMContentLoaded", () => {
  bindPathPreview("id_model_weights_path", "weights-preview");
  bindPathPreview("id_shapefile_path", "shapefile-preview");
  bindPathPreview("id_path", "root-path-preview");
  bindRootTypeStatus();
});

function bindRootTypeStatus() {
  const typeSelect = document.getElementById("id_path_type");
  const preview = document.getElementById("root-path-preview");
  if (!typeSelect || !preview) {
    return;
  }
  const update = () => {
    const value = typeSelect.value;
    preview.dataset.status = value === "output" ? "off" : "on";
  };
  typeSelect.addEventListener("change", update);
  update();
}
