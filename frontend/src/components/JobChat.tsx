import { useEffect, useRef, useState } from 'react'
import { chatStream } from '../api/client'
import { usePreferences, formatPrefsForPrompt } from '../hooks/usePreferences'
import type { ChatMessage, JobListing } from '../types'

interface Props {
  job: JobListing
  jobContent?: string | null
}

const GREETING = '有什麼關於這個職缺的問題想問我？'
const STORAGE_KEY = 'careerpilot_chats'

function loadHistory(jobLink: string): ChatMessage[] {
  try {
    const all = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, ChatMessage[]>
    return all[jobLink] ?? []
  } catch {
    return []
  }
}

function saveHistory(jobLink: string, messages: ChatMessage[]): void {
  try {
    const all = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, ChatMessage[]>
    all[jobLink] = messages
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
  } catch {
    // ignore storage quota errors
  }
}

export default function JobChat({ job, jobContent }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadHistory(job.link))
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [prefs] = usePreferences()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    saveHistory(job.link, messages)
  }, [job.link, messages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleClear() {
    setMessages([])
  }

  async function handleSend() {
    if (!input.trim() || isStreaming) return

    const userMsg: ChatMessage = { role: 'user', content: input.trim() }
    const nextMessages = [...messages, userMsg]
    setMessages([...nextMessages, { role: 'assistant', content: '' }])
    setInput('')
    setIsStreaming(true)

    try {
      const userCv = localStorage.getItem('careerpilot_cv') ?? ''
      const prefsStr = formatPrefsForPrompt(prefs)

      await chatStream(nextMessages, job, userCv + prefsStr, jobContent ?? '', chunk => {
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          updated[updated.length - 1] = { ...last, content: last.content + chunk }
          return updated
        })
      })
    } catch {
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        const separator = last.content ? '\n\n' : ''
        updated[updated.length - 1] = {
          ...last,
          content: last.content + separator + '⚠ 回應中斷，請再試一次',
        }
        return updated
      })
    } finally {
      setIsStreaming(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="job-chat">
      <div className="job-chat__header">
        <span className="job-chat__title">職缺 Q&amp;A</span>
        {messages.length > 0 && (
          <button
            className="btn-export"
            style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
            onClick={handleClear}
          >
            清空
          </button>
        )}
      </div>

      <div className="job-chat__messages">
        <div className="job-chat__bubble job-chat__bubble--greeting">
          {GREETING}
        </div>
        {messages.map((msg, i) => (
          <div key={`${i}-${msg.role}`} className={`job-chat__bubble job-chat__bubble--${msg.role}`}>
            {msg.content}
            {isStreaming && i === messages.length - 1 && msg.role === 'assistant' && (
              <span className="job-chat__cursor">▌</span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="job-chat__input-row">
        <textarea
          className="job-chat__input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="輸入問題（Enter 送出，Shift+Enter 換行）"
          disabled={isStreaming}
          rows={2}
        />
        <button
          className="job-chat__send-btn"
          disabled={isStreaming || !input.trim()}
          onClick={handleSend}
        >
          送出
        </button>
      </div>
    </div>
  )
}
