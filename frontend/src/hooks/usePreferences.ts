import { useLocalStorage } from './useLocalStorage'

export interface UserPreferences {
  target_salary: number
  preferred_tech: string
  career_goals: string
  avoided_industries: string
  user_name: string
}

const DEFAULT_PREFS: UserPreferences = {
  target_salary: 0,
  preferred_tech: '',
  career_goals: '',
  avoided_industries: '',
  user_name: '',
}

export function usePreferences() {
  return useLocalStorage<UserPreferences>('careerpilot_prefs', DEFAULT_PREFS)
}

export function formatPrefsForPrompt(prefs: UserPreferences): string {
  const parts: string[] = []
  if (prefs.target_salary > 0)
    parts.push(`目標薪資：${prefs.target_salary.toLocaleString()} 元/月以上`)
  if (prefs.preferred_tech) parts.push(`偏好技術/產業：${prefs.preferred_tech}`)
  if (prefs.career_goals) parts.push(`職涯目標：${prefs.career_goals}`)
  if (prefs.avoided_industries) parts.push(`避開產業：${prefs.avoided_industries}`)
  if (parts.length === 0) return ''
  return `\n\n[個人偏好]\n${parts.join('\n')}`
}
