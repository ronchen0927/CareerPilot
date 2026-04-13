# 📡 JobRadar

[![CI](https://github.com/ronchen0927/JobRadar/actions/workflows/ci.yml/badge.svg)](https://github.com/ronchen0927/JobRadar/actions/workflows/ci.yml)

> 快速搜尋 [104 人力銀行](https://www.104.com.tw/) 職缺的工具，輸入關鍵字即可一鍵搜尋、篩選、收藏、追蹤，並支援新職缺自動通知。

## ✨ 功能特色

- 🔍 **多關鍵字搜尋** — 逗號分隔最多 5 個關鍵字，結果自動合併去重
- 📍 **篩選條件** — 依地區（六都）、工作經歷、最低月薪篩選
- ⚡ **非同步爬取** — 多頁、多關鍵字同時抓取，速度飛快
- 🪟 **職缺詳細 Modal** — 點職位名稱展開詳情，不跳新分頁
- ⭐ **收藏 + 狀態追蹤** — 星星收藏職缺，標記「想投 / 已投 / 面試中 / 錄取 / 不適合」
- 📋 **投遞看板** — Kanban 看板視覺化求職進度，拖曳卡片更新狀態
- 🔔 **定時通知** — 設定條件後，有新職缺時自動推播至 Line Notify 或 Webhook
- 📊 **結果一覽表** — 刊登日期、職位、公司、城市、經歷、學歷、薪水
- 📥 **匯出 CSV** — 一鍵下載搜尋結果（UTF-8 BOM，Excel 直接開啟）
- 🌙 **深色 / 淺色模式** — 右上角一鍵切換，自動記住偏好

## 🚀 快速開始

### 1. 環境需求

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) 套件管理工具

### 2. 啟動後端

```bash
cd backend
uv sync --group dev                               # 安裝依賴（含開發工具）
uv run uvicorn app.main:app --reload --port 8000  # 啟動 API server（含排程）
```

### 3. 啟動前端

```bash
cd frontend
python -m http.server 3000   # 或用 npx serve -l 3000
```

### 4. 開始使用

打開瀏覽器前往 👉 **http://localhost:3000**

| 頁面 | 說明 |
|------|------|
| `index.html` | 主搜尋頁，含收藏列表 |
| `dashboard.html` | Kanban 投遞看板 |
| `alerts.html` | 定時通知設定 |

## 🏗️ 技術架構

| 層級 | 技術 |
|------|------|
| 後端 API | FastAPI + Uvicorn |
| 排程 | asyncio 背景 task（內建，零額外依賴） |
| 爬蟲 | aiohttp（非同步） + 104 內部 JSON API |
| 前端 | Vanilla HTML / CSS / JavaScript（多頁 SPA） |
| 套件管理 | uv |
| 資料儲存 | localStorage（前端）、alerts.json（後端提醒設定） |
| 測試 | pytest + httpx（79 個測試，含 API 整合測試） |
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
  "experience": ["3"]
}
```

### 取得篩選選項

```
GET /api/jobs/options
```

### 職缺提醒

```
GET    /api/alerts              # 列出所有提醒
POST   /api/alerts              # 建立提醒
DELETE /api/alerts/{id}         # 刪除提醒
POST   /api/alerts/{id}/trigger # 立即觸發（測試用）
```

建立提醒範例：

```json
{
  "keyword": "Python",
  "pages": 3,
  "areas": ["6001001000"],
  "experience": [],
  "min_salary": 50000,
  "notify_type": "line",
  "notify_target": "YOUR_LINE_NOTIFY_TOKEN",
  "interval_minutes": 60
}
```

> 💡 Line Notify Token 請至 https://notify-bot.line.me/my/ 申請

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
