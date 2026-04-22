# 🧭 CareerPilot

[![CI](https://github.com/ronchen0927/CareerPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/ronchen0927/CareerPilot/actions/workflows/ci.yml)

> AI 求職助理平台：搜尋職缺、AI 評估匹配度、自動生成求職信與改寫履歷、職缺 Q&A 對話，全流程一站搞定。

## ✨ 功能特色

- 🔍 **多來源搜尋** — 同時搜尋 104 人力銀行、CakeResume 與 Yourator，結果自動合併去重
- 🧠 **多關鍵字** — 逗號分隔最多 5 個關鍵字
- 📍 **篩選條件** — 依地區（六都）、工作經歷篩選；Yourator 額外支援職缺類別與月薪區間
- ⚡ **非同步爬取** — 多頁、多關鍵字同時抓取，速度飛快
- 🪟 **職缺詳細 Modal** — 點職位名稱展開詳情，不跳新分頁
- ⭐ **收藏 + 狀態追蹤** — 星星收藏職缺，標記「想投 / 已投 / 面試中 / 錄取 / 不適合」
- 📋 **投遞看板** — Kanban 看板視覺化求職進度，拖曳卡片更新狀態
- 🔔 **定時通知** — 設定條件後，有新職缺時自動推播至 Line Notify 或 Webhook
- ✨ **AI 職缺評分** — 貼上任何平台的職缺描述，或輸入 URL 自動擷取，搭配 PDF 履歷取得 AI 評估
- 💌 **AI 求職信** — 根據職缺與個人履歷自動生成客製化求職信，附歷史記錄
- 📝 **AI 履歷改寫** — 針對特定職缺改寫履歷內容，突顯匹配亮點，附歷史記錄
- 💬 **職缺 Q&A 對話** — 每個職缺獨立的 AI 串流問答，對話記錄自動保存
- 🔑 **AI 關鍵字建議** — 上傳 CV 後由 AI 建議 3-5 組適合的職位搜尋關鍵字
- 💓 **職缺活躍度偵測** — 背景定期檢查收藏職缺是否仍然有效，標記已關閉職缺
- 📥 **匯出 CSV** — 一鍵下載搜尋結果（UTF-8 BOM，Excel 直接開啟）
- 🌙 **深色 / 淺色模式** — 右上角一鍵切換，自動記住偏好

## 🚀 快速開始

### 環境需求

- Python 3.13+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) 套件管理工具

### 1. 啟動後端

```bash
cd backend
uv sync --group dev                               # 安裝依賴（含開發工具）
uv run playwright install chromium                # 安裝 Chromium（首次需執行）
uv run uvicorn app.main:app --reload --port 8000  # 啟動 API server
```

如需使用 AI 功能（評分、求職信、履歷改寫、Q&A 對話、關鍵字建議），在 `backend/.env` 加入：

```
OPENAI_API_KEY=sk-...
```

### 2. 啟動前端

```bash
cd frontend
npm install      # 安裝依賴（首次需執行）
npm run dev      # 啟動開發 server
```

### 3. 開始使用

打開瀏覽器前往 👉 **http://localhost:5173**

| 路由 | 說明 |
|------|------|
| `/` | 主搜尋頁，含收藏列表 |
| `/dashboard` | Kanban 投遞看板 |
| `/alerts` | 定時通知設定 |
| `/evaluate` | AI 職缺評分（貼文字 / 輸入 URL / 上傳 PDF 履歷） |
| `/history` | AI 評分歷史記錄 |
| `/cover-letter` | AI 求職信生成 |
| `/cover-letters` | 求職信歷史記錄 |
| `/resume-rewrite` | AI 履歷改寫 |
| `/resume-rewrites` | 履歷改寫歷史記錄 |
| `/settings` | 個人偏好設定（職缺條件、期望薪資等） |

## 🏗️ 技術架構

| 層級 | 技術 |
|------|------|
| 後端 API | FastAPI + Uvicorn |
| 排程 | asyncio 背景 task（內建，零額外依賴） |
| 爬蟲 | aiohttp（非同步）+ 104 內部 JSON API、CakeResume HTML、Yourator JSON API |
| 內容擷取 | trafilatura + Goose3（aiohttp 路徑）、Playwright（JS 渲染頁面 fallback） |
| AI 功能 | OpenAI API（GPT）、pdfplumber（PDF 解析）、StreamingResponse（串流回應） |
| 資料庫 | SQLite（aiosqlite），儲存評分、求職信、履歷改寫、職缺活躍度記錄 |
| 前端 | React 18 + TypeScript + Vite |
| 路由 | React Router v6 |
| 套件管理 | uv（後端）、npm（前端） |
| 資料儲存 | localStorage（書籤、看板、CV、對話記錄、使用者偏好）、alerts.json（提醒設定） |
| 測試 | pytest + httpx |
| 程式碼品質 | Ruff（lint + format）、pre-commit hooks、GitHub Actions CI |

## 📡 API 參考

啟動後端後，可前往 **http://localhost:8000/docs** 查看互動式 API 文件（Swagger UI）。

### 搜尋職缺

```
POST /api/jobs/search
```

```json
{
  "keyword": "Python",
  "pages": 5,
  "areas": ["6001001000"],
  "experience": ["3"],
  "sources": ["104", "cake", "yourator"],
  "categories": ["back-end"],
  "salary_min": 60000,
  "salary_max": 100000
}
```

> `categories` 與 `salary_min` / `salary_max` 僅對 Yourator 來源有效。

### AI 評分

```
POST /api/jobs/evaluate-text   # 純文字 JD 評分
POST /api/jobs/evaluate        # 結構化 JobListing 評分（搜尋結果 Modal 使用）
GET  /api/history              # 評分歷史列表
GET  /api/history/{id}         # 單筆評分記錄
```

### AI 求職信

```
POST /api/jobs/cover-letter    # 生成求職信
GET  /api/cover-letters        # 歷史列表
GET  /api/cover-letters/{id}   # 單筆記錄
```

### AI 履歷改寫

```
POST /api/jobs/resume-rewrite  # 改寫履歷
GET  /api/resume-rewrites      # 歷史列表
GET  /api/resume-rewrites/{id} # 單筆記錄
```

### 職缺 Q&A 對話（串流）

```
POST /api/chat
```

```json
{
  "messages": [{ "role": "user", "content": "這個職缺適合我嗎？" }],
  "job": { "..." },
  "user_cv": "個人履歷文字"
}
```

回應為 `text/plain; charset=utf-8` 串流，前端以 `ReadableStream` 接收。

### PDF 履歷解析 & AI 關鍵字建議

```
POST /api/cv/parse              # multipart/form-data，欄位名稱 file，回傳 { "text": "..." }
POST /api/cv/suggest-keywords   # { "cv_text": "..." } → { "keywords": ["...", ...] }
```

### URL 頁面擷取

```
POST /api/jobs/fetch-url
```

```json
{ "url": "https://www.cakeresume.com/jobs/..." }
```

擷取策略：104 detail API → aiohttp+trafilatura/Goose3 → Playwright（三層 fallback）。

### 職缺活躍度

```
POST /api/liveness/status   # 查詢指定 URL 清單的活躍狀態
POST /api/liveness/check    # 立即觸發指定 URL 的重新檢查
```

### 職缺提醒

```
GET    /api/alerts              # 列出所有提醒
POST   /api/alerts              # 建立提醒
DELETE /api/alerts/{id}         # 刪除提醒
POST   /api/alerts/{id}/trigger # 立即觸發（測試用）
```

## 🧪 開發與測試

```bash
cd backend
uv run pytest                        # 執行全部測試
uv run pytest tests/test_scraper.py  # 執行單一測試檔
uv run ruff check .                  # Lint 檢查
uv run ruff format .                 # 格式化
```

pre-commit hooks 會在每次 commit 時自動執行 Ruff lint 與格式化：

```bash
uv run pre-commit install   # 安裝 hooks（只需執行一次）
```

## 📄 授權

MIT License
