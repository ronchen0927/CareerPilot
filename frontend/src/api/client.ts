import type {
  Alert,
  AlertCreateRequest,
  AlertsListResponse,
  ChatMessage,
  ChatRequest,
  CVSuggestKeywordsResponse,
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

const API_BASE = 'http://localhost:8000'

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function fetchOptions(): Promise<JobOptions> {
  return apiFetch<JobOptions>('/api/jobs/options')
}

export function searchJobs(req: JobSearchRequest): Promise<JobSearchResponse> {
  return apiFetch<JobSearchResponse>('/api/jobs/search', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function evaluateJob(req: JobEvaluateRequest): Promise<JobEvaluateResponse> {
  return apiFetch<JobEvaluateResponse>('/api/jobs/evaluate', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function evaluateJobText(req: JobEvaluateTextRequest): Promise<JobEvaluateResponse> {
  return apiFetch<JobEvaluateResponse>('/api/jobs/evaluate-text', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function fetchAlerts(): Promise<AlertsListResponse> {
  return apiFetch<AlertsListResponse>('/api/alerts')
}

export function createAlert(req: AlertCreateRequest): Promise<Alert> {
  return apiFetch<Alert>('/api/alerts', { method: 'POST', body: JSON.stringify(req) })
}

export function deleteAlert(id: string): Promise<void> {
  return apiFetch<void>(`/api/alerts/${id}`, { method: 'DELETE' })
}

export function triggerAlert(id: string): Promise<TriggerAlertResponse> {
  return apiFetch<TriggerAlertResponse>(`/api/alerts/${id}/trigger`, { method: 'POST' })
}

export async function parseCvPdf(file: File): Promise<{ text: string }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/api/cv/parse`, { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<{ text: string }>
}

export function fetchJobUrl(url: string): Promise<{ text: string }> {
  return apiFetch<{ text: string }>('/api/jobs/fetch-url', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

export function fetchEvaluations(): Promise<EvaluationRecord[]> {
  return apiFetch<EvaluationRecord[]>('/api/evaluations')
}

export function fetchEvaluation(id: number): Promise<EvaluationRecord> {
  return apiFetch<EvaluationRecord>(`/api/evaluations/${id}`)
}

export function deleteEvaluation(id: number): Promise<void> {
  return apiFetch<void>(`/api/evaluations/${id}`, { method: 'DELETE' })
}

export function generateCoverLetter(req: CoverLetterRequest): Promise<CoverLetterResponse> {
  return apiFetch<CoverLetterResponse>('/api/jobs/cover-letter', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function fetchCoverLetters(): Promise<CoverLetterRecord[]> {
  return apiFetch<CoverLetterRecord[]>('/api/cover-letters')
}

export function fetchCoverLetter(id: number): Promise<CoverLetterRecord> {
  return apiFetch<CoverLetterRecord>(`/api/cover-letters/${id}`)
}

export function deleteCoverLetter(id: number): Promise<void> {
  return apiFetch<void>(`/api/cover-letters/${id}`, { method: 'DELETE' })
}

export function rewriteResume(req: ResumeRewriteRequest): Promise<ResumeRewriteResponse> {
  return apiFetch<ResumeRewriteResponse>('/api/jobs/resume-rewrite', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function fetchResumeRewrites(): Promise<ResumeRewriteRecord[]> {
  return apiFetch<ResumeRewriteRecord[]>('/api/resume-rewrites')
}

export function fetchResumeRewrite(id: number): Promise<ResumeRewriteRecord> {
  return apiFetch<ResumeRewriteRecord>(`/api/resume-rewrites/${id}`)
}

export function deleteResumeRewrite(id: number): Promise<void> {
  return apiFetch<void>(`/api/resume-rewrites/${id}`, { method: 'DELETE' })
}

export function fetchLivenessStatus(urls: string[]): Promise<LivenessMap> {
  return apiFetch<LivenessMap>('/api/liveness/status', {
    method: 'POST',
    body: JSON.stringify({ urls }),
  })
}

export function triggerLivenessCheck(urls: string[]): Promise<{ checked: number }> {
  return apiFetch<{ checked: number }>('/api/liveness/check', {
    method: 'POST',
    body: JSON.stringify({ urls }),
  })
}

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

export function suggestKeywords(cvText: string): Promise<CVSuggestKeywordsResponse> {
  return apiFetch<CVSuggestKeywordsResponse>('/api/cv/suggest-keywords', {
    method: 'POST',
    body: JSON.stringify({ cv_text: cvText }),
  })
}
