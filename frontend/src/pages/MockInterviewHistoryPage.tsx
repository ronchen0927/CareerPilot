import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteMockInterview, fetchMockInterviews } from '../api/client'
import type { MockInterviewRecord } from '../types'

const LABEL_KEY = (id: number) => `mock_interview_label_${id}`

function getLabel(id: number): string {
  return localStorage.getItem(LABEL_KEY(id)) ?? `紀錄 #${id}`
}

function saveLabel(id: number, label: string) {
  const trimmed = label.trim()
  if (trimmed) localStorage.setItem(LABEL_KEY(id), trimmed)
  else localStorage.removeItem(LABEL_KEY(id))
}

export default function MockInterviewHistoryPage() {
  const [records, setRecords] = useState<MockInterviewRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')
  const [labels, setLabels] = useState<Record<number, string>>({})
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { loadRecords() }, [])

  useEffect(() => {
    if (editingId !== null) inputRef.current?.focus()
  }, [editingId])

  async function loadRecords() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchMockInterviews()
      setRecords(data)
      const map: Record<number, string> = {}
      data.forEach(r => { map[r.id] = getLabel(r.id) })
      setLabels(map)
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

  function startEdit(e: React.MouseEvent, id: number) {
    e.preventDefault()
    e.stopPropagation()
    setEditingId(id)
    setEditValue(labels[id] ?? getLabel(id))
  }

  function commitEdit(id: number) {
    saveLabel(id, editValue)
    setLabels(prev => ({ ...prev, [id]: editValue.trim() || `紀錄 #${id}` }))
    setEditingId(null)
  }

  if (loading) return <div className="container"><p>載入中...</p></div>
  if (error) return <div className="container"><p style={{ color: 'var(--color-error)' }}>{error}</p></div>

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
                {editingId === record.id ? (
                  <input
                    ref={inputRef}
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    onBlur={() => commitEdit(record.id)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') commitEdit(record.id)
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    onClick={e => e.stopPropagation()}
                    style={{
                      fontSize: '1.1rem',
                      fontWeight: 600,
                      border: 'none',
                      borderBottom: '2px solid var(--color-primary)',
                      background: 'transparent',
                      color: 'var(--text-primary)',
                      outline: 'none',
                      flex: 1,
                      marginRight: '1rem',
                    }}
                  />
                ) : (
                  <h3
                    onClick={e => startEdit(e, record.id)}
                    title="點擊編輯標題"
                    style={{ fontSize: '1.1rem', margin: 0, color: 'var(--text-primary)', cursor: 'text' }}
                  >
                    {labels[record.id] ?? getLabel(record.id)}
                  </h3>
                )}
                <button
                  onClick={() => handleDelete(record.id)}
                  style={{ background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer', fontSize: '0.9rem', flexShrink: 0 }}
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
                overflow: 'hidden',
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
