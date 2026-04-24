import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchResumeMatches } from '../api/client'
import type { ResumeMatchRecord } from '../types'

export default function ResumeMatchDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [record, setRecord] = useState<ResumeMatchRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!id) return
    fetchResumeMatches()
      .then(records => {
        const found = records.find(r => r.id === parseInt(id))
        if (found) {
          setRecord(found)
        } else {
          setError('記錄不存在')
        }
      })
      .catch(e => setError(e instanceof Error ? e.message : '載入失敗'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="container">
        <section className="loading">
          <div className="loading__spinner" />
          <p>載入中...</p>
        </section>
      </div>
    )
  }

  if (error || !record) {
    return (
      <div className="container">
        <section className="error">
          <p>{error || '記錄不存在'}</p>
          <button className="btn-search" onClick={() => navigate('/resume-match-history')}>
            返回歷史記錄
          </button>
        </section>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="page-intro">
        <h1 className="page-intro__title">履歷匹配詳情</h1>
        <p className="page-intro__sub">
          分析時間：{new Date(record.created_at).toLocaleString('zh-TW')}
        </p>
      </div>

      <section className="search-card">
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>
            職缺描述
          </h2>
          <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
            {record.job_text}
          </p>
          {record.job_url && (
            <p style={{ marginTop: '0.5rem' }}>
              <a href={record.job_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-primary)' }}>
                查看原始職缺
              </a>
            </p>
          )}
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>
            履歷內容
          </h2>
          <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
            {record.user_cv}
          </p>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '0.5rem', color: 'var(--color-primary)' }}>
            契合度分析 ({record.match_score}%)
          </h2>
          <div style={{ marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>能力缺口分析</h3>
            <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
              {record.gap_analysis}
            </p>
          </div>
          <div>
            <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>答題與彌補策略</h3>
            <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
              {record.answer_strategy}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="btn-search" onClick={() => navigate('/interview-prep')}>
            返回面試準備
          </button>
          <button className="btn-search" onClick={() => navigate('/resume-match-history')}>
            查看所有歷史
          </button>
        </div>
      </section>
    </div>
  )
}