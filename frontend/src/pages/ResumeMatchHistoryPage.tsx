import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deleteResumeMatch, fetchResumeMatches } from '../api/client'
import type { ResumeMatchRecord } from '../types'

export default function ResumeMatchHistoryPage() {
  const [records, setRecords] = useState<ResumeMatchRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchResumeMatches()
      .then(setRecords)
      .catch(e => setError(e instanceof Error ? e.message : '載入失敗'))
      .finally(() => setLoading(false))
  }, [])

  async function handleDelete(e: React.MouseEvent, id: number) {
    e.stopPropagation()
    try {
      await deleteResumeMatch(id)
      setRecords(prev => prev.filter(r => r.id !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : '刪除失敗')
    }
  }

  return (
    <div className="container">
      <div className="page-intro">
        <h1 className="page-intro__title">履歷匹配歷史</h1>
        <p className="page-intro__sub">回顧過去的情境感知履歷解析記錄</p>
      </div>

      {loading && (
        <section className="loading">
          <div className="loading__spinner" />
          <p>載入中...</p>
        </section>
      )}

      {error && (
        <section className="error">
          <p>{error}</p>
        </section>
      )}

      {!loading && !error && records.length === 0 && (
        <section className="empty">
          <p>還沒有任何履歷匹配記錄</p>
        </section>
      )}

      {!loading && !error && records.length > 0 && (
        <section className="history-list">
          {records.map(record => (
            <article
              key={record.id}
              className="history-item"
              onClick={() => navigate(`/resume-match-history/${record.id}`)}
            >
              <div className="history-item__header">
                <div className="history-item__score">
                  <span className="score score--match">{record.match_score}%</span>
                  <span className="score-label">契合度</span>
                </div>
                <div className="history-item__meta">
                  <time className="history-item__date">
                    {new Date(record.created_at).toLocaleString('zh-TW')}
                  </time>
                  <button
                    className="btn-delete"
                    onClick={e => handleDelete(e, record.id)}
                    title="刪除記錄"
                  >
                    🗑️
                  </button>
                </div>
              </div>
              <div className="history-item__content">
                <h3 className="history-item__title">
                  {record.job_text.length > 100
                    ? `${record.job_text.substring(0, 100)}...`
                    : record.job_text}
                </h3>
                {record.job_url && (
                  <p className="history-item__url">
                    <a href={record.job_url} target="_blank" rel="noopener noreferrer">
                      {record.job_url}
                    </a>
                  </p>
                )}
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  )
}