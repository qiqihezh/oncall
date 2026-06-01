const page = document.querySelector("main")?.dataset.page;

if (page === "v1" || page === "v2") {
  const form = document.querySelector("#search-form");
  const query = document.querySelector("#query");
  const results = document.querySelector("#results");
  const summary = document.querySelector("#summary");
  const submit = form.querySelector("button[type='submit']");
  const endpoint = page === "v1" ? "/v1/search" : "/v2/search";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const q = query.value.trim();
    if (!q) return;
    setBusy(submit, true);
    summary.textContent = "查询中";
    results.className = "empty";
    results.textContent = "正在查询...";
    try {
      const response = await fetch(`${endpoint}?q=${encodeURIComponent(q)}`);
      const data = await response.json();
      renderResults(results, data.results || []);
      summary.textContent = `${data.query || q} · ${data.results?.length || 0} 条结果`;
    } catch (error) {
      renderError(results, "请求失败，请确认服务已启动。");
      summary.textContent = "请求失败";
    } finally {
      setBusy(submit, false);
    }
  });

  bindExamples((value) => {
    query.value = value;
    form.requestSubmit();
  });
}

if (page === "v3") {
  const form = document.querySelector("#chat-form");
  const input = document.querySelector("#message");
  const log = document.querySelector("#chat-log");
  const summary = document.querySelector("#summary");
  const submit = form.querySelector("button[type='submit']");
  log.innerHTML = "";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    clearEmpty(log);
    appendMessage(log, "用户", message, "user");
    input.value = "";
    setBusy(submit, true);
    summary.textContent = "Agent 处理中";

    try {
      const response = await fetch("/v3/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await response.json();
      appendMessage(log, "Agent", data.answer || "", "agent");
      appendTools(log, data.toolCalls || [], data.agent || {});
      summary.textContent = `${data.documents?.length || 0} 个 SOP · ${data.agent?.planner || "unknown"}`;
    } catch (error) {
      appendMessage(log, "错误", "请求失败，请确认服务已启动。", "error");
      summary.textContent = "请求失败";
    } finally {
      setBusy(submit, false);
    }
  });

  bindExamples((value) => {
    input.value = value;
    form.requestSubmit();
  });
}

function renderResults(container, items) {
  if (!items.length) {
    container.className = "empty";
    container.textContent = "暂无结果。";
    return;
  }

  container.className = "";
  container.innerHTML = items
    .map(
      (item) => `
        <article class="item">
          <div class="item-title">
            <strong>${escapeHtml(item.id)} - ${escapeHtml(item.title)}</strong>
            <span class="badge">score ${escapeHtml(String(item.score))}</span>
          </div>
          <p>${escapeHtml(item.snippet)}</p>
        </article>
      `
    )
    .join("");
}

function appendMessage(container, role, text, kind = "") {
  const block = document.createElement("div");
  block.className = `message ${kind}`.trim();
  block.innerHTML = `<strong>${escapeHtml(role)}</strong><p>${escapeHtml(text)}</p>`;
  container.appendChild(block);
}

function appendTools(container, calls, agent) {
  const block = document.createElement("div");
  block.className = "message tools";
  const rows = calls
    .map((call, index) => {
      const fname = call.args?.fname || "";
      return `
        <div class="tool-row">
          <span>${index + 1}. ${escapeHtml(call.tool || "readFile")}</span>
          <code>${escapeHtml(fname)}</code>
        </div>
      `;
    })
    .join("");
  block.innerHTML = `
    <strong>readFile 工具调用</strong>
    <div class="meta">mode: ${escapeHtml(agent.mode || "-")} · planner: ${escapeHtml(agent.planner || "-")} · answer: ${escapeHtml(agent.answerMode || "-")}</div>
    <div class="tool-list">${rows || "<span class='empty'>无工具调用</span>"}</div>
  `;
  container.appendChild(block);
}

function renderError(container, message) {
  container.className = "message error";
  container.textContent = message;
}

function bindExamples(handler) {
  document.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => handler(button.dataset.example || ""));
  });
}

function setBusy(button, busy) {
  button.disabled = busy;
  button.textContent = busy ? "处理中..." : page === "v3" ? "发送" : "搜索";
}

function clearEmpty(container) {
  if (container.classList.contains("empty")) {
    container.className = "";
    container.innerHTML = "";
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
