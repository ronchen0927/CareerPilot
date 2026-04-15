import { useEffect, useState } from 'react'
import { deleteEvaluation, fetchEvaluations } from '../api/client'
import type { EvaluationRecord } from '../types'

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

export default function HistoryPage() {
  const [records, setRecords] = useState<EvaluationRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  useEffect(() => {
    fetchEvaluations()
      .then(setRecords)
      .catch(e => setError(e instanceof Error ? e.message : '載入失敗'))
      .finally(() => setLoading(false))
  }, [])

  function toggleExpand(id: number) {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  async function handleDelete(id: number) {
    try {
      await deleteEvaluation(id)
      setRecords(prev => prev.filter(r => r.id !== id))
    } catch (e) {
      alert(e instanceof Error ? e.message : '刪除失敗')
    }
  }

  return (
    <div className="container">
      <header className="header">
        <div className="header__logo">
          <span className="header__icon">📜</span>
          <h1 className="header__title">評分歷史</h1>
        </div>
        <p className="header__subtitle">回顧過去的 AI 評分，思考面試策略</p>
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
          <p style={{ padding: '2rem 0' }}>還沒有評分紀錄，去 <a href="/evaluate">AI 職缺評分</a> 頁面評估看看吧！</p>
        </section>
      )}

      {records.map(r => (
        <section key={r.id} className="search-card" style={{ marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            {/* Score badge */}
            <span
              className={`ai-score ${getScoreClass(r.score)}`}
              style={{ flexShrink: 0, cursor: 'default' }}
            >
              {r.score}
            </span>

            {/* Main content */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span className="ai-result__summary" style={{ fontWeight: 500 }}>{r.summary}</span>
                <span style={{ fontSize: '0.75rem', opacity: 0.5, whiteSpace: 'nowrap' }}>
                  {r.created_at}
                </span>
              </div>
              <p style={{
                fontSize: '0.82rem',
                opacity: 0.65,
                marginTop: '0.25rem',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {r.job_url
                  ? <a href={r.job_url} target="_blank" rel="noopener noreferrer">{r.job_text_snippet}</a>
                  : r.job_text_snippet
                }
              </p>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '0.4rem', flexShrink: 0 }}>
              <button
                className="btn-export"
                style={{ padding: '0.3rem 0.7rem', fontSize: '0.8rem' }}
                onClick={() => toggleExpand(r.id)}
              >
                {expanded.has(r.id) ? '收起' : '展開'}
              </button>
              <button
                className="btn-export"
                style={{ padding: '0.3rem 0.7rem', fontSize: '0.8rem', color: 'var(--color-error, #f87171)' }}
                onClick={() => handleDelete(r.id)}
              >
                刪除
              </button>
            </div>
          </div>

          {/* Expanded detail */}
          {expanded.has(r.id) && (
            <div className="ai-result__body" style={{ marginTop: '0.75rem', borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem' }}>
              <div className="ai-result__section">
                <span className="ai-result__label" style={{ background: 'var(--color-tag-bg, rgba(99,102,241,0.15))', color: 'var(--color-tag-text, #818cf8)' }}>職缺描述</span>
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontSize: '0.82rem',
                  opacity: 0.8,
                  margin: '0.4rem 0 0.75rem',
                  fontFamily: 'inherit',
                  maxHeight: '12rem',
                  overflowY: 'auto',
                  background: 'var(--color-card-bg, rgba(255,255,255,0.03))',
                  padding: '0.6rem',
                  borderRadius: '0.4rem',
                }}>
                  {r.job_text}
                </pre>
              </div>
              {r.match_points.length > 0 && (
                <div className="ai-result__section">
                  <span className="ai-result__label ai-result__label--match">優勢</span>
                  <ul className="ai-result__list ai-result__list--match">
                    {r.match_points.map((p, i) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
              )}
              {r.gap_points.length > 0 && (
                <div className="ai-result__section">
                  <span className="ai-result__label ai-result__label--gap">落差</span>
                  <ul className="ai-result__list ai-result__list--gap">
                    {r.gap_points.map((p, i) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
              )}
              <p className="ai-result__rec">{r.recommendation}</p>
            </div>
          )}
        </section>
      ))}
    </div>
  )
}
