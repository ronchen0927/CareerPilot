import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
  const navigate = useNavigate()

  useEffect(() => {
    fetchEvaluations()
      .then(setRecords)
      .catch(e => setError(e instanceof Error ? e.message : '載入失敗'))
      .finally(() => setLoading(false))
  }, [])

  async function handleDelete(e: React.MouseEvent, id: number) {
    e.stopPropagation()
    try {
      await deleteEvaluation(id)
      setRecords(prev => prev.filter(r => r.id !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : '刪除失敗')
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
          <p style={{ padding: '2rem 0' }}>
            還沒有評分紀錄，去 <a href="/evaluate">AI 職缺評分</a> 頁面評估看看吧！
          </p>
        </section>
      )}

      {records.map(r => (
        <section
          key={r.id}
          className="search-card"
          style={{ marginBottom: '0.75rem', cursor: 'pointer' }}
          onClick={() => navigate(`/history/${r.id}`, { state: r })}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <span className={`ai-score ${getScoreClass(r.score)}`} style={{ flexShrink: 0 }}>
              {r.score}
            </span>

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
                {r.job_text_snippet}
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
