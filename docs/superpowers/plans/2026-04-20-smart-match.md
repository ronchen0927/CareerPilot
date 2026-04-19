# Smart Match Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "智慧推薦" page where users upload their CV (PDF), AI suggests job search keywords, user confirms, the app searches multiple job boards, and auto-evaluates the top 10 results.

**Architecture:** New `POST /api/cv/suggest-keywords` backend endpoint calls OpenAI to extract keywords from CV text. Frontend three-phase page (input → keywords → results) reuses existing `parseCvPdf`, `searchJobs`, `evaluateJob`, `JobModal`, and `CheckboxGroup` infrastructure. Top-10 jobs are batch-evaluated client-side with `Promise.allSettled`; remaining jobs evaluate on-click via JobModal.

**Tech Stack:** FastAPI, OpenAI `gpt-5.4-mini`, pydantic-settings, React 18, TypeScript, existing `client.ts` fetch helpers.

---

## File Map

| Action | Path |
|--------|------|
| Modify | `backend/app/models.py` |
| Modify | `backend/app/routers/cv.py` |
| Create | `backend/tests/test_api_cv.py` |
| Modify | `frontend/src/types/index.ts` |
| Modify | `frontend/src/api/client.ts` |
| Create | `frontend/src/pages/SmartMatchPage.tsx` |
| Modify | `frontend/src/App.tsx` |
| Modify | `frontend/src/components/Layout.tsx` |

---

### Task 1: Add Pydantic models for suggest-keywords

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add two new models at the end of `backend/app/models.py`**

```python
class CVSuggestKeywordsRequest(BaseModel):
    """AI 關鍵字建議請求"""

    cv_text: str = Field(min_length=10, description="履歷純文字")


class CVSuggestKeywordsResponse(BaseModel):
    """AI 關鍵字建議結果"""

    keywords: list[str] = Field(description="3-5 組建議職位關鍵字")
```

- [ ] **Step 2: Verify models import cleanly**

```bash
cd backend && uv run python -c "from app.models import CVSuggestKeywordsRequest, CVSuggestKeywordsResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add CVSuggestKeywordsRequest/Response models"
```

---

### Task 2: Write failing tests for suggest-keywords

**Files:**
- Create: `backend/tests/test_api_cv.py`

- [ ] **Step 1: Create the test file**

```python
"""Tests for POST /api/cv/suggest-keywords."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSuggestKeywords:
    def test_returns_keywords_list(self, client):
        with (
            patch("app.routers.cv.settings") as mock_settings,
            patch("app.routers.cv.AsyncOpenAI") as MockAI,
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            inst = MagicMock()
            MockAI.return_value = inst
            mock_resp = MagicMock()
            mock_resp.choices[0].message.content = '{"keywords": ["後端工程師", "Python 工程師", "Django 開發"]}'
            inst.chat.completions.create = AsyncMock(return_value=mock_resp)

            resp = client.post(
                "/api/cv/suggest-keywords",
                json={"cv_text": "熟悉 Python、Django、PostgreSQL，有 3 年後端開發經驗"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "keywords" in data
        assert isinstance(data["keywords"], list)
        assert len(data["keywords"]) >= 1

    def test_missing_openai_key_returns_503(self, client):
        with patch("app.routers.cv.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            resp = client.post(
                "/api/cv/suggest-keywords",
                json={"cv_text": "熟悉 Python、Django，有 3 年後端開發經驗"},
            )
        assert resp.status_code == 503

    def test_cv_text_too_short_returns_422(self, client):
        resp = client.post(
            "/api/cv/suggest-keywords",
            json={"cv_text": "短"},
        )
        assert resp.status_code == 422

    def test_missing_cv_text_returns_422(self, client):
        resp = client.post("/api/cv/suggest-keywords", json={})
        assert resp.status_code == 422

    def test_openai_error_returns_502(self, client):
        with (
            patch("app.routers.cv.settings") as mock_settings,
            patch("app.routers.cv.AsyncOpenAI") as MockAI,
        ):
            mock_settings.OPENAI_API_KEY = "sk-test"
            inst = MagicMock()
            MockAI.return_value = inst
            inst.chat.completions.create = AsyncMock(side_effect=Exception("rate limit"))

            resp = client.post(
                "/api/cv/suggest-keywords",
                json={"cv_text": "熟悉 Python、Django，有 3 年後端開發經驗"},
            )
        assert resp.status_code == 502
```

- [ ] **Step 2: Run tests to confirm they all FAIL (endpoint doesn't exist yet)**

```bash
cd backend && uv run pytest tests/test_api_cv.py -v
```

Expected: All 5 tests FAIL — `404` or import errors.

---

### Task 3: Implement the suggest-keywords endpoint

**Files:**
- Modify: `backend/app/routers/cv.py`

- [ ] **Step 1: Replace the full content of `backend/app/routers/cv.py`**

```python
import io
import json

import pdfplumber
from fastapi import APIRouter, HTTPException, UploadFile
from openai import AsyncOpenAI

from ..config import settings
from ..models import CVSuggestKeywordsRequest, CVSuggestKeywordsResponse

router = APIRouter(prefix="/api/cv", tags=["cv"])

MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/parse")
async def parse_cv(file: UploadFile):
    """從上傳的 PDF 履歷中抽取純文字"""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="請上傳 PDF 格式的履歷")

    raw = await file.read()
    if len(raw) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="檔案大小超過 5 MB 限制")

    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages_text).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF 解析失敗：{e}") from e

    if not text:
        raise HTTPException(status_code=422, detail="無法從此 PDF 擷取文字，請確認非掃描圖片格式")

    return {"text": text}


@router.post("/suggest-keywords", response_model=CVSuggestKeywordsResponse)
async def suggest_keywords(request: CVSuggestKeywordsRequest):
    """根據履歷內容，用 AI 建議 3-5 組求職關鍵字"""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="尚未設定 OPENAI_API_KEY，請在 backend/.env 加入 OPENAI_API_KEY=sk-...",
        )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = f"""You are a career advisor. Based on the resume below, suggest 3 to 5 Traditional Chinese job search keywords (職位名稱) that best match the candidate's skills and experience.

## Resume
{request.cv_text.strip()}

## Response format (JSON only, no extra text)
{{
  "keywords": ["關鍵字1", "關鍵字2", "關鍵字3"]
}}

Rules:
- Each keyword is a job title in Traditional Chinese (繁體中文), e.g. "後端工程師", "Python 工程師", "資料工程師"
- Return 3 to 5 keywords
- JSON only, no explanations
"""
    try:
        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_completion_tokens=200,
        )
        data = json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API 錯誤：{e}") from e

    keywords = data.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []

    return CVSuggestKeywordsResponse(keywords=keywords)
```

- [ ] **Step 2: Run tests — all should pass**

```bash
cd backend && uv run pytest tests/test_api_cv.py -v
```

Expected:
```
PASSED tests/test_api_cv.py::TestSuggestKeywords::test_returns_keywords_list
PASSED tests/test_api_cv.py::TestSuggestKeywords::test_missing_openai_key_returns_503
PASSED tests/test_api_cv.py::TestSuggestKeywords::test_cv_text_too_short_returns_422
PASSED tests/test_api_cv.py::TestSuggestKeywords::test_missing_cv_text_returns_422
PASSED tests/test_api_cv.py::TestSuggestKeywords::test_openai_error_returns_502
5 passed
```

- [ ] **Step 3: Run full test suite to catch regressions**

```bash
cd backend && uv run pytest -v
```

Expected: All existing tests still pass.

- [ ] **Step 4: Lint and format**

```bash
cd backend && uv run ruff check . && uv run ruff format .
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/cv.py backend/tests/test_api_cv.py
git commit -m "feat: add POST /api/cv/suggest-keywords endpoint"
```

---

### Task 4: Frontend types and API client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add `CVSuggestKeywordsResponse` interface to `frontend/src/types/index.ts`**

Append at the end of the file:

```typescript
export interface CVSuggestKeywordsResponse {
  keywords: string[]
}
```

- [ ] **Step 2: Add `suggestKeywords` function to `frontend/src/api/client.ts`**

Add the import at the top of the imports block (add `CVSuggestKeywordsResponse` to the existing import from `'../types'`):

```typescript
import type {
  Alert,
  AlertCreateRequest,
  AlertsListResponse,
  CVSuggestKeywordsResponse,
  ChatMessage,
  ChatRequest,
  CoverLetterRecord,
  CoverLetterRequest,
  CoverLetterResponse,
  EvaluationRecord,
  JobEvaluateRequest,
  JobEvaluateResponse,
  JobEvaluateTextRequest,
  JobListing,
  JobOptions,
  JobSearchRequest,
  JobSearchResponse,
  LivenessMap,
  ResumeRewriteRecord,
  ResumeRewriteRequest,
  ResumeRewriteResponse,
  TriggerAlertResponse,
} from '../types'
```

Then append the new function at the end of the file (before the closing):

```typescript
export function suggestKeywords(cvText: string): Promise<CVSuggestKeywordsResponse> {
  return apiFetch<CVSuggestKeywordsResponse>('/api/cv/suggest-keywords', {
    method: 'POST',
    body: JSON.stringify({ cv_text: cvText }),
  })
}
```

- [ ] **Step 3: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add suggestKeywords API client function and type"
```

---

### Task 5: Create SmartMatchPage

**Files:**
- Create: `frontend/src/pages/SmartMatchPage.tsx`

- [ ] **Step 1: Create the full page**

```tsx
import { useEffect, useRef, useState } from 'react'
import { evaluateJob, fetchOptions, parseCvPdf, searchJobs, suggestKeywords } from '../api/client'
import CheckboxGroup from '../components/CheckboxGroup'
import JobModal from '../components/JobModal'
import type { JobEvaluateResponse, JobListing, JobOptions } from '../types'

const FALLBACK_OPTIONS: JobOptions = {
  areas: [
    { value: '6001001000', label: '台北市' },
    { value: '6001002000', label: '新北市' },
    { value: '6001006000', label: '新竹市' },
    { value: '6001008000', label: '台中市' },
    { value: '6001014000', label: '台南市' },
    { value: '6001016000', label: '高雄市' },
  ],
  experience: [
    { value: '1', label: '1年以下' },
    { value: '3', label: '1-3年' },
    { value: '5', label: '3-5年' },
    { value: '10', label: '5-10年' },
    { value: '99', label: '10年以上' },
  ],
}

type Phase = 'input' | 'keywords' | 'results'

const AUTO_EVAL_LIMIT = 10

export default function SmartMatchPage() {
  const [phase, setPhase] = useState<Phase>('input')
  const [cvText, setCvText] = useState<string>(() => localStorage.getItem('careerpilot_cv') ?? '')
  const [keywords, setKeywords] = useState<string[]>([])
  const [newKeyword, setNewKeyword] = useState('')
  const [sources, setSources] = useState<string[]>(['104'])
  const [areas, setAreas] = useState<string[]>([])
  const [options, setOptions] = useState<JobOptions>(FALLBACK_OPTIONS)
  const [jobs, setJobs] = useState<JobListing[]>([])
  const [evaluations, setEvaluations] = useState<Map<string, JobEvaluateResponse>>(new Map())
  const [evalErrors, setEvalErrors] = useState<Set<string>>(new Set())
  const [selectedJob, setSelectedJob] = useState<JobListing | null>(null)
  const [loadingKeywords, setLoadingKeywords] = useState(false)
  const [loadingSearch, setLoadingSearch] = useState(false)
  const [loadingEval, setLoadingEval] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchOptions().then(setOptions).catch(() => {})
  }, [])

  async function handleFileUpload(file: File) {
    setError(null)
    try {
      const { text } = await parseCvPdf(file)
      setCvText(text)
      localStorage.setItem('careerpilot_cv', text)
      await handleProceedToKeywords(text)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'PDF 解析失敗')
    }
  }

  async function handleProceedToKeywords(text: string) {
    setLoadingKeywords(true)
    setError(null)
    let suggested: string[] = []
    try {
      const res = await suggestKeywords(text)
      suggested = res.keywords
    } catch {
      // fall through with empty keywords — user can add manually
    }
    setKeywords(suggested)
    setPhase('keywords')
    setLoadingKeywords(false)
  }

  function handleAddKeyword() {
    const kw = newKeyword.trim()
    if (kw && !keywords.includes(kw)) {
      setKeywords(prev => [...prev, kw])
    }
    setNewKeyword('')
  }

  function handleRemoveKeyword(kw: string) {
    setKeywords(prev => prev.filter(k => k !== kw))
  }

  async function handleSearch() {
    if (keywords.length === 0) { setError('請至少填入一個搜尋關鍵字'); return }
    if (sources.length === 0) { setError('請至少選擇一個搜尋來源'); return }
    setLoadingSearch(true)
    setError(null)
    try {
      // Search with first keyword (multi-keyword is out of scope for v1)
      const res = await searchJobs({ keyword: keywords[0], pages: 5, areas, experience: [], sources })
      const allJobs = res.results
      setJobs(allJobs)
      setPhase('results')

      // Batch evaluate top N
      const topJobs = allJobs.slice(0, AUTO_EVAL_LIMIT)
      setLoadingEval(true)
      const results = await Promise.allSettled(
        topJobs.map(job => evaluateJob({ job, user_cv: cvText }))
      )
      const newEvals = new Map<string, JobEvaluateResponse>()
      const newErrors = new Set<string>()
      results.forEach((result, i) => {
        if (result.status === 'fulfilled') {
          newEvals.set(topJobs[i].link, result.value)
        } else {
          newErrors.add(topJobs[i].link)
        }
      })
      setEvaluations(newEvals)
      setEvalErrors(newErrors)
    } catch (e) {
      setError(e instanceof Error ? e.message : '搜尋失敗')
    } finally {
      setLoadingSearch(false)
      setLoadingEval(false)
    }
  }

  const sortedJobs = [...jobs].sort((a, b) => {
    const aScore = evaluations.get(a.link)?.dimensions?.overall_score ?? -1
    const bScore = evaluations.get(b.link)?.dimensions?.overall_score ?? -1
    return bScore - aScore
  })

  return (
    <div className="container">
      <header className="header">
        <div className="header__logo">
          <span className="header__icon">🎯</span>
          <h1 className="header__title">智慧推薦</h1>
        </div>
        <p className="header__subtitle">上傳履歷，AI 幫你找最符合技能樹的職缺</p>
      </header>

      {/* Phase 1: CV input */}
      {phase === 'input' && (
        <section className="search-card">
          {cvText ? (
            <div>
              <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                已載入履歷（{cvText.length} 字）
              </p>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button
                  className="btn-search"
                  style={{ flex: 1 }}
                  disabled={loadingKeywords}
                  onClick={() => handleProceedToKeywords(cvText)}
                >
                  <span className="btn-search__text">
                    {loadingKeywords ? 'AI 分析中...' : '使用已存履歷 →'}
                  </span>
                </button>
                <button
                  className="btn-search"
                  style={{ flex: 1, background: 'var(--bg-secondary)' }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <span className="btn-search__text">重新上傳 PDF</span>
                </button>
              </div>
            </div>
          ) : (
            <div>
              <p style={{ marginBottom: '1rem' }}>請上傳你的履歷 PDF，AI 會自動分析並推薦職缺。</p>
              <button className="btn-search" onClick={() => fileInputRef.current?.click()}>
                <span className="btn-search__text">上傳 PDF 履歷</span>
                <span className="btn-search__icon">↑</span>
              </button>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            style={{ display: 'none' }}
            onChange={async e => {
              const file = e.target.files?.[0]
              if (!file) return
              e.target.value = ''
              await handleFileUpload(file)
            }}
          />
          {error && (
            <p style={{ color: 'var(--color-error)', marginTop: '0.75rem', fontSize: '0.9rem' }}>
              {error}
            </p>
          )}
        </section>
      )}

      {/* Phase 2: Confirm keywords */}
      {phase === 'keywords' && (
        <section className="search-card">
          <h2 style={{ marginBottom: '1rem', fontSize: '1rem' }}>AI 建議的搜尋關鍵字</h2>
          {keywords.length === 0 && (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.75rem' }}>
              AI 未能產生建議，請手動輸入關鍵字。
            </p>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
            {keywords.map(kw => (
              <span key={kw} style={{
                display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                padding: '0.25rem 0.6rem', borderRadius: '999px',
                background: 'var(--color-primary)', color: '#fff', fontSize: '0.85rem',
              }}>
                {kw}
                <button
                  onClick={() => handleRemoveKeyword(kw)}
                  style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '1rem', lineHeight: 1, padding: 0 }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
            <input
              className="form-input"
              placeholder="新增關鍵字"
              value={newKeyword}
              onChange={e => setNewKeyword(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleAddKeyword() } }}
              style={{ flex: 1 }}
            />
            <button className="btn-search" style={{ flexShrink: 0 }} onClick={handleAddKeyword}>
              <span className="btn-search__text">新增</span>
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">選擇地區</label>
            <CheckboxGroup options={options.areas} selected={areas} prefix="sm-area" onChange={setAreas} />
          </div>

          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label className="form-label">搜尋來源</label>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              {[
                { value: '104', label: '104 人力銀行' },
                { value: 'cake', label: 'CakeResume' },
                { value: 'yourator', label: 'Yourator' },
                { value: 'meetjob', label: 'MeetJob' },
              ].map(opt => (
                <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.9rem' }}>
                  <input
                    type="checkbox"
                    checked={sources.includes(opt.value)}
                    onChange={e => {
                      if (e.target.checked) setSources(prev => [...prev, opt.value])
                      else setSources(prev => prev.filter(s => s !== opt.value))
                    }}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          {error && (
            <p style={{ color: 'var(--color-error)', margin: '0.75rem 0', fontSize: '0.9rem' }}>{error}</p>
          )}

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
            <button className="btn-search" style={{ background: 'var(--bg-secondary)', flex: 1 }} onClick={() => setPhase('input')}>
              <span className="btn-search__text">← 返回</span>
            </button>
            <button className="btn-search" style={{ flex: 2 }} disabled={loadingSearch} onClick={handleSearch}>
              <span className="btn-search__text">{loadingSearch ? '搜尋中...' : '開始搜尋'}</span>
              <span className="btn-search__icon">→</span>
            </button>
          </div>
        </section>
      )}

      {/* Phase 3: Results */}
      {phase === 'results' && (
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              找到 {jobs.length} 筆職缺，前 {Math.min(AUTO_EVAL_LIMIT, jobs.length)} 筆自動評分中{loadingEval ? '...' : '完成'}
            </p>
            <button
              className="btn-search"
              style={{ padding: '0.4rem 0.9rem', fontSize: '0.85rem' }}
              onClick={() => { setPhase('keywords'); setJobs([]); setEvaluations(new Map()); setEvalErrors(new Set()) }}
            >
              ← 修改搜尋
            </button>
          </div>

          {jobs.length === 0 && (
            <div className="search-card" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
              <p>找不到符合的職缺，試試修改關鍵字或搜尋來源。</p>
            </div>
          )}

          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {sortedJobs.map(job => {
              const eval_ = evaluations.get(job.link)
              const hasError = evalErrors.has(job.link)
              const isAutoEvalJob = jobs.indexOf(job) < AUTO_EVAL_LIMIT
              return (
                <li
                  key={job.link}
                  className="result-card"
                  onClick={() => setSelectedJob(job)}
                  style={{ cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <div style={{ minWidth: 0 }}>
                      <p style={{ fontWeight: 600, margin: 0 }}>{job.job}</p>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0.2rem 0 0' }}>
                        {job.company} · {job.city} · {job.salary}
                      </p>
                    </div>
                    <div style={{ flexShrink: 0, textAlign: 'right' }}>
                      {eval_ && (
                        <span style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--color-primary)' }}>
                          {eval_.score}
                        </span>
                      )}
                      {hasError && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--color-error)' }}>評分失敗</span>
                      )}
                      {isAutoEvalJob && !eval_ && !hasError && loadingEval && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>評分中…</span>
                      )}
                    </div>
                  </div>
                  {eval_?.summary && (
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.4rem 0 0' }}>
                      {eval_.summary}
                    </p>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {selectedJob && (
        <JobModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors. If `initialEvaluation` prop doesn't exist on `JobModal`, fix the prop name to match what `JobModal` actually accepts.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SmartMatchPage.tsx
git commit -m "feat: add SmartMatchPage with 3-phase CV-to-jobs flow"
```

---

### Task 6: Wire up routing and nav

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Add route in `frontend/src/App.tsx`**

Add import after the existing page imports:

```typescript
import SmartMatchPage from './pages/SmartMatchPage'
```

Add route inside the `<Route element={<Layout />}>` block, before the catch-all:

```tsx
<Route path="smart-match" element={<SmartMatchPage />} />
```

- [ ] **Step 2: Add nav link in `frontend/src/components/Layout.tsx`**

Inside the `求職` sidebar group (after the `職缺提醒` NavLink):

```tsx
<NavLink to="/smart-match" className="sidebar__link" onClick={closeSidebar}>
  智慧推薦
</NavLink>
```

- [ ] **Step 3: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: register /smart-match route and add sidebar nav link"
```

---

### Task 7: Manual smoke test

- [ ] **Step 1: Start backend**

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Start frontend**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Open http://localhost:5173/smart-match and verify:**
  1. Page loads and shows CV upload area (or "使用已存履歷" if localStorage has CV)
  2. Upload a PDF → parses and shows "已載入履歷 (N 字)"
  3. Click "使用已存履歷" → AI suggests keywords (spinner shows "AI 分析中...")
  4. Keywords appear as deletable tags; can add new ones
  5. Click "開始搜尋" → results appear
  6. Top 10 show score badges as evaluation completes
  7. Clicking a job opens JobModal
  8. "修改搜尋" returns to keyword phase

- [ ] **Step 4: Final commit if any UI tweaks were needed**

```bash
git add -p  # stage only intentional changes
git commit -m "fix: smart-match UI tweaks from smoke test"
```
