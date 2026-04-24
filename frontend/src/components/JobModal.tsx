import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { evaluateJob, fetchJobUrl } from '../api/client'
import DimensionsPanel from './DimensionsPanel'
import JobChat from './JobChat'
import { formatPrefsForPrompt, usePreferences } from '../hooks/usePreferences'
import type { BookmarkStatus, JobEvaluateResponse, JobListing } from '../types'

interface Props {
  job: JobListing
  onClose: () => void
  bookmarkStatus?: BookmarkStatus
}

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

export default function JobModal({ job, onClose, bookmarkStatus }: Props) {
  const [evalResult, setEvalResult] = useState<JobEvaluateResponse | null>(null)
  const [evalLoading, setEvalLoading] = useState(false)
  const [evalError, setEvalError] = useState<string | null>(null)
  const [jobContent, setJobContent] = useState<string | null>(null)
  const navigate = useNavigate()
  const [prefs] = usePreferences()

  function navigateWithJobContent(route: string) {
    const metadataText = [
      `職位：${job.job}`,
      `公司：${job.company}`,
      `城市：${job.city}`,
      `經歷要求：${job.experience}`,
      `最低學歷：${job.education}`,
      `薪水：${job.salary}`,
    ].join('\n')
    navigate(route, { state: { job_text: jobContent ?? metadataText, job_url: job.link } })
    onClose()
  }

  function handleRewriteResume() {
    navigateWithJobContent('/resume-rewrite')
  }

  function handleCoverLetter() {
    navigateWithJobContent('/cover-letter')
  }

  function handleInterviewPrep() {
    navigateWithJobContent('/interview-prep')
  }

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', handleKey)
    }
  }, [onClose])

  useEffect(() => {
    if (!job.link) return
    fetchJobUrl(job.link)
      .then(({ text }) => setJobContent(text))
      .catch(() => {})
  }, [job.link])

  async function handleEvaluate() {
    setEvalLoading(true)
    setEvalError(null)
    try {
      const cv = localStorage.getItem('careerpilot_cv') ?? ''
      const result = await evaluateJob({
        job,
        user_cv: cv + formatPrefsForPrompt(prefs),
        job_description: jobContent ?? '',
      })
      setEvalResult(result)
    } catch (err) {
      setEvalError(err instanceof Error ? err.message : '評分失敗')
    } finally {
      setEvalLoading(false)
    }
  }

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-job"
      onClick={e => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="modal">
        <button className="modal__close" aria-label="關閉" onClick={onClose}>
          ✕
        </button>
        <h3 id="modal-job" className="modal__title">
          {job.job}
        </h3>

        <div className="modal__grid">
          <div className="modal__field">
            <span className="modal__label">公司</span>
            <span className="modal__value">{job.company}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">城市</span>
            <span className="modal__value">{job.city}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">刊登日期</span>
            <span className="modal__value">{job.is_featured ? '精選職缺' : job.date}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">經歷要求</span>
            <span className="modal__value">{job.experience}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">最低學歷</span>
            <span className="modal__value">{job.education}</span>
          </div>
          <div className="modal__field">
            <span className="modal__label">薪水</span>
            <span className="modal__value modal__value--salary">{job.salary}</span>
          </div>
        </div>

        <a
          href={job.link}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-goto"
        >
          前往查看完整詳情 →
        </a>

        <button
          type="button"
          className="btn-export"
          style={{ marginTop: '0.6rem', width: '100%' }}
          onClick={handleRewriteResume}
        >
          ✍️ 針對此職缺改寫履歷
        </button>

        {bookmarkStatus === '想投' && (
          <button
            type="button"
            className="btn-export"
            style={{ marginTop: '0.4rem', width: '100%' }}
            onClick={handleCoverLetter}
          >
            ✉️ 產生 AI 推薦信
          </button>
        )}

        <button
          type="button"
          className="btn-export"
          style={{ marginTop: '0.4rem', width: '100%' }}
          onClick={handleInterviewPrep}
        >
          🗣️ AI 面試與履歷解析
        </button>

        <div className="modal__ai-section">
          <button className="btn-evaluate" disabled={evalLoading} onClick={handleEvaluate}>
            {evalLoading ? '評分中...' : evalResult ? '✨ 重新評分' : '✨ AI 評分'}
          </button>

          {evalError && (
            <div className="ai-result">
              <p className="ai-result__error">評分失敗：{evalError}</p>
            </div>
          )}

          {evalResult && !evalError && (
            <div className="ai-result">
              <div className="ai-result__header">
                <span className={`ai-score ${getScoreClass(evalResult.score)}`}>
                  {evalResult.score}
                </span>
                <span className="ai-result__summary">{evalResult.summary}</span>
              </div>
              {(evalResult.match_points.length > 0 || evalResult.gap_points.length > 0) && (
                <div className="ai-result__body">
                  {evalResult.match_points.length > 0 && (
                    <div className="ai-result__section">
                      <span className="ai-result__label ai-result__label--match">優勢</span>
                      <ul className="ai-result__list ai-result__list--match">
                        {evalResult.match_points.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {evalResult.gap_points.length > 0 && (
                    <div className="ai-result__section">
                      <span className="ai-result__label ai-result__label--gap">落差</span>
                      <ul className="ai-result__list ai-result__list--gap">
                        {evalResult.gap_points.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              <p className="ai-result__rec">{evalResult.recommendation}</p>
              {evalResult.dimensions && <DimensionsPanel dimensions={evalResult.dimensions} />}
            </div>
          )}
        </div>

        <JobChat job={job} jobContent={jobContent} />
      </div>
    </div>
  )
}
