import { usePreferences } from '../hooks/usePreferences'

export default function SettingsPage() {
  const [prefs, setPrefs] = usePreferences()

  function update<K extends keyof typeof prefs>(key: K, value: (typeof prefs)[K]) {
    setPrefs({ ...prefs, [key]: value })
  }

  return (
    <div className="container">
      <div className="page-intro">
        <h1 className="page-intro__title">個人偏好設定</h1>
        <p className="page-intro__sub">設定將自動注入 AI 評分提示詞，資料僅存於本機</p>
      </div>

      <section className="search-card">
        <div className="form-group">
          <label className="form-label" htmlFor="target-salary">
            目標月薪（元，0 為不設定）
          </label>
          <input
            type="number"
            id="target-salary"
            className="form-input"
            min={0}
            step={1000}
            value={prefs.target_salary}
            onChange={e => update('target_salary', parseInt(e.target.value, 10) || 0)}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="preferred-tech">
            偏好技術 / 產業
            <span className="form-label__hint">例：Python、FastAPI、金融科技</span>
          </label>
          <input
            type="text"
            id="preferred-tech"
            className="form-input"
            placeholder="例：Python, FastAPI, 雲端服務, SaaS"
            value={prefs.preferred_tech}
            onChange={e => update('preferred_tech', e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="career-goals">
            職涯目標
          </label>
          <textarea
            id="career-goals"
            className="form-input"
            rows={3}
            placeholder="例：希望轉型為後端 Tech Lead，有帶團隊機會，或能接觸系統設計..."
            value={prefs.career_goals}
            onChange={e => update('career_goals', e.target.value)}
            style={{ resize: 'vertical', fontFamily: 'inherit' }}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="avoided-industries">
            避開產業
            <span className="form-label__hint">AI 評分時會列為負面因素</span>
          </label>
          <input
            type="text"
            id="avoided-industries"
            className="form-input"
            placeholder="例：傳統製造業, 保險業"
            value={prefs.avoided_industries}
            onChange={e => update('avoided_industries', e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="user-name">
            姓名
            <span className="form-label__hint">用於推薦信結尾署名</span>
          </label>
          <input
            type="text"
            id="user-name"
            className="form-input"
            placeholder="例：Pin Yuan Chen"
            value={prefs.user_name}
            onChange={e => update('user_name', e.target.value)}
          />
        </div>

        <p style={{ fontSize: '0.8rem', opacity: 0.55, marginTop: '0.5rem' }}>
          自動儲存，無需按確認
        </p>
      </section>
    </div>
  )
}
