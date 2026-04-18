import type { EvaluationDimensions } from '../types'

interface Props {
  dimensions: EvaluationDimensions
}

const SCORE_BARS: { key: keyof EvaluationDimensions; label: string }[] = [
  { key: 'skill_match', label: '技能匹配' },
  { key: 'salary_fairness', label: '薪資合理' },
  { key: 'growth_potential', label: '成長空間' },
  { key: 'location_flexibility', label: '地理彈性' },
]

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = ((value - 1) / 4) * 100
  const color = value >= 4 ? '#10b981' : value >= 2.5 ? '#f59e0b' : '#ef4444'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem' }}>
      <span style={{ minWidth: '4.5rem', opacity: 0.7 }}>{label}</span>
      <div style={{ flex: 1, height: '6px', borderRadius: '3px', background: 'var(--color-border, rgba(255,255,255,0.08))' }}>
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: '3px', background: color, transition: 'width 0.3s' }} />
      </div>
      <span style={{ minWidth: '1.8rem', textAlign: 'right', color, fontWeight: 600 }}>
        {value.toFixed(1)}
      </span>
    </div>
  )
}

export default function DimensionsPanel({ dimensions }: Props) {
  const isLowScore = dimensions.overall_score < 3.5

  return (
    <div className="ai-result__dimensions">
      {isLowScore && (
        <div style={{
          background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: '8px',
          padding: '0.5rem 0.75rem',
          fontSize: '0.83rem',
          color: '#ef4444',
          marginBottom: '0.75rem',
        }}>
          ⚠️ 不建議投遞（綜合評分 {dimensions.overall_score.toFixed(1)} / 5）
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.6rem' }}>
        <span style={{
          fontSize: '0.75rem',
          padding: '0.15rem 0.55rem',
          borderRadius: '999px',
          background: 'var(--color-tag-bg, rgba(99,102,241,0.15))',
          color: 'var(--color-tag-text, #818cf8)',
        }}>
          {dimensions.job_category}
        </span>
        <span style={{
          fontSize: '0.75rem',
          padding: '0.15rem 0.55rem',
          borderRadius: '999px',
          background: dimensions.level_move === '升遷'
            ? 'rgba(16,185,129,0.12)'
            : dimensions.level_move === '後退'
              ? 'rgba(239,68,68,0.12)'
              : 'rgba(245,158,11,0.12)',
          color: dimensions.level_move === '升遷'
            ? '#10b981'
            : dimensions.level_move === '後退'
              ? '#ef4444'
              : '#f59e0b',
        }}>
          職級：{dimensions.level_move}
        </span>
        <span style={{
          fontSize: '0.75rem',
          padding: '0.15rem 0.55rem',
          borderRadius: '999px',
          background: isLowScore ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)',
          color: isLowScore ? '#ef4444' : '#10b981',
        }}>
          綜合 {dimensions.overall_score.toFixed(1)} / 5
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        {SCORE_BARS.map(({ key, label }) => (
          <ScoreBar key={key} label={label} value={dimensions[key] as number} />
        ))}
      </div>
    </div>
  )
}
