"use strict";

function readOptions() {
  return {
    rule: document.querySelector('[name="organizationRule"]:checked').value,
    excluded_extensions: document.querySelector("#excludedExtensions").value
      .split(/[,\s]+/).filter(Boolean),
  };
}

let latestRunId = null;
let undoRunId = null;

function setOperationBusy(busy) {
  state.operationBusy = busy;
  for (const id of ["folderPath", "selectFolderButton", "organizationRule",
                    "excludedExtensions", "saveSettings", "startOverButton", "undoLatest"]) {
    document.getElementById(id).disabled = busy;
  }
  elements.previewButton.disabled = busy || !state.folder;
  elements.organizeButton.disabled = busy || !state.preview || !state.preview.plan_count || !!state.jobId;
  document.querySelector("#undoLatest").disabled = busy || !state.undoEligible;
  document.querySelector("#refreshHistory").disabled = busy;
  document.querySelector(".folder-panel").setAttribute("aria-busy", String(busy));
}

async function refreshHistory() {
  const { history } = await api("/api/history");
  const rows = document.querySelector("#historyRows");
  clearElement(rows);
  latestRunId = history.length ? history[0].run_id : null;
  state.undoEligible = !!history.length &&
    history[0].moves.some(move => ["moved", "pending"].includes(move.status));
  document.querySelector("#undoLatest").disabled = state.operationBusy || !state.undoEligible;
  document.querySelector("#historyEmpty").hidden = history.length > 0;
  document.querySelector("#undoAvailability").textContent = state.undoEligible
    ? "直前の整理に、元に戻せるファイルがあります。実行前に一覧を確認できます。"
    : history.length ? "直前の整理に、元に戻せるファイルはありません。" : "整理履歴ができると、ここから元に戻せます。";
  const statuses = { running: "処理中", completed: "整理完了", interrupted: "中断・確認が必要" };
  for (const run of history) {
    const card = document.createElement("article");
    card.className = "history-card";
    const meta = document.createElement("div");
    meta.className = "history-meta";
    for (const text of [new Date(run.executed_at).toLocaleString("ja-JP"), statuses[run.status] || "結果を確認してください"]) {
      const span = document.createElement("span"); span.textContent = text; meta.appendChild(span);
    }
    // Display only: lets CSS colour the status pill without parsing its text.
    meta.lastChild.dataset.status = statuses[run.status] ? run.status : "unknown";
    card.appendChild(meta);
    const path = document.createElement("p"); path.className = "history-path";
    path.textContent = run.folder; path.title = run.folder; card.appendChild(path);
    const detail = document.createElement("p"); detail.className = "history-detail";
    const remaining = run.moves.filter(move => ["moved", "pending"].includes(move.status)).length;
    detail.textContent = `${run.rule === "type" ? "ファイル種類別" : "拡張子別"} · 移動 ${run.success_count} 件 / 失敗 ${run.failure_count} 件 · ` +
      (run.run_id === latestRunId && remaining ? "元に戻す予定を確認できます" : remaining ? "元に戻せるのは直前の整理のみです" : "元に戻す対象なし");
    card.appendChild(detail);
    if (run.undo_attempts && run.undo_attempts.length) {
      const undo = document.createElement("p"); undo.className = "history-detail";
      undo.textContent = run.undo_attempts.map(attempt => `元に戻す：成功 ${attempt.success_count} 件 / 失敗 ${attempt.failure_count} 件`).join("、");
      card.appendChild(undo);
    }
    const technical = document.createElement("details");
    const summary = document.createElement("summary"); summary.textContent = "実行IDを表示";
    const id = document.createElement("p"); id.textContent = run.run_id;
    technical.append(summary, id); card.appendChild(technical); rows.appendChild(card);
  }
}

const state = {
  folder: null,
  preview: null,
  jobId: null,
  polling: false,
  operationBusy: false,
  undoEligible: false,
  phase: "idle",
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
      "アプリとの通信を確認できませんでした。処理中の場合は「処理状況を再確認」を押してください。それ以外の場合は少し待ってから再度操作してください。"
    );
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `通信に失敗しました（${response.status}）`);
  }
  return data;
}

function showError(message) {
  state.phase = "error";
  document.querySelector("#appStatus").textContent = "エラーの内容を確認してください。";
  elements.errorMessage.textContent = message;
  elements.errorBanner.hidden = false;
  scrollToPanel(elements.errorBanner);
}

function clearError() {
  elements.errorBanner.hidden = true;
  elements.errorMessage.textContent = "";
}

function clearUndoResult() {
  const panel = document.querySelector("#undoResult");
  panel.hidden = true;
  panel.classList.remove("has-error");
  clearElement(panel);
}
function scrollToPanel(element) {
  element.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
}

function setStep(activeStep) {
  document.querySelectorAll(".step").forEach((step) => {
    const number = Number(step.dataset.step);
    step.classList.toggle("is-active", number === activeStep);
    step.classList.toggle("is-done", number < activeStep);
    if (number === activeStep) step.setAttribute("aria-current", "step");
    else step.removeAttribute("aria-current");
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
  document.querySelector("#excludedCount").textContent = "";
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
  state.phase = state.folder ? "folder-selected" : "idle";
  document.querySelector("#appStatus").textContent = state.folder
    ? "整理方法を選んで、整理予定を確認してください。" : "整理したいフォルダを選択してください。";
}

function renderPreview(preview) {
  clearElement(elements.previewRows);
  clearElement(elements.previewFailureList);
  // Display only: wrap the number so it matches the other KPI values.
  const excludedCount = document.querySelector("#excludedCount");
  clearElement(excludedCount);
  const excludedNumber = document.createElement("strong");
  excludedNumber.textContent = preview.excluded_count;
  excludedCount.append(excludedNumber, " 件");
  document.querySelector("#settingsStatus").textContent = "設定を保存しました。";
  document.querySelector("#planCount").textContent = preview.plan_count;
  document.querySelector("#previewFailureCount").textContent = preview.failure_count;

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
    elements.previewNoticeText.textContent = "移動できる対象がありません。除外設定や対象フォルダを確認してください。サブフォルダ内・拡張子なしのファイルは整理しません。";
  } else if (preview.failure_count > 0) {
    elements.previewNotice.hidden = false;
    elements.previewNoticeText.textContent = "一部の予定を作成できませんでした。下のエラー内容を確認してください。";
  } else {
    elements.previewNotice.hidden = true;
  }

  elements.organizeButton.disabled = preview.plan_count === 0;
  setStep(2);
  state.phase = "preview-ready";
  document.querySelector("#appStatus").textContent = preview.plan_count
    ? "移動先を確認したら、「整理を実行」を押してください。" : "移動予定は0件です。フォルダや設定を見直してください。";
  scrollToPanel(elements.previewSection);
}

function renderProgress(job) {
  elements.progressSection.setAttribute("aria-busy", String(!["completed", "failed"].includes(job.status)));
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
      ? "ファイルを整理しています。処理が完了するまでお待ちください。"
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
  state.phase = hasFailure ? "error" : "completed";
  document.querySelector("#appStatus").textContent = hasFailure ? "整理結果と、移動できなかった理由を確認してください。" : "整理が完了しました。履歴から元に戻すこともできます。";
  elements.organizeButton.disabled = true;
  setStep(3);
  scrollToPanel(elements.resultSection);
}

async function pollJob(jobId) {
  if (jobId !== state.jobId || state.polling) return;
  state.polling = true;
  document.querySelector("#retryProgress").hidden = true;
  try {
    const job = await api(`/api/jobs/${jobId}`);
    renderProgress(job);

    if (job.status === "completed" || job.status === "failed") {
      state.polling = false;
      setOperationBusy(false);
      renderResult(job);
      refreshHistory().catch(error => showError(error.message));
      return;
    }

    state.polling = false;
    window.setTimeout(() => pollJob(jobId), 350);
  } catch (error) {
    state.polling = false;
    showError(`処理状況を取得できませんでした: ${error.message}`);
    document.querySelector("#retryProgress").hidden = false;
  }
}

async function selectFolder() {
  if (state.operationBusy) return;
  setOperationBusy(true);
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
    setOperationBusy(false);
  }
}

async function createPreview() {
  if (state.operationBusy || !state.folder) return;
  setOperationBusy(true);
  clearError();
  resetPreview();
  setButtonLoading(elements.previewButton, true, "予定を作成中…");
  try {
    const preview = await api("/api/preview", {
      method: "POST",
      body: JSON.stringify({ folder: state.folder, ...readOptions() }),
    });
    state.preview = preview;
    renderPreview(preview);
  } catch (error) {
    showError(error.message);
  } finally {
    setButtonLoading(elements.previewButton, false);
    setOperationBusy(false);
  }
}

async function startOrganization() {
  clearError();
  if (!state.preview || state.operationBusy || state.jobId) return;
  // Display only: a new organization starts, so the previous Undo message no longer applies.
  clearUndoResult();
  setOperationBusy(true);
  state.phase = "running";
  document.querySelector("#appStatus").textContent = "整理中です。完了するまでお待ちください。";

  elements.organizeButton.disabled = true;
  elements.progressSection.hidden = false;
  elements.resultSection.hidden = true;
  setStep(3);
  scrollToPanel(elements.progressSection);

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
    setOperationBusy(false);
    elements.organizeButton.disabled = false;
    showError(error.message);
    setStep(2);
  }
}

elements.selectFolderButton.addEventListener("click", selectFolder);
elements.previewButton.addEventListener("click", createPreview);
elements.closeError.addEventListener("click", clearError);

for (const id of ["organizationRule", "excludedExtensions"]) {
  document.getElementById(id).addEventListener("input", () => {
    resetPreview();
    document.querySelector("#settingsStatus").textContent = "設定を変更しました。保存するか、プレビューして反映してください。";
  });
}
document.querySelector("#saveSettings").addEventListener("click", async () => {
  if (state.operationBusy) return;
  setOperationBusy(true);
  try {
    await api("/api/settings", { method: "POST", body: JSON.stringify(readOptions()) });
    document.querySelector("#settingsStatus").textContent = "設定を保存しました。";
  } catch (error) { showError(error.message); }
  finally { setOperationBusy(false); }
});
document.querySelector("#refreshHistory").addEventListener("click", () => {
  refreshHistory().catch(error => showError(error.message));
});
document.querySelector("#undoLatest").addEventListener("click", async () => {
  if (state.operationBusy || !state.undoEligible) return;
  setOperationBusy(true);
  try {
    const preview = await api(`/api/history/${latestRunId}/undo-preview`);
    undoRunId = preview.run_id;
    const list = document.querySelector("#undoFiles");
    clearElement(list);
    document.querySelector("#undoCount").textContent = `${preview.moves.length} 件の復元予定`;
    for (const move of preview.moves) {
      const item = document.createElement("li");
      item.textContent = `${move.destination} → ${move.source}`;
      list.appendChild(item);
    }
    document.querySelector("#undoDialog").returnValue = "cancel";
    document.querySelector("#undoDialog").showModal();
  } catch (error) { showError(error.message); }
  finally { setOperationBusy(false); }
});
document.querySelector("#undoDialog").addEventListener("close", async event => {
  if (event.target.returnValue !== "undo") return;
  if (state.operationBusy) return;
  setOperationBusy(true);
  document.querySelector("#undoResult").hidden = false;
  document.querySelector("#undoResult").textContent = "元の場所に戻しています。完了するまでお待ちください。";
  try {
    const result = await api(`/api/history/${undoRunId}/undo`, {
      method: "POST", body: JSON.stringify({ confirmed: true }),
    });
    const panel = document.querySelector("#undoResult");
    clearElement(panel);
    panel.classList.toggle("has-error", result.failure_count > 0);
    const summary = document.createElement("p");
    summary.textContent = `元に戻す：成功 ${result.success_count} 件 / 失敗 ${result.failure_count} 件。` +
      (result.failure_count ? "下の理由を確認してください。問題を解消した後、残りのファイルを再試行できます。" : "ファイルを元の場所に戻しました。");
    panel.appendChild(summary);
    const list = document.createElement("ul");
    for (const failure of result.failures) { const item = document.createElement("li"); item.textContent = `${failure.source}: ${failure.message}`; list.appendChild(item); }
    if (result.failures.length) panel.appendChild(list);
    resetPreview();
  } catch (error) {
    document.querySelector("#undoResult").textContent = "元に戻す処理を確認できませんでした。エラーと履歴を確認してください。";
    document.querySelector("#undoResult").classList.add("has-error");
    showError(error.message);
  }
  finally {
    setOperationBusy(false);
    refreshHistory().catch(error => showError(error.message));
  }
});

(async () => {
  setOperationBusy(true);
  try {
    const settings = await api("/api/settings");
    document.querySelector(`[name="organizationRule"][value="${settings.rule}"]`).checked = true;
    document.querySelector("#excludedExtensions").value = settings.excluded_extensions.join(", ");
    await refreshHistory();
  } catch (error) { showError(error.message); }
  finally { setOperationBusy(false); }
})();

elements.folderPath.addEventListener("input", () => {
  state.folder = elements.folderPath.value.trim() || null;
  resetPreview();
  elements.previewButton.disabled = !state.folder;
});

elements.organizeButton.addEventListener("click", () => {
  if (!state.preview || !state.preview.plan_count || state.operationBusy || state.jobId) return;
  elements.confirmDialog.returnValue = "cancel";
  elements.confirmCount.textContent = `${state.preview.plan_count}件`;
  elements.confirmDialog.showModal();
});

elements.confirmDialog.addEventListener("close", () => {
  if (elements.confirmDialog.returnValue === "default") startOrganization();
});

elements.startOverButton.addEventListener("click", () => {
  if (state.operationBusy) return;
  state.folder = null;
  state.preview = null;
  state.jobId = null;
  state.polling = false;
  elements.folderPath.value = "";
  elements.previewButton.disabled = true;
  resetPreview();
  clearError();
  elements.folderPath.focus();
  window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
});

document.querySelector("#retryProgress").addEventListener("click", () => {
  if (state.jobId && !state.polling) pollJob(state.jobId);
});
