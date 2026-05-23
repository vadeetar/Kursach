const API = "/api/v1";

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data);
    throw new Error(detail);
  }
  return data;
}

function badge(priority) {
  return `<span class="badge ${priority}">${priority}</span>`;
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ru-RU");
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
    loadTab(btn.dataset.tab);
  });
});

function loadTab(name) {
  if (name === "dashboard") loadDashboard();
  if (name === "findings") loadFindings();
  if (name === "assets") loadAssets();
  if (name === "vulnerabilities") loadVulnerabilities();
}

async function loadDashboard() {
  const report = await api("/reports/executive-summary");
  const s = report.stats;
  document.getElementById("stats-grid").innerHTML = `
    <div class="stat-card"><div class="value">${s.total_vulnerabilities}</div><div class="label">CVE в базе</div></div>
    <div class="stat-card"><div class="value">${s.total_assets}</div><div class="label">Активов ПО</div></div>
    <div class="stat-card"><div class="value">${s.total_findings}</div><div class="label">Находок</div></div>
    <div class="stat-card"><div class="value">${s.findings_overdue}</div><div class="label">Просрочено SLA</div></div>
    <div class="stat-card"><div class="value">${s.critical_count}</div><div class="label">Critical CVE</div></div>
    <div class="stat-card"><div class="value">${s.findings_in_progress}</div><div class="label">В работе</div></div>
  `;
  document.getElementById("recommendations").innerHTML = report.recommendations
    .map((r) => `<li>${r}</li>`)
    .join("");
}

async function loadFindings() {
  const status = document.getElementById("finding-status-filter").value;
  const priority = document.getElementById("finding-priority-filter").value;
  const overdue = document.getElementById("overdue-only").checked;
  const params = new URLSearchParams({ limit: "100" });
  if (status) params.set("status", status);
  if (priority) params.set("priority", priority);
  if (overdue) params.set("overdue_only", "true");

  const data = await api(`/findings?${params}`);
  const rows = await Promise.all(
    data.items.map((f) => api(`/findings/${f.id}`))
  );

  document.getElementById("findings-body").innerHTML = rows
    .map(
      (d) => `
      <tr>
        <td>${d.id}</td>
        <td><a href="${d.vulnerability.nvd_url || "#"}" target="_blank" rel="noopener">${d.vulnerability.cve_id}</a></td>
        <td>${d.asset.package_name}@${d.asset.version}</td>
        <td>${d.vulnerability.cvss_score}</td>
        <td>${d.risk_score ?? "—"}</td>
        <td>${badge(d.priority)}</td>
        <td>${d.status}</td>
        <td>${formatDate(d.remediation_due_date)}</td>
        <td><button type="button" class="secondary" data-edit="${d.id}">Изменить</button></td>
      </tr>`
    )
    .join("");

  document.querySelectorAll("[data-edit]").forEach((btn) => {
    btn.addEventListener("click", () => openFindingDialog(btn.dataset.edit));
  });
}

async function openFindingDialog(id) {
  const f = await api(`/findings/${id}`);
  const form = document.getElementById("finding-form");
  form.finding_id.value = id;
  form.status.value = f.status;
  form.assigned_to.value = f.assigned_to || "";
  form.remediation_notes.value = f.remediation_notes || "";
  document.getElementById("finding-dialog").showModal();
}

document.getElementById("finding-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const id = fd.get("finding_id");
  await api(`/findings/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      status: fd.get("status"),
      assigned_to: fd.get("assigned_to") || null,
      remediation_notes: fd.get("remediation_notes") || null,
    }),
  });
  document.getElementById("finding-dialog").close();
  loadFindings();
});

document.getElementById("dialog-cancel").addEventListener("click", () => {
  document.getElementById("finding-dialog").close();
});

["finding-status-filter", "finding-priority-filter", "overdue-only"].forEach((id) => {
  document.getElementById(id).addEventListener("change", loadFindings);
});

async function loadAssets() {
  const data = await api("/assets?limit=200");
  document.getElementById("assets-body").innerHTML = data.items
    .map(
      (a) => `<tr>
        <td>${a.id}</td><td>${a.ecosystem}</td><td>${a.package_name}</td>
        <td>${a.version}</td><td>${a.business_criticality || "—"}</td><td>${a.owner_team || "—"}</td>
      </tr>`
    )
    .join("");
}

document.getElementById("asset-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  await api("/assets", {
    method: "POST",
    body: JSON.stringify({
      ecosystem: fd.get("ecosystem"),
      package_name: fd.get("package_name"),
      version: fd.get("version"),
      business_criticality: fd.get("business_criticality"),
    }),
  });
  e.target.reset();
  loadAssets();
});

async function loadVulnerabilities() {
  const q = document.getElementById("cve-search").value;
  const params = new URLSearchParams({ limit: "50" });
  if (q) params.set("search_text", q);
  const data = await api(`/vulnerabilities?${params}`);
  document.getElementById("vulns-body").innerHTML = data.items
    .map(
      (v) => `<tr>
        <td><a href="${v.nvd_url || "#"}" target="_blank" rel="noopener">${v.cve_id}</a></td>
        <td>${v.cvss_score}</td>
        <td>${v.epss_score != null ? (v.epss_score * 100).toFixed(1) + "%" : "—"}</td>
        <td>${badge(v.severity)}</td>
        <td>${(v.description || "").slice(0, 120)}…</td>
      </tr>`
    )
    .join("");
}

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

document.getElementById("cve-search").addEventListener("input", debounce(loadVulnerabilities, 400));

const appendLog = (msg) => {
  const el = document.getElementById("task-log");
  el.textContent += msg + "\n";
};

document.getElementById("btn-sync-nvd").addEventListener("click", async () => {
  appendLog("Запуск синхронизации NVD (может занять 1–2 мин.)...");
  try {
    const r = await api("/tasks/sync-nvd", { method: "POST" });
    appendLog(r.message);
    loadDashboard();
  } catch (e) {
    appendLog("Ошибка: " + e.message);
  }
});

document.getElementById("btn-update-epss").addEventListener("click", async () => {
  appendLog("Обновление EPSS...");
  try {
    const r = await api("/tasks/update-epss", { method: "POST" });
    appendLog(r.message);
  } catch (e) {
    appendLog("Ошибка: " + e.message);
  }
});

document.getElementById("btn-match").addEventListener("click", async () => {
  appendLog("Сопоставление активов с CVE...");
  try {
    const r = await api("/tasks/match-assets", { method: "POST" });
    appendLog(r.message);
    loadFindings();
  } catch (e) {
    appendLog("Ошибка: " + e.message);
  }
});

loadDashboard();
