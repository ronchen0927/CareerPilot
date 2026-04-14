import type { Option } from '../types'

interface Props {
  options: Option[]
  selected: string[]
  prefix: string
  onChange: (values: string[]) => void
}

export default function CheckboxGroup({ options, selected, prefix, onChange }: Props) {
  function handleChange(value: string, checked: boolean) {
    onChange(checked ? [...selected, value] : selected.filter(v => v !== value))
  }

  return (
    <div className="checkbox-grid">
      {options.map((opt, i) => (
        <div className="checkbox-chip" key={opt.value}>
          <input
            type="checkbox"
            id={`${prefix}-${i}`}
            value={opt.value}
            checked={selected.includes(opt.value)}
            onChange={e => handleChange(opt.value, e.target.checked)}
          />
          <label htmlFor={`${prefix}-${i}`}>{opt.label}</label>
        </div>
      ))}
    </div>
  )
}
