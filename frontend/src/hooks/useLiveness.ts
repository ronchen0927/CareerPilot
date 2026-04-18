import { useEffect, useState } from 'react'
import { fetchLivenessStatus, triggerLivenessCheck } from '../api/client'
import type { LivenessMap } from '../types'

export function useLiveness(urls: string[]) {
  const urlKey = urls.slice().sort().join('\n')
  const [statusMap, setStatusMap] = useState<LivenessMap>({})
  const [recheckLoading, setRecheckLoading] = useState(false)

  useEffect(() => {
    if (!urlKey) return
    const list = urlKey.split('\n').filter(Boolean)
    fetchLivenessStatus(list)
      .then(setStatusMap)
      .catch(() => {})
  }, [urlKey])

  async function recheck() {
    const list = urlKey.split('\n').filter(Boolean)
    if (list.length === 0) return
    setRecheckLoading(true)
    try {
      await triggerLivenessCheck(list)
      const data = await fetchLivenessStatus(list)
      setStatusMap(data)
    } catch {
      // fail silently — liveness is non-critical
    } finally {
      setRecheckLoading(false)
    }
  }

  return { statusMap, recheckLoading, recheck }
}
