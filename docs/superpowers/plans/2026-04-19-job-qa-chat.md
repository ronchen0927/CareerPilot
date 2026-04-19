# Job Q&A Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-job multi-turn Q&A chat panel inside JobModal, powered by a streaming OpenAI endpoint, with conversation history persisted in localStorage per job URL.

**Architecture:** A new `POST /api/chat` endpoint streams OpenAI responses using `StreamingResponse`. A new `JobChat.tsx` React component reads/writes conversation history to `careerpilot_chats` in localStorage (keyed by `job.link`), and renders inside the existing `JobModal.tsx` below the AI evaluation section.

**Tech Stack:** FastAPI `StreamingResponse`, OpenAI async streaming (`stream=True`), React `fetch` + `ReadableStream`, localStorage.

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `backend/app/routers/chat.py` | Streaming `/api/chat` endpoint |
| Modify | `backend/app/main.py` | Register chat router |
| Create | `backend/tests/test_api_chat.py` | Backend tests |
| Modify | `frontend/src/types/index.ts` | Add `ChatMessage` interface |
| Modify | `frontend/src/api/client.ts` | Add `chatStream()` function |
| Create | `frontend/src/components/JobChat.tsx` | Chat UI component |
| Modify | `frontend/src/components/JobModal.tsx` | Mount `<JobChat>` in modal |
| Modify | `frontend/css/style.css` | Chat component styles |

---

## Task 1: Backend — `routers/chat.py` with tests (TDD)

**Files:**
- Create: `backend/tests/test_api_chat.py`
- Create: `backend/app/routers/chat.py`
- Modify: `backend/app/main.py`

### Step 1.1 — Write failing tests

Create `backend/tests/test_api_chat.py`:

```python
"""Tests for POST /api/chat streaming endpoint."""
from unittest.mock import AsyncMock, MagicMock, patch


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


def _make_fake_stream(contents: list[str]):
    """Return an async generator that yields mock OpenAI chunks."""
    async def _gen():
        for text in contents:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = text
            yield chunk
    return _gen()


class TestChat:
    def test_streams_text_response(self, client):
        with patch("app.routers.chat.AsyncOpenAI") as MockAI:
            inst = MagicMock()
            MockAI.return_value = inst
            inst.chat.completions.create = AsyncMock(
                return_value=_make_fake_stream(["你好", "！"])
            )
            resp = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "我適合嗎？"}],
                    "job": _job_payload(),
                    "user_cv": "Python 工程師，3 年經驗",
                },
            )
        assert resp.status_code == 200
        assert "你好" in resp.text
        assert "！" in resp.text

    def test_empty_messages_still_returns_200(self, client):
        with patch("app.routers.chat.AsyncOpenAI") as MockAI:
            inst = MagicMock()
            MockAI.return_value = inst
            inst.chat.completions.create = AsyncMock(
                return_value=_make_fake_stream(["開始吧"])
            )
            resp = client.post(
                "/api/chat",
                json={"messages": [], "job": _job_payload(), "user_cv": ""},
            )
        assert resp.status_code == 200

    def test_missing_openai_key_returns_503(self, client):
        with patch("app.routers.chat.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            resp = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": "test"}],
                    "job": _job_payload(),
                    "user_cv": "",
                },
            )
        assert resp.status_code == 503

    def test_missing_messages_field_returns_422(self, client):
        resp = client.post(
            "/api/chat",
            json={"job": _job_payload(), "user_cv": ""},
        )
        assert resp.status_code == 422

    def test_missing_job_field_returns_422(self, client):
        resp = client.post(
            "/api/chat",
            json={"messages": [], "user_cv": ""},
        )
        assert resp.status_code == 422
```

- [ ] **Step 1.2 — Run tests to confirm they fail**

```bash
cd backend && uv run pytest tests/test_api_chat.py -v
```

Expected: `ImportError` or `404` — `chat` router doesn't exist yet.

- [ ] **Step 1.3 — Create `backend/app/routers/chat.py`**

```python
"""Streaming job Q&A chat endpoint."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from ..config import settings
from ..models import JobListing

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    job: JobListing
    user_cv: str


_SYSTEM_PROMPT = """\
You are a professional career advisor helping a job seeker evaluate and prepare \
for a specific job opportunity. Always respond in Traditional Chinese (繁體中文).

[Target Job]
Title: {job}
Company: {company}
City: {city}
Salary: {salary}
Experience required: {experience}
Education required: {education}
Job URL: {link}

[User Resume and Preferences]
{user_cv}\
"""


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
            yield f"\n\n⚠ 回應失敗：{e}"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")
```

- [ ] **Step 1.4 — Register the router in `backend/app/main.py`**

Find the import line (line 12):
```python
from .routers import alerts, cover_letter, cv, evaluate, fetch_url, history, jobs, liveness, resume
```
Change to:
```python
from .routers import alerts, chat, cover_letter, cv, evaluate, fetch_url, history, jobs, liveness, resume
```

Find the `app.include_router(liveness.router)` line and add after it:
```python
app.include_router(chat.router)
```

- [ ] **Step 1.5 — Run tests to confirm they pass**

```bash
cd backend && uv run pytest tests/test_api_chat.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 1.6 — Run full test suite to confirm no regressions**

```bash
cd backend && uv run pytest -v
```

Expected: all existing tests still PASS.

- [ ] **Step 1.7 — Commit**

```bash
git checkout -b feat/job-qa-chat
git add backend/app/routers/chat.py backend/app/main.py backend/tests/test_api_chat.py
git commit -m "feat: add streaming /api/chat endpoint for per-job Q&A"
```

---

## Task 2: Frontend types + API client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 2.1 — Add `ChatMessage` to `frontend/src/types/index.ts`**

Add at the end of the file:

```ts
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  messages: ChatMessage[]
  job: JobListing
  user_cv: string
}
```

- [ ] **Step 2.2 — Add `chatStream()` to `frontend/src/api/client.ts`**

Add at the top import block:
```ts
import type {
  // ... existing imports ...
  ChatMessage,
  ChatRequest,
} from '../types'
```

Add at the end of the file:

```ts
export async function chatStream(
  messages: ChatMessage[],
  job: JobListing,
  userCv: string,
  onChunk: (chunk: string) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, job, user_cv: userCv } satisfies ChatRequest),
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

- [ ] **Step 2.3 — Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 2.4 — Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add ChatMessage type and chatStream() API function"
```

---

## Task 3: Chat component styles

**Files:**
- Modify: `frontend/css/style.css`

- [ ] **Step 3.1 — Append chat styles to `frontend/css/style.css`**

Add at the end of the file:

```css
/* ==========================================================
   Job Chat
   ========================================================== */
.job-chat {
  margin-top: var(--space-md);
  border-top: 1px solid var(--border);
  padding-top: var(--space-md);
}

.job-chat__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
}

.job-chat__title {
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-3);
}

.job-chat__messages {
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: var(--space-sm);
  padding: 0.25rem 0;
}

.job-chat__messages::-webkit-scrollbar { width: 3px; }
.job-chat__messages::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 2px;
}

.job-chat__bubble {
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: 0.845rem;
  line-height: 1.65;
  max-width: 88%;
  white-space: pre-wrap;
  word-break: break-word;
}

.job-chat__bubble--user {
  background: var(--accent-dim);
  border: 1px solid var(--accent);
  color: var(--text-1);
  align-self: flex-end;
}

.job-chat__bubble--assistant {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text-1);
  align-self: flex-start;
}

.job-chat__bubble--greeting {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text-2);
  align-self: flex-start;
  font-style: italic;
}

.job-chat__cursor {
  display: inline-block;
  color: var(--accent);
  animation: pulse 0.8s ease-in-out infinite;
  font-size: 0.72rem;
  margin-left: 2px;
}

.job-chat__input-row {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
}

.job-chat__input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-1);
  font-family: inherit;
  font-size: 0.845rem;
  line-height: 1.5;
  resize: none;
  outline: none;
  transition: border-color var(--t-fast);
}

.job-chat__input:focus  { border-color: var(--border-focus); }
.job-chat__input:disabled { opacity: 0.5; cursor: not-allowed; }

.job-chat__send-btn {
  padding: 0.5rem 0.9rem;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  color: #fff;
  font-family: inherit;
  font-size: 0.845rem;
  font-weight: 600;
  cursor: pointer;
  transition: filter var(--t-fast);
  white-space: nowrap;
  flex-shrink: 0;
}

.job-chat__send-btn:hover:not(:disabled) { filter: brightness(1.1); }
.job-chat__send-btn:disabled { opacity: 0.45; cursor: not-allowed; }
```

- [ ] **Step 3.2 — Commit**

```bash
git add frontend/css/style.css
git commit -m "feat: add job-chat CSS component styles"
```

---

## Task 4: `JobChat.tsx` component

**Files:**
- Create: `frontend/src/components/JobChat.tsx`

- [ ] **Step 4.1 — Create `frontend/src/components/JobChat.tsx`**

```tsx
import { useEffect, useRef, useState } from 'react'
import { chatStream } from '../api/client'
import { formatPrefsForPrompt, usePreferences } from '../hooks/usePreferences'
import type { ChatMessage, JobListing } from '../types'

interface Props {
  job: JobListing
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

export default function JobChat({ job }: Props) {
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
    setMessages(nextMessages)
    setInput('')
    setIsStreaming(true)

    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      const cv = localStorage.getItem('careerpilot_cv') ?? ''
      const userCv = cv + formatPrefsForPrompt(prefs)

      await chatStream(nextMessages, job, userCv, chunk => {
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
        updated[updated.length - 1] = {
          ...last,
          content: last.content || '⚠ 回應中斷，請再試一次',
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
          <button className="btn-export" style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }} onClick={handleClear}>
            清空
          </button>
        )}
      </div>

      <div className="job-chat__messages">
        <div className="job-chat__bubble job-chat__bubble--greeting">
          {GREETING}
        </div>
        {messages.map((msg, i) => (
          <div key={i} className={`job-chat__bubble job-chat__bubble--${msg.role}`}>
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

- [ ] **Step 4.2 — Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4.3 — Commit**

```bash
git add frontend/src/components/JobChat.tsx
git commit -m "feat: add JobChat component with localStorage history and streaming"
```

---

## Task 5: Integrate `JobChat` into `JobModal`

**Files:**
- Modify: `frontend/src/components/JobModal.tsx`

- [ ] **Step 5.1 — Add import to `JobModal.tsx`**

At the top of `frontend/src/components/JobModal.tsx`, add after the existing imports:

```tsx
import JobChat from './JobChat'
```

- [ ] **Step 5.2 — Mount `<JobChat>` inside the modal**

In `JobModal.tsx`, find the closing `</div>` of `.modal__ai-section` (currently the last element before the closing `</div>` of `.modal`). Add `<JobChat>` after it:

```tsx
        </div>  {/* end modal__ai-section */}

        <JobChat job={job} />

      </div>  {/* end modal */}
```

- [ ] **Step 5.3 — Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5.4 — Manual smoke test**

1. Start backend: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173, search for any job
4. Click a job to open the modal
5. Scroll to the bottom — confirm "職缺 Q&A" section is visible
6. Type a question and press Enter — confirm streaming response appears
7. Close and reopen the same job modal — confirm conversation history is preserved
8. Click "清空" — confirm history is cleared

- [ ] **Step 5.5 — Commit**

```bash
git add frontend/src/components/JobModal.tsx
git commit -m "feat: mount JobChat in JobModal for per-job Q&A"
```

---

## Task 6: PR

- [ ] **Step 6.1 — Push and open PR**

```bash
git push -u origin feat/job-qa-chat
gh pr create \
  --title "feat: per-job Q&A chat with streaming AI responses" \
  --body "Adds a multi-turn Q&A chat panel inside JobModal. Uses a new POST /api/chat streaming endpoint. Conversation history persisted in localStorage keyed by job URL. See docs/superpowers/specs/2026-04-19-job-qa-chat-design.md."
```
