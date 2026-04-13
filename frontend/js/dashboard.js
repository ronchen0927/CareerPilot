/**
 * JobRadar — 投遞看板 (Job Tracker Dashboard)
 *
 * Kanban board that reads bookmarks from localStorage.
 * Cards can be dragged between columns to update status.
 */

const STATUSES = ["想投", "已投", "面試中", "錄取", "不適合"];

const STATUS_CONFIG = {
    "想投":   { color: "#6366f1", bg: "rgba(99,102,241,0.12)" },
    "已投":   { color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
    "面試中": { color: "#8b5cf6", bg: "rgba(139,92,246,0.12)" },
    "錄取":   { color: "#10b981", bg: "rgba(16,185,129,0.12)" },
    "不適合": { color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
};

// The link of the card currently being dragged
let draggedLink = null;

// ==========================================
// Bookmark Storage
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

// ==========================================
// Board Rendering
// ==========================================
function renderBoard() {
    const bookmarks = loadBookmarks();
    const entries = Object.entries(bookmarks);
    const board = document.getElementById("kanban-board");
    const emptyState = document.getElementById("empty-state");

    if (entries.length === 0) {
        board.classList.add("hidden");
        emptyState.classList.remove("hidden");
        renderStats({});
        return;
    }

    board.classList.remove("hidden");
    emptyState.classList.add("hidden");

    // Group jobs by status
    const groups = Object.fromEntries(STATUSES.map(s => [s, []]));
    for (const [link, bm] of entries) {
        const status = bm.status || "想投";
        if (groups[status]) groups[status].push([link, bm]);
    }

    board.innerHTML = STATUSES
        .map(status => renderColumn(status, groups[status]))
        .join("");

    setupDragAndDrop();
    renderStats(groups);
}

function renderColumn(status, jobs) {
    const cfg = STATUS_CONFIG[status];
    return `
        <div class="kanban-column"
             style="--col-color:${cfg.color}; --col-bg:${cfg.bg}">
          <div class="kanban-column__header">
            <span class="kanban-column__title">${status}</span>
            <span class="kanban-column__count">${jobs.length}</span>
          </div>
          <div class="kanban-cards" data-status="${status}">
            ${jobs.map(([link, bm]) => renderCard(link, bm)).join("")}
            <div class="kanban-drop-zone"></div>
          </div>
        </div>
    `;
}

function renderCard(link, bm) {
    return `
        <div class="kanban-card" draggable="true" data-link="${escapeHtml(link)}">
          <button class="kanban-card__remove" data-link="${escapeHtml(link)}" title="移除">✕</button>
          <a href="${escapeHtml(link)}" target="_blank" rel="noopener" class="kanban-card__title">
            ${escapeHtml(bm.job)}
          </a>
          <div class="kanban-card__meta">
            <span class="kanban-card__company">${escapeHtml(bm.company)}</span>
            <span class="kanban-card__city">${escapeHtml(bm.city)}</span>
          </div>
          <span class="kanban-card__salary">${escapeHtml(bm.salary)}</span>
        </div>
    `;
}

function renderStats(groups) {
    const statsBar = document.getElementById("stats-bar");
    const total = Object.values(groups).flat().length;

    statsBar.innerHTML = [
        `<span class="stat-total">${total} 筆收藏</span>`,
        ...STATUSES
            .filter(s => (groups[s] || []).length > 0)
            .map(s => {
                const cfg = STATUS_CONFIG[s];
                return `<span class="stat-chip"
                    style="color:${cfg.color}; border-color:${cfg.color}; background:${cfg.bg}">
                    ${s} ${groups[s].length}
                </span>`;
            }),
    ].join("");
}

// ==========================================
// Drag and Drop
// ==========================================
function setupDragAndDrop() {
    // Cards — drag source
    document.querySelectorAll(".kanban-card").forEach(card => {
        card.addEventListener("dragstart", (e) => {
            draggedLink = card.dataset.link;
            e.dataTransfer.effectAllowed = "move";
            // Defer class addition so the drag ghost renders normally
            requestAnimationFrame(() => card.classList.add("kanban-card--dragging"));
        });

        card.addEventListener("dragend", () => {
            card.classList.remove("kanban-card--dragging");
            document.querySelectorAll(".kanban-cards").forEach(col =>
                col.classList.remove("kanban-cards--drag-over")
            );
        });
    });

    // Column drop zones
    document.querySelectorAll(".kanban-cards").forEach(zone => {
        zone.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
            zone.classList.add("kanban-cards--drag-over");
        });

        zone.addEventListener("dragleave", (e) => {
            if (!zone.contains(e.relatedTarget)) {
                zone.classList.remove("kanban-cards--drag-over");
            }
        });

        zone.addEventListener("drop", (e) => {
            e.preventDefault();
            zone.classList.remove("kanban-cards--drag-over");

            const newStatus = zone.dataset.status;
            if (!draggedLink || !newStatus) return;

            const bookmarks = loadBookmarks();
            if (bookmarks[draggedLink]) {
                bookmarks[draggedLink].status = newStatus;
                saveBookmarks(bookmarks);
                renderBoard();
            }
            draggedLink = null;
        });
    });

    // Remove buttons
    document.querySelectorAll(".kanban-card__remove").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            e.preventDefault(); // prevent card link from firing
            const link = btn.dataset.link;
            const bookmarks = loadBookmarks();
            delete bookmarks[link];
            saveBookmarks(bookmarks);
            renderBoard();
        });
    });
}

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
    renderBoard();
});
