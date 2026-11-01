import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import type { Briefing, EventItem, Fact, Health, LeadsResponse, ScreenItem, Target } from './types'
import { LEAD_STAGES } from './types'

type LoadState<T> = { data: T | null; error: string | null }

function usePolling<T>(fetcher: () => Promise<T>, ms: number): LoadState<T> {
  const [state, setState] = useState<LoadState<T>>({ data: null, error: null })
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const data = await fetcher()
        if (alive) setState({ data, error: null })
      } catch (err) {
        if (alive) setState((prev) => ({ data: prev.data, error: String(err) }))
      }
    }
    tick()
    const id = setInterval(tick, ms)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [fetcher, ms])
  return state
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <div className="card-k">{title}</div>
      <div className="card-v">{children}</div>
    </section>
  )
}

const ok = (v: boolean) => (v ? 'ok' : 'bad')
const warn = (v: boolean) => (v ? 'ok' : 'warn')

function MorningBriefing() {
  const [brief, setBrief] = useState<Briefing | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sweeping, setSweeping] = useState(false)
  const [sweepMsg, setSweepMsg] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setBrief(await api.briefing())
      setError(null)
    } catch (err) {
      setError(String(err))
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const runSweep = async () => {
    setSweeping(true)
    setSweepMsg(null)
    try {
      const r = await api.runSweep()
      setSweepMsg(
        `swept ${r.targets_total} targets → ${r.facts_learned} new facts to review`
      )
      await refresh()
    } catch (err) {
      setSweepMsg(String(err))
    } finally {
      setSweeping(false)
    }
  }

  const s = brief?.summary

  return (
    <section className="card wide">
      <div className="card-k">Morning briefing</div>
      <div className="card-v">
        {error && <p className="bad">{error}</p>}
        {!brief && !error && <p className="muted">loading…</p>}
        {brief && s && (
          <>
            <p className="brief-date">{brief.date}</p>
            <div className="brief-stats">
              <span>studied <b>{s.targets_studied}</b></span>
              <span>learned <b>{s.facts_learned}</b></span>
              <span>awaiting you <b>{s.facts_pending}</b></span>
              <span>opportunities <b>{s.opportunities}</b></span>
              {s.failures > 0 && <span className="bad">failed {s.failures}</span>}
            </div>

            {brief.opportunities.length > 0 && (
              <div className="opps">
                {brief.opportunities.slice(0, 5).map((op, i) => (
                  <div key={i} className="opp-row">
                    <span className={`opp-kind ${op.kind}`}>{op.kind}</span>
                    <div>
                      <div className="opp-title">{op.title}</div>
                      <div className="muted">{op.why}</div>
                      <div className="opp-action">next: {op.suggested_action}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="brief-actions">
              <button disabled={sweeping} onClick={runSweep}>
                {sweeping ? 'sweeping…' : 'run sweep now'}
              </button>
              <button className="ghost" onClick={refresh}>
                refresh briefing
              </button>
              {sweepMsg && <span className="notice">{sweepMsg}</span>}
            </div>
          </>
        )}
      </div>
    </section>
  )
}

function Leads() {
  const [data, setData] = useState<LeadsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setData(await api.leads())
      setError(null)
    } catch (err) {
      setError(String(err))
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const runFinder = async () => {
    setBusy(true)
    setNotice(null)
    try {
      const r = await api.findLeads()
      setNotice(
        `scanned ${r.candidates} candidates → ${r.added.length} new leads ` +
          `(${r.skipped_existing} already known, ${r.below_threshold} below score)`
      )
      await refresh()
    } catch (err) {
      setNotice(String(err))
    } finally {
      setBusy(false)
    }
  }

  const advance = async (id: number, stage: string) => {
    setBusy(true)
    try {
      const r = await api.moveLeadStage(id, stage)
      setNotice(r.detail)
      await refresh()
    } catch (err) {
      setNotice(String(err))
    } finally {
      setBusy(false)
    }
  }

  const p = data?.pipeline
  const nextStage: Record<string, string> = {
    new: 'contacted',
    contacted: 'replied',
    replied: 'proposal',
    proposal: 'won',
  }

  return (
    <section className="card wide">
      <div className="card-k">Leads — prospecting pipeline</div>
      <div className="card-v">
        {error && <p className="bad">{error}</p>}
        {p && (
          <div className="pipe-stats">
            {LEAD_STAGES.map((s) => (
              <span key={s} className={`pipe-chip ${s}`}>
                {s} <b>{p.counts[s]}</b>
              </span>
            ))}
            <span className="muted">
              {p.total} total · win rate {p.win_rate}%
            </span>
          </div>
        )}

        {data && data.items.length > 0 && (
          <div className="leads">
            {data.items.slice(0, 12).map((l) => (
              <div key={l.id} className={`lead-row stage-${l.stage}`}>
                <span className={`lead-grade ${l.grade}`}>{l.grade}</span>
                <div className="lead-main">
                  <div className="lead-name">
                    {l.name}
                    <span className="lead-loc">
                      {l.location && ` · ${l.location}`} · {l.stage}
                    </span>
                  </div>
                  <ul className="lead-reasons">
                    {l.reasons.slice(0, 3).map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
                <div className="lead-score">{l.score}</div>
                <div className="lead-actions">
                  {nextStage[l.stage] && (
                    <button
                      disabled={busy}
                      onClick={() => advance(l.id, nextStage[l.stage])}
                    >
                      → {nextStage[l.stage]}
                    </button>
                  )}
                  {l.stage !== 'lost' && l.stage !== 'won' && (
                    <button
                      className="ghost"
                      disabled={busy}
                      onClick={() => advance(l.id, 'lost')}
                    >
                      lost
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        {data && data.items.length === 0 && (
          <p className="muted">
            No leads yet — run the finder to mine what Gideon knows.
          </p>
        )}

        <div className="brief-actions">
          <button disabled={busy} onClick={runFinder}>
            {busy ? 'working…' : 'run lead finder'}
          </button>
          <button className="ghost" onClick={refresh}>
            refresh
          </button>
          {notice && <span className="notice">{notice}</span>}
        </div>
      </div>
    </section>
  )
}

function LearningLoop() {
  const [targets, setTargets] = useState<Target[]>([])
  const [pending, setPending] = useState<Fact[]>([])
  const [hungerMsg, setHungerMsg] = useState('')
  const [busy, setBusy] = useState<number | 'new' | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', url: '', kind: 'competitor' })

  const refresh = useCallback(async () => {
    try {
      const [t, a] = await Promise.all([api.targets(), api.approvals()])
      setTargets(t.items)
      setPending(a.items)
      setHungerMsg(t.hunger.hunger.message)
    } catch (err) {
      setNotice(String(err))
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const act = async (key: number | 'new', fn: () => Promise<void>) => {
    setBusy(key)
    setNotice(null)
    try {
      await fn()
      await refresh()
    } catch (err) {
      setNotice(String(err))
    } finally {
      setBusy(null)
    }
  }

  const addTarget = () =>
    act('new', async () => {
      if (!form.name.trim() || !form.url.trim()) throw new Error('name and url required')
      await api.addTarget(form)
      setForm({ name: '', url: '', kind: 'competitor' })
    })

  return (
    <section className="card wide">
      <div className="card-k">Learning loop</div>
      <div className="card-v">
        <p className={`hunger ${pending.length ? 'warn' : 'ok'}`}>
          {hungerMsg || '…'} {pending.length > 0 && `· ${pending.length} awaiting your approval`}
        </p>

        <div className="targets">
          {targets.map((t) => (
            <div key={t.id} className={`target-row ${t.active ? '' : 'paused'}`}>
              <span className="target-name">
                [{t.kind}] {t.name}
                {!t.active && <span className="paused-tag"> paused</span>}
              </span>
              <span className="target-meta">
                {t.last_researched
                  ? `studied ${t.last_researched.slice(0, 10)}`
                  : 'not yet studied'}
              </span>
              {t.active ? (
                <>
                  <button
                    disabled={busy === t.id}
                    onClick={() =>
                      act(t.id, async () => {
                        const r = await api.research(t.id)
                        setNotice(
                          r.ok
                            ? `studied ${t.name}: ${r.added.length} new facts to review`
                            : `study failed: ${r.error}`
                        )
                      })
                    }
                  >
                    {busy === t.id ? 'studying…' : 'study now'}
                  </button>
                  <button
                    className="ghost"
                    disabled={busy === t.id}
                    onClick={() => act(t.id, () => api.pauseTarget(t.id).then(() => {}))}
                  >
                    pause
                  </button>
                </>
              ) : (
                <button
                  disabled={busy === t.id}
                  onClick={() => act(t.id, () => api.resumeTarget(t.id).then(() => {}))}
                >
                  resume
                </button>
              )}
            </div>
          ))}
          {targets.length === 0 && <p className="muted">No targets yet — add one below.</p>}
        </div>

        <div className="add-row">
          <input
            placeholder="Name (e.g. Salon Kings)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            placeholder="https://competitor-site.com"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
          />
          <select
            value={form.kind}
            onChange={(e) => setForm({ ...form, kind: e.target.value })}
          >
            <option value="competitor">competitor</option>
            <option value="market">market</option>
            <option value="prospect">prospect</option>
            <option value="resource">resource</option>
          </select>
          <button disabled={busy === 'new'} onClick={addTarget}>
            {busy === 'new' ? 'adding…' : '+ add target'}
          </button>
        </div>

        {notice && <p className="notice">{notice}</p>}

        {pending.length > 0 && (
          <div className="queue">
            <div className="queue-title">Approval queue — nothing becomes memory without you</div>
            {pending.slice(0, 8).map((f) => (
              <div key={f.id} className="fact-row">
                <span className="fact-text">{f.content}</span>
                <span className="fact-src">{f.category}</span>
                <button
                  disabled={busy === f.id}
                  onClick={() => act(f.id, () => api.approveFact(f.id).then(() => {}))}
                >
                  approve
                </button>
              </div>
            ))}
            {pending.length > 8 && (
              <p className="muted">…and {pending.length - 8} more</p>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

export default function App() {
  const health = usePolling<Health>(() => api.health(), 10_000)
  const events = usePolling<EventItem[]>(() => api.events(1), 15_000)
  const screens = usePolling<ScreenItem[]>(() => api.screens(), 30_000)

  const h = health.data

  return (
    <main className="shell">
      <div className="badge">Nexora Growth Agent</div>
      <h1>GIDEON</h1>
      <p className="tagline">Digital systems that move businesses forward.</p>

      <div className="grid">
        <Card title="Core">
          {h ? (
            <>
              <span className={ok(h.status === 'ok')}>{h.status}</span> · v{h.version}
            </>
          ) : (
            'connecting…'
          )}
        </Card>

        <Card title="Storage">
          {h ? (
            <>
              <span className={ok(h.database.ok)}>
                {h.database.ok ? 'healthy' : 'error'}
              </span>{' '}
              · {h.database.tables.length} tables
            </>
          ) : (
            '…'
          )}
        </Card>

        <Card title="Constitution">
          {h ? (
            <>
              {h.constitution.autonomy} ·{' '}
              <span className="warn">{h.constitution.ledger_claims} claims</span>
            </>
          ) : (
            '…'
          )}
        </Card>

        <Card title="LLM">
          {h ? (
            h.llm.ok ? (
              <span className={warn(true)}>{h.llm.models.length} model(s)</span>
            ) : (
              <span className="warn">ollama offline</span>
            )
          ) : (
            '…'
          )}
        </Card>

        <Card title="Last event">
          {events.error ? (
            <span className="bad">{events.error}</span>
          ) : (
            events.data?.[0]?.summary ?? 'none yet'
          )}
        </Card>

        <Card title="Data screens">
          {screens.data?.length ? `${screens.data.length} saved` : 'none yet'}
        </Card>
      </div>

      <MorningBriefing />
      <Leads />
      <LearningLoop />

      <p className="status">
        {health.error
          ? `⚠ ${health.error}`
          : h
            ? `Status: ${h.status} · data at ${h.data_dir}`
            : 'Initializing…'}
      </p>

      <footer className="footer">
        PHASE 0 · FOUNDATION · GIDEON DISPLAY ARRIVES IN PHASE 7
      </footer>
    </main>
  )
}
