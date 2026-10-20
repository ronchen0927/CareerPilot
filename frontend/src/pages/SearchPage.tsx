import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchJobUrl, fetchOptions, searchJobs } from '../api/client'
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

const YOURATOR_CATEGORY_OPTIONS = [
  { value: '後端工程', label: '後端工程' },
  { value: '前端工程', label: '前端工程' },
  { value: 'AI 工程師', label: 'AI 工程師' },
  { value: '行動應用開發', label: '行動應用開發' },
  { value: '資料科學', label: '資料科學' },
  { value: 'DevOps / SRE', label: 'DevOps / SRE' },
  { value: '資安工程', label: '資安工程' },
  { value: '全端工程師', label: '全端工程師' },
]

const CAKE_SENIORITY_OPTIONS = [
  { value: 'entry_level', label: '初階' },
  { value: 'mid_senior_level', label: '中高階' },
  { value: 'associate', label: '助理' },
  { value: 'director', label: '經理 / 總監' },
  { value: 'internship_level', label: '實習' },
  { value: 'executive', label: '經營層 (VP, GM, C-Level)' },
]

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

const SOURCE_BADGE_KEY: Record<string, string> = {
  '104': '104',
  CakeResume: 'cake',
  Yourator: 'yourator',
}

const SOURCE_BADGE_LABEL: Record<string, string> = {
  '104': '104',
  CakeResume: 'Cake',
  Yourator: 'Yourator',
}

export default function SearchPage() {
  const [keyword, setKeyword] = useState('Python')
  const [pages, setPages] = useState(5)
  const [areas, setAreas] = useState<string[]>([])
  const [experience, setExperience] = useState<string[]>([])
  const [sources, setSources] = useState<string[]>(['104'])
  const [minSalary, setMinSalary] = useState(0)
  const [minAnnualSalary, setMinAnnualSalary] = useState(0)
  // Yourator 專屬篩選
  const [youraCategories, setYouraCategories] = useState<string[]>([])
  const [youratSalaryMin, setYouratSalaryMin] = useState(0)
  const [youratSalaryMax, setYouratSalaryMax] = useState(0)
  // CakeResume 專屬篩選
  const [cakeSeniority, setCakeSeniority] = useState<string[]>([])
  const [cakeSalaryMin, setCakeSalaryMin] = useState(0)
  const [cakeSalaryMax, setCakeSalaryMax] = useState(0)
  const [options, setOptions] = useState<JobOptions>(FALLBACK_OPTIONS)
  const [allResults, setAllResults] = useState<JobListing[]>([])
  const [searchedKeywords, setSearchedKeywords] = useState<string[]>([])
  const [elapsedTime, setElapsedTime] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedJob, setSelectedJob] = useState<JobListing | null>(null)
  
  // Tab UI State
  const [activeTab, setActiveTab] = useState<string>('104')

  useEffect(() => {
    if (sources.length > 0 && !sources.includes(activeTab)) {
      setActiveTab(sources[0])
    }
  }, [sources, activeTab])

  const { bookmarks, toggle: toggleBookmark, remove: removeBookmark, setStatus, isBookmarked } =
    useBookmarks()

  const navigate = useNavigate()
  const [fetchingLink, setFetchingLink] = useState<string | null>(null)
  const [fetchLinkError, setFetchLinkError] = useState<string | null>(null)

  async function handleCoverLetter(link: string) {
    setFetchingLink(link)
    setFetchLinkError(null)
    try {
      const data = await fetchJobUrl(link)
      navigate('/cover-letter', { state: { job_text: data.text, job_url: link } })
    } catch {
      setFetchLinkError(link)
      setTimeout(() => setFetchLinkError(null), 3000)
    } finally {
      setFetchingLink(null)
    }
  }

  const effectiveMinMonthly = Math.max(minSalary, Math.round(minAnnualSalary / 12))
  const displayedResults = useMemo(
    () => (effectiveMinMonthly > 0 ? allResults.filter(j => j.salary_low >= effectiveMinMonthly) : allResults),
    [allResults, effectiveMinMonthly],
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
    setLoading(true)
    setError(null)
    setAllResults([])
    setSearchedKeywords(kws)

    try {
      const isYourator = sources.includes('yourator')
      const isCake = sources.includes('cake')
      const responses = await Promise.all(
        kws.map(kw => searchJobs({
          keyword: kw,
          pages,
          areas,
          experience,
          sources,
          categories: isYourator ? youraCategories : [],
          salary_min: isYourator ? youratSalaryMin : 0,
          salary_max: isYourator ? youratSalaryMax : 0,
          cake_seniority: isCake ? cakeSeniority : [],
          cake_salary_min: isCake ? cakeSalaryMin : 0,
          cake_salary_max: isCake ? cakeSalaryMax : 0,
        })),
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
      <div className="page-intro">
        <h1 className="page-intro__title">職缺搜尋</h1>
        <p className="page-intro__subtitle">104 人力銀行 / CakeResume 職缺快速搜尋</p>
      </div>

      {/* Search Form */}
      <section className="search-card">
        <form onSubmit={handleSearch}>
          <div className="form-group">
            <label className="form-label" htmlFor="keyword">
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
              搜尋來源
            </label>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              {[
                { value: '104', label: '104 人力銀行' },
                { value: 'cake', label: 'CakeResume' },
                { value: 'yourator', label: 'Yourator' },
              ].map(opt => (
                <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontSize: '0.9rem' }}>
                  <input
                    type="checkbox"
                    checked={sources.includes(opt.value)}
                    onChange={e => {
                      if (e.target.checked) setSources(prev => [...prev, opt.value])
                      else setSources(prev => prev.filter(s => s !== opt.value))
                    }}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          {/* Tabs Navigation */}
          {sources.length > 0 && (
            <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #e2e8f0', marginBottom: '1.5rem', paddingBottom: '0.5rem' }}>
              {sources.includes('104') && (
                <button
                  type="button"
                  onClick={() => setActiveTab('104')}
                  style={{
                    padding: '0.5rem 1rem',
                    background: activeTab === '104' ? '#eff6ff' : 'transparent',
                    color: activeTab === '104' ? '#2563eb' : '#64748b',
                    border: '1px solid',
                    borderColor: activeTab === '104' ? '#bfdbfe' : 'transparent',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontWeight: activeTab === '104' ? '600' : '400',
                    transition: 'all 0.2s'
                  }}
                >
                  104 人力銀行設定
                </button>
              )}
              {sources.includes('cake') && (
                <button
                  type="button"
                  onClick={() => setActiveTab('cake')}
                  style={{
                    padding: '0.5rem 1rem',
                    background: activeTab === 'cake' ? '#eff6ff' : 'transparent',
                    color: activeTab === 'cake' ? '#2563eb' : '#64748b',
                    border: '1px solid',
                    borderColor: activeTab === 'cake' ? '#bfdbfe' : 'transparent',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontWeight: activeTab === 'cake' ? '600' : '400',
                    transition: 'all 0.2s'
                  }}
                >
                  CakeResume 設定
                </button>
              )}
              {sources.includes('yourator') && (
                <button
                  type="button"
                  onClick={() => setActiveTab('yourator')}
                  style={{
                    padding: '0.5rem 1rem',
                    background: activeTab === 'yourator' ? '#eff6ff' : 'transparent',
                    color: activeTab === 'yourator' ? '#2563eb' : '#64748b',
                    border: '1px solid',
                    borderColor: activeTab === 'yourator' ? '#bfdbfe' : 'transparent',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontWeight: activeTab === 'yourator' ? '600' : '400',
                    transition: 'all 0.2s'
                  }}
                >
                  Yourator 設定
                </button>
              )}
            </div>
          )}

          {/* Tab Contents */}
          <div style={{ minHeight: '180px', marginBottom: '1.5rem', padding: '1rem', background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}>
            {sources.length === 0 && (
              <p style={{ color: '#64748b', textAlign: 'center', marginTop: '2rem' }}>請至少勾選一個搜尋來源</p>
            )}

            {activeTab === '104' && sources.includes('104') && (
              <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
                <div className="form-group">
                  <label className="form-label">選擇地區</label>
                  <CheckboxGroup
                    options={options.areas}
                    selected={areas}
                    prefix="area"
                    onChange={setAreas}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">經歷要求</label>
                  <CheckboxGroup
                    options={options.experience}
                    selected={experience}
                    prefix="exp"
                    onChange={setExperience}
                  />
                </div>

                <div className="form-group" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '10rem' }}>
                    <label className="form-label" htmlFor="min-salary">
                      最低月薪（元，0 為不限）
                    </label>
                    <input
                      type="number"
                      id="min-salary"
                      className="form-input"
                      value={minSalary}
                      min={0}
                      step={5000}
                      placeholder="例：40000"
                      onChange={e => setMinSalary(parseInt(e.target.value, 10) || 0)}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: '10rem' }}>
                    <label className="form-label" htmlFor="min-annual-salary">
                      最低年薪（元，0 為不限）
                    </label>
                    <input
                      type="number"
                      id="min-annual-salary"
                      className="form-input"
                      value={minAnnualSalary}
                      min={0}
                      step={50000}
                      placeholder="例：600000"
                      onChange={e => setMinAnnualSalary(parseInt(e.target.value, 10) || 0)}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'cake' && sources.includes('cake') && (
              <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
                <div className="form-group">
                  <label className="form-label">選擇地區</label>
                  <CheckboxGroup
                    options={options.areas}
                    selected={areas}
                    prefix="cake-area"
                    onChange={setAreas}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">CakeResume 年資等級</label>
                  <CheckboxGroup
                    options={CAKE_SENIORITY_OPTIONS}
                    selected={cakeSeniority}
                    prefix="cake-sen"
                    onChange={setCakeSeniority}
                  />
                </div>

                <div className="form-group" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '10rem' }}>
                    <label className="form-label" htmlFor="cake-salary-min">
                      CakeResume 月薪下限（0 為不限）
                    </label>
                    <input
                      type="number"
                      id="cake-salary-min"
                      className="form-input"
                      value={cakeSalaryMin}
                      min={0}
                      step={5000}
                      placeholder="例：70000"
                      onChange={e => setCakeSalaryMin(parseInt(e.target.value, 10) || 0)}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: '10rem' }}>
                    <label className="form-label" htmlFor="cake-salary-max">
                      CakeResume 月薪上限（0 為不限）
                    </label>
                    <input
                      type="number"
                      id="cake-salary-max"
                      className="form-input"
                      value={cakeSalaryMax}
                      min={0}
                      step={5000}
                      placeholder="例：100000"
                      onChange={e => setCakeSalaryMax(parseInt(e.target.value, 10) || 0)}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'yourator' && sources.includes('yourator') && (
              <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
                <div className="form-group">
                  <label className="form-label">選擇地區</label>
                  <CheckboxGroup
                    options={options.areas}
                    selected={areas}
                    prefix="youra-area"
                    onChange={setAreas}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Yourator 職缺類別</label>
                  <CheckboxGroup
                    options={YOURATOR_CATEGORY_OPTIONS}
                    selected={youraCategories}
                    prefix="youra-cat"
                    onChange={setYouraCategories}
                  />
                </div>

                <div className="form-group" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '10rem' }}>
                    <label className="form-label" htmlFor="yourat-salary-min">
                      Yourator 月薪下限（0 為不限）
                    </label>
                    <input
                      type="number"
                      id="yourat-salary-min"
                      className="form-input"
                      value={youratSalaryMin}
                      min={0}
                      step={5000}
                      placeholder="例：70000"
                      onChange={e => setYouratSalaryMin(parseInt(e.target.value, 10) || 0)}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: '10rem' }}>
                    <label className="form-label" htmlFor="yourat-salary-max">
                      Yourator 月薪上限（0 為不限）
                    </label>
                    <input
                      type="number"
                      id="yourat-salary-max"
                      className="form-input"
                      value={youratSalaryMax}
                      min={0}
                      step={5000}
                      placeholder="例：100000"
                      onChange={e => setYouratSalaryMax(parseInt(e.target.value, 10) || 0)}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          <button type="submit" className="btn-search" disabled={loading || sources.length === 0}>
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
                {effectiveMinMonthly > 0
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
                      <span className={`source-badge source-badge--${SOURCE_BADGE_KEY[job.source] ?? '104'}`}>
                        {SOURCE_BADGE_LABEL[job.source] ?? job.source}
                      </span>
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
                    <td style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                      {bm.status === '想投' && (
                        <>
                          <button
                            className="btn-export"
                            style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
                            disabled={fetchingLink !== null}
                            onClick={() => handleCoverLetter(link)}
                          >
                            {fetchingLink === link ? '抓取中...' : 'AI 推薦信'}
                          </button>
                          {fetchLinkError === link && (
                            <span style={{ color: 'var(--color-error, #e53e3e)', fontSize: '0.75rem' }}>
                              擷取失敗
                            </span>
                          )}
                        </>
                      )}
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

      {selectedJob && (
        <JobModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          bookmarkStatus={bookmarks[selectedJob.link]?.status}
        />
      )}
    </div>
  )
}
