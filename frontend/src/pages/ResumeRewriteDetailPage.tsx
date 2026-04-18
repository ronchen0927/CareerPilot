import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { fetchResumeRewrite } from '../api/client'
import type { ResumeRewriteRecord } from '../types'

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

  async function handleCopy() {
    if (!record) return
    await navigator.clipboard.writeText(record.result)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleDownloadPdf() {
    if (!record) return
    const win = window.open('', '_blank')
    if (!win) return
    const escaped = record.result.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    win.document.write(`<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>履歷改寫結果</title>
  <style>
    body { font-family: 'Noto Serif TC', 'Noto Serif', serif; line-height: 1.85; padding: 2.5cm 3cm; color: #1a1a1a; font-size: 12pt; }
    pre { white-space: pre-wrap; word-break: break-word; font-family: inherit; margin: 0; }
    @media print { body { padding: 1.5cm 2cm; } }
  </style>
</head>
<body>
  <pre>${escaped}</pre>
  <script>window.onload = function() { window.print(); }<\/script>
</body>
</html>`)
    win.document.close()
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
                  改寫結果
                </span>
                <span style={{ fontSize: '0.75rem', opacity: 0.5 }}>{record.created_at}</span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn-export" style={{ padding: '0.3rem 0.8rem', fontSize: '0.85rem' }} onClick={handleCopy}>
                  {copied ? '已複製 ✓' : '複製'}
                </button>
                <button className="btn-export" style={{ padding: '0.3rem 0.8rem', fontSize: '0.85rem' }} onClick={handleDownloadPdf}>
                  📥 下載 PDF
                </button>
              </div>
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '0.95rem', lineHeight: 1.75, fontFamily: 'inherit', margin: 0 }}>
              {record.result}
            </pre>
          </section>
        </>
      )}
    </div>
  )
}
