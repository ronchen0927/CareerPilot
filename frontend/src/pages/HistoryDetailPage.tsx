import { useEffect, useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { fetchEvaluation } from '../api/client'
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

export default function HistoryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { state } = useLocation()
  const navigate = useNavigate()

  const [record, setRecord] = useState<EvaluationRecord | null>(state ?? null)
  const [loading, setLoading] = useState(!state)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (state) return
    fetchEvaluation(Number(id))
      .then(setRecord)
      .catch(e => setError(e instanceof Error ? e.message : '載入失敗'))
      .finally(() => setLoading(false))
  }, [id, state])

  return (
    <div className="container">
      <header className="header">
        <div className="header__logo">
          <button
            className="btn-export"
            style={{ marginRight: '0.75rem', padding: '0.3rem 0.8rem' }}
            onClick={() => navigate('/history')}
          >
            ← 返回
          </button>
          <span className="header__icon">📜</span>
          <h1 className="header__title">評分詳情</h1>
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
                <a
                  href={record.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: '0.8rem', opacity: 0.7 }}
                >
                  開啟原始連結 ↗
                </a>
              )}
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

          {/* AI Result */}
          <section className="search-card">
            <div className="ai-result">
              <div className="ai-result__header">
                <span className={`ai-score ${getScoreClass(record.score)}`}>{record.score}</span>
                <span className="ai-result__summary">{record.summary}</span>
                <span style={{ fontSize: '0.75rem', opacity: 0.5, marginLeft: 'auto', whiteSpace: 'nowrap' }}>
                  {record.created_at}
                </span>
              </div>

              {(record.match_points.length > 0 || record.gap_points.length > 0) && (
                <div className="ai-result__body">
                  {record.match_points.length > 0 && (
                    <div className="ai-result__section">
                      <span className="ai-result__label ai-result__label--match">優勢</span>
                      <ul className="ai-result__list ai-result__list--match">
                        {record.match_points.map((p, i) => <li key={i}>{p}</li>)}
                      </ul>
                    </div>
                  )}
                  {record.gap_points.length > 0 && (
                    <div className="ai-result__section">
                      <span className="ai-result__label ai-result__label--gap">落差</span>
                      <ul className="ai-result__list ai-result__list--gap">
                        {record.gap_points.map((p, i) => <li key={i}>{p}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <p className="ai-result__rec">{record.recommendation}</p>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
