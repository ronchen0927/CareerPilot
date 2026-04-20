import { useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useBookmarks } from '../hooks/useBookmarks'
import { useLiveness } from '../hooks/useLiveness'
import type { BookmarkEntry, BookmarkStatus } from '../types'

const STATUSES: BookmarkStatus[] = ['想投', '已投', '面試中', '錄取', '不適合']

const STATUS_CONFIG: Record<BookmarkStatus, { color: string; bg: string }> = {
  想投:  { color: '#64748B', bg: 'rgba(100,116,139,0.1)' },
  已投:  { color: '#2563EB', bg: 'rgba(37,99,235,0.1)' },
  面試中: { color: '#7C3AED', bg: 'rgba(124,58,237,0.1)' },
  錄取:  { color: '#059669', bg: 'rgba(5,150,105,0.1)' },
  不適合: { color: '#DC2626', bg: 'rgba(220,38,38,0.1)' },
}

export default function DashboardPage() {
  const { bookmarks, setStatus, remove } = useBookmarks()
  const draggedLink = useRef<string | null>(null)
  const [dragOverStatus, setDragOverStatus] = useState<BookmarkStatus | null>(null)

  const entries = Object.entries(bookmarks)
  const bookmarkUrls = useMemo(() => Object.keys(bookmarks), [bookmarks])
  const { statusMap, recheckLoading, recheck } = useLiveness(bookmarkUrls)
  const groups = Object.fromEntries(
    STATUSES.map(s => [
      s,
      entries.filter(([, bm]) => (bm.status ?? '想投') === s) as [string, BookmarkEntry][],
    ]),
  ) as Record<BookmarkStatus, [string, BookmarkEntry][]>

  const total = entries.length

  function handleDragStart(link: string) {
    draggedLink.current = link
  }

  function handleDragOver(e: React.DragEvent, status: BookmarkStatus) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverStatus(status)
  }

  function handleDragLeave(e: React.DragEvent) {
    if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) {
      setDragOverStatus(null)
    }
  }

  function handleDrop(e: React.DragEvent, status: BookmarkStatus) {
    e.preventDefault()
    setDragOverStatus(null)
    const link = draggedLink.current
    if (link && bookmarks[link]) {
      setStatus(link, status)
      draggedLink.current = null
    }
  }

  if (total === 0) {
    return (
      <div className="dashboard-container">
        <div className="page-intro">
          <h1 className="page-intro__title">投遞看板</h1>
          <p className="page-intro__sub">拖曳職缺卡片以更新投遞狀態</p>
        </div>
        <div className="empty-state">
          <p className="empty-state__text">還沒有收藏的職缺</p>
          <p className="empty-state__hint">回主頁搜尋並點擊 ☆ 來收藏職缺</p>
          <Link to="/" className="btn-goto" style={{ maxWidth: '200px', marginTop: '0.5rem' }}>
            去搜尋職缺 →
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      <div className="page-intro" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="page-intro__title">投遞看板</h1>
          <p className="page-intro__sub">拖曳職缺卡片以更新投遞狀態</p>
        </div>
        <div className="stats-bar">
          <span className="stat-total">{total} 筆收藏</span>
          {STATUSES.filter(s => groups[s].length > 0).map(s => {
            const cfg = STATUS_CONFIG[s]
            return (
              <span
                key={s}
                className="stat-chip"
                style={{ color: cfg.color, borderColor: cfg.color, background: cfg.bg }}
              >
                {s} {groups[s].length}
              </span>
            )
          })}
          <button
            className="btn-export"
            style={{ padding: '0.2rem 0.7rem', fontSize: '0.78rem', marginLeft: 'auto' }}
            disabled={recheckLoading}
            onClick={recheck}
          >
            {recheckLoading ? '檢查中...' : '重新檢查職缺'}
          </button>
        </div>
      </div>

      <div className="kanban-board">
        {STATUSES.map(status => {
          const cfg = STATUS_CONFIG[status]
          const cards = groups[status]
          const isDragOver = dragOverStatus === status

          return (
            <div
              key={status}
              className="kanban-column"
              style={
                { '--col-color': cfg.color, '--col-bg': cfg.bg } as React.CSSProperties
              }
            >
              <div className="kanban-column__header">
                <span className="kanban-column__title">{status}</span>
                <span className="kanban-column__count">{cards.length}</span>
              </div>
              <div
                className={`kanban-cards ${isDragOver ? 'kanban-cards--drag-over' : ''}`}
                onDragOver={e => handleDragOver(e, status)}
                onDragLeave={handleDragLeave}
                onDrop={e => handleDrop(e, status)}
              >
                {cards.map(([link, bm]) => (
                  <KanbanCard
                    key={link}
                    link={link}
                    bm={bm}
                    liveness={statusMap[link] ?? null}
                    onDragStart={() => handleDragStart(link)}
                    onRemove={() => remove(link)}
                  />
                ))}
                <div className="kanban-drop-zone" />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface CardProps {
  link: string
  bm: BookmarkEntry
  liveness: import('../types').LivenessInfo | null
  onDragStart: () => void
  onRemove: () => void
}

function KanbanCard({ link, bm, liveness, onDragStart, onRemove }: CardProps) {
  const [isDragging, setIsDragging] = useState(false)

  return (
    <div
      className={`kanban-card ${isDragging ? 'kanban-card--dragging' : ''}`}
      draggable
      onDragStart={() => {
        onDragStart()
        requestAnimationFrame(() => setIsDragging(true))
      }}
      onDragEnd={() => setIsDragging(false)}
    >
      <button
        className="kanban-card__remove"
        title="移除"
        onClick={e => {
          e.preventDefault()
          onRemove()
        }}
      >
        ✕
      </button>
      <a
        href={link}
        target="_blank"
        rel="noopener noreferrer"
        className="kanban-card__title"
        onClick={e => e.stopPropagation()}
      >
        {bm.job}
      </a>
      <div className="kanban-card__meta">
        <span className="kanban-card__company">{bm.company}</span>
        <span className="kanban-card__city">{bm.city}</span>
      </div>
      <span className="kanban-card__salary">{bm.salary}</span>
      {liveness?.status === 'dead' && (
        <span style={{
          display: 'inline-block',
          marginTop: '0.35rem',
          fontSize: '0.72rem',
          padding: '0.1rem 0.45rem',
          borderRadius: '999px',
          background: 'rgba(239,68,68,0.12)',
          color: '#ef4444',
          border: '1px solid rgba(239,68,68,0.3)',
        }}>
          職缺已關閉
        </span>
      )}
      {liveness?.status === 'unknown' && (
        <span style={{
          display: 'inline-block',
          marginTop: '0.35rem',
          fontSize: '0.72rem',
          padding: '0.1rem 0.45rem',
          borderRadius: '999px',
          background: 'rgba(156,163,175,0.12)',
          color: '#9ca3af',
          border: '1px solid rgba(156,163,175,0.2)',
        }}>
          狀態未知
        </span>
      )}
    </div>
  )
}
