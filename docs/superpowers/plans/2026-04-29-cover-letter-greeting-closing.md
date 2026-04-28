# Cover Letter Greeting & Closing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 AI 產生求職信時自動加上自然的開頭稱呼與結尾敬語/署名，不再需要使用者手動補。

**Architecture:** 前端新增「公司名稱」欄位（可手動填或點按鈕讓 AI 從 JD 萃取），姓名從個人偏好讀取；兩欄位送至後端，後端修改 prompt 讓 AI 一次產出含開頭結尾的完整信件。

**Tech Stack:** FastAPI + Pydantic (backend), React + TypeScript (frontend), OpenAI AsyncOpenAI client

---

## File Map

| 動作 | 路徑 | 說明 |
|------|------|------|
| Modify | `backend/app/models.py` | `CoverLetterRequest` 新增 `company_name`, `user_name`；新增 `ExtractCompanyRequest`, `ExtractCompanyResponse` |
| Modify | `backend/app/routers/cover_letter.py` | 修改 `_PROMPT`；新增 `/api/jobs/extract-company` 端點 |
| Create | `backend/tests/test_api_cover_letter.py` | 後端測試：新欄位、greeting/closing 輸出、extract-company 端點 |
| Modify | `frontend/src/types/index.ts` | `CoverLetterRequest` 新增 `company_name`, `user_name` |
| Modify | `frontend/src/hooks/usePreferences.ts` | `UserPreferences` 新增 `user_name` |
| Modify | `frontend/src/pages/SettingsPage.tsx` | 新增姓名輸入欄 |
| Modify | `frontend/src/api/client.ts` | 更新 `generateCoverLetter`；新增 `extractCompanyName` |
| Modify | `frontend/src/pages/CoverLetterPage.tsx` | 新增公司名稱欄 + 自動偵測按鈕；傳入 `user_name` |

---

### Task 1: Backend models — 新增欄位與 Extract 型別

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: 修改 `CoverLetterRequest`，新增兩個選填欄位**

找到 `class CoverLetterRequest`（約第 100 行），改為：

```python
class CoverLetterRequest(BaseModel):
    """AI 推薦信請求"""

    job_text: str = Field(min_length=10, description="職缺描述文字")
    user_cv: str = Field(default="", description="求職者履歷或背景描述")
    company_name: str = Field(default="", description="招募公司名稱（選填，用於開頭稱呼）")
    user_name: str = Field(default="", description="求職者姓名（選填，用於結尾署名）")
```

- [ ] **Step 2: 新增 ExtractCompanyRequest 與 ExtractCompanyResponse**

在 `CoverLetterResponse` 之後插入：

```python
class ExtractCompanyRequest(BaseModel):
    """公司名稱萃取請求"""

    job_text: str = Field(min_length=10, description="職缺描述文字")


class ExtractCompanyResponse(BaseModel):
    """公司名稱萃取結果"""

    company_name: str = Field(description="萃取到的公司名稱，無法判斷時為空字串")
```

- [ ] **Step 3: 確認 models.py 無語法錯誤**

```bash
cd backend && uv run python -c "from app.models import CoverLetterRequest, ExtractCompanyRequest, ExtractCompanyResponse; print('OK')"
```

預期輸出：`OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add company_name/user_name to CoverLetterRequest and ExtractCompany models"
```

---

### Task 2: Backend cover_letter.py — 修改 prompt 與新增 extract-company 端點

**Files:**
- Modify: `backend/app/routers/cover_letter.py`

- [ ] **Step 1: 替換 `_PROMPT` 常數**

將整個 `_PROMPT = """..."""` 區塊替換為：

```python
_PROMPT = """\
You are a career coach helping a job seeker write a cover letter in Traditional Chinese.

## Instructions
- Write 3–4 natural paragraphs for the body, approximately 250–350 characters total.
- Use first-person, conversational tone — as if the candidate is speaking directly to the hiring manager.
- Do NOT use clichés like "I am writing to express my interest" or overly formal phrases like "貴公司" or "敬啟者".
- Pick 2–3 concrete skills or achievements from the CV that directly match the job requirements.
{greeting_instruction}
{closing_instruction}
- All output must be in Traditional Chinese (繁體中文).

## Job Description
{job_text}

## Candidate Background
{user_cv}
"""

_EXTRACT_COMPANY_PROMPT = """\
Extract the company name from the following job description.
Return ONLY the company name as it appears in the text (Traditional Chinese or English).
If you cannot determine the company name, return an empty string.
Output only the company name, nothing else — no explanation, no punctuation.

Job Description:
{job_text}
"""
```

- [ ] **Step 2: 更新 `generate_cover_letter` 函數，注入 greeting/closing 指令**

將函數 body 的 prompt 組裝部分改為：

```python
@router.post("/api/jobs/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(request: CoverLetterRequest):
    """根據職缺描述與履歷，用 AI 產生自我推薦信並存入資料庫"""
    client = _make_client()
    cv_section = request.user_cv.strip() or "（未提供）"

    if request.company_name.strip():
        greeting_instruction = (
            f"- Start with a natural, warm greeting addressing the {request.company_name.strip()} "
            "recruiting team. The phrasing should feel genuine — adapt tone to the company culture, "
            "not formulaic. For example: '親愛的 ACME 招募夥伴：' or '嗨，XXX 團隊：'"
        )
    else:
        greeting_instruction = "- Do not include a salutation header."

    if request.user_name.strip():
        closing_instruction = (
            "- End with an appropriate closing phrase that matches the letter's tone "
            "(e.g. 「祝商祺」for startups, 「此致 敬禮」for formal companies, "
            "「期待有機會加入你們」for casual), then a blank line, then the sender's name: "
            f"{request.user_name.strip()}"
        )
    else:
        closing_instruction = "- Do not include a sign-off or signature."

    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT.format(
                        greeting_instruction=greeting_instruction,
                        closing_instruction=closing_instruction,
                        job_text=request.job_text.strip(),
                        user_cv=cv_section,
                    ),
                }
            ],
            temperature=0.7,
            max_completion_tokens=1200,
        )
        letter = (response.choices[0].message.content or "").strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e

    if not letter:
        raise HTTPException(status_code=502, detail="AI 未回傳內容，請稍後再試")

    record_id = await save_cover_letter(job_text=request.job_text.strip(), letter=letter)
    return CoverLetterResponse(id=record_id, letter=letter)
```

- [ ] **Step 3: 新增 `extract_company_name` 端點**（在 `generate_cover_letter` 下方加入）

```python
@router.post("/api/jobs/extract-company", response_model=ExtractCompanyResponse)
async def extract_company_name(request: ExtractCompanyRequest):
    """從職缺描述中用 AI 萃取公司名稱"""
    client = _make_client()
    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {
                    "role": "user",
                    "content": _EXTRACT_COMPANY_PROMPT.format(
                        job_text=request.job_text.strip()[:3000]
                    ),
                }
            ],
            temperature=0,
            max_completion_tokens=50,
        )
        company_name = (response.choices[0].message.content or "").strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e

    return ExtractCompanyResponse(company_name=company_name)
```

- [ ] **Step 4: 更新 import — 加入新 models**

確認 `cover_letter.py` 頂部的 import 包含新型別：

```python
from ..models import (
    CoverLetterRecord,
    CoverLetterRequest,
    CoverLetterResponse,
    ExtractCompanyRequest,
    ExtractCompanyResponse,
)
```

- [ ] **Step 5: 確認語法**

```bash
cd backend && uv run python -c "from app.routers.cover_letter import router; print('OK')"
```

預期輸出：`OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/cover_letter.py
git commit -m "feat: update cover letter prompt for greeting/closing and add extract-company endpoint"
```

---

### Task 3: Backend tests — cover letter 新功能測試

**Files:**
- Create: `backend/tests/test_api_cover_letter.py`

- [ ] **Step 1: 寫測試（含 extract-company 與新欄位）**

```python
"""Tests for cover letter endpoints — greeting/closing fields and extract-company."""

from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_ai(content: str) -> tuple:
    """回傳 (MockAI class, instance mock)，content 為 AI 回傳文字。"""
    inst = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = content
    inst.chat.completions.create = AsyncMock(return_value=mock_resp)
    return inst


class TestGenerateCoverLetterGreetingClosing:
    def test_returns_letter_with_company_and_name(self, client):
        inst = _make_mock_ai("親愛的 ACME 招募夥伴：\n\n正文內容...\n\n此致 敬禮\nPin Yuan Chen")
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
            patch("app.routers.cover_letter.save_cover_letter", new=AsyncMock(return_value=1)),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/cover-letter",
                json={
                    "job_text": "後端工程師，熟悉 Python，ACME 公司",
                    "user_cv": "3 年 Python 經驗",
                    "company_name": "ACME",
                    "user_name": "Pin Yuan Chen",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "letter" in data
        assert "id" in data

    def test_returns_letter_without_optional_fields(self, client):
        inst = _make_mock_ai("正文內容...")
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
            patch("app.routers.cover_letter.save_cover_letter", new=AsyncMock(return_value=2)),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/cover-letter",
                json={"job_text": "後端工程師，熟悉 Python", "user_cv": ""},
            )
        assert resp.status_code == 200

    def test_missing_openai_key_returns_503(self, client):
        with patch("app.routers.cover_letter.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            resp = client.post(
                "/api/jobs/cover-letter",
                json={"job_text": "後端工程師職缺描述", "user_cv": ""},
            )
        assert resp.status_code == 503


class TestExtractCompanyName:
    def test_returns_company_name(self, client):
        inst = _make_mock_ai("ACME 科技")
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/extract-company",
                json={"job_text": "ACME 科技招募後端工程師，需熟悉 Python"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "company_name" in data
        assert data["company_name"] == "ACME 科技"

    def test_returns_empty_string_when_not_found(self, client):
        inst = _make_mock_ai("")
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/extract-company",
                json={"job_text": "招募後端工程師，需熟悉 Python"},
            )
        assert resp.status_code == 200
        assert resp.json()["company_name"] == ""

    def test_missing_openai_key_returns_503(self, client):
        with patch("app.routers.cover_letter.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            resp = client.post(
                "/api/jobs/extract-company",
                json={"job_text": "後端工程師職缺描述"},
            )
        assert resp.status_code == 503

    def test_job_text_too_short_returns_422(self, client):
        resp = client.post("/api/jobs/extract-company", json={"job_text": "短"})
        assert resp.status_code == 422

    def test_openai_error_returns_502(self, client):
        inst = MagicMock()
        inst.chat.completions.create = AsyncMock(side_effect=Exception("rate limit"))
        with (
            patch("app.routers.cover_letter.settings") as mock_settings,
            patch("app.routers.cover_letter.AsyncOpenAI", return_value=inst),
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            resp = client.post(
                "/api/jobs/extract-company",
                json={"job_text": "ACME 科技招募後端工程師職缺"},
            )
        assert resp.status_code == 502
```

- [ ] **Step 2: 執行測試，確認通過**

```bash
cd backend && uv run pytest tests/test_api_cover_letter.py -v
```

預期：所有 8 個測試 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_api_cover_letter.py
git commit -m "test: add cover letter greeting/closing and extract-company tests"
```

---

### Task 4: Frontend types — CoverLetterRequest 新增欄位

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 更新 `CoverLetterRequest` interface**

找到 `interface CoverLetterRequest`，改為：

```typescript
export interface CoverLetterRequest {
  job_text: string
  user_cv: string
  company_name?: string
  user_name?: string
}
```

- [ ] **Step 2: 型別檢查**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

預期：無錯誤輸出

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add company_name and user_name to CoverLetterRequest type"
```

---

### Task 5: Frontend usePreferences — 新增 user_name

**Files:**
- Modify: `frontend/src/hooks/usePreferences.ts`

- [ ] **Step 1: 更新 `UserPreferences` interface 與預設值**

```typescript
export interface UserPreferences {
  target_salary: number
  preferred_tech: string
  career_goals: string
  avoided_industries: string
  user_name: string
}

const DEFAULT_PREFS: UserPreferences = {
  target_salary: 0,
  preferred_tech: '',
  career_goals: '',
  avoided_industries: '',
  user_name: '',
}
```

（`usePreferences` 函數與 `formatPrefsForPrompt` 不需改動）

- [ ] **Step 2: 型別檢查**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

預期：無錯誤輸出

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/usePreferences.ts
git commit -m "feat: add user_name to UserPreferences"
```

---

### Task 6: Frontend SettingsPage — 新增姓名輸入欄

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: 在「避開產業」欄位後、`<p>自動儲存...</p>` 之前插入姓名欄位**

```tsx
<div className="form-group">
  <label className="form-label" htmlFor="user-name">
    姓名
    <span className="form-label__hint">用於推薦信結尾署名</span>
  </label>
  <input
    type="text"
    id="user-name"
    className="form-input"
    placeholder="例：Pin Yuan Chen"
    value={prefs.user_name}
    onChange={e => update('user_name', e.target.value)}
  />
</div>
```

- [ ] **Step 2: 型別檢查**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

預期：無錯誤輸出

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx
git commit -m "feat: add user_name input to SettingsPage"
```

---

### Task 7: Frontend client.ts — 更新 API 呼叫

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 新增 `extractCompanyName` 函數**

在 `generateCoverLetter` 函數下方加入：

```typescript
export function extractCompanyName(job_text: string): Promise<{ company_name: string }> {
  return apiFetch<{ company_name: string }>('/api/jobs/extract-company', {
    method: 'POST',
    body: JSON.stringify({ job_text }),
  })
}
```

（`generateCoverLetter` 本身不需改動，它已接受 `CoverLetterRequest` 物件，新欄位會自動序列化）

- [ ] **Step 2: 型別檢查**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

預期：無錯誤輸出

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add extractCompanyName API client function"
```

---

### Task 8: Frontend CoverLetterPage — 公司名稱欄位與自動偵測

**Files:**
- Modify: `frontend/src/pages/CoverLetterPage.tsx`

- [ ] **Step 1: 更新 import，引入新函數與 hook**

```typescript
import { useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { extractCompanyName, fetchJobUrl, generateCoverLetter, parseCvPdf } from '../api/client'
import { usePreferences } from '../hooks/usePreferences'
```

- [ ] **Step 2: 在元件頂部新增 state 與讀取 user_name**

在現有 state 宣告後加入：

```typescript
const [prefs] = usePreferences()
const [companyName, setCompanyName] = useState('')
const [extractLoading, setExtractLoading] = useState(false)
const [extractError, setExtractError] = useState<string | null>(null)
```

- [ ] **Step 3: 新增 `handleExtractCompany` 函數**

在 `handleCvUpload` 函數後加入：

```typescript
async function handleExtractCompany() {
  if (jobText.trim().length < 10) return
  setExtractLoading(true)
  setExtractError(null)
  try {
    const data = await extractCompanyName(jobText.trim())
    if (data.company_name) setCompanyName(data.company_name)
    else setExtractError('無法從職缺描述中判斷公司名稱，請手動填寫')
  } catch (err) {
    setExtractError(err instanceof Error ? err.message : '偵測失敗')
  } finally {
    setExtractLoading(false)
  }
}
```

- [ ] **Step 4: 更新 `handleGenerate`，帶入新欄位**

```typescript
const data = await generateCoverLetter({
  job_text: jobText,
  user_cv: cv,
  company_name: companyName.trim(),
  user_name: prefs.user_name.trim(),
})
```

- [ ] **Step 5: 在「職缺描述」欄位之前插入「公司名稱」欄位**

在 `{/* Job text */}` section 之前加入：

```tsx
{/* Company name */}
<div className="form-group">
  <label className="form-label" htmlFor="company-name">
    公司名稱（選填）
    <span className="form-label__hint">用於開頭稱呼，可自動從職缺描述偵測</span>
  </label>
  <div style={{ display: 'flex', gap: '0.5rem' }}>
    <input
      type="text"
      id="company-name"
      className="form-input"
      placeholder="例：SWAG、台積電"
      value={companyName}
      onChange={e => setCompanyName(e.target.value)}
      style={{ flex: 1 }}
    />
    <button
      type="button"
      className="btn-search"
      style={{ width: 'auto', padding: '0 1.2rem' }}
      disabled={extractLoading || jobText.trim().length < 10}
      onClick={handleExtractCompany}
    >
      {extractLoading ? '偵測中...' : '自動偵測'}
    </button>
  </div>
  {extractError && (
    <p style={{ color: 'var(--color-error, #f87171)', fontSize: '0.85rem', marginTop: '0.4rem' }}>
      {extractError}
    </p>
  )}
</div>
```

- [ ] **Step 6: 型別檢查**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

預期：無錯誤輸出

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/CoverLetterPage.tsx
git commit -m "feat: add company name field with AI auto-detect to CoverLetterPage"
```

---

### Task 9: 整合驗證

- [ ] **Step 1: 啟動後端**

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: 啟動前端**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: 手動測試流程**

1. 前往 `http://localhost:5173/settings`，在「姓名」欄填入你的名字，確認自動儲存
2. 前往「AI 推薦信」頁面
3. 貼上一份含公司名稱的職缺描述（例如「SWAG 公司招募後端工程師...」）
4. 點「自動偵測」— 確認公司名稱欄位被填入
5. 也測試手動覆寫公司名稱
6. 點「產生推薦信」
7. 確認產出信件開頭包含公司名稱稱呼、結尾包含敬語與你的姓名
8. 前往歷史記錄，確認完整信件（含開頭結尾）被儲存

- [ ] **Step 4: 執行所有後端測試確認無回歸**

```bash
cd backend && uv run pytest -v
```

預期：全部 PASS
