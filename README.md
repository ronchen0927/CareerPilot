# 🧭 CareerPilot

[![CI](https://github.com/ronchen0927/CareerPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/ronchen0927/CareerPilot/actions/workflows/ci.yml)

> AI 求職助理平台：搜尋職缺、AI 評估匹配度、自動生成求職信，全流程一站搞定。

## ✨ 功能特色

- 🔍 **多來源搜尋** — 同時搜尋 104 人力銀行與 CakeResume，結果自動合併去重
- 🧠 **多關鍵字** — 逗號分隔最多 5 個關鍵字
- 📍 **篩選條件** — 依地區（六都）、工作經歷、最低月薪篩選
- ⚡ **非同步爬取** — 多頁、多關鍵字同時抓取，速度飛快
- 🪟 **職缺詳細 Modal** — 點職位名稱展開詳情，不跳新分頁
- ⭐ **收藏 + 狀態追蹤** — 星星收藏職缺，標記「想投 / 已投 / 面試中 / 錄取 / 不適合」
- 📋 **投遞看板** — Kanban 看板視覺化求職進度，拖曳卡片更新狀態
- 🔔 **定時通知** — 設定條件後，有新職缺時自動推播至 Line Notify 或 Webhook
- ✨ **AI 職缺評分** — 貼上任何平台的職缺描述，或輸入 URL 自動擷取，搭配 PDF 履歷取得 AI 評估
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

如需使用 AI 評分功能，在 `backend/.env` 加入：

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

## 🏗️ 技術架構

| 層級 | 技術 |
|------|------|
| 後端 API | FastAPI + Uvicorn |
| 排程 | asyncio 背景 task（內建，零額外依賴） |
| 爬蟲 | aiohttp（非同步）+ 104 內部 JSON API、CakeResume HTML |
| AI 評分 | OpenAI API（GPT）、pdfplumber（PDF 解析）、Playwright（URL 擷取） |
| 前端 | React 18 + TypeScript + Vite |
| 路由 | React Router v6 |
| 套件管理 | uv（後端）、npm（前端） |
| 資料儲存 | localStorage（書籤、看板狀態、CV）、alerts.json（後端提醒設定） |
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
  "sources": ["104", "CakeResume"]
}
```

### AI 評分

```
POST /api/jobs/evaluate-text   # 純文字 JD 評分
POST /api/jobs/evaluate        # 結構化 JobListing 評分（搜尋結果 Modal 使用）
```

```json
{
  "job_text": "職缺描述全文...",
  "user_cv": "個人背景描述（選填）"
}
```

### PDF 履歷解析

```
POST /api/cv/parse   # multipart/form-data，欄位名稱 file，回傳 { "text": "..." }
```

### URL 頁面擷取

```
POST /api/jobs/fetch-url
```

```json
{ "url": "https://www.cakeresume.com/jobs/..." }
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
