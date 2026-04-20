# Cover Letter Button for 想投 Bookmarks — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "AI 推薦信" button for "想投" bookmarked jobs in both the SearchPage bookmark table and JobModal.

**Architecture:** Three frontend files are modified. CoverLetterPage gains navigation-state pre-fill (same pattern as ResumeRewritePage). SearchPage adds a per-row fetch-then-navigate button for 想投 rows. JobModal accepts a new `bookmarkStatus` prop and renders the button when it equals `'想投'`.

**Tech Stack:** React, React Router (`useNavigate`, `useLocation`), existing `fetchJobUrl` API call, existing `/cover-letter` route.

---

### Task 1: CoverLetterPage — pre-fill from navigation state

**Files:**
- Modify: `frontend/src/pages/CoverLetterPage.tsx`

- [ ] **Step 1: Add `useLocation` import**

Open `frontend/src/pages/CoverLetterPage.tsx`. Line 2 currently reads:
```tsx
import { useNavigate } from 'react-router-dom'
```
Change it to:
```tsx
import { useLocation, useNavigate } from 'react-router-dom'
```

- [ ] **Step 2: Read navigation state and initialize state from it**

After the existing `const navigate = useNavigate()` line (currently line 20), add:
```tsx
const location = useLocation()
const locState = location.state as { job_text?: string; job_url?: string } | null
```

Then change the two existing `useState` initialisers for `jobUrl` and `jobText`:

**Before:**
```tsx
const [jobUrl, setJobUrl] = useState('')
const [jobText, setJobText] = useState('')
```

**After:**
```tsx
const [jobUrl, setJobUrl] = useState(locState?.job_url ?? '')
const [jobText, setJobText] = useState(locState?.job_text ?? '')
```

- [ ] **Step 3: Type-check**

```bash
cd frontend
./node_modules/.bin/tsc --noEmit -p tsconfig.app.json
```

Expected: only the two pre-existing unrelated errors in `CoverLetterDetailPage.tsx` and `ResumeRewriteDetailPage.tsx` (unused `navigate`). No new errors.

- [ ] **Step 4: Manual smoke test**

Start the dev server (`npm run dev`) and navigate directly to `http://localhost:5173/cover-letter` — both fields should be empty (unchanged default behaviour).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/CoverLetterPage.tsx
git commit -m "feat: pre-fill CoverLetterPage from navigation state"
```

---

### Task 2: SearchPage — "AI 推薦信" button for 想投 rows

**Files:**
- Modify: `frontend/src/pages/SearchPage.tsx`

- [ ] **Step 1: Add missing imports**

Line 1 currently reads:
```tsx
import { useEffect, useMemo, useState } from 'react'
```
Change to:
```tsx
import { useEffect, useMemo, useState } from 'react'
```
*(no change needed — `useState` is already imported)*

Line 2 currently reads:
```tsx
import { Link } from 'react-router-dom'
```
Change to:
```tsx
import { Link, useNavigate } from 'react-router-dom'
```

Line 3 currently reads:
```tsx
import { fetchOptions, searchJobs } from '../api/client'
```
Change to:
```tsx
import { fetchJobUrl, fetchOptions, searchJobs } from '../api/client'
```

- [ ] **Step 2: Add `useNavigate` call and new state**

Inside `SearchPage()`, after the existing `useBookmarks()` call (around line 67), add:
```tsx
const navigate = useNavigate()
const [fetchingLink, setFetchingLink] = useState<string | null>(null)
const [fetchLinkError, setFetchLinkError] = useState<string | null>(null)
```

- [ ] **Step 3: Add `handleCoverLetter` handler**

After the state declarations above, add:
```tsx
async function handleCoverLetter(link: string) {
  setFetchingLink(link)
  setFetchLinkError(null)
  try {
    const data = await fetchJobUrl(link)
    navigate('/cover-letter', { state: { job_text: data.text, job_url: link } })
  } catch {
    setFetchLinkError(link)
    setTimeout(() => setFetchLinkError(null), 3000)
  } finally {
    setFetchingLink(null)
  }
}
```

- [ ] **Step 4: Add button in bookmark table row**

Find the `<td>` that contains the "移除" button (around line 427):
```tsx
<td>
  <button className="btn-remove" onClick={() => removeBookmark(link)}>
    移除
  </button>
</td>
```

Replace it with:
```tsx
<td style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
  {bm.status === '想投' && (
    <>
      <button
        className="btn-export"
        style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
        disabled={fetchingLink === link}
        onClick={() => handleCoverLetter(link)}
      >
        {fetchingLink === link ? '抓取中...' : 'AI 推薦信'}
      </button>
      {fetchLinkError === link && (
        <span style={{ color: 'var(--color-error, #e53e3e)', fontSize: '0.75rem' }}>
          擷取失敗
        </span>
      )}
    </>
  )}
  <button className="btn-remove" onClick={() => removeBookmark(link)}>
    移除
  </button>
</td>
```

- [ ] **Step 5: Type-check**

```bash
cd frontend
./node_modules/.bin/tsc --noEmit -p tsconfig.app.json
```

Expected: same two pre-existing errors only.

- [ ] **Step 6: Manual smoke test**

1. Search for a job and bookmark it (status defaults to 想投).
2. Scroll to the bookmarks table — confirm the "AI 推薦信" button appears on that row.
3. Change the bookmark status to "已投" — confirm the button disappears.
4. Change it back to "想投" — confirm the button reappears.
5. Click "AI 推薦信" — button should show "抓取中...", then navigate to `/cover-letter` with the job text pre-filled.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/SearchPage.tsx
git commit -m "feat: add AI cover letter button for 想投 bookmarks in SearchPage"
```

---

### Task 3: JobModal — "AI 推薦信" button when status is 想投

**Files:**
- Modify: `frontend/src/components/JobModal.tsx`
- Modify: `frontend/src/pages/SearchPage.tsx` (pass prop)

- [ ] **Step 1: Add `BookmarkStatus` import to JobModal**

Line 7 of `frontend/src/components/JobModal.tsx` currently reads:
```tsx
import type { JobEvaluateResponse, JobListing } from '../types'
```
Change to:
```tsx
import type { BookmarkStatus, JobEvaluateResponse, JobListing } from '../types'
```

- [ ] **Step 2: Add `bookmarkStatus` prop to the Props interface**

Currently:
```tsx
interface Props {
  job: JobListing
  onClose: () => void
}
```
Change to:
```tsx
interface Props {
  job: JobListing
  onClose: () => void
  bookmarkStatus?: BookmarkStatus
}
```

- [ ] **Step 3: Destructure the new prop**

Currently:
```tsx
export default function JobModal({ job, onClose }: Props) {
```
Change to:
```tsx
export default function JobModal({ job, onClose, bookmarkStatus }: Props) {
```

- [ ] **Step 4: Add `handleCoverLetter` function**

After the existing `handleRewriteResume` function (around line 45), add:
```tsx
function handleCoverLetter() {
  const metadataText = [
    `職位：${job.job}`,
    `公司：${job.company}`,
    `城市：${job.city}`,
    `經歷要求：${job.experience}`,
    `最低學歷：${job.education}`,
    `薪水：${job.salary}`,
  ].join('\n')
  navigate('/cover-letter', { state: { job_text: jobContent ?? metadataText, job_url: job.link } })
  onClose()
}
```

- [ ] **Step 5: Add the button in the modal JSX**

Find the existing resume-rewrite button (around line 138):
```tsx
<button
  type="button"
  className="btn-export"
  style={{ marginTop: '0.6rem', width: '100%' }}
  onClick={handleRewriteResume}
>
  ✍️ 針對此職缺改寫履歷
</button>
```

Add the cover letter button immediately after it:
```tsx
{bookmarkStatus === '想投' && (
  <button
    type="button"
    className="btn-export"
    style={{ marginTop: '0.4rem', width: '100%' }}
    onClick={handleCoverLetter}
  >
    ✉️ 產生 AI 推薦信
  </button>
)}
```

- [ ] **Step 6: Pass `bookmarkStatus` from SearchPage**

In `frontend/src/pages/SearchPage.tsx`, find the last line of the component (around line 440):
```tsx
{selectedJob && <JobModal job={selectedJob} onClose={() => setSelectedJob(null)} />}
```
Change to:
```tsx
{selectedJob && (
  <JobModal
    job={selectedJob}
    onClose={() => setSelectedJob(null)}
    bookmarkStatus={bookmarks[selectedJob.link]?.status}
  />
)}
```

- [ ] **Step 7: Type-check**

```bash
cd frontend
./node_modules/.bin/tsc --noEmit -p tsconfig.app.json
```

Expected: same two pre-existing errors only.

- [ ] **Step 8: Manual smoke test**

1. Search for a job. Open its modal — confirm "✉️ 產生 AI 推薦信" button is **not** visible (job not bookmarked).
2. Close the modal. Bookmark the job (default status: 想投). Open the modal again — confirm the button **is** visible.
3. Close the modal. Change bookmark status to "已投". Open modal — confirm button is **gone**.
4. Click "✉️ 產生 AI 推薦信" — modal closes, navigates to `/cover-letter` with the job description pre-filled.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/JobModal.tsx frontend/src/pages/SearchPage.tsx
git commit -m "feat: show AI cover letter button in JobModal when bookmark status is 想投"
```
