/**
 * 104 Job Scraper — Frontend Application
 *
 * Handles:
 * - Loading filter options from API
 * - Submitting search requests
 * - Rendering results table
 * - Loading / error state management
 */

const API_BASE = "http://localhost:8000";

// DOM references
const searchForm = document.getElementById("search-form");
const searchBtn = document.getElementById("search-btn");
const loadingEl = document.getElementById("loading");
const resultsEl = document.getElementById("results");
const errorEl = document.getElementById("error");
const errorMsg = document.getElementById("error-message");
const errorDismiss = document.getElementById("error-dismiss");
const resultCount = document.getElementById("result-count");
const resultTime = document.getElementById("result-time");
const resultsBody = document.getElementById("results-body");
const areaContainer = document.getElementById("area-options");
const expContainer = document.getElementById("experience-options");

// ==========================================
// Init — Load Options
// ==========================================
async function loadOptions() {
    try {
        const res = await fetch(`${API_BASE}/api/jobs/options`);
        if (!res.ok) throw new Error("無法載入選項");
        const data = await res.json();

        renderCheckboxes(areaContainer, data.areas, "area");
        renderCheckboxes(expContainer, data.experience, "exp");
    } catch (err) {
        console.error("載入選項失敗:", err);
        // Fallback: render hardcoded options
        renderFallbackOptions();
    }
}

function renderCheckboxes(container, options, prefix) {
    container.innerHTML = options
        .map(
            (opt, i) => `
      <div class="checkbox-chip">
        <input type="checkbox" id="${prefix}-${i}" value="${opt.value}">
        <label for="${prefix}-${i}">${opt.label}</label>
      </div>
    `
        )
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
    renderCheckboxes(areaContainer, areas, "area");
    renderCheckboxes(expContainer, exps, "exp");
}

// ==========================================
// Search
// ==========================================
searchForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    await performSearch();
});

async function performSearch() {
    const keyword = document.getElementById("keyword").value.trim();
    const pages = parseInt(document.getElementById("pages").value, 10) || 5;

    if (!keyword) return;

    // Gather checked values
    const areas = getCheckedValues("#area-options input:checked");
    const experience = getCheckedValues("#experience-options input:checked");

    // UI state
    showLoading();

    try {
        const res = await fetch(`${API_BASE}/api/jobs/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ keyword, pages, areas, experience }),
        });

        if (!res.ok) {
            const detail = await res.json().catch(() => ({}));
            throw new Error(detail.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        renderResults(data);
    } catch (err) {
        showError(err.message || "搜尋時發生未知錯誤");
    }
}

function getCheckedValues(selector) {
    return Array.from(document.querySelectorAll(selector)).map((cb) => cb.value);
}

// ==========================================
// Render Results
// ==========================================
function renderResults(data) {
    hideLoading();
    errorEl.classList.add("hidden");

    resultCount.textContent = `${data.count} 筆結果`;
    resultTime.textContent = `耗時 ${data.elapsed_time} 秒`;

    resultsBody.innerHTML = data.results
        .map(
            (job, i) => `
      <tr class="${job.is_featured ? "featured" : ""}" style="animation-delay: ${i * 0.03}s">
        <td>
          ${job.is_featured
                    ? '<span class="featured-badge">⭐ 精選</span>'
                    : escapeHtml(job.date)
                }
        </td>
        <td>
          <a href="${escapeHtml(job.link)}" target="_blank" rel="noopener" class="job-link">
            ${escapeHtml(job.job)}
          </a>
        </td>
        <td>${escapeHtml(job.company)}</td>
        <td>${escapeHtml(job.city)}</td>
        <td>${escapeHtml(job.experience)}</td>
        <td>${escapeHtml(job.education)}</td>
        <td><span class="salary-text">${escapeHtml(job.salary)}</span></td>
      </tr>
    `
        )
        .join("");

    resultsEl.classList.remove("hidden");

    // Scroll to results
    resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ==========================================
// UI State Helpers
// ==========================================
function showLoading() {
    loadingEl.classList.remove("hidden");
    resultsEl.classList.add("hidden");
    errorEl.classList.add("hidden");
    searchBtn.disabled = true;
    searchBtn.querySelector(".btn-search__text").textContent = "搜尋中...";
}

function hideLoading() {
    loadingEl.classList.add("hidden");
    searchBtn.disabled = false;
    searchBtn.querySelector(".btn-search__text").textContent = "開始搜尋";
}

function showError(msg) {
    hideLoading();
    resultsEl.classList.add("hidden");
    errorMsg.textContent = msg;
    errorEl.classList.remove("hidden");
}

errorDismiss.addEventListener("click", () => {
    errorEl.classList.add("hidden");
});

// ==========================================
// Utilities
// ==========================================
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
}

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

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    themeIcon.textContent = next === "light" ? "☀️" : "🌙";
}

themeToggle.addEventListener("click", toggleTheme);

// ==========================================
// Boot
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    loadOptions();
});
