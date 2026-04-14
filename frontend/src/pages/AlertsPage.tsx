import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { createAlert, deleteAlert, fetchAlerts, fetchOptions, triggerAlert } from '../api/client'
import CheckboxGroup from '../components/CheckboxGroup'
import type { Alert, JobOptions } from '../types'

type NotifyType = 'line' | 'webhook'

const FALLBACK_OPTIONS: JobOptions = {
  areas: [
    { value: '6001001000', label: '台北市' },
    { value: '6001002000', label: '新北市' },
    { value: '6001006000', label: '新竹市' },
    { value: '6001008000', label: '台中市' },
    { value: '6001014000', label: '台南市' },
    { value: '6001016000', label: '高雄市' },
  ],
  experience: [
    { value: '1', label: '1年以下' },
    { value: '3', label: '1-3年' },
    { value: '5', label: '3-5年' },
    { value: '10', label: '5-10年' },
    { value: '99', label: '10年以上' },
  ],
}

function formatInterval(minutes: number): string {
  if (minutes < 60) return `${minutes} 分鐘`
  if (minutes === 60) return '1 小時'
  if (minutes < 1440) return `${minutes / 60} 小時`
  return '天'
}

function formatLastRun(isoStr: string | null): string {
  if (!isoStr) return '尚未執行'
  const diff = Date.now() - new Date(isoStr).getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1) return '剛剛執行'
  if (min < 60) return `${min} 分鐘前執行`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小時前執行`
  return `${Math.floor(hr / 24)} 天前執行`
}

export default function AlertsPage() {
  // Form state
  const [keyword, setKeyword] = useState('')
  const [areas, setAreas] = useState<string[]>([])
  const [experience, setExperience] = useState<string[]>([])
  const [alertPages, setAlertPages] = useState(3)
  const [minSalary, setMinSalary] = useState(0)
  const [interval, setInterval] = useState(60)
  const [notifyType, setNotifyType] = useState<NotifyType>('line')
  const [notifyTarget, setNotifyTarget] = useState('')

  // UI state
  const [options, setOptions] = useState<JobOptions>(FALLBACK_OPTIONS)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [triggeringId, setTriggeringId] = useState<string | null>(null)
  const [triggerResult, setTriggerResult] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchOptions()
      .then(setOptions)
      .catch(() => {
        /* keep fallback */
      })
    loadAlerts()
  }, [])

  async function loadAlerts() {
    try {
      const data = await fetchAlerts()
      setAlerts(data.alerts)
    } catch {
      setError('無法載入提醒列表，請確認後端是否運行中')
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await createAlert({
        keyword,
        areas,
        experience,
        pages: alertPages,
        min_salary: minSalary,
        notify_type: notifyType,
        notify_target: notifyTarget,
        interval_minutes: interval,
      })
      // Reset form
      setKeyword('')
      setAreas([])
      setExperience([])
      setAlertPages(3)
      setMinSalary(0)
      setInterval(60)
      setNotifyType('line')
      setNotifyTarget('')
      await loadAlerts()
    } catch (err) {
      setError(err instanceof Error ? err.message : '建立失敗，請確認後端是否運行中')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteAlert(id)
      await loadAlerts()
    } catch (err) {
      setError(err instanceof Error ? err.message : '刪除失敗')
    }
  }

  async function handleTrigger(id: string) {
    setTriggeringId(id)
    try {
      const data = await triggerAlert(id)
      setTriggerResult(prev => ({ ...prev, [id]: `✓ 找到 ${data.new_jobs_found} 筆新職缺` }))
      setTimeout(() => {
        setTriggerResult(prev => {
          const next = { ...prev }
          delete next[id]
          return next
        })
        setTriggeringId(null)
        loadAlerts()
      }, 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '觸發失敗')
      setTriggeringId(null)
    }
  }

  return (
    <div className="container">
      <header className="alerts-header">
        <div className="alerts-header__left">
          <Link to="/" className="btn-back">
            ← 回主頁
          </Link>
          <div>
            <h1 className="alerts-title">職缺提醒</h1>
            <p className="alerts-subtitle">設定條件，有新職缺時自動通知</p>
          </div>
        </div>
      </header>

      {/* Create Alert Form */}
      <section className="search-card" style={{ animation: 'fade-in-up 0.5s ease 0.1s both' }}>
        <h2 className="section-title">新增提醒</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="alert-keyword">
              <span className="form-label__icon">💼</span>
              搜尋關鍵字
            </label>
            <input
              type="text"
              id="alert-keyword"
              className="form-input"
              placeholder="職稱、技能..."
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">
                <span className="form-label__icon">📍</span>
                地區
              </label>
              <CheckboxGroup
                options={options.areas}
                selected={areas}
                prefix="a-area"
                onChange={setAreas}
              />
            </div>
            <div className="form-group">
              <label className="form-label">
                <span className="form-label__icon">⏳</span>
                經歷
              </label>
              <CheckboxGroup
                options={options.experience}
                selected={experience}
                prefix="a-exp"
                onChange={setExperience}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label" htmlFor="alert-pages">
                <span className="form-label__icon">📄</span>
                爬取頁數
              </label>
              <input
                type="number"
                id="alert-pages"
                className="form-input"
                value={alertPages}
                min={1}
                max={10}
                onChange={e => setAlertPages(parseInt(e.target.value, 10) || 3)}
              />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="alert-min-salary">
                <span className="form-label__icon">💰</span>
                最低月薪（元，0 不限）
              </label>
              <input
                type="number"
                id="alert-min-salary"
                className="form-input"
                value={minSalary}
                min={0}
                step={1000}
                onChange={e => setMinSalary(parseInt(e.target.value, 10) || 0)}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="alert-interval">
              <span className="form-label__icon">⏰</span>
              檢查頻率
            </label>
            <select
              id="alert-interval"
              className="form-input form-select"
              value={interval}
              onChange={e => setInterval(parseInt(e.target.value, 10))}
            >
              <option value={30}>每 30 分鐘</option>
              <option value={60}>每 1 小時</option>
              <option value={120}>每 2 小時</option>
              <option value={240}>每 4 小時</option>
              <option value={480}>每 8 小時</option>
              <option value={1440}>每天一次</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">
              <span className="form-label__icon">🔔</span>
              通知方式
            </label>
            <div className="notify-type-grid">
              {(['line', 'webhook'] as const).map(type => (
                <label className="notify-type-chip" key={type}>
                  <input
                    type="radio"
                    name="notify-type"
                    value={type}
                    checked={notifyType === type}
                    onChange={() => setNotifyType(type)}
                  />
                  <span>{type === 'line' ? 'Line Notify' : 'Webhook URL'}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="alert-target">
              <span className="form-label__icon">{notifyType === 'line' ? '🔑' : '🌐'}</span>
              {notifyType === 'line' ? 'Line Notify Token' : 'Webhook URL'}
              {notifyType === 'line' && (
                <a
                  href="https://notify-bot.line.me/my/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="form-label__link"
                >
                  取得 Token →
                </a>
              )}
            </label>
            <input
              type="text"
              id="alert-target"
              className="form-input"
              placeholder={
                notifyType === 'line' ? '貼上 Line Notify Token...' : 'https://hooks.example.com/...'
              }
              value={notifyTarget}
              onChange={e => setNotifyTarget(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn-search" disabled={submitting}>
            <span className="btn-search__text">{submitting ? '建立中...' : '建立提醒'}</span>
            <span className="btn-search__icon">+</span>
          </button>
        </form>
      </section>

      {/* Active Alerts */}
      {alerts.length > 0 && (
        <section className="alerts-list-section">
          <h2 className="section-title">已設定的提醒</h2>
          <div className="alerts-list">
            {alerts.map(alert => (
              <div className="alert-card" key={alert.id}>
                <div className="alert-card__header">
                  <div className="alert-card__keyword">{alert.keyword}</div>
                  <div className="alert-card__actions">
                    <button
                      className="btn-trigger"
                      disabled={triggeringId === alert.id}
                      onClick={() => handleTrigger(alert.id)}
                    >
                      {triggerResult[alert.id] ?? (triggeringId === alert.id ? '執行中...' : '立即測試')}
                    </button>
                    <button className="btn-delete" onClick={() => handleDelete(alert.id)}>
                      刪除
                    </button>
                  </div>
                </div>
                <div className="alert-card__meta">
                  {alert.min_salary > 0 && (
                    <span className="alert-chip alert-chip--salary">
                      月薪 ≥ {alert.min_salary.toLocaleString()} 元
                    </span>
                  )}
                  {alert.areas.length > 0 && (
                    <span className="alert-chip">📍 {alert.areas.length} 個地區</span>
                  )}
                  {alert.experience.length > 0 && (
                    <span className="alert-chip">⏳ {alert.experience.length} 個經歷</span>
                  )}
                  <span className="alert-chip">📄 {alert.pages} 頁</span>
                </div>
                <div className="alert-card__footer">
                  <span
                    className={`alert-notify-badge alert-notify-badge--${alert.notify_type}`}
                  >
                    {alert.notify_type === 'line' ? 'Line Notify' : 'Webhook'}
                  </span>
                  <span className="alert-interval">每 {formatInterval(alert.interval_minutes)}</span>
                  <span className="alert-last-run">{formatLastRun(alert.last_run)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {alerts.length === 0 && !error && (
        <div className="alerts-empty">
          <p className="alerts-empty__text">
            還沒有設定任何提醒，在上方填寫條件後點「建立提醒」。
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <section className="error-card">
          <span className="error-card__icon">⚠️</span>
          <p className="error-card__text">{error}</p>
          <button className="btn-dismiss" onClick={() => setError(null)}>
            關閉
          </button>
        </section>
      )}
    </div>
  )
}
