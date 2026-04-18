import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { fetchResumeRewrite } from '../api/client'
import type { ResumeRewriteRecord } from '../types'

const MODE_LABEL: Record<string, string> = {
  plain: '整份純文字',
  structured: '分段結構化',
}

export default function ResumeRewriteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { state } = useLocation()
  const navigate = useNavigate()

  const [record, setRecord] = useState<ResumeRewriteRecord | null>(state ?? null)
  const [loading, setLoading] = useState(!state)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (state) return
    fetchResumeRewrite(Number(id))
      .then(setRecord)
      .catch(e => setError(e instanceof Error ? e.message : '載入失敗'))
      .finally(() => setLoading(false))
  }, [id, state])

  function toCopyText(r: ResumeRewriteRecord): string {
    if (r.plain_result) return r.plain_result
    if (r.structured_result) {
      return [
        r.structured_result.summary,
        '',
        '【工作經歷】',
        ...r.structured_result.experience.map(e => `• ${e}`),
        '',
        '【技能】',
        r.structured_result.skills.join('、'),
      ].join('\n')
    }
    return ''
  }

  async function handleCopy() {
    if (!record) return
    await navigator.clipboard.writeText(toCopyText(record))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="container">
      <header className="header">
        <div className="header__logo">
          <button
            className="btn-export"
            style={{ marginRight: '0.75rem', padding: '0.3rem 0.8rem' }}
            onClick={() => navigate('/resume-rewrites')}
          >
            ← 返回
          </button>
          <span className="header__icon">📝</span>
          <h1 className="header__title">履歷改寫詳情</h1>
        </div>
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

      {record && (
        <>
          {/* Job description */}
          <section className="search-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <span className="ai-result__label" style={{ background: 'var(--color-tag-bg, rgba(99,102,241,0.15))', color: 'var(--color-tag-text, #818cf8)' }}>
                職缺描述
              </span>
              {record.job_url && (
                <a href={record.job_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.8rem', opacity: 0.7 }}>
                  開啟原始連結 ↗
                </a>
              )}
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '0.85rem', lineHeight: 1.65, fontFamily: 'inherit', margin: 0 }}>
              {record.job_text}
            </pre>
          </section>

          {/* Original CV */}
          <section className="search-card">
            <div style={{ marginBottom: '0.75rem' }}>
              <span className="ai-result__label" style={{ background: 'var(--color-tag-bg, rgba(99,102,241,0.15))', color: 'var(--color-tag-text, #818cf8)' }}>
                原始履歷
              </span>
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '0.85rem', lineHeight: 1.65, fontFamily: 'inherit', margin: 0 }}>
              {record.original_cv}
            </pre>
          </section>

          {/* Rewritten result */}
          <section className="search-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="ai-result__label" style={{ background: 'var(--color-tag-bg, rgba(99,102,241,0.15))', color: 'var(--color-tag-text, #818cf8)' }}>
                  改寫結果｜{MODE_LABEL[record.mode] ?? record.mode}
                </span>
                <span style={{ fontSize: '0.75rem', opacity: 0.5 }}>{record.created_at}</span>
              </div>
              <button className="btn-export" style={{ padding: '0.3rem 0.8rem', fontSize: '0.85rem' }} onClick={handleCopy}>
                {copied ? '已複製 ✓' : '複製'}
              </button>
            </div>

            {record.plain_result && (
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '0.95rem', lineHeight: 1.75, fontFamily: 'inherit', margin: 0 }}>
                {record.plain_result}
              </pre>
            )}

            {record.structured_result && (
              <>
                <div style={{ marginBottom: '1rem' }}>
                  <h4 style={{ fontSize: '0.85rem', opacity: 0.7, margin: '0 0 0.4rem 0' }}>自我介紹</h4>
                  <p style={{ fontSize: '0.95rem', lineHeight: 1.75, margin: 0 }}>
                    {record.structured_result.summary}
                  </p>
                </div>

                {record.structured_result.experience.length > 0 && (
                  <div style={{ marginBottom: '1rem' }}>
                    <h4 style={{ fontSize: '0.85rem', opacity: 0.7, margin: '0 0 0.4rem 0' }}>工作經歷</h4>
                    <ul style={{ fontSize: '0.95rem', lineHeight: 1.75, margin: 0, paddingLeft: '1.2rem' }}>
                      {record.structured_result.experience.map((e, i) => (
                        <li key={i}>{e}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {record.structured_result.skills.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: '0.85rem', opacity: 0.7, margin: '0 0 0.4rem 0' }}>技能</h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                      {record.structured_result.skills.map((s, i) => (
                        <span
                          key={i}
                          style={{
                            fontSize: '0.85rem',
                            padding: '0.25rem 0.7rem',
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
              </>
            )}
          </section>
        </>
      )}
    </div>
  )
}
