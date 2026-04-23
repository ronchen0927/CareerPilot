import { useLocation } from 'react-router-dom'
import { fetchJobUrl, generateMockInterview, generateResumeMatch } from '../api/client'
import type { MockInterviewResponse, ResumeMatchResponse } from '../types'

export default function InterviewPrepPage() {
  const location = useLocation()
  const locState = location.state as { job_text?: string; job_url?: string } | null

  const [jobUrl, setJobUrl] = useState(locState?.job_url ?? '')
  const [jobText, setJobText] = useState(locState?.job_text ?? '')
  const [cvText, setCvText] = useState(() => localStorage.getItem('careerpilot_cv') ?? '')
  
  const [fetchLoading, setFetchLoading] = useState(false)
  
  const [loadingMock, setLoadingMock] = useState(false)
  const [mockResult, setMockResult] = useState<MockInterviewResponse | null>(null)
  
  const [loadingMatch, setLoadingMatch] = useState(false)
  const [matchResult, setMatchResult] = useState<ResumeMatchResponse | null>(null)
  
  const [error, setError] = useState<string | null>(null)

  async function handleFetchUrl() {
    if (!jobUrl.trim()) return
    setFetchLoading(true)
    setError(null)
    try {
      const data = await fetchJobUrl(jobUrl.trim())
      setJobText(data.text)
    } catch (err) {
      setError(err instanceof Error ? err.message : '頁面擷取失敗')
    } finally {
      setFetchLoading(false)
    }
  }

  async function handleGenerateMockInterview() {
    if (!jobText.trim()) {
      setError('請輸入目標職缺描述')
      return
    }
    setLoadingMock(true)
    setError(null)
    setMockResult(null)
    try {
      const res = await generateMockInterview({ job_text: jobText })
      setMockResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成失敗')
    } finally {
      setLoadingMock(false)
    }
  }

  async function handleGenerateResumeMatch() {
    if (!jobText.trim()) {
      setError('請輸入目標職缺描述')
      return
    }
    setLoadingMatch(true)
    setError(null)
    setMatchResult(null)
    try {
      const res = await generateResumeMatch({ job_text: jobText, user_cv: cvText })
      setMatchResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : '比對失敗')
    } finally {
      setLoadingMatch(false)
    }
  }

  return (
    <div className="container">
      <div className="page-intro">
        <h1 className="page-intro__title">AI 面試與履歷比對</h1>
        <p className="page-intro__sub">基於 RAG 架構與個人知識庫，動態生成模擬面試題，並精準比對您的經驗與特定職缺。</p>
      </div>

      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 400px' }}>
          <section className="search-card">
            <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>輸入資料</h2>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label" htmlFor="job-url">
                職缺網址（選填）
                <span className="form-label__hint">自動從網址擷取，或從我的收藏匯入</span>
              </label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="url"
                  id="job-url"
                  className="form-input"
                  placeholder="https://www.104.com.tw/job/..."
                  value={jobUrl}
                  onChange={e => setJobUrl(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn-search"
                  style={{ width: 'auto', padding: '0 1.2rem' }}
                  disabled={fetchLoading || !jobUrl.trim()}
                  onClick={handleFetchUrl}
                >
                  {fetchLoading ? '擷取中...' : '擷取'}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">目標職缺描述 (JD)</label>
              <textarea
                className="form-input"
                rows={8}
                placeholder="請貼上完整的職缺描述..."
                value={jobText}
                onChange={(e) => setJobText(e.target.value)}
              />
            </div>
            
            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label className="form-label">您的履歷 (已從設定載入)</label>
              <textarea
                className="form-input"
                rows={4}
                placeholder="如需更新履歷，請前往設定或在此編輯..."
                value={cvText}
                onChange={(e) => {
                  setCvText(e.target.value)
                  localStorage.setItem('careerpilot_cv', e.target.value)
                }}
              />
            </div>

            {error && <p style={{ color: 'var(--color-error)', margin: '1rem 0' }}>{error}</p>}

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
              <button 
                className="btn-search" 
                style={{ flex: 1, background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                onClick={handleGenerateResumeMatch}
                disabled={loadingMatch || loadingMock}
              >
                <span className="btn-search__text">{loadingMatch ? '比對中...' : '情境感知履歷解析'}</span>
              </button>
              <button 
                className="btn-search" 
                style={{ flex: 1 }}
                onClick={handleGenerateMockInterview}
                disabled={loadingMatch || loadingMock}
              >
                <span className="btn-search__text">{loadingMock ? '生成中...' : 'AI 模擬面試系統'}</span>
              </button>
            </div>
          </section>
        </div>

        <div style={{ flex: '1 1 400px' }}>
          {matchResult && (
            <section className="search-card" style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>
                履歷解析結果 (契合度: {matchResult.match_score}%)
              </h2>
              <div style={{ marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>能力缺口分析</h3>
                <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
                  {matchResult.gap_analysis}
                </p>
              </div>
              <div>
                <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>答題與彌補策略</h3>
                <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
                  {matchResult.answer_strategy}
                </p>
              </div>
            </section>
          )}

          {mockResult && (
            <section className="search-card">
              <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>
                模擬面試題庫
              </h2>
              <div style={{ marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>技術面試題</h3>
                <ul style={{ paddingLeft: '1.2rem', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                  {mockResult.technical_questions.map((q, i) => (
                    <li key={i} style={{ marginBottom: '0.3rem' }}>{q}</li>
                  ))}
                </ul>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>行為面試題</h3>
                <ul style={{ paddingLeft: '1.2rem', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                  {mockResult.behavioral_questions.map((q, i) => (
                    <li key={i} style={{ marginBottom: '0.3rem' }}>{q}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>準備建議</h3>
                <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
                  {mockResult.tips}
                </p>
              </div>
            </section>
          )}

          {!matchResult && !mockResult && !loadingMatch && !loadingMock && (
            <section className="search-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px', color: 'var(--text-secondary)' }}>
              請輸入職缺描述並點擊左側按鈕以產生分析或面試題。
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
