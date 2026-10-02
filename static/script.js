const $ = (id) => document.getElementById(id);

const url = $("url");
const quality = $("quality");
const analyze = $("analyze");
const download = $("download");
const preview = $("preview");
const thumb = $("thumb");
const title = $("title");
const meta = $("meta");
const statusBox = $("statusBox");
const statusText = $("statusText");
const percent = $("percent");
const barFill = $("barFill");
const result = $("result");
const resultTitle = $("resultTitle");
const saveBtn = $("saveBtn");
const errorBox = $("error");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}
function clearError() {
  errorBox.classList.add("hidden");
}
function setBusy(button, busy, text) {
  button.disabled = busy;
  if (busy) {
    button.dataset.old = button.textContent;
    button.textContent = text;
  } else {
    button.textContent = button.dataset.old || button.textContent;
  }
}

analyze.onclick = async () => {
  clearError();
  const value = url.value.trim();
  if (!value) return showError("Paste a video URL first.");

  setBusy(analyze, true, "Reading...");
  try {
    const res = await fetch("/api/info", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({url:value})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not read URL.");

    thumb.src = data.thumbnail || "";
    title.textContent = data.title || "Untitled video";
    meta.textContent = data.uploader ? `By ${data.uploader}` : "Video detected";
    preview.classList.remove("hidden");
  } catch(e) {
    showError(e.message);
  } finally {
    setBusy(analyze, false);
  }
};

download.onclick = async () => {
  clearError();
  result.classList.add("hidden");

  const value = url.value.trim();
  if (!value) return showError("Paste a video URL first.");

  setBusy(download, true, "Starting...");
  statusBox.classList.remove("hidden");
  statusText.textContent = "Starting download...";
  percent.textContent = "0%";
  barFill.style.width = "0%";

  try {
    const res = await fetch("/api/download", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({url:value, quality:quality.value})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not start download.");

    await poll(data.job_id);
  } catch(e) {
    showError(e.message);
    statusBox.classList.add("hidden");
  } finally {
    setBusy(download, false);
  }
};

async function poll(jobId) {
  while (true) {
    const res = await fetch(`/api/status/${jobId}`);
    const data = await res.json();

    if (data.status === "error") throw new Error(data.error || "Download failed.");

    const p = Number(data.progress || 0);
    percent.textContent = `${p}%`;
    barFill.style.width = `${p}%`;

    if (data.status === "starting") statusText.textContent = "Preparing...";
    if (data.status === "downloading") statusText.textContent = "Downloading...";
    if (data.status === "processing") statusText.textContent = "Processing MP4...";

    if (data.status === "complete") {
      statusText.textContent = "Complete";
      percent.textContent = "100%";
      barFill.style.width = "100%";
      resultTitle.textContent = data.title || "Your video is ready.";
      saveBtn.href = data.download_url;
      result.classList.remove("hidden");
      break;
    }

    await new Promise(r => setTimeout(r, 800));
  }
}
