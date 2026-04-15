import { useEffect, useRef, useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage'

interface Props {
  onClose: () => void
}

export default function CVModal({ onClose }: Props) {
  const [savedCV, setSavedCV] = useLocalStorage('careerpilot_cv', '')
  const [draft, setDraft] = useState(savedCV)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    textareaRef.current?.focus()
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  function handleSave() {
    setSavedCV(draft.trim())
    onClose()
  }

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cv-modal-title"
      onClick={e => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="modal">
        <button className="modal__close" aria-label="關閉" onClick={onClose}>
          ✕
        </button>
        <h3 id="cv-modal-title" className="modal__title">
          設定履歷背景
        </h3>
        <p className="cv-modal__hint">
          貼入你的履歷或個人背景，AI 評分時將用於比對職缺適合度。留空則僅依職缺資訊評分。
        </p>
        <textarea
          ref={textareaRef}
          className="cv-textarea"
          value={draft}
          onChange={e => setDraft(e.target.value)}
          placeholder="例：5年 Python 後端開發經驗，熟悉 FastAPI、Django，有 AWS 使用經驗..."
        />
        <button className="btn-goto" style={{ marginTop: '1rem' }} onClick={handleSave}>
          儲存履歷
        </button>
      </div>
    </div>
  )
}
