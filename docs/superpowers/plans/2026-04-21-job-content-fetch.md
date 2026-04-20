# Job Content Auto-Fetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-fetch job page content when JobModal opens, then inject the full JD into AI evaluation and Q&A prompts.

**Architecture:** Backend replaces BeautifulSoup parser with trafilatura → Goose3 chain; evaluate and chat endpoints accept an optional `job_description` field; JobModal fetches the URL in background on mount and passes the result down to both evaluate and JobChat.

**Tech Stack:** Python — `trafilatura`, `goose3` (new); TypeScript/React — existing fetch helpers, useState/useEffect

**Branch:** `git checkout -b feat/job-content-fetch` before starting. Open PR against `main` when all tasks complete.

---

## File Map

| File | Action |
|------|--------|
| `backend/pyproject.toml` | Add `trafilatura`, `goose3` dependencies |
| `backend/app/fetchers.py` | Replace `parse_html` (BeautifulSoup) with trafilatura → Goose3 |
| `backend/tests/test_fetchers.py` | New — unit tests for `parse_html` |
| `backend/app/models.py` | Add `job_description` field to `JobEvaluateRequest` |
| `backend/app/routers/evaluate.py` | Use `job_description` in hash + prompt |
| `backend/tests/test_api_evaluate.py` | New — tests for job_description in evaluate endpoint |
| `backend/app/routers/chat.py` | Add `job_description` to `ChatRequest` + system prompt |
| `backend/tests/test_api_chat.py` | Add test for job_description in system prompt |
| `frontend/src/types/index.ts` | Add `job_description?` to `JobEvaluateRequest` + `ChatRequest` |
| `frontend/src/api/client.ts` | Add `jobDescription` param to `chatStream` |
| `frontend/src/components/JobModal.tsx` | Auto-fetch on mount; pass `job_description` to evaluate; pass `jobContent` to JobChat |
| `frontend/src/components/JobChat.tsx` | Accept `jobContent` prop; pass to `chatStream` |

---

### Task 1: Add trafilatura and goose3 dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add dependencies**

In `backend/pyproject.toml`, add to the `dependencies` list (keep alphabetical order):

```toml
dependencies = [
    "aiohttp>=3.13.3",
    "aiosqlite>=0.21",
    "beautifulsoup4>=4.14.3",
    "fastapi>=0.131.0",
    "goose3>=3.1.18",
    "lxml>=6.0.2",
    "openai>=1.0.0",
    "pdfplumber>=0.11.9",
    "playwright>=1.58.0",
    "pydantic-settings>=2.13.1",
    "python-dotenv>=1.2.1",
    "python-multipart>=0.0.26",
    "trafilatura>=2.0.0",
    "uvicorn[standard]>=0.41.0",
]
```

- [ ] **Step 2: Install**

```bash
cd backend
uv sync --group dev
```

Expected: resolves and installs both packages without errors.

- [ ] **Step 3: Smoke-check imports**

```bash
uv run python -c "import trafilatura; from goose3 import Goose; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "deps: add trafilatura and goose3 for job content extraction"
```

---

### Task 2: Replace parse_html in fetchers.py

**Files:**
- Modify: `backend/app/fetchers.py`
- Create: `backend/tests/test_fetchers.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_fetchers.py`:

```python
"""Unit tests for fetchers.parse_html."""

from unittest.mock import MagicMock, patch

from app.fetchers import parse_html


def test_parse_html_returns_trafilatura_result():
    with patch("app.fetchers.trafilatura.extract", return_value="  Extracted content  ") as mock_t:
        result = parse_html("<html><body><p>x</p></body></html>")
    assert result == "Extracted content"
    mock_t.assert_called_once()


def test_parse_html_falls_back_to_goose3_when_trafilatura_returns_none():
    mock_article = MagicMock()
    mock_article.cleaned_text = "Goose extracted"
    with (
        patch("app.fetchers.trafilatura.extract", return_value=None),
        patch("app.fetchers.Goose") as MockGoose,
    ):
        MockGoose.return_value.extract.return_value = mock_article
        result = parse_html("<html><body><p>x</p></body></html>")
    assert result == "Goose extracted"


def test_parse_html_returns_empty_string_when_both_fail():
    mock_article = MagicMock()
    mock_article.cleaned_text = ""
    with (
        patch("app.fetchers.trafilatura.extract", return_value=None),
        patch("app.fetchers.Goose") as MockGoose,
    ):
        MockGoose.return_value.extract.return_value = mock_article
        result = parse_html("<html></html>")
    assert result == ""


def test_parse_html_handles_goose3_exception_gracefully():
    with (
        patch("app.fetchers.trafilatura.extract", return_value=None),
        patch("app.fetchers.Goose") as MockGoose,
    ):
        MockGoose.return_value.extract.side_effect = Exception("parse error")
        result = parse_html("<html></html>")
    assert result == ""
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
uv run pytest tests/test_fetchers.py -v
```

Expected: `ImportError` or `AttributeError` — `trafilatura` / `Goose` not yet imported in `fetchers.py`.

- [ ] **Step 3: Rewrite fetchers.py**

Replace the entire `backend/app/fetchers.py` with:

```python
"""Shared HTTP fetch helpers used by the URL-fetch endpoint and the liveness checker."""

import logging

import aiohttp
import trafilatura
from goose3 import Goose
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

FETCH_TIMEOUT_S = 15
FETCH_TIMEOUT_MS = 15_000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def parse_html(html: str) -> str:
    """Extract main content from HTML using trafilatura → Goose3 fallback."""
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    if text and text.strip():
        return text.strip()
    try:
        g = Goose()
        article = g.extract(raw_html=html)
        text = article.cleaned_text
        if text and text.strip():
            return text.strip()
    except Exception:
        pass
    return ""


async def fetch_with_aiohttp(url: str) -> str | None:
    """Try to fetch the page with aiohttp + trafilatura/Goose3. Returns None on failure."""
    try:
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_S)
        async with aiohttp.ClientSession(headers=_HEADERS, timeout=timeout) as session:
            async with session.get(url, ssl=False) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        return parse_html(html) or None
    except Exception as e:
        logger.debug("aiohttp fetch failed for %s: %s", url, e)
        return None


async def fetch_with_playwright(url: str) -> str:
    """Fallback: launch headless Chromium and extract text content."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_extra_http_headers({"User-Agent": _HEADERS["User-Agent"]})
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=FETCH_TIMEOUT_MS)
            await page.wait_for_load_state("networkidle", timeout=FETCH_TIMEOUT_MS)
        except PlaywrightTimeout:
            pass
        html = await page.content()
        await browser.close()
    return parse_html(html)
```

- [ ] **Step 4: Run tests**

```bash
cd backend
uv run pytest tests/test_fetchers.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Run full suite to check for regressions**

```bash
cd backend
uv run pytest -v
```

Expected: all tests pass (existing tests that relied on `parse_html` still work since the function signature is unchanged).

- [ ] **Step 6: Lint and format**

```bash
cd backend
uv run ruff check .
uv run ruff format .
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/fetchers.py backend/tests/test_fetchers.py
git commit -m "feat: replace BeautifulSoup parser with trafilatura → Goose3 in fetchers.py"
```

---

### Task 3: Extend JobEvaluateRequest and /evaluate endpoint

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/routers/evaluate.py`
- Create: `backend/tests/test_api_evaluate.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_api_evaluate.py`:

```python
"""Tests for POST /api/jobs/evaluate with job_description field."""

from unittest.mock import AsyncMock, patch

from app.models import JobEvaluateResponse


def _job_payload(**kwargs) -> dict:
    base = {
        "job": "後端工程師",
        "date": "2026/01/01",
        "link": "https://www.104.com.tw/job/abc",
        "company": "測試公司",
        "city": "台北市",
        "experience": "1-3年",
        "education": "大學",
        "salary": "50,000 ~ 70,000 元",
        "salary_low": 50000,
        "salary_high": 70000,
        "is_featured": False,
        "source": "104",
    }
    base.update(kwargs)
    return base


_FAKE_RESULT = JobEvaluateResponse(
    score="A",
    summary="良好匹配",
    match_points=["技能符合"],
    gap_points=[],
    recommendation="建議投遞",
)


def test_job_description_included_in_prompt(client):
    captured = {}

    async def fake_call_openai(openai_client, prompt):
        captured["prompt"] = prompt
        return _FAKE_RESULT

    with (
        patch("app.routers.evaluate.settings") as mock_settings,
        patch("app.routers.evaluate._call_openai", fake_call_openai),
        patch("app.routers.evaluate.get_cached", AsyncMock(return_value=None)),
        patch("app.routers.evaluate.save_evaluation", AsyncMock()),
    ):
        mock_settings.OPENAI_API_KEY = "sk-test"
        resp = client.post(
            "/api/jobs/evaluate",
            json={
                "job": _job_payload(),
                "user_cv": "",
                "job_description": "需要熟悉 Python、FastAPI、PostgreSQL",
            },
        )
    assert resp.status_code == 200
    assert "FastAPI" in captured["prompt"]
    assert "PostgreSQL" in captured["prompt"]


def test_evaluate_without_job_description_omits_jd_section(client):
    captured = {}

    async def fake_call_openai(openai_client, prompt):
        captured["prompt"] = prompt
        return _FAKE_RESULT

    with (
        patch("app.routers.evaluate.settings") as mock_settings,
        patch("app.routers.evaluate._call_openai", fake_call_openai),
        patch("app.routers.evaluate.get_cached", AsyncMock(return_value=None)),
        patch("app.routers.evaluate.save_evaluation", AsyncMock()),
    ):
        mock_settings.OPENAI_API_KEY = "sk-test"
        resp = client.post(
            "/api/jobs/evaluate",
            json={"job": _job_payload(), "user_cv": ""},
        )
    assert resp.status_code == 200
    assert "Job Description" not in captured["prompt"]
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
uv run pytest tests/test_api_evaluate.py -v
```

Expected: FAIL — `job_description` not yet a field on `JobEvaluateRequest`.

- [ ] **Step 3: Add field to models.py**

In `backend/app/models.py`, update `JobEvaluateRequest`:

```python
class JobEvaluateRequest(BaseModel):
    """AI 評分請求"""

    job: JobListing = Field(description="要評分的職缺")
    user_cv: str = Field(default="", description="求職者履歷或背景描述（選填）")
    job_description: str = Field(default="", description="職缺內文全文（選填）")
```

- [ ] **Step 4: Update evaluate.py — hash and prompt**

In `backend/app/routers/evaluate.py`, update the `evaluate_job` function body:

```python
@router.post("/evaluate", response_model=JobEvaluateResponse)
async def evaluate_job(request: JobEvaluateRequest):
    """使用 GPT 評估職缺與求職者的匹配程度（結構化職缺資料）"""
    job = request.job
    job_repr = f"{job.job}|{job.company}|{job.city}|{job.experience}|{job.education}|{job.salary}"
    job_hash = _compute_hash(job_repr, request.user_cv.strip(), request.job_description.strip())

    cached = await get_cached(job_hash)
    if cached:
        return _row_to_response(cached)

    client = _make_openai_client()
    cv_section = f"\n\n## 求職者背景\n{request.user_cv.strip()}" if request.user_cv.strip() else ""
    jd_section = (
        f"\n\nJob Description (full text):\n{request.job_description.strip()}"
        if request.job_description.strip()
        else ""
    )

    prompt = f"""You are a professional career advisor. Evaluate the fit between the candidate and the job listing below, then respond in strict JSON format.

## Job Listing
- Title: {job.job}
- Company: {job.company}
- City: {job.city}
- Experience required: {job.experience}
- Education required: {job.education}
- Salary: {job.salary}{jd_section}{cv_section}

## Response format (JSON only, no extra text)
{{
  "score": "Letter grade with optional +/- (e.g. A, B+, C-)",
  "summary": "One-sentence verdict in Traditional Chinese, max 25 characters",
  "match_points": ["Up to 3 strengths in Traditional Chinese, max 20 chars each"],
  "gap_points": ["Up to 3 risks or gaps in Traditional Chinese, max 20 chars each — empty array if none"],
  "recommendation": "Application advice in Traditional Chinese, max 50 characters",
{_DIMENSIONS_SPEC}
}}

All text values must be written in Traditional Chinese (繁體中文).
"""
    result = await _call_openai(client, prompt)
    await save_evaluation(
        job_hash=job_hash,
        job_text=job_repr,
        job_url=job.link or None,
        score=result.score,
        summary=result.summary,
        match_points=result.match_points,
        gap_points=result.gap_points,
        recommendation=result.recommendation,
        dimensions=result.dimensions.model_dump() if result.dimensions else None,
    )
    return result
```

- [ ] **Step 5: Run tests**

```bash
cd backend
uv run pytest tests/test_api_evaluate.py -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Run full suite**

```bash
cd backend
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 7: Lint and format**

```bash
cd backend
uv run ruff check .
uv run ruff format .
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/models.py backend/app/routers/evaluate.py backend/tests/test_api_evaluate.py
git commit -m "feat: add job_description field to evaluate endpoint"
```

---

### Task 4: Extend /chat endpoint with job_description

**Files:**
- Modify: `backend/app/routers/chat.py`
- Modify: `backend/tests/test_api_chat.py`

- [ ] **Step 1: Write failing test**

In `backend/tests/test_api_chat.py`, add this test inside `class TestChat`:

```python
def test_job_description_included_in_system_prompt(self, client):
    captured = {}

    async def fake_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        return _make_fake_stream(["OK"])

    with (
        patch("app.routers.chat.settings") as mock_settings,
        patch("app.routers.chat.AsyncOpenAI") as MockAI,
    ):
        mock_settings.OPENAI_API_KEY = "sk-test"
        inst = MagicMock()
        MockAI.return_value = inst
        inst.chat.completions.create = AsyncMock(side_effect=fake_create)
        resp = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "job": _job_payload(),
                "user_cv": "",
                "job_description": "需要熟悉 Kubernetes 和 Terraform",
            },
        )
    assert resp.status_code == 200
    system_content = captured["messages"][0]["content"]
    assert "Kubernetes" in system_content
    assert "Terraform" in system_content
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
uv run pytest tests/test_api_chat.py::TestChat::test_job_description_included_in_system_prompt -v
```

Expected: FAIL — `job_description` not yet on `ChatRequest`.

- [ ] **Step 3: Update chat.py**

In `backend/app/routers/chat.py`, update `ChatRequest` and the `chat` function:

```python
class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    job: JobListing
    user_cv: str
    job_description: str = ""


@router.post("/api/chat")
async def chat(request: ChatRequest):
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="尚未設定 OPENAI_API_KEY，請在 backend/.env 加入 OPENAI_API_KEY=sk-...",
        )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    job = request.job
    system_content = _SYSTEM_PROMPT.format(
        job=job.job,
        company=job.company,
        city=job.city,
        salary=job.salary,
        experience=job.experience,
        education=job.education,
        link=job.link,
        user_cv=request.user_cv.strip() or "（未提供）",
    )
    if request.job_description.strip():
        system_content += f"\n\n[Job Description]\n{request.job_description.strip()}"

    async def generate():
        try:
            stream = await client.chat.completions.create(
                model="gpt-5.4-mini",
                messages=[
                    {"role": "system", "content": system_content},
                    *[{"role": m.role, "content": m.content} for m in request.messages],
                ],
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            from openai import OpenAIError

            if isinstance(e, OpenAIError):
                yield "\n\n⚠ 服務暫時無法使用，請稍後再試。"
            else:
                yield "\n\n⚠ 發生未預期的錯誤，請稍後再試。"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")
```

- [ ] **Step 4: Run tests**

```bash
cd backend
uv run pytest tests/test_api_chat.py -v
```

Expected: all chat tests pass, including the new one.

- [ ] **Step 5: Run full suite**

```bash
cd backend
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Lint and format**

```bash
cd backend
uv run ruff check .
uv run ruff format .
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/chat.py backend/tests/test_api_chat.py
git commit -m "feat: add job_description field to chat endpoint system prompt"
```

---

### Task 5: Update frontend types and client.ts

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Update JobEvaluateRequest and ChatRequest in types/index.ts**

In `frontend/src/types/index.ts`, update both interfaces:

```typescript
export interface JobEvaluateRequest {
  job: JobListing
  user_cv: string
  job_description?: string
}
```

```typescript
export interface ChatRequest {
  messages: ChatMessage[]
  job: JobListing
  user_cv: string
  job_description?: string
}
```

- [ ] **Step 2: Update chatStream signature in client.ts**

In `frontend/src/api/client.ts`, replace the `chatStream` function:

```typescript
export async function chatStream(
  messages: ChatMessage[],
  job: JobListing,
  userCv: string,
  jobDescription: string,
  onChunk: (chunk: string) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      job,
      user_cv: userCv,
      job_description: jobDescription,
    } satisfies ChatRequest),
  })
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`)
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    onChunk(decoder.decode(value, { stream: true }))
  }
}
```

- [ ] **Step 3: Type-check**

```bash
cd frontend
npx tsc --noEmit
```

Expected: errors on `JobChat.tsx` (callers of `chatStream` now missing the `jobDescription` argument). These will be fixed in Task 7.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add job_description to frontend types and chatStream signature"
```

---

### Task 6: Update JobModal.tsx

**Files:**
- Modify: `frontend/src/components/JobModal.tsx`

- [ ] **Step 1: Update JobModal.tsx**

Replace the entire `frontend/src/components/JobModal.tsx` with:

```tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { evaluateJob, fetchJobUrl } from '../api/client'
import DimensionsPanel from './DimensionsPanel'
import JobChat from './JobChat'
import { formatPrefsForPrompt, usePreferences } from '../hooks/usePreferences'
import type { JobEvaluateResponse, JobListing } from '../types'

interface Props {
  job: JobListing
  onClose: () => void
}

const SCORE_CLASS: Record<string, string> = {
  A: 'score--a',
  B: 'score--b',
  C: 'score--c',
  D: 'score--d',
  F: 'score--f',
}

function getScoreClass(score: string): string {
  return SCORE_CLASS[score[0]?.toUpperCase() ?? ''] ?? ''
}

export default function JobModal({ job, onClose }: Props) {
  const [evalResult, setEvalResult] = useState<JobEvaluateResponse | null>(null)
  const [evalLoading, setEvalLoading] = useState(false)
  const [evalError, setEvalError] = useState<string | null>(null)
  const [jobContent, setJobContent] = useState<string | null>(null)
  const navigate = useNavigate()
  const [prefs] = usePreferences()

  function handleRewriteResume() {
    const jobText = [
      `職位：${job.job}`,
      `公司：${job.company}`,
      `城市：${job.city}`,
      `經歷要求：${job.experience}`,
      `最低學歷：${job.education}`,
      `薪水：${job.salary}`,
    ].join('\n')
    navigate('/resume-rewrite', { state: { job_text: jobText, job_url: job.link } })
    onClose()
  }

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', handleKey)
    }
  }, [onClose])

  useEffect(() => {
    if (!job.link) return
    fetchJobUrl(job.link)
      .then(({ text }) => setJobContent(text))
      .catch(() => {})
  }, [job.link])

  async function handleEvaluate() {
    setEvalLoading(true)
    setEvalError(null)
    try {
      const cv = localStorage.getItem('careerpilot_cv') ?? ''
      const result = await evaluateJob({
        job,
        user_cv: cv + formatPrefsForPrompt(prefs),
        job_description: jobContent ?? '',
      })
      setEvalResult(result)
    } catch (err) {
      setEvalError(err instanceof Error ? err.message : '評分失敗')
    } finally {
      setEvalLoading(false)
    }
  }

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-job"
      onClick={e => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="modal">
        <button className="modal__close" aria-label="關閉" onClick={onClose}>
          ✕
        </button>
        <h3 id="modal-job" className="modal__title">
          {job.job}
        </h3>

        <div className="modal__grid">
          <div className="modal__field">
            <span className="modal__label">公司</span>
            <span className="modal__value">{job.company}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">城市</span>
            <span className="modal__value">{job.city}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">刊登日期</span>
            <span className="modal__value">{job.is_featured ? '精選職缺' : job.date}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">經歷要求</span>
            <span className="modal__value">{job.experience}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">最低學歷</span>
            <span className="modal__value">{job.education}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">薪水</span>
            <span className="modal__value modal__value--salary">{job.salary}</span>
          </div>
        </div>

        <a
          href={job.link}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-goto"
        >
          前往查看完整詳情 →
        </a>

        <button
          type="button"
          className="btn-export"
          style={{ marginTop: '0.6rem', width: '100%' }}
          onClick={handleRewriteResume}
        >
          ✍️ 針對此職缺改寫履歷
        </button>

        <div className="modal__ai-section">
          <button className="btn-evaluate" disabled={evalLoading} onClick={handleEvaluate}>
            {evalLoading ? '評分中...' : evalResult ? '✨ 重新評分' : '✨ AI 評分'}
          </button>

          {evalError && (
            <div className="ai-result">
              <p className="ai-result__error">評分失敗：{evalError}</p>
            </div>
          )}

          {evalResult && !evalError && (
            <div className="ai-result">
              <div className="ai-result__header">
                <span className={`ai-score ${getScoreClass(evalResult.score)}`}>
                  {evalResult.score}
                </span>
                <span className="ai-result__summary">{evalResult.summary}</span>
              </div>
              {(evalResult.match_points.length > 0 || evalResult.gap_points.length > 0) && (
                <div className="ai-result__body">
                  {evalResult.match_points.length > 0 && (
                    <div className="ai-result__section">
                      <span className="ai-result__label ai-result__label--match">優勢</span>
                      <ul className="ai-result__list ai-result__list--match">
                        {evalResult.match_points.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {evalResult.gap_points.length > 0 && (
                    <div className="ai-result__section">
                      <span className="ai-result__label ai-result__label--gap">落差</span>
                      <ul className="ai-result__list ai-result__list--gap">
                        {evalResult.gap_points.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              <p className="ai-result__rec">{evalResult.recommendation}</p>
              {evalResult.dimensions && <DimensionsPanel dimensions={evalResult.dimensions} />}
            </div>
          )}
        </div>

        <JobChat job={job} jobContent={jobContent} />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend
npx tsc --noEmit
```

Expected: error on `JobChat` — `jobContent` prop not yet accepted. Fix in Task 7.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/JobModal.tsx
git commit -m "feat: auto-fetch job content on modal open, pass to evaluate and chat"
```

---

### Task 7: Update JobChat.tsx

**Files:**
- Modify: `frontend/src/components/JobChat.tsx`

- [ ] **Step 1: Update JobChat.tsx**

Replace `frontend/src/components/JobChat.tsx` with:

```tsx
import { useEffect, useRef, useState } from 'react'
import { chatStream } from '../api/client'
import { usePreferences, formatPrefsForPrompt } from '../hooks/usePreferences'
import type { ChatMessage, JobListing } from '../types'

interface Props {
  job: JobListing
  jobContent?: string | null
}

const GREETING = '有什麼關於這個職缺的問題想問我？'
const STORAGE_KEY = 'careerpilot_chats'

function loadHistory(jobLink: string): ChatMessage[] {
  try {
    const all = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, ChatMessage[]>
    return all[jobLink] ?? []
  } catch {
    return []
  }
}

function saveHistory(jobLink: string, messages: ChatMessage[]): void {
  try {
    const all = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, ChatMessage[]>
    all[jobLink] = messages
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
  } catch {
    // ignore storage quota errors
  }
}

export default function JobChat({ job, jobContent }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadHistory(job.link))
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [prefs] = usePreferences()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    saveHistory(job.link, messages)
  }, [job.link, messages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleClear() {
    setMessages([])
  }

  async function handleSend() {
    if (!input.trim() || isStreaming) return

    const userMsg: ChatMessage = { role: 'user', content: input.trim() }
    const nextMessages = [...messages, userMsg]
    setMessages([...nextMessages, { role: 'assistant', content: '' }])
    setInput('')
    setIsStreaming(true)

    try {
      const userCv = localStorage.getItem('careerpilot_cv') ?? ''
      const prefsStr = formatPrefsForPrompt(prefs)

      await chatStream(nextMessages, job, userCv + prefsStr, jobContent ?? '', chunk => {
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          updated[updated.length - 1] = { ...last, content: last.content + chunk }
          return updated
        })
      })
    } catch {
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        const separator = last.content ? '\n\n' : ''
        updated[updated.length - 1] = {
          ...last,
          content: last.content + separator + '⚠ 回應中斷，請再試一次',
        }
        return updated
      })
    } finally {
      setIsStreaming(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="job-chat">
      <div className="job-chat__header">
        <span className="job-chat__title">職缺 Q&amp;A</span>
        {messages.length > 0 && (
          <button
            className="btn-export"
            style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
            onClick={handleClear}
          >
            清空
          </button>
        )}
      </div>

      <div className="job-chat__messages">
        <div className="job-chat__bubble job-chat__bubble--greeting">
          {GREETING}
        </div>
        {messages.map((msg, i) => (
          <div key={`${i}-${msg.role}`} className={`job-chat__bubble job-chat__bubble--${msg.role}`}>
            {msg.content}
            {isStreaming && i === messages.length - 1 && msg.role === 'assistant' && (
              <span className="job-chat__cursor">▌</span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="job-chat__input-row">
        <textarea
          className="job-chat__input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="輸入問題（Enter 送出，Shift+Enter 換行）"
          disabled={isStreaming}
          rows={2}
        />
        <button
          className="job-chat__send-btn"
          disabled={isStreaming || !input.trim()}
          onClick={handleSend}
        >
          送出
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend
npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 3: Run backend tests one final time**

```bash
cd backend
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/JobChat.tsx
git commit -m "feat: pass job_description to chat via jobContent prop"
```
