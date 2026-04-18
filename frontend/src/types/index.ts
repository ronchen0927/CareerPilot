export interface JobSearchRequest {
  keyword: string
  pages: number
  areas: string[]
  experience: string[]
  sources: string[]
}

export interface JobListing {
  job: string
  date: string
  link: string
  company: string
  city: string
  experience: string
  education: string
  salary: string
  salary_low: number
  salary_high: number
  is_featured: boolean
  source: string
}

export interface JobSearchResponse {
  results: JobListing[]
  count: number
  elapsed_time: number
}

export interface Option {
  value: string
  label: string
}

export interface JobOptions {
  areas: Option[]
  experience: Option[]
}

export type BookmarkStatus = '想投' | '已投' | '面試中' | '錄取' | '不適合'

export interface BookmarkEntry {
  job: string
  date: string
  company: string
  city: string
  salary: string
  status: BookmarkStatus
}

export type Bookmarks = Record<string, BookmarkEntry>

export interface AlertCreateRequest {
  keyword: string
  areas: string[]
  experience: string[]
  pages: number
  min_salary: number
  notify_type: 'line' | 'webhook'
  notify_target: string
  interval_minutes: number
}

export interface Alert {
  id: string
  keyword: string
  areas: string[]
  experience: string[]
  pages: number
  min_salary: number
  notify_type: 'line' | 'webhook'
  notify_target: string
  interval_minutes: number
  last_run: string | null
  seen_links: string[]
}

export interface AlertsListResponse {
  alerts: Alert[]
}

export interface TriggerAlertResponse {
  new_jobs_found: number
}

export interface JobEvaluateRequest {
  job: JobListing
  user_cv: string
}

export interface JobEvaluateTextRequest {
  job_text: string
  user_cv: string
}

export interface JobEvaluateResponse {
  score: string
  summary: string
  match_points: string[]
  gap_points: string[]
  recommendation: string
  from_cache?: boolean
}

export interface CoverLetterRequest {
  job_text: string
  user_cv: string
}

export interface CoverLetterResponse {
  id: number
  letter: string
}

export interface CoverLetterRecord {
  id: number
  job_text_snippet: string
  job_text: string
  letter: string
  created_at: string
}

export type ResumeRewriteMode = 'plain' | 'structured'

export interface ResumeStructured {
  summary: string
  experience: string[]
  skills: string[]
}

export interface ResumeRewriteRequest {
  job_text: string
  user_cv: string
  mode: ResumeRewriteMode
  job_url?: string | null
}

export interface ResumeRewriteResponse {
  id: number
  mode: ResumeRewriteMode
  plain_result?: string | null
  structured_result?: ResumeStructured | null
}

export interface ResumeRewriteRecord {
  id: number
  job_text_snippet: string
  job_text: string
  job_url: string | null
  original_cv: string
  mode: ResumeRewriteMode
  plain_result: string | null
  structured_result: ResumeStructured | null
  created_at: string
}

export interface EvaluationRecord {
  id: number
  job_text_snippet: string
  job_text: string
  job_url: string | null
  score: string
  summary: string
  match_points: string[]
  gap_points: string[]
  recommendation: string
  created_at: string
}
