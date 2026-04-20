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
    try {
      const res = await suggestKeywords(text)
      setKeywords(res.keywords)
    } catch {
      setKeywords([])
    } finally {
      setPhase('keywords')
      setLoadingKeywords(false)
    }
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
      const res = await searchJobs({ keyword: keywords[0], pages: 5, areas, experience: [], sources })
      const allJobs = res.results
      setJobs(allJobs)
      setPhase('results')

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
      <div className="page-intro">
        <h1 className="page-intro__title">智慧推薦</h1>
        <p className="page-intro__sub">上傳履歷，AI 自動建議關鍵字並找出最符合的職缺</p>
      </div>

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
          <h2 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>AI 建議的搜尋關鍵字</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '1rem' }}>
            搜尋時將使用第一個關鍵字，可刪除或調整順序。
          </p>
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
              style={{ flex: 1, minWidth: 0 }}
            />
            <button className="btn-search" style={{ width: 'auto', flexShrink: 0, padding: '0 1.25rem' }} onClick={handleAddKeyword}>
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
              找到 {jobs.length} 筆職缺，前 {Math.min(AUTO_EVAL_LIMIT, jobs.length)} 筆自動評分{loadingEval ? '中...' : '完成'}
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
