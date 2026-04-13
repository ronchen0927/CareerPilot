/**
 * JobRadar — 職缺提醒管理頁面
 *
 * Handles:
 * - Loading filter options from API
 * - Creating / deleting alerts via API
 * - Triggering an alert immediately (for testing)
 * - Rendering the active alerts list
 */

const API_BASE = "http://localhost:8000";

// ==========================================
// Init — Load Options
// ==========================================
async function loadOptions() {
    try {
        const res = await fetch(`${API_BASE}/api/jobs/options`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        renderCheckboxes(document.getElementById("alert-area-options"), data.areas, "a-area");
        renderCheckboxes(document.getElementById("alert-exp-options"), data.experience, "a-exp");
    } catch {
        renderFallbackOptions();
    }
}

function renderCheckboxes(container, options, prefix) {
    container.innerHTML = options
        .map((opt, i) => `
            <div class="checkbox-chip">
                <input type="checkbox" id="${prefix}-${i}" value="${opt.value}">
                <label for="${prefix}-${i}">${opt.label}</label>
            </div>
        `)
        .join("");
}

function renderFallbackOptions() {
    const areas = [
        { value: "6001001000", label: "台北市" },
        { value: "6001002000", label: "新北市" },
        { value: "6001006000", label: "新竹市" },
        { value: "6001008000", label: "台中市" },
        { value: "6001014000", label: "台南市" },
        { value: "6001016000", label: "高雄市" },
    ];
    const exps = [
        { value: "1", label: "1年以下" },
        { value: "3", label: "1-3年" },
        { value: "5", label: "3-5年" },
        { value: "10", label: "5-10年" },
        { value: "99", label: "10年以上" },
    ];
    renderCheckboxes(document.getElementById("alert-area-options"), areas, "a-area");
    renderCheckboxes(document.getElementById("alert-exp-options"), exps, "a-exp");
}

// ==========================================
// Notify Type Toggle
// ==========================================
const notifyRadios = document.querySelectorAll("input[name='notify-type']");
const targetIcon = document.getElementById("target-icon");
const targetLabel = document.getElementById("target-label");
const targetHint = document.getElementById("target-hint");
const targetInput = document.getElementById("alert-target");

notifyRadios.forEach(radio => {
    radio.addEventListener("change", () => {
        if (radio.value === "line") {
            targetIcon.textContent = "🔑";
            targetLabel.textContent = "Line Notify Token";
            targetHint.textContent = "取得 Token →";
            targetHint.href = "https://notify-bot.line.me/my/";
            targetHint.classList.remove("hidden");
            targetInput.placeholder = "貼上 Line Notify Token...";
        } else {
            targetIcon.textContent = "🌐";
            targetLabel.textContent = "Webhook URL";
            targetHint.classList.add("hidden");
            targetInput.placeholder = "https://hooks.example.com/...";
        }
    });
});

// ==========================================
// Create Alert
// ==========================================
document.getElementById("alert-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const keyword = document.getElementById("alert-keyword").value.trim();
    const pages = parseInt(document.getElementById("alert-pages").value, 10) || 3;
    const minSalary = parseInt(document.getElementById("alert-min-salary").value, 10) || 0;
    const interval = parseInt(document.getElementById("alert-interval").value, 10);
    const notifyType = document.querySelector("input[name='notify-type']:checked").value;
    const notifyTarget = targetInput.value.trim();

    const areas = getCheckedValues("#alert-area-options input:checked");
    const experience = getCheckedValues("#alert-exp-options input:checked");

    const btn = document.getElementById("alert-submit-btn");
    btn.disabled = true;
    btn.querySelector(".btn-search__text").textContent = "建立中...";

    try {
        const res = await fetch(`${API_BASE}/api/alerts`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                keyword,
                pages,
                areas,
                experience,
                min_salary: minSalary,
                notify_type: notifyType,
                notify_target: notifyTarget,
                interval_minutes: interval,
            }),
        });

        if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            throw new Error(detail.detail || `HTTP ${res.status}`);
        }

        // Reset form
        document.getElementById("alert-form").reset();
        await loadAlerts();
    } catch (err) {
        showError(err.message || "建立失敗，請確認後端是否運行中");
    } finally {
        btn.disabled = false;
        btn.querySelector(".btn-search__text").textContent = "建立提醒";
    }
});

function getCheckedValues(selector) {
    return Array.from(document.querySelectorAll(selector)).map(cb => cb.value);
}

// ==========================================
// Load & Render Alerts List
// ==========================================
async function loadAlerts() {
    try {
        const res = await fetch(`${API_BASE}/api/alerts`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        renderAlerts(data.alerts);
    } catch {
        showError("無法載入提醒列表，請確認後端是否運行中");
    }
}

function renderAlerts(alerts) {
    const section = document.getElementById("alerts-list-section");
    const list = document.getElementById("alerts-list");
    const empty = document.getElementById("alerts-empty");

    if (alerts.length === 0) {
        section.classList.add("hidden");
        empty.classList.remove("hidden");
        return;
    }

    section.classList.remove("hidden");
    empty.classList.add("hidden");

    list.innerHTML = alerts.map(alert => `
        <div class="alert-card" data-id="${escapeHtml(alert.id)}">
          <div class="alert-card__header">
            <div class="alert-card__keyword">${escapeHtml(alert.keyword)}</div>
            <div class="alert-card__actions">
              <button class="btn-trigger" data-id="${escapeHtml(alert.id)}" title="立即觸發">立即測試</button>
              <button class="btn-delete" data-id="${escapeHtml(alert.id)}" title="刪除">刪除</button>
            </div>
          </div>
          <div class="alert-card__meta">
            ${alert.min_salary > 0 ? `<span class="alert-chip alert-chip--salary">月薪 ≥ ${alert.min_salary.toLocaleString()} 元</span>` : ""}
            ${alert.areas.length > 0 ? `<span class="alert-chip">📍 ${alert.areas.length} 個地區</span>` : ""}
            ${alert.experience.length > 0 ? `<span class="alert-chip">⏳ ${alert.experience.length} 個經歷</span>` : ""}
            <span class="alert-chip">📄 ${alert.pages} 頁</span>
          </div>
          <div class="alert-card__footer">
            <span class="alert-notify-badge alert-notify-badge--${escapeHtml(alert.notify_type)}">
              ${alert.notify_type === "line" ? "Line Notify" : "Webhook"}
            </span>
            <span class="alert-interval">每 ${formatInterval(alert.interval_minutes)}</span>
            <span class="alert-last-run">${formatLastRun(alert.last_run)}</span>
          </div>
        </div>
    `).join("");

    // Attach handlers
    list.querySelectorAll(".btn-delete").forEach(btn => {
        btn.addEventListener("click", () => deleteAlert(btn.dataset.id));
    });
    list.querySelectorAll(".btn-trigger").forEach(btn => {
        btn.addEventListener("click", () => triggerAlert(btn.dataset.id, btn));
    });
}

// ==========================================
// Delete Alert
// ==========================================
async function deleteAlert(alertId) {
    try {
        const res = await fetch(`${API_BASE}/api/alerts/${alertId}`, { method: "DELETE" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await loadAlerts();
    } catch (err) {
        showError(err.message || "刪除失敗");
    }
}

// ==========================================
// Trigger Alert (test)
// ==========================================
async function triggerAlert(alertId, btn) {
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = "執行中...";

    try {
        const res = await fetch(`${API_BASE}/api/alerts/${alertId}/trigger`, { method: "POST" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        btn.textContent = `✓ 找到 ${data.new_jobs_found} 筆新職缺`;
        setTimeout(() => {
            btn.textContent = original;
            btn.disabled = false;
            loadAlerts();
        }, 3000);
    } catch (err) {
        showError(err.message || "觸發失敗");
        btn.textContent = original;
        btn.disabled = false;
    }
}

// ==========================================
// Utilities
// ==========================================
function formatInterval(minutes) {
    if (minutes < 60) return `${minutes} 分鐘`;
    if (minutes === 60) return "1 小時";
    if (minutes < 1440) return `${minutes / 60} 小時`;
    return "天";
}

function formatLastRun(isoStr) {
    if (!isoStr) return "尚未執行";
    const diff = Date.now() - new Date(isoStr).getTime();
    const min = Math.floor(diff / 60000);
    if (min < 1) return "剛剛執行";
    if (min < 60) return `${min} 分鐘前執行`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr} 小時前執行`;
    return `${Math.floor(hr / 24)} 天前執行`;
}

function showError(msg) {
    const errorEl = document.getElementById("error");
    document.getElementById("error-message").textContent = msg;
    errorEl.classList.remove("hidden");
}

document.getElementById("error-dismiss").addEventListener("click", () => {
    document.getElementById("error").classList.add("hidden");
});

// ==========================================
// Theme Toggle
// ==========================================
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = themeToggle.querySelector(".theme-toggle__icon");

function initTheme() {
    const saved = localStorage.getItem("theme");
    if (saved) {
        document.documentElement.setAttribute("data-theme", saved);
        themeIcon.textContent = saved === "light" ? "☀️" : "🌙";
    }
}

themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    themeIcon.textContent = next === "light" ? "☀️" : "🌙";
});

// ==========================================
// Boot
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    loadOptions();
    loadAlerts();
});
