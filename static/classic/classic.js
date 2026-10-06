"use strict";
// Classic Edition only: sidebar views and display summaries.
// Every file operation, API call and lock stays in the shared static/app.js; this file only
// reads what app.js has already rendered and never changes its elements or state.
(() => {
  const views = { organize: "classicViewOrganize", history: "classicViewHistory", help: "classicViewHelp" };
  const main = document.querySelector(".classic-main");

  function clear(element) {
    while (element.firstChild) element.removeChild(element.firstChild);
  }

  // Views are toggled with hidden only; app.js elements stay in the DOM in every view.
  function showView(name) {
    if (!views[name]) return;
    for (const [key, id] of Object.entries(views)) document.getElementById(id).hidden = key !== name;
    document.querySelectorAll(".nav-item[data-view]").forEach((item) => {
      if (item.dataset.view === name) item.setAttribute("aria-current", "page");
      else item.removeAttribute("aria-current");
    });
    main.scrollTop = 0;
    document.getElementById(views[name]).querySelector("h1").focus({ preventScroll: true });
  }

  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => showView(button.dataset.view));
  });

  // Destination text is "folder\file" (or "folder/file"); everything before the file name
  // is the destination folder. Only the rendered rows are read; the API is unchanged.
  function folderOf(destination) {
    const parts = destination.split(/[\\/]/);
    return parts.length > 1 ? parts.slice(0, -1).join("\\") : "（このフォルダー）";
  }

  function renderFolders(rowsId, listId, totalId, countId) {
    const counts = new Map();
    for (const cell of document.querySelectorAll(`#${rowsId} td.destination`)) {
      const name = folderOf(cell.textContent);
      counts.set(name, (counts.get(name) || 0) + 1);
    }
    const list = document.getElementById(listId);
    clear(list);
    const sorted = [...counts].sort((a, b) => b[1] - a[1]);
    for (const [name, count] of sorted) {
      const item = document.createElement("li");
      const label = document.createElement("span");
      label.className = "folder-name";
      label.textContent = name;
      const number = document.createElement("span");
      number.className = "folder-count";
      number.textContent = `${count} 件`;
      item.append(label, number);
      list.appendChild(item);
    }
    if (!sorted.length) {
      const item = document.createElement("li");
      item.className = "folder-empty";
      item.textContent = "移動予定はありません";
      list.appendChild(item);
    }
    document.getElementById(totalId).textContent = `全${counts.size}個`;
    if (countId) document.getElementById(countId).textContent = counts.size;
  }

  // "直前の整理" card: a read-only copy of the first card app.js rendered in #historyRows.
  function renderLatest() {
    const card = document.querySelector("#historyRows .history-card");
    const path = document.getElementById("classicLatestPath");
    const meta = document.getElementById("classicLatestMeta");
    clear(meta);
    if (!card) {
      path.textContent = "まだ整理履歴はありません。";
      path.removeAttribute("title");
      return;
    }
    path.textContent = card.querySelector(".history-path").textContent;
    path.title = path.textContent;
    const [date, status] = card.querySelectorAll(".history-meta span");
    const detail = card.querySelector(".history-detail");
    const texts = [date ? date.textContent : ""]
      .concat(detail ? detail.textContent.split(" · ").slice(0, 2) : []);
    for (const text of texts.filter(Boolean)) {
      const span = document.createElement("span");
      span.textContent = text;
      meta.appendChild(span);
    }
    if (status) {
      const pill = document.createElement("span");
      pill.className = "status-pill";
      pill.dataset.status = status.dataset.status || "unknown";
      pill.textContent = status.textContent;
      meta.appendChild(pill);
    }
  }

  const watch = (id, render) => {
    new MutationObserver(render).observe(document.getElementById(id), { childList: true });
    render();
  };
  watch("previewRows", () => renderFolders("previewRows", "classicFolderList", "classicFolderTotal", "classicFolderCount"));
  watch("successRows", () => renderFolders("successRows", "classicResultFolderList", "classicResultFolderTotal"));
  watch("historyRows", renderLatest);
})();
