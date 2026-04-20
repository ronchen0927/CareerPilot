import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { fetchCoverLetter } from '../api/client'
import type { CoverLetterRecord } from '../types'

export default function CoverLetterDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { state } = useLocation()
  const navigate = useNavigate()

  const [record, setRecord] = useState<CoverLetterRecord | null>(state ?? null)
  const [loading, setLoading] = useState(!state)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (state) return
    fetchCoverLetter(Number(id))
      .then(setRecord)
      .catch(e => setError(e instanceof Error ? e.message : '載入失敗'))
      .finally(() => setLoading(false))
  }, [id, state])

  async function handleCopy() {
    if (!record) return
    await navigator.clipboard.writeText(record.letter)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="container">
      <div className="page-intro">
        <h1 className="page-intro__title">推薦信詳情</h1>
      </div>

      {loading && (
        <section className="loading">
          <div className="loading__spinner" />
          <p className="loading__text">載入中...</p>
        </section>
      )}

      {error && (
        <section className="error-card">
          <p className="error-card__text">{error}</p>
        </section>
      )}

      {record && (
        <>
          {/* Job description */}
          <section className="search-card">
            <div style={{ marginBottom: '0.75rem' }}>
              <span className="ai-result__label" style={{ background: 'var(--color-tag-bg, rgba(99,102,241,0.15))', color: 'var(--color-tag-text, #818cf8)' }}>
                職缺描述
              </span>
            </div>
            <pre style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: '0.85rem',
              lineHeight: 1.65,
              fontFamily: 'inherit',
              margin: 0,
            }}>
              {record.job_text}
            </pre>
          </section>

          {/* Cover letter */}
          <section className="search-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="ai-result__label" style={{ background: 'var(--color-tag-bg, rgba(99,102,241,0.15))', color: 'var(--color-tag-text, #818cf8)' }}>
                  推薦信
                </span>
                <span style={{ fontSize: '0.75rem', opacity: 0.5 }}>{record.created_at}</span>
              </div>
              <button
                className="btn-export"
                style={{ padding: '0.3rem 0.8rem', fontSize: '0.85rem' }}
                onClick={handleCopy}
              >
                {copied ? '已複製 ✓' : '複製'}
              </button>
            </div>
            <pre style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: '0.95rem',
              lineHeight: 1.75,
              fontFamily: 'inherit',
              margin: 0,
            }}>
              {record.letter}
            </pre>
          </section>
        </>
      )}
    </div>
  )
}
