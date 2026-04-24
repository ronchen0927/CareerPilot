import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteMockInterview, fetchMockInterviews } from '../api/client'
import type { MockInterviewRecord } from '../types'

export default function MockInterviewHistoryPage() {
  const [records, setRecords] = useState<MockInterviewRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRecords()
  }, [])

  async function loadRecords() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchMockInterviews()
      setRecords(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '載入失敗')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('確定刪除此紀錄？')) return
    try {
      await deleteMockInterview(id)
      await loadRecords()
    } catch (e) {
      alert('刪除失敗')
    }
  }

  if (loading) {
    return (
      <div className="container">
        <p>載入中...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container">
        <p style={{ color: 'var(--color-error)' }}>{error}</p>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="page-intro">
        <h1 className="page-intro__title">歷史模擬面試題庫</h1>
        <p className="page-intro__sub">管理與回顧之前由 AI 生成的面試題</p>
      </div>

      <div style={{ display: 'grid', gap: '1rem' }}>
        {records.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)' }}>尚無歷史紀錄。</p>
        ) : (
          records.map(record => (
            <div key={record.id} className="search-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <h3 style={{ fontSize: '1.1rem', margin: 0, color: 'var(--text-primary)' }}>
                  紀錄 #{record.id}
                </h3>
                <button 
                  onClick={() => handleDelete(record.id)}
                  style={{ background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer', fontSize: '0.9rem' }}
                >
                  刪除
                </button>
              </div>
              <p style={{ 
                fontSize: '0.9rem', 
                color: 'var(--text-secondary)',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden'
              }}>
                {record.job_text}
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {record.created_at}
                </span>
                <Link to={`/mock-interviews/${record.id}`} className="btn-search" style={{ padding: '0.3rem 1rem', fontSize: '0.9rem', width: 'auto' }}>
                  查看詳情 →
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
