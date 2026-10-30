import { useEffect, useState } from 'react'
import { api } from './api'
import type { EventItem, Health, ScreenItem } from './types'

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
