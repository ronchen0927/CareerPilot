/**
 * 104 Job Scraper — Frontend Application
 *
 * Handles:
 * - Loading filter options from API
 * - Multi-keyword search (comma-separated, parallel fetches, merged & deduped)
 * - Salary filter (client-side, instant)
 * - Rendering results table with job detail modal
 * - Bookmark management (localStorage)
 * - CSV export
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
const keywordTagsEl = document.getElementById("keyword-tags");
const resultsBody = document.getElementById("results-body");
const areaContainer = document.getElementById("area-options");
const expContainer = document.getElementById("experience-options");
const minSalaryInput = document.getElementById("min-salary");
const exportCsvBtn = document.getElementById("export-csv-btn");
const bookmarksEl = document.getElementById("bookmarks");
const bookmarksBody = document.getElementById("bookmarks-body");
const bookmarkCountEl = document.getElementById("bookmark-count");
const jobModal = document.getElementById("job-modal");
const modalClose = document.getElementById("modal-close");

// ==========================================
// State
// ==========================================
let lastResults = [];       // All results from the last API call
let displayedResults = [];  // After salary filter — what's shown in the table

const STATUSES = ["想投", "已投", "面試中", "錄取", "不適合"];
const STATUS_CSS = {
    "想投":   "status--want",
    "已投":   "status--applied",
    "面試中": "status--interview",
    "錄取":   "status--offer",
    "不適合": "status--reject",
};

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
// Search (multi-keyword support)
// ==========================================
searchForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    await performSearch();
});

async function performSearch() {
    const rawKeyword = document.getElementById("keyword").value.trim();
    // Split by comma, deduplicate, drop empty entries
    const keywords = [...new Set(
        rawKeyword.split(",").map(k => k.trim()).filter(Boolean)
    )];

    if (keywords.length === 0) return;
    if (keywords.length > 5) {
        showError("最多支援 5 個關鍵字，請減少後再搜尋");
        return;
    }

    const pages = parseInt(document.getElementById("pages").value, 10) || 5;
    const areas = getCheckedValues("#area-options input:checked");
    const experience = getCheckedValues("#experience-options input:checked");

    showLoading(keywords);

    try {
        // Fire all keyword searches in parallel
        const responses = await Promise.all(
            keywords.map(keyword =>
                fetch(`${API_BASE}/api/jobs/search`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ keyword, pages, areas, experience }),
                })
            )
        );

        const allData = await Promise.all(
            responses.map(async (res) => {
                if (!res.ok) {
                    const detail = await res.json().catch(() => ({}));
                    throw new Error(detail.detail || `HTTP ${res.status}`);
                }
                return res.json();
            })
        );

        // Merge, deduplicate by link, sort by date descending
        const seen = new Set();
        const merged = [];
        let maxElapsed = 0;

        for (const data of allData) {
            maxElapsed = Math.max(maxElapsed, data.elapsed_time);
            for (const job of data.results) {
                if (!seen.has(job.link)) {
                    seen.add(job.link);
                    merged.push(job);
                }
            }
        }

        merged.sort((a, b) => b.date.localeCompare(a.date));

        renderResults(
            { results: merged, count: merged.length, elapsed_time: maxElapsed },
            keywords
        );
    } catch (err) {
        showError(err.message || "搜尋時發生未知錯誤");
    }
}

function getCheckedValues(selector) {
    return Array.from(document.querySelectorAll(selector)).map((cb) => cb.value);
}

// ==========================================
// Salary Filter
// ==========================================
function getMinSalary() {
    return parseInt(minSalaryInput.value, 10) || 0;
}

minSalaryInput.addEventListener("input", () => {
    if (lastResults.length > 0) applyAndRenderResults();
});

function applyAndRenderResults() {
    const minSalary = getMinSalary();
    displayedResults = minSalary > 0
        ? lastResults.filter(job => job.salary_low >= minSalary)
        : [...lastResults];

    if (minSalary > 0) {
        resultCount.textContent = `${displayedResults.length} 筆（共 ${lastResults.length} 筆，已篩選）`;
    } else {
        resultCount.textContent = `${lastResults.length} 筆結果`;
    }

    renderTable(displayedResults);
}

// ==========================================
// Render Results
// ==========================================
function renderResults(data, keywords = []) {
    hideLoading();
    errorEl.classList.add("hidden");

    lastResults = data.results;
    resultTime.textContent = `耗時 ${data.elapsed_time} 秒`;

    renderKeywordTags(keywords);
    applyAndRenderResults();

    resultsEl.classList.remove("hidden");
    resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderKeywordTags(keywords) {
    if (!keywordTagsEl) return;
    keywordTagsEl.innerHTML = keywords
        .map(k => `<span class="keyword-tag">${escapeHtml(k)}</span>`)
        .join("");
}

function renderTable(jobs) {
    const bookmarks = loadBookmarks();
    resultsBody.innerHTML = jobs
        .map((job, i) => {
            const starred = !!bookmarks[job.link];
            return `
      <tr class="${job.is_featured ? "featured" : ""}" style="animation-delay: ${i * 0.03}s">
        <td>
          ${job.is_featured
                    ? '<span class="featured-badge">⭐ 精選</span>'
                    : escapeHtml(job.date)
                }
        </td>
        <td>
          <button class="job-link job-detail-btn" data-link="${escapeHtml(job.link)}">
            ${escapeHtml(job.job)}
          </button>
        </td>
        <td>${escapeHtml(job.company)}</td>
        <td>${escapeHtml(job.city)}</td>
        <td>${escapeHtml(job.experience)}</td>
        <td>${escapeHtml(job.education)}</td>
        <td><span class="salary-text">${escapeHtml(job.salary)}</span></td>
        <td>
          <button class="btn-bookmark ${starred ? "btn-bookmark--active" : ""}"
                  data-link="${escapeHtml(job.link)}"
                  title="${starred ? "取消收藏" : "加入收藏"}">
            ${starred ? "★" : "☆"}
          </button>
        </td>
      </tr>
    `;
        })
        .join("");
}

// Consolidated event delegation for results table
resultsBody.addEventListener("click", (e) => {
    const detailBtn = e.target.closest(".job-detail-btn");
    if (detailBtn) {
        const link = detailBtn.dataset.link;
        const job = displayedResults.find(j => j.link === link);
        if (job) openJobModal(job);
        return;
    }

    const bookmarkBtn = e.target.closest(".btn-bookmark");
    if (bookmarkBtn) {
        const link = bookmarkBtn.dataset.link;
        const job = displayedResults.find(j => j.link === link);
        if (job) toggleBookmark(job);
    }
});

// ==========================================
// Job Detail Modal (Feature 7)
// ==========================================
function openJobModal(job) {
    document.getElementById("modal-job").textContent = job.job;
    document.getElementById("modal-company").textContent = job.company;
    document.getElementById("modal-city").textContent = job.city;
    document.getElementById("modal-date").textContent = job.is_featured ? "精選職缺" : job.date;
    document.getElementById("modal-experience").textContent = job.experience;
    document.getElementById("modal-education").textContent = job.education;
    document.getElementById("modal-salary").textContent = job.salary;
    document.getElementById("modal-link").href = job.link;
    jobModal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
}

function closeJobModal() {
    jobModal.classList.add("hidden");
    document.body.style.overflow = "";
}

modalClose.addEventListener("click", closeJobModal);

jobModal.addEventListener("click", (e) => {
    if (e.target === jobModal) closeJobModal();
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !jobModal.classList.contains("hidden")) closeJobModal();
});

// ==========================================
// Bookmark Management (localStorage)
// ==========================================
function loadBookmarks() {
    try {
        return JSON.parse(localStorage.getItem("jobradar_bookmarks") || "{}");
    } catch {
        return {};
    }
}

function saveBookmarks(bookmarks) {
    localStorage.setItem("jobradar_bookmarks", JSON.stringify(bookmarks));
}

function toggleBookmark(job) {
    const bookmarks = loadBookmarks();
    if (bookmarks[job.link]) {
        delete bookmarks[job.link];
    } else {
        bookmarks[job.link] = {
            job: job.job,
            date: job.date,
            company: job.company,
            city: job.city,
            salary: job.salary,
            status: "想投",
        };
    }
    saveBookmarks(bookmarks);
    renderBookmarks();
    updateStarButtons();
}

function setBookmarkStatus(link, status) {
    const bookmarks = loadBookmarks();
    if (bookmarks[link]) {
        bookmarks[link].status = status;
        saveBookmarks(bookmarks);
    }
}

function removeBookmark(link) {
    const bookmarks = loadBookmarks();
    delete bookmarks[link];
    saveBookmarks(bookmarks);
    renderBookmarks();
    updateStarButtons();
}

function updateStarButtons() {
    const bookmarks = loadBookmarks();
    document.querySelectorAll(".btn-bookmark").forEach(btn => {
        const link = btn.dataset.link;
        const starred = !!bookmarks[link];
        btn.textContent = starred ? "★" : "☆";
        btn.title = starred ? "取消收藏" : "加入收藏";
        btn.classList.toggle("btn-bookmark--active", starred);
    });
}

// ==========================================
// Render Bookmark Section
// ==========================================
function renderBookmarks() {
    const bookmarks = loadBookmarks();
    const entries = Object.entries(bookmarks);

    if (entries.length === 0) {
        bookmarksEl.classList.add("hidden");
        return;
    }

    bookmarksEl.classList.remove("hidden");
    bookmarkCountEl.textContent = `${entries.length} 筆`;

    bookmarksBody.innerHTML = entries
        .map(([link, bm]) => `
      <tr data-link="${escapeHtml(link)}">
        <td>${escapeHtml(bm.date)}</td>
        <td>
          <a href="${escapeHtml(link)}" target="_blank" rel="noopener" class="job-link">
            ${escapeHtml(bm.job)}
          </a>
        </td>
        <td>${escapeHtml(bm.company)}</td>
        <td>${escapeHtml(bm.city)}</td>
        <td><span class="salary-text">${escapeHtml(bm.salary)}</span></td>
        <td>
          <select class="status-select ${STATUS_CSS[bm.status] || ""}">
            ${STATUSES.map(s => `<option value="${s}" ${s === bm.status ? "selected" : ""}>${s}</option>`).join("")}
          </select>
        </td>
        <td>
          <button class="btn-remove">移除</button>
        </td>
      </tr>
    `)
        .join("");
}

// Event delegation for bookmark section
bookmarksBody.addEventListener("change", (e) => {
    if (e.target.classList.contains("status-select")) {
        const link = e.target.closest("tr").dataset.link;
        setBookmarkStatus(link, e.target.value);
        e.target.className = `status-select ${STATUS_CSS[e.target.value] || ""}`;
    }
});

bookmarksBody.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-remove");
    if (!btn) return;
    const link = btn.closest("tr").dataset.link;
    removeBookmark(link);
});

// ==========================================
// CSV Export
// ==========================================
exportCsvBtn.addEventListener("click", () => {
    if (displayedResults.length === 0) return;

    const headers = ["刊登日期", "職位", "公司名稱", "城市", "經歷", "最低學歷", "薪水", "連結"];
    const rows = displayedResults.map(job => [
        job.date,
        job.job,
        job.company,
        job.city,
        job.experience,
        job.education,
        job.salary,
        job.link,
    ]);

    const csv = [headers, ...rows]
        .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(","))
        .join("\n");

    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `jobradar_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
});

// ==========================================
// UI State Helpers
// ==========================================
function showLoading(keywords = []) {
    loadingEl.classList.remove("hidden");
    resultsEl.classList.add("hidden");
    errorEl.classList.add("hidden");
    searchBtn.disabled = true;
    searchBtn.querySelector(".btn-search__text").textContent = "搜尋中...";
    const text = keywords.length > 1
        ? `正在搜尋「${keywords.join("」、「")}」...`
        : "正在搜尋職缺中...";
    loadingEl.querySelector(".loading__text").textContent = text;
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
    renderBookmarks();
});
