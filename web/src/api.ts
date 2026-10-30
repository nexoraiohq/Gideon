import type { EventItem, Health, ScreenItem } from './types'

async function getJson<T>(path: string): Promise<T> {
  const resp = await fetch(path)
  if (!resp.ok) throw new Error(`${path} → HTTP ${resp.status}`)
  return (await resp.json()) as T
}

export const api = {
  health: () => getJson<Health>('/api/health'),
  events: (limit = 5) => getJson<EventItem[]>(`/api/events?limit=${limit}`),
  screens: () => getJson<ScreenItem[]>('/api/screens'),
}
