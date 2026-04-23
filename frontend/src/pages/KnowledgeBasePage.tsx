import { useEffect, useState } from 'react'
import { createRagDocument, deleteRagDocument, fetchRagDocuments, extractCV } from '../api/client'
import type { RagDocumentResponse } from '../types'

export default function KnowledgeBasePage() {
  const [docs, setDocs] = useState<RagDocumentResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [docType, setDocType] = useState('project')
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [extracting, setExtracting] = useState(false)

  useEffect(() => {
    loadDocs()
  }, [])

  async function loadDocs() {
    setLoading(true)
    try {
      const data = await fetchRagDocuments()
      setDocs(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '載入失敗')
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd() {
    if (!content.trim()) return
    setSaving(true)
    setError(null)
    try {
      await createRagDocument({ doc_type: docType, content })
      setContent('')
      await loadDocs()
    } catch (e) {
      setError(e instanceof Error ? e.message : '新增失敗')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('確定刪除？')) return
    try {
      await deleteRagDocument(id)
      await loadDocs()
    } catch (e) {
      setError(e instanceof Error ? e.message : '刪除失敗')
    }
  }

  async function handleAutoExtract() {
    const cvText = localStorage.getItem('careerpilot_cv')
    if (!cvText || cvText.trim().length < 50) {
      setError('尚未設定履歷，或履歷內容過短。請先在左下角「設定履歷」中上傳 PDF。')
      return
    }
    if (!confirm('這將會透過 AI 自動解析您的履歷，並將專案與工作經歷匯入知識庫。可能需要幾十秒鐘，確定要執行嗎？')) return
    
    setExtracting(true)
    setError(null)
    try {
      const res = await extractCV(cvText)
      alert(`自動萃取完成！\n${res.message}`)
      await loadDocs()
    } catch (e) {
      setError(e instanceof Error ? e.message : '自動萃取失敗')
    } finally {
      setExtracting(false)
    }
  }

  return (
    <div className="container">
      <div className="page-intro">
        <h1 className="page-intro__title">個人知識庫 (RAG)</h1>
        <p className="page-intro__sub">管理您的專案經驗、歷史面試題庫等資料，以供 AI 面試與履歷解析使用。</p>
      </div>

      <section className="search-card" style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>新增資料</h2>
        <div className="form-group">
          <label className="form-label">資料類型</label>
          <select 
            className="form-input" 
            value={docType} 
            onChange={(e) => setDocType(e.target.value)}
          >
            <option value="project">個人專案經驗</option>
            <option value="experience">過往工作經歷</option>
            <option value="interview_question">歷史面試題庫</option>
            <option value="other">其他</option>
          </select>
        </div>
        <div className="form-group" style={{ marginTop: '1rem' }}>
          <label className="form-label">內容 (請提供詳盡描述以便 AI 精準比對)</label>
          <textarea
            className="form-input"
            rows={5}
            placeholder="請輸入資料內容..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </div>
        {error && <p style={{ color: 'var(--color-error)', margin: '1rem 0' }}>{error}</p>}
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <button 
            className="btn-search" 
            onClick={handleAdd} 
            disabled={saving || extracting || content.length < 10}
            style={{ flex: 1 }}
          >
            <span className="btn-search__text">{saving ? '新增中...' : '新增至知識庫'}</span>
          </button>
          
          <button 
            className="btn-search" 
            onClick={handleAutoExtract} 
            disabled={saving || extracting}
            style={{ flex: 1, background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
            title="從已上傳的履歷自動解析並建立專案與經歷檔案"
          >
            <span className="btn-search__text">{extracting ? 'AI 萃取中...' : '✨ 從履歷自動萃取'}</span>
          </button>
        </div>
      </section>

      <section className="search-card">
        <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>已存資料 ({docs.length})</h2>
        {loading ? (
          <p>載入中...</p>
        ) : docs.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)' }}>尚無資料。</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {docs.map(doc => (
              <div key={doc.id} className="result-card" style={{ padding: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ 
                    background: 'var(--bg-secondary)', 
                    padding: '0.2rem 0.6rem', 
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                  }}>
                    {doc.doc_type === 'project' ? '專案' : 
                     doc.doc_type === 'experience' ? '經歷' : 
                     doc.doc_type === 'interview_question' ? '面試題' : '其他'}
                  </span>
                  <button 
                    onClick={() => handleDelete(doc.id)}
                    style={{ background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer' }}
                  >
                    刪除
                  </button>
                </div>
                <p style={{ fontSize: '0.95rem', whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>
                  {doc.content}
                </p>
                <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  建立於 {doc.created_at}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
