import { useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { fetchJobUrl, parseCvPdf, rewriteResume } from '../api/client'
import type { ResumeRewriteResponse } from '../types'

interface LocationState {
  job_text?: string
  job_url?: string | null
}

export default function ResumeRewritePage() {
  const { state } = useLocation() as { state: LocationState | null }
  const navigate = useNavigate()

  const [jobUrl, setJobUrl] = useState(state?.job_url ?? '')
  const [jobText, setJobText] = useState(state?.job_text ?? '')
  const [cv, setCv] = useState(() => localStorage.getItem('careerpilot_cv') ?? '')
  const [plainResult, setPlainResult] = useState<ResumeRewriteResponse | null>(null)
  const [structuredResult, setStructuredResult] = useState<ResumeRewriteResponse | null>(null)

  const [fetchLoading, setFetchLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [cvLoading, setCvLoading] = useState(false)
  const [cvError, setCvError] = useState<string | null>(null)
  const [genLoading, setGenLoading] = useState(false)
  const [genError, setGenError] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

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
      if (cvFileRef.current) cvFileRef.current.value = ''
    }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault()
    if (jobText.trim().length < 10 || cv.trim().length < 1) return
    setGenLoading(true)
    setGenError(null)
    setPlainResult(null)
    setStructuredResult(null)
    try {
      const common = {
        job_text: jobText,
        user_cv: cv,
        job_url: jobUrl.trim() || null,
      }
      const [plain, structured] = await Promise.all([
        rewriteResume({ ...common, mode: 'plain' }),
        rewriteResume({ ...common, mode: 'structured' }),
      ])
      setPlainResult(plain)
      setStructuredResult(structured)
    } catch (err) {
      setGenError(err instanceof Error ? err.message : '生成失敗，請稍後再試')
    } finally {
      setGenLoading(false)
    }
  }

  async function handleCopy(key: string, text: string) {
    await navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const structuredText = structuredResult?.structured_result
    ? [
        structuredResult.structured_result.summary,
        '',
        '【工作經歷】',
        ...structuredResult.structured_result.experience.map(e => `• ${e}`),
        '',
        '【技能】',
        structuredResult.structured_result.skills.join('、'),
      ].join('\n')
    : ''

  return (
    <div className="container">
      <header className="header">
        <div className="header__logo">
          <span className="header__icon">📝</span>
          <h1 className="header__title">AI 履歷改寫</h1>
        </div>
        <p className="header__subtitle">
          針對職缺需求，同時產出「整份純文字」與「分段結構化」兩個版本供你比較
        </p>
      </header>

      <section className="search-card">
        <form onSubmit={handleGenerate}>
          {/* URL fetch */}
          <div className="form-group">
            <label className="form-label" htmlFor="rr-job-url">
              <span className="form-label__icon">🔗</span>
              職缺網址（選填）
              <span className="form-label__hint">自動擷取頁面內容，失敗時請改用手動貼上</span>
            </label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="url"
                id="rr-job-url"
                className="form-input"
                placeholder="https://www.cakeresume.com/jobs/..."
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
            <label className="form-label" htmlFor="rr-job-text">
              <span className="form-label__icon">📋</span>
              職缺描述
            </label>
            <textarea
              id="rr-job-text"
              className="form-input"
              rows={8}
              placeholder="貼上職缺標題、工作內容、要求條件等資訊..."
              value={jobText}
              onChange={e => setJobText(e.target.value)}
              required
              style={{ resize: 'vertical', fontFamily: 'inherit' }}
            />
          </div>

          {/* CV */}
          <div className="form-group">
            <label className="form-label" htmlFor="rr-user-cv">
              <span className="form-label__icon">👤</span>
              原始履歷
              <span className="form-label__hint">資料儲存在本機；可上傳 PDF 自動填入</span>
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
              <input ref={cvFileRef} type="file" accept=".pdf" style={{ display: 'none' }} onChange={handleCvUpload} />
              <button type="button" className="btn-export" disabled={cvLoading} onClick={() => cvFileRef.current?.click()}>
                {cvLoading ? '解析中...' : '上傳 PDF 履歷'}
              </button>
              {cv && <span style={{ fontSize: '0.8rem', opacity: 0.6 }}>已填入 {cv.length} 字</span>}
            </div>
            {cvError && (
              <p style={{ color: 'var(--color-error, #f87171)', fontSize: '0.85rem', marginBottom: '0.4rem' }}>
                ⚠️ {cvError}
              </p>
            )}
            <textarea
              id="rr-user-cv"
              className="form-input"
              rows={6}
              placeholder="貼上或上傳你目前的履歷內容（必填）"
              value={cv}
              onChange={e => handleCvChange(e.target.value)}
              required
              style={{ resize: 'vertical', fontFamily: 'inherit' }}
            />
          </div>

          <button type="submit" className="btn-search" disabled={genLoading}>
            <span className="btn-search__text">
              {genLoading ? '生成中（兩版同時跑）...' : '📝 產生改寫履歷'}
            </span>
            <span className="btn-search__icon">→</span>
          </button>
        </form>
      </section>

      {genLoading && (
        <section className="loading">
          <div className="loading__spinner" />
          <p className="loading__text">AI 改寫中，請稍候...</p>
        </section>
      )}

      {genError && (
        <section className="error-card">
          <span className="error-card__icon">⚠️</span>
          <p className="error-card__text">{genError}</p>
          <button className="btn-dismiss" onClick={() => setGenError(null)}>關閉</button>
        </section>
      )}

      {(plainResult || structuredResult) && (
        <>
          {/* Plain result */}
          {plainResult?.plain_result && (
            <section className="search-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="ai-result__label" style={{ background: 'var(--color-tag-bg, rgba(99,102,241,0.15))', color: 'var(--color-tag-text, #818cf8)' }}>
                    版本 A｜整份純文字
                  </span>
                  <button
                    className="btn-export"
                    style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
                    onClick={() => navigate(`/resume-rewrites/${plainResult.id}`)}
                  >
                    詳情 →
                  </button>
                </div>
                <button
                  className="btn-export"
                  style={{ padding: '0.3rem 0.8rem', fontSize: '0.85rem' }}
                  onClick={() => handleCopy('plain', plainResult.plain_result ?? '')}
                >
                  {copiedKey === 'plain' ? '已複製 ✓' : '複製'}
                </button>
              </div>
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '0.9rem', lineHeight: 1.75, fontFamily: 'inherit', margin: 0 }}>
                {plainResult.plain_result}
              </pre>
            </section>
          )}

          {/* Structured result */}
          {structuredResult?.structured_result && (
            <section className="search-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="ai-result__label" style={{ background: 'var(--color-tag-bg, rgba(99,102,241,0.15))', color: 'var(--color-tag-text, #818cf8)' }}>
                    版本 B｜分段結構化
                  </span>
                  <button
                    className="btn-export"
                    style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
                    onClick={() => navigate(`/resume-rewrites/${structuredResult.id}`)}
                  >
                    詳情 →
                  </button>
                </div>
                <button
                  className="btn-export"
                  style={{ padding: '0.3rem 0.8rem', fontSize: '0.85rem' }}
                  onClick={() => handleCopy('structured', structuredText)}
                >
                  {copiedKey === 'structured' ? '已複製 ✓' : '複製全部'}
                </button>
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <h4 style={{ fontSize: '0.85rem', opacity: 0.7, margin: '0 0 0.4rem 0' }}>自我介紹</h4>
                <p style={{ fontSize: '0.9rem', lineHeight: 1.75, margin: 0 }}>
                  {structuredResult.structured_result.summary}
                </p>
              </div>

              {structuredResult.structured_result.experience.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <h4 style={{ fontSize: '0.85rem', opacity: 0.7, margin: '0 0 0.4rem 0' }}>工作經歷</h4>
                  <ul style={{ fontSize: '0.9rem', lineHeight: 1.7, margin: 0, paddingLeft: '1.2rem' }}>
                    {structuredResult.structured_result.experience.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}

              {structuredResult.structured_result.skills.length > 0 && (
                <div>
                  <h4 style={{ fontSize: '0.85rem', opacity: 0.7, margin: '0 0 0.4rem 0' }}>技能</h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {structuredResult.structured_result.skills.map((s, i) => (
                      <span
                        key={i}
                        style={{
                          fontSize: '0.82rem',
                          padding: '0.2rem 0.6rem',
                          borderRadius: '999px',
                          background: 'var(--color-tag-bg, rgba(99,102,241,0.15))',
                          color: 'var(--color-tag-text, #818cf8)',
                        }}
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  )
}
