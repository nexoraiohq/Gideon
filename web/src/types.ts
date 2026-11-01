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

export interface Fact {
  id: number
  content: string
  category: string
  source_url: string | null
  learned_at: string
  approved: number
}

export interface HungerStatus {
  day: string
  items: number
  chars: number
  min_items: number
  min_chars: number
  hungry: boolean
  message: string
}

export interface Target {
  id: number
  name: string
  url: string
  kind: string
  notes: string
  active: number
  created_at: string
  last_researched: string | null
}

export interface TargetsResponse {
  items: Target[]
  hunger: {
    hunger: HungerStatus
    active_targets: number
    pending_approvals: number
    approved_facts: number
  }
}

export interface ApprovalsResponse {
  items: Fact[]
  pending: number
}

export interface Opportunity {
  kind: string
  title: string
  why: string
  evidence: { fact_id: number; source_url: string | null }[]
  suggested_action: string
  evidence_count: number
}

export interface Briefing {
  date: string
  hours: number
  summary: {
    sweeps: number
    targets_studied: number
    facts_learned: number
    facts_pending: number
    facts_approved_recent: number
    failures: number
    opportunities: number
  }
  opportunities: Opportunity[]
  hunger: HungerStatus
  text: string
}

export const LEAD_STAGES = [
  'new',
  'contacted',
  'replied',
  'proposal',
  'won',
  'lost',
] as const

export type LeadStage = (typeof LEAD_STAGES)[number]

export interface Lead {
  id: number
  name: string
  kind: string
  location: string
  url: string | null
  contact: string
  source_url: string | null
  score: number
  grade: string
  reasons: string[]
  stage: LeadStage
  notes: string
  created_at: string
  updated_at: string
}

export interface PipelineReport {
  counts: Record<LeadStage, number>
  avg_scores: Record<string, number>
  total: number
  won: number
  win_rate: number
}

export interface LeadsResponse {
  items: Lead[]
  total: number
  pipeline: PipelineReport
}

export interface FindLeadsResponse {
  candidates: number
  added: { id: number; name: string; score: number; reasons: string[] }[]
  skipped_existing: number
  below_threshold: number
}
