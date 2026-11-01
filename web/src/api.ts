import type {
  ApprovalsResponse,
  Briefing,
  EventItem,
  Health,
  ScreenItem,
  TargetsResponse,
} from './types'

async function getJson<T>(path: string): Promise<T> {
  const resp = await fetch(path)
  if (!resp.ok) throw new Error(`${path} → HTTP ${resp.status}`)
  return (await resp.json()) as T
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(path, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!resp.ok) {
    const detail = await resp.text().catch(() => '')
    throw new Error(`${path} → HTTP ${resp.status} ${detail}`)
  }
  return (await resp.json()) as T
}

export const api = {
  health: () => getJson<Health>('/api/health'),
  events: (limit = 5) => getJson<EventItem[]>(`/api/events?limit=${limit}`),
  screens: () => getJson<ScreenItem[]>('/api/screens'),
  targets: () => getJson<TargetsResponse>('/api/targets'),
  approvals: () => getJson<ApprovalsResponse>('/api/approvals'),
  addTarget: (data: { name: string; url: string; kind: string }) =>
    postJson<{ target_id: number }>('/api/targets', data),
  research: (id: number) =>
    postJson<{ ok: boolean; added: number[]; skipped: number; error?: string }>(
      `/api/targets/${id}/research`
    ),
  pauseTarget: (id: number) =>
    postJson<{ paused: boolean }>(`/api/targets/${id}/pause`),
  resumeTarget: (id: number) =>
    postJson<{ resumed: boolean }>(`/api/targets/${id}/resume`),
  approveFact: (id: number) =>
    postJson<{ approved: boolean }>(`/api/facts/${id}/approve`),
  briefing: (hours = 24) => getJson<Briefing>(`/api/briefing?hours=${hours}`),
  runSweep: () =>
    postJson<{ targets_total: number; facts_learned: number; failed: unknown[] }>(
      '/api/sweep'
    ),
}
