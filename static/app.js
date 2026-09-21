"use strict";

const state = {
  folder: null,
  preview: null,
  jobId: null,
  polling: false,
};

const elements = {
  folderPath: document.querySelector("#folderPath"),
  selectFolderButton: document.querySelector("#selectFolderButton"),
  previewButton: document.querySelector("#previewButton"),
  organizeButton: document.querySelector("#organizeButton"),
  startOverButton: document.querySelector("#startOverButton"),
  previewSection: document.querySelector("#previewSection"),
  previewEmpty: document.querySelector("#previewEmpty"),
  previewContent: document.querySelector("#previewContent"),
  previewBadge: document.querySelector("#previewBadge"),
  previewRows: document.querySelector("#previewRows"),
  previewFailures: document.querySelector("#previewFailures"),
  previewFailureList: document.querySelector("#previewFailureList"),
  previewNotice: document.querySelector("#previewNotice"),
  previewNoticeText: document.querySelector("#previewNoticeText"),
  progressSection: document.querySelector("#progressSection"),
  progressStatus: document.querySelector("#progressStatus"),
  currentFile: document.querySelector("#currentFile"),
  progressPercent: document.querySelector("#progressPercent"),
  progressBar: document.querySelector("#progressBar"),
  progressTrack: document.querySelector(".progress-track"),
  progressCount: document.querySelector("#progressCount"),
  resultSection: document.querySelector("#resultSection"),
  resultIcon: document.querySelector("#resultIcon"),
  resultHeading: document.querySelector("#resultHeading"),
  resultDescription: document.querySelector("#resultDescription"),
  successCount: document.querySelector("#successCount"),
  failureCount: document.querySelector("#failureCount"),
  processedCount: document.querySelector("#processedCount"),
  successResults: document.querySelector("#successResults"),
  failureResults: document.querySelector("#failureResults"),
  successRows: document.querySelector("#successRows"),
  failureRows: document.querySelector("#failureRows"),
  errorBanner: document.querySelector("#errorBanner"),
  errorMessage: document.querySelector("#errorMessage"),
  closeError: document.querySelector("#closeError"),
  confirmDialog: document.querySelector("#confirmDialog"),
  confirmCount: document.querySelector("#confirmCount"),
};

function setButtonLoading(button, loading, text) {
  if (loading) {
    button.dataset.originalText = button.textContent;
    button.textContent = text;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
  }
}

async function api(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      ...options,
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
  } catch (error) {
    throw new Error(
      "Webアプリのサーバーへ接続できません。起動時のコンソールを閉じずに、ページを再読み込みしてください。"
    );
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `通信に失敗しました（${response.status}）`);
  }
  return data;
}

function showError(message) {
  elements.errorMessage.textContent = message;
  elements.errorBanner.hidden = false;
  elements.errorBanner.scrollIntoView({ behavior: "smooth", block: "center" });
}

function clearError() {
  elements.errorBanner.hidden = true;
  elements.errorMessage.textContent = "";
}

function setStep(activeStep) {
  document.querySelectorAll(".step").forEach((step) => {
    const number = Number(step.dataset.step);
    step.classList.toggle("is-active", number === activeStep);
    step.classList.toggle("is-done", number < activeStep);
  });
}

function clearElement(element) {
  while (element.firstChild) element.removeChild(element.firstChild);
}

function addCell(row, text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) cell.className = className;
  row.appendChild(cell);
}

function resetPreview() {
  state.preview = null;
  state.jobId = null;
  state.polling = false;
  elements.previewEmpty.hidden = false;
  elements.previewContent.hidden = true;
  elements.previewBadge.hidden = true;
  elements.organizeButton.disabled = true;
  elements.progressSection.hidden = true;
  elements.resultSection.hidden = true;
  clearElement(elements.previewRows);
  clearElement(elements.previewFailureList);
  setStep(1);
}

function renderPreview(preview) {
  clearElement(elements.previewRows);
  clearElement(elements.previewFailureList);

  elements.previewEmpty.hidden = true;
  elements.previewContent.hidden = false;
  elements.previewBadge.hidden = false;
  elements.previewBadge.querySelector("strong").textContent = preview.plan_count;

  for (const plan of preview.plans) {
    const row = document.createElement("tr");
    addCell(row, plan.source_name, "file-name");
    addCell(row, plan.extension, "file-ext-cell");
    row.children[1].innerHTML = "";
    const extensionBadge = document.createElement("span");
    extensionBadge.className = "file-ext";
    extensionBadge.textContent = plan.extension;
    row.children[1].appendChild(extensionBadge);
    addCell(row, plan.destination_relative, "destination");
    elements.previewRows.appendChild(row);
  }

  elements.previewFailures.hidden = preview.failures.length === 0;
  for (const failure of preview.failures) {
    const item = document.createElement("li");
    item.textContent = `${failure.source}: ${failure.message}`;
    elements.previewFailureList.appendChild(item);
  }

  if (preview.plan_count === 0) {
    elements.previewNotice.hidden = false;
    elements.previewNoticeText.textContent = "このフォルダ直下に、拡張子を持つ整理対象ファイルはありません。";
  } else if (preview.failure_count > 0) {
    elements.previewNotice.hidden = false;
    elements.previewNoticeText.textContent = "一部の予定を作成できませんでした。下のエラー内容を確認してください。";
  } else {
    elements.previewNotice.hidden = true;
  }

  elements.organizeButton.disabled = preview.plan_count === 0;
  setStep(2);
  elements.previewSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderProgress(job) {
  const progress = Math.min(100, Math.max(0, job.progress));
  elements.progressBar.style.width = `${progress}%`;
  elements.progressTrack.setAttribute("aria-valuenow", String(progress));
  elements.progressPercent.textContent = `${progress}%`;
  elements.progressCount.textContent = `${job.processed} / ${job.total} 件`;
  elements.currentFile.textContent = job.current_file
    ? `処理中: ${job.current_file}`
    : job.status === "completed"
      ? "すべての処理が完了しました"
      : "準備中…";
  elements.progressStatus.textContent = job.status === "queued"
    ? "整理の準備をしています…"
    : job.status === "running"
      ? "ファイルを整理しています。画面を閉じずにお待ちください。"
      : job.status === "completed"
        ? "整理処理が完了しました。"
        : "処理中にエラーが発生しました。";
}

function renderResult(job) {
  const hasFailure = job.failure_count > 0 || job.status === "failed";
  elements.resultIcon.textContent = hasFailure ? "!" : "✓";
  elements.resultIcon.classList.toggle("has-error", hasFailure);
  elements.resultHeading.textContent = job.status === "failed"
    ? "整理を最後まで実行できませんでした"
    : hasFailure
      ? "整理が完了しました（一部エラーあり）"
      : "整理が完了しました";
  elements.resultDescription.textContent = job.error || (
    hasFailure
      ? "成功したファイルとエラー内容を確認してください。"
      : "すべての対象ファイルを安全に移動しました。"
  );

  elements.successCount.textContent = job.success_count;
  elements.failureCount.textContent = job.failure_count;
  elements.processedCount.textContent = job.success_count + job.failure_count;

  clearElement(elements.successRows);
  for (const file of job.successful_files) {
    const row = document.createElement("tr");
    addCell(row, file.source_name, "file-name");
    addCell(row, file.destination_relative, "destination");
    elements.successRows.appendChild(row);
  }
  elements.successResults.hidden = job.successful_files.length === 0;

  clearElement(elements.failureRows);
  for (const failure of job.failed_files) {
    const row = document.createElement("tr");
    addCell(row, failure.source, "file-name");
    addCell(row, failure.message, "error-message");
    elements.failureRows.appendChild(row);
  }
  elements.failureResults.hidden = job.failed_files.length === 0;

  elements.resultSection.hidden = false;
  elements.organizeButton.disabled = true;
  setStep(3);
  elements.resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function pollJob(jobId) {
  state.polling = true;
  try {
    const job = await api(`/api/jobs/${jobId}`);
    renderProgress(job);

    if (job.status === "completed" || job.status === "failed") {
      state.polling = false;
      renderResult(job);
      return;
    }

    window.setTimeout(() => pollJob(jobId), 350);
  } catch (error) {
    state.polling = false;
    showError(`処理状況を取得できませんでした: ${error.message}`);
  }
}

async function selectFolder() {
  clearError();
  setButtonLoading(elements.selectFolderButton, true, "選択画面を開いています…");
  try {
    const result = await api("/api/select-folder", { method: "POST", body: "{}" });
    if (!result.cancelled) {
      state.folder = result.folder;
      elements.folderPath.value = result.folder;
      elements.folderPath.title = result.folder;
      resetPreview();
      elements.previewButton.disabled = false;
    }
  } catch (error) {
    showError(error.message);
  } finally {
    setButtonLoading(elements.selectFolderButton, false);
  }
}

async function createPreview() {
  clearError();
  resetPreview();
  setButtonLoading(elements.previewButton, true, "予定を作成中…");
  try {
    const preview = await api("/api/preview", {
      method: "POST",
      body: JSON.stringify({ folder: state.folder }),
    });
    state.preview = preview;
    renderPreview(preview);
  } catch (error) {
    showError(error.message);
  } finally {
    setButtonLoading(elements.previewButton, false);
  }
}

async function startOrganization() {
  clearError();
  if (!state.preview) return;

  elements.organizeButton.disabled = true;
  elements.progressSection.hidden = false;
  elements.resultSection.hidden = true;
  setStep(3);
  elements.progressSection.scrollIntoView({ behavior: "smooth", block: "start" });

  try {
    const job = await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify({ preview_id: state.preview.preview_id }),
    });
    state.jobId = job.job_id;
    renderProgress(job);
    pollJob(job.job_id);
  } catch (error) {
    elements.progressSection.hidden = true;
    elements.organizeButton.disabled = false;
    showError(error.message);
    setStep(2);
  }
}

elements.selectFolderButton.addEventListener("click", selectFolder);
elements.previewButton.addEventListener("click", createPreview);
elements.closeError.addEventListener("click", clearError);

elements.folderPath.addEventListener("input", () => {
  state.folder = elements.folderPath.value.trim() || null;
  resetPreview();
  elements.previewButton.disabled = !state.folder;
});

elements.organizeButton.addEventListener("click", () => {
  if (!state.preview) return;
  elements.confirmCount.textContent = `${state.preview.plan_count}件`;
  elements.confirmDialog.showModal();
});

elements.confirmDialog.addEventListener("close", () => {
  if (elements.confirmDialog.returnValue === "default") startOrganization();
});

elements.startOverButton.addEventListener("click", () => {
  state.folder = null;
  state.preview = null;
  state.jobId = null;
  state.polling = false;
  elements.folderPath.value = "";
  elements.previewButton.disabled = true;
  resetPreview();
  clearError();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
