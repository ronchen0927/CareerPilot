import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deleteResumeRewrite, fetchResumeRewrites } from '../api/client'
import type { ResumeRewriteRecord } from '../types'

const MODE_LABEL: Record<string, string> = {
  plain: '整份純文字',
  structured: '分段結構化',
}

export default function ResumeRewriteHistoryPage() {
  const [records, setRecords] = useState<ResumeRewriteRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchResumeRewrites()
      .then(setRecords)
      .catch(e => setError(e instanceof Error ? e.message : '載入失敗'))
      .finally(() => setLoading(false))
  }, [])

  async function handleDelete(e: React.MouseEvent, id: number) {
    e.stopPropagation()
    try {
      await deleteResumeRewrite(id)
      setRecords(prev => prev.filter(r => r.id !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : '刪除失敗')
    }
  }

  function preview(r: ResumeRewriteRecord): string {
    if (r.plain_result) return r.plain_result.slice(0, 60)
    if (r.structured_result) return r.structured_result.summary.slice(0, 60)
    return ''
  }

  return (
    <div className="container">
      <header className="header">
        <div className="header__logo">
          <span className="header__icon">🗂️</span>
          <h1 className="header__title">履歷改寫歷史</h1>
        </div>
        <p className="header__subtitle">過去針對不同職缺的履歷改寫紀錄</p>
      </header>

      {loading && (
        <section className="loading">
          <div className="loading__spinner" />
          <p className="loading__text">載入中...</p>
        </section>
      )}

      {error && (
        <section className="error-card">
          <span className="error-card__icon">⚠️</span>
          <p className="error-card__text">{error}</p>
        </section>
      )}

      {!loading && !error && records.length === 0 && (
        <section className="search-card" style={{ textAlign: 'center', color: 'var(--color-muted)' }}>
          <p style={{ padding: '2rem 0' }}>
            還沒有紀錄，去 <a href="/resume-rewrite">AI 履歷改寫</a> 頁面試試看！
          </p>
        </section>
      )}

      {records.map(r => (
        <section
          key={r.id}
          className="search-card"
          style={{ marginBottom: '0.75rem', cursor: 'pointer' }}
          onClick={() => navigate(`/resume-rewrites/${r.id}`, { state: r })}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.4rem', flexShrink: 0 }}>📝</span>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 500 }}>{r.job_text_snippet}…</span>
                <span
                  style={{
                    fontSize: '0.7rem',
                    padding: '0.1rem 0.5rem',
                    borderRadius: '999px',
                    background: 'var(--color-tag-bg, rgba(99,102,241,0.15))',
                    color: 'var(--color-tag-text, #818cf8)',
                  }}
                >
                  {MODE_LABEL[r.mode] ?? r.mode}
                </span>
                <span style={{ fontSize: '0.75rem', opacity: 0.5, whiteSpace: 'nowrap' }}>{r.created_at}</span>
              </div>
              <p
                style={{
                  fontSize: '0.82rem',
                  opacity: 0.6,
                  marginTop: '0.25rem',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {preview(r)}…
              </p>
            </div>

            <button
              className="btn-export"
              style={{ padding: '0.3rem 0.7rem', fontSize: '0.8rem', color: 'var(--color-error, #f87171)', flexShrink: 0 }}
              onClick={e => handleDelete(e, r.id)}
            >
              刪除
            </button>
          </div>
        </section>
      ))}
    </div>
  )
}
