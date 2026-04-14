import type {
  Alert,
  AlertCreateRequest,
  AlertsListResponse,
  JobEvaluateRequest,
  JobEvaluateResponse,
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
