import type {
  Alert,
  AlertCreateRequest,
  AlertsListResponse,
  EvaluationRecord,
  JobEvaluateRequest,
  JobEvaluateResponse,
  JobEvaluateTextRequest,
  JobOptions,
  JobSearchRequest,
  JobSearchResponse,
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
