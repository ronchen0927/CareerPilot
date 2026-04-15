import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchOptions, searchJobs } from '../api/client'
import CheckboxGroup from '../components/CheckboxGroup'
import JobModal from '../components/JobModal'
import { useBookmarks } from '../hooks/useBookmarks'
import type { JobListing, JobOptions } from '../types'

const STATUSES = ['想投', '已投', '面試中', '錄取', '不適合'] as const
type Status = (typeof STATUSES)[number]

const STATUS_CSS: Record<Status, string> = {
  想投: 'status--want',
  已投: 'status--applied',
  面試中: 'status--interview',
  錄取: 'status--offer',
  不適合: 'status--reject',
}

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

export default function SearchPage() {
  const [keyword, setKeyword] = useState('Python')
  const [pages, setPages] = useState(5)
  const [areas, setAreas] = useState<string[]>([])
  const [experience, setExperience] = useState<string[]>([])
  const [sources, setSources] = useState<string[]>(['104'])
  const [minSalary, setMinSalary] = useState(0)
  const [options, setOptions] = useState<JobOptions>(FALLBACK_OPTIONS)
  const [allResults, setAllResults] = useState<JobListing[]>([])
  const [searchedKeywords, setSearchedKeywords] = useState<string[]>([])
  const [elapsedTime, setElapsedTime] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedJob, setSelectedJob] = useState<JobListing | null>(null)

  const { bookmarks, toggle: toggleBookmark, remove: removeBookmark, setStatus, isBookmarked } =
    useBookmarks()

  const displayedResults = useMemo(
    () => (minSalary > 0 ? allResults.filter(j => j.salary_low >= minSalary) : allResults),
    [allResults, minSalary],
  )

  useEffect(() => {
    fetchOptions()
      .then(setOptions)
      .catch(() => {
        /* keep fallback */
      })
  }, [])

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const kws = [...new Set(keyword.split(',').map(k => k.trim()).filter(Boolean))]
    if (kws.length === 0) return
    if (kws.length > 5) { setError('最多支援 5 個關鍵字，請減少後再搜尋'); return }
    if (sources.length === 0) { setError('請至少選擇一個搜尋來源'); return }

    setLoading(true)
    setError(null)
    setAllResults([])
    setSearchedKeywords(kws)

    try {
      const responses = await Promise.all(
        kws.map(kw => searchJobs({ keyword: kw, pages, areas, experience, sources })),
      )
      const seen = new Set<string>()
      const merged: JobListing[] = []
      let maxElapsed = 0

      for (const data of responses) {
        maxElapsed = Math.max(maxElapsed, data.elapsed_time)
        for (const job of data.results) {
          if (!seen.has(job.link)) {
            seen.add(job.link)
            merged.push(job)
          }
        }
      }
      merged.sort((a, b) => b.date.localeCompare(a.date))
      setAllResults(merged)
      setElapsedTime(maxElapsed)
    } catch (err) {
      setError(err instanceof Error ? err.message : '搜尋時發生未知錯誤')
    } finally {
      setLoading(false)
    }
  }

  function handleSourceChange(value: string, checked: boolean) {
    setSources(prev => (checked ? [...prev, value] : prev.filter(s => s !== value)))
  }

  function exportCSV() {
    if (displayedResults.length === 0) return
    const headers = ['刊登日期', '職位', '公司名稱', '城市', '經歷', '最低學歷', '薪水', '來源', '連結']
    const rows = displayedResults.map(j => [
      j.date, j.job, j.company, j.city, j.experience, j.education, j.salary, j.source, j.link,
    ])
    const csv = [headers, ...rows]
      .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
      .join('\n')
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `careerpilot_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const bookmarkEntries = Object.entries(bookmarks)

  return (
    <div className="container">
      <header className="header">
        <div className="header__logo">
          <span className="header__icon">🧭</span>
          <h1 className="header__title">CareerPilot</h1>
        </div>
        <p className="header__subtitle">104 &amp; CakeResume 職缺快速搜尋</p>
      </header>

      {/* Search Form */}
      <section className="search-card">
        <form onSubmit={handleSearch}>
          <div className="form-group">
            <label className="form-label" htmlFor="keyword">
              <span className="form-label__icon">💼</span>
              搜尋關鍵字
              <span className="form-label__hint">多個關鍵字用逗號分隔，最多 5 個</span>
            </label>
            <input
              type="text"
              id="keyword"
              className="form-input"
              placeholder="例：Python, 後端工程師, Django"
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="pages">
              <span className="form-label__icon">📄</span>
              爬取頁數
            </label>
            <input
              type="number"
              id="pages"
              className="form-input"
              value={pages}
              min={1}
              max={20}
              onChange={e => setPages(parseInt(e.target.value, 10) || 5)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              <span className="form-label__icon">🔍</span>
              搜尋來源
            </label>
            <div className="checkbox-grid">
              {(['104', 'CakeResume'] as const).map(src => (
                <div className="checkbox-chip" key={src}>
                  <input
                    type="checkbox"
                    id={`source-${src}`}
                    value={src}
                    checked={sources.includes(src)}
                    onChange={e => handleSourceChange(src, e.target.checked)}
                  />
                  <label htmlFor={`source-${src}`}>
                    {src === '104' ? '104 人力銀行' : src}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">
              <span className="form-label__icon">📍</span>
              選擇地區
            </label>
            <CheckboxGroup
              options={options.areas}
              selected={areas}
              prefix="area"
              onChange={setAreas}
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              <span className="form-label__icon">⏳</span>
              經歷要求
            </label>
            <CheckboxGroup
              options={options.experience}
              selected={experience}
              prefix="exp"
              onChange={setExperience}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="min-salary">
              <span className="form-label__icon">💰</span>
              最低月薪（元，0 為不限）
            </label>
            <input
              type="number"
              id="min-salary"
              className="form-input"
              value={minSalary}
              min={0}
              step={1000}
              placeholder="例：40000"
              onChange={e => setMinSalary(parseInt(e.target.value, 10) || 0)}
            />
          </div>

          <button type="submit" className="btn-search" disabled={loading}>
            <span className="btn-search__text">{loading ? '搜尋中...' : '開始搜尋'}</span>
            <span className="btn-search__icon">→</span>
          </button>
        </form>
      </section>

      {/* Loading */}
      {loading && (
        <section className="loading">
          <div className="loading__spinner" />
          <p className="loading__text">
            {searchedKeywords.length > 1
              ? `正在搜尋「${searchedKeywords.join('」、「')}」...`
              : '正在搜尋職缺中...'}
          </p>
        </section>
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

      {/* Results */}
      {!loading && allResults.length > 0 && (
        <section className="results">
          <div className="results__header">
            <h2 className="results__title">搜尋結果</h2>
            <div className="results__meta">
              <span className="results__badge">
                {minSalary > 0
                  ? `${displayedResults.length} 筆（共 ${allResults.length} 筆，已篩選）`
                  : `${allResults.length} 筆結果`}
              </span>
              {elapsedTime !== null && (
                <span className="results__time">耗時 {elapsedTime} 秒</span>
              )}
              <button className="btn-export" onClick={exportCSV}>
                匯出 CSV
              </button>
            </div>
          </div>

          {searchedKeywords.length > 1 && (
            <div className="keyword-tags">
              {searchedKeywords.map(k => (
                <span className="keyword-tag" key={k}>
                  {k}
                </span>
              ))}
            </div>
          )}

          <div className="table-wrapper">
            <table className="results-table">
              <thead>
                <tr>
                  <th>刊登日期</th>
                  <th>職位</th>
                  <th>公司名稱</th>
                  <th>城市</th>
                  <th>經歷</th>
                  <th>最低學歷</th>
                  <th>薪水</th>
                  <th>來源</th>
                  <th>收藏</th>
                </tr>
              </thead>
              <tbody>
                {displayedResults.map((job, i) => (
                  <tr
                    key={job.link}
                    className={job.is_featured ? 'featured' : ''}
                    style={{ animationDelay: `${i * 0.03}s` }}
                  >
                    <td>
                      {job.is_featured ? (
                        <span className="featured-badge">⭐ 精選</span>
                      ) : (
                        job.date
                      )}
                    </td>
                    <td>
                      <button
                        className="job-link job-detail-btn"
                        onClick={() => setSelectedJob(job)}
                      >
                        {job.job}
                      </button>
                    </td>
                    <td>{job.company}</td>
                    <td>{job.city}</td>
                    <td>{job.experience}</td>
                    <td>{job.education}</td>
                    <td>
                      <span className="salary-text">{job.salary}</span>
                    </td>
                    <td>
                      {job.source === 'CakeResume' ? (
                        <span className="source-badge source-badge--cake">CakeResume</span>
                      ) : (
                        <span className="source-badge source-badge--104">104</span>
                      )}
                    </td>
                    <td>
                      <button
                        className={`btn-bookmark ${isBookmarked(job.link) ? 'btn-bookmark--active' : ''}`}
                        title={isBookmarked(job.link) ? '取消收藏' : '加入收藏'}
                        onClick={() => toggleBookmark(job)}
                      >
                        {isBookmarked(job.link) ? '★' : '☆'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Bookmarks */}
      {bookmarkEntries.length > 0 && (
        <section className="bookmarks">
          <div className="bookmarks__header">
            <h2 className="bookmarks__title">★ 收藏列表</h2>
            <span className="results__badge">{bookmarkEntries.length} 筆</span>
            <Link to="/dashboard" className="btn-dashboard">
              看板視圖 →
            </Link>
          </div>
          <div className="table-wrapper">
            <table className="results-table">
              <thead>
                <tr>
                  <th>刊登日期</th>
                  <th>職位</th>
                  <th>公司名稱</th>
                  <th>城市</th>
                  <th>薪水</th>
                  <th>狀態</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {bookmarkEntries.map(([link, bm]) => (
                  <tr key={link}>
                    <td>{bm.date}</td>
                    <td>
                      <a
                        href={link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="job-link"
                      >
                        {bm.job}
                      </a>
                    </td>
                    <td>{bm.company}</td>
                    <td>{bm.city}</td>
                    <td>
                      <span className="salary-text">{bm.salary}</span>
                    </td>
                    <td>
                      <select
                        className={`status-select ${STATUS_CSS[bm.status] ?? ''}`}
                        value={bm.status}
                        onChange={e => setStatus(link, e.target.value as Status)}
                      >
                        {STATUSES.map(s => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <button className="btn-remove" onClick={() => removeBookmark(link)}>
                        移除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {selectedJob && <JobModal job={selectedJob} onClose={() => setSelectedJob(null)} />}
    </div>
  )
}
