import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchMockInterviewDetail } from '../api/client'
import type { MockInterviewRecord } from '../types'

export default function MockInterviewDetailPage() {
  const { id } = useParams()
  const [record, setRecord] = useState<MockInterviewRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    loadRecord(parseInt(id, 10))
  }, [id])

  async function loadRecord(recordId: number) {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchMockInterviewDetail(recordId)
      setRecord(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '載入詳情失敗')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="container"><p>載入中...</p></div>
  }

  if (error || !record) {
    return (
      <div className="container">
        <p style={{ color: 'var(--color-error)' }}>{error ?? '找不到紀錄'}</p>
        <Link to="/mock-interviews" style={{ color: 'var(--color-primary)' }}>返回列表</Link>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="page-intro" style={{ marginBottom: '1rem' }}>
        <Link to="/mock-interviews" style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', textDecoration: 'none', marginBottom: '0.5rem', display: 'inline-block' }}>
          ← 返回列表
        </Link>
        <h1 className="page-intro__title" style={{ marginTop: '0.5rem' }}>模擬面試紀錄 #{record.id}</h1>
        <p className="page-intro__sub">{record.created_at}</p>
      </div>

      <div style={{ display: 'grid', gap: '1.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
        <section className="search-card">
          <h2 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>目標職缺 (JD)</h2>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem', color: 'var(--text-secondary)', fontFamily: 'inherit', margin: 0 }}>
            {record.job_text}
          </pre>
        </section>

        <section className="search-card">
          <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>
            模擬面試題庫
          </h2>
          <div style={{ marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>技術面試題</h3>
            <ul style={{ paddingLeft: '1.2rem', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              {record.technical_questions.map((q, i) => (
                <li key={i} style={{ marginBottom: '0.3rem' }}>{q}</li>
              ))}
            </ul>
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>行為面試題</h3>
            <ul style={{ paddingLeft: '1.2rem', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              {record.behavioral_questions.map((q, i) => (
                <li key={i} style={{ marginBottom: '0.3rem' }}>{q}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>準備建議</h3>
            <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
              {record.tips}
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}
