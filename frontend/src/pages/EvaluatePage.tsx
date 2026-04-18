import { useRef, useState } from 'react'
import { evaluateJobText, fetchJobUrl, parseCvPdf } from '../api/client'
import type { JobEvaluateResponse } from '../types'

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

export default function EvaluatePage() {
  const [jobUrl, setJobUrl] = useState('')
  const [jobText, setJobText] = useState('')
  const [cv, setCv] = useState(() => localStorage.getItem('careerpilot_cv') ?? '')
  const [result, setResult] = useState<JobEvaluateResponse | null>(null)

  const [fetchLoading, setFetchLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [evalLoading, setEvalLoading] = useState(false)
  const [evalError, setEvalError] = useState<string | null>(null)
  const [cvLoading, setCvLoading] = useState(false)
  const [cvError, setCvError] = useState<string | null>(null)

  const cvFileRef = useRef<HTMLInputElement>(null)

  function handleCvChange(value: string) {
    setCv(value)
    localStorage.setItem('careerpilot_cv', value)
  }

  async function handleFetchUrl() {
    if (!jobUrl.trim()) return
    setFetchLoading(true)
    setFetchError(null)
    try {
      const data = await fetchJobUrl(jobUrl.trim())
      setJobText(data.text)
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : '頁面擷取失敗')
    } finally {
      setFetchLoading(false)
    }
  }

  async function handleCvUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setCvLoading(true)
    setCvError(null)
    try {
      const data = await parseCvPdf(file)
      handleCvChange(data.text)
    } catch (err) {
      setCvError(err instanceof Error ? err.message : 'PDF 解析失敗')
    } finally {
      setCvLoading(false)
      // reset input so same file can be re-uploaded
      if (cvFileRef.current) cvFileRef.current.value = ''
    }
  }

  async function handleEvaluate(e: React.FormEvent) {
    e.preventDefault()
    if (jobText.trim().length < 10) return
    setEvalLoading(true)
    setEvalError(null)
    setResult(null)
    try {
      const data = await evaluateJobText({ job_text: jobText, user_cv: cv })
      setResult(data)
    } catch (err) {
      setEvalError(err instanceof Error ? err.message : '評分失敗，請稍後再試')
    } finally {
      setEvalLoading(false)
    }
  }

  return (
    <div className="container">
      <header className="header">
        <div className="header__logo">
          <span className="header__icon">✨</span>
          <h1 className="header__title">AI 職缺評分</h1>
        </div>
        <p className="header__subtitle">貼上任何平台的職缺描述，立即取得 AI 評估</p>
      </header>

      <section className="search-card">
        <form onSubmit={handleEvaluate}>

          {/* URL fetch */}
          <div className="form-group">
            <label className="form-label" htmlFor="job-url">
              <span className="form-label__icon">🔗</span>
              職缺網址（選填）
              <span className="form-label__hint">自動擷取頁面內容，失敗時請改用手動貼上</span>
            </label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="url"
                id="job-url"
                className="form-input"
                placeholder="https://www.104.com.tw/job/..."
                value={jobUrl}
                onChange={e => setJobUrl(e.target.value)}
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="btn-search"
                style={{ width: 'auto', padding: '0 1.2rem' }}
                disabled={fetchLoading || !jobUrl.trim()}
                onClick={handleFetchUrl}
              >
                {fetchLoading ? '擷取中...' : '擷取'}
              </button>
            </div>
            {fetchError && (
              <p style={{ color: 'var(--color-error, #f87171)', fontSize: '0.85rem', marginTop: '0.4rem' }}>
                ⚠️ {fetchError}，請直接貼上職缺描述
              </p>
            )}
          </div>

          {/* Job text */}
          <div className="form-group">
            <label className="form-label" htmlFor="job-text">
              <span className="form-label__icon">📋</span>
              職缺描述
              <span className="form-label__hint">從 104、Yourator 等平台複製貼上，或由上方自動擷取</span>
            </label>
            <textarea
              id="job-text"
              className="form-input"
              rows={10}
              placeholder="貼上職缺標題、公司名稱、工作內容、要求條件、薪資等資訊..."
              value={jobText}
              onChange={e => setJobText(e.target.value)}
              required
              style={{ resize: 'vertical', fontFamily: 'inherit' }}
            />
          </div>

          {/* CV */}
          <div className="form-group">
            <label className="form-label" htmlFor="user-cv">
              <span className="form-label__icon">👤</span>
              我的背景（選填）
              <span className="form-label__hint">資料儲存在本機；可上傳 PDF 自動填入</span>
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
              <input
                ref={cvFileRef}
                type="file"
                accept=".pdf"
                style={{ display: 'none' }}
                onChange={handleCvUpload}
              />
              <button
                type="button"
                className="btn-export"
                disabled={cvLoading}
                onClick={() => cvFileRef.current?.click()}
              >
                {cvLoading ? '解析中...' : '上傳 PDF 履歷'}
              </button>
              {cv && (
                <span style={{ fontSize: '0.8rem', opacity: 0.6 }}>
                  已填入 {cv.length} 字
                </span>
              )}
            </div>
            {cvError && (
              <p style={{ color: 'var(--color-error, #f87171)', fontSize: '0.85rem', marginBottom: '0.4rem' }}>
                ⚠️ {cvError}
              </p>
            )}
            <textarea
              id="user-cv"
              className="form-input"
              rows={5}
              placeholder="例：3 年 Python 後端經驗，熟悉 FastAPI、PostgreSQL，有帶領小型團隊經驗..."
              value={cv}
              onChange={e => handleCvChange(e.target.value)}
              style={{ resize: 'vertical', fontFamily: 'inherit' }}
            />
          </div>

          <button type="submit" className="btn-search" disabled={evalLoading}>
            <span className="btn-search__text">{evalLoading ? '評分中...' : '✨ 開始評分'}</span>
            <span className="btn-search__icon">→</span>
          </button>
        </form>
      </section>

      {evalLoading && (
        <section className="loading">
          <div className="loading__spinner" />
          <p className="loading__text">AI 分析中，請稍候...</p>
        </section>
      )}

      {evalError && (
        <section className="error-card">
          <span className="error-card__icon">⚠️</span>
          <p className="error-card__text">{evalError}</p>
          <button className="btn-dismiss" onClick={() => setEvalError(null)}>
            關閉
          </button>
        </section>
      )}

      {result && (
        <section className="search-card">
          <div className="ai-result">
            <div className="ai-result__header">
              <span className={`ai-score ${getScoreClass(result.score)}`}>{result.score}</span>
              <span className="ai-result__summary">{result.summary}</span>
              {result.from_cache && (
                <span style={{
                  fontSize: '0.72rem',
                  padding: '0.15rem 0.5rem',
                  borderRadius: '999px',
                  background: 'var(--color-tag-bg, rgba(99,102,241,0.15))',
                  color: 'var(--color-tag-text, #818cf8)',
                  marginLeft: 'auto',
                  whiteSpace: 'nowrap',
                }}>
                  已快取
                </span>
              )}
            </div>
            {(result.match_points.length > 0 || result.gap_points.length > 0) && (
              <div className="ai-result__body">
                {result.match_points.length > 0 && (
                  <div className="ai-result__section">
                    <span className="ai-result__label ai-result__label--match">優勢</span>
                    <ul className="ai-result__list ai-result__list--match">
                      {result.match_points.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.gap_points.length > 0 && (
                  <div className="ai-result__section">
                    <span className="ai-result__label ai-result__label--gap">落差</span>
                    <ul className="ai-result__list ai-result__list--gap">
                      {result.gap_points.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            <p className="ai-result__rec">{result.recommendation}</p>
          </div>
        </section>
      )}
    </div>
  )
}
