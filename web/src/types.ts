/** Types mirroring the FastAPI response contracts (single source: gideon/app.py). */

export interface DatabaseHealth {
  ok: boolean
  tables: string[]
  path: string
  error?: string
}

export interface ConstitutionHealth {
  version: string
  autonomy: string
  ledger_claims: number
}

export interface OllamaStatus {
  ok: boolean
  url: string
  models: string[]
  error?: string
}

export interface Health {
  status: 'ok' | 'degraded'
  version: string
  data_dir: string
  database: DatabaseHealth
  constitution: ConstitutionHealth
  llm: OllamaStatus
}

export interface EventItem {
  id: number
  ts: string
  kind: string
  summary: string
  payload: Record<string, unknown>
}

export interface ScreenItem {
  id: number
  created_at: string
  kind: string
  title: string
}
