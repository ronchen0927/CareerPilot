/**
 * Shared utilities used across all pages.
 */

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = String(text || "");
    return div.innerHTML;
}
