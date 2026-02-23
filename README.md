# 104 職缺搜尋

利用爬蟲在 104 人力銀行上搜尋職缺，前後端分離架構。

## 架構

- **後端**：FastAPI + aiohttp + BeautifulSoup（非同步爬蟲）
- **前端**：Vanilla HTML/CSS/JS SPA
- **套件管理**：uv

## 啟動方式

### 後端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 前端

直接用瀏覽器開啟，或用任意 HTTP server 提供服務：

```bash
cd frontend

# 方法 1: Python
python -m http.server 3000

# 方法 2: npx
npx serve -l 3000
```

然後瀏覽 http://localhost:3000

## API 端點

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API 資訊 |
| `GET` | `/api/jobs/options` | 取得地區 & 經歷篩選選項 |
| `POST` | `/api/jobs/search` | 搜尋職缺 |
| `GET` | `/docs` | Swagger API 文件 |

### 搜尋請求範例

```json
POST /api/jobs/search
{
  "keyword": "Django",
  "pages": 5,
  "areas": ["6001001000"],
  "experience": ["3"]
}
```
