# GIDEON — Nexora Growth Agent
### Build Plan (planning document only — build not started, awaiting approval)

> **Mission:** Take Nexora Studio from zero clients to predictable monthly cashflow.
> **Behavior:** A Gideon-style AI chief of staff (The Flash) — always researching, calm and
> precise, proactive with briefings, loyal to the owner's decisions, honest in every claim.

---

## 1. Persona Specification (Gideon mode — applies to EVERYTHING)

| Trait | In practice |
|---|---|
| Calm & precise | Short clear sentences. No filler. Data first, then recommendation. |
| Proactive, never intrusive | Reports at scheduled times (morning/evening). Interrupts only for real revenue opportunities. |
| Presents, doesn't push | Shows findings + options + its recommendation, then waits: *"I recommend X. Your call."* |
| Always ready | Voice wake-word / hotkey — it's listening the moment it's addressed. |
| Knows its place | Green decisions it acts on. Yellow it proposes. Red it never does. |
| Transparency | On "why?" it explains reasoning and cites sources, like Gideon pulling up data on screen. |
| Honest selling | Every claim traceable to the Delivery Ledger. No promises Nexora can't deliver. |

---

## 2. The Constitution (rules that outrank everything)

### 2.1 Delivery Ledger (source of truth)
A verified file of what Nexora actually delivers: services, tech stack, timelines, pricing
boundaries, real case studies (States Barbershop), testimonials, capacity.
- Every outbound message, post, and proposal is fact-checked against it **before generation reaches you**.
- Unverifiable claims (e.g. "#1 agency", "200% sales increase") are **blocked at generation time**.
- Out-of-capacity requests from prospects are flagged as business signals: *"new service demand."*

### 2.2 Decision tiers
| Tier | Examples | Action |
|---|---|---|
| 🟢 Decide alone | Lead prioritization, message wording, follow-up timing, playbook tuning, research priorities | Act + log in daily report |
| 🟡 Propose, wait | Pricing changes, new services, publishing posts, new channels, spending money, self-code changes | Proposal with reasoning → owner yes/no |
| 🔴 Never | Contracts, refunds, legal claims, promises beyond ledger, anything public as Nexora | Blocked by rule |

### 2.3 Autonomy ladder (earn trust over time)
1. **Weeks 1–2:** every message (email included) waits for one-tap approval.
2. **Earned:** email auto-sends within rules (daily caps, tone guardrails, no pricing without review). WhatsApp stays "Gideon drafts → owner sends" permanently by default.
3. **Never without owner:** pricing quotes, contracts, public posts, refunds.

---

## 3. Core Modules

### M1 — Brain & Memory
- Local LLM (Ollama) + SQLite knowledge store with embeddings for recall.
- Stores: Nexora profile (learned from site/docs), Delivery Ledger, facts with **source URL + date**, conversation history, decisions log.

### M2 — Target-Driven Learning
Owner sets a **target** (URL / topic / document set) + a **learning instruction**.
Loop: crawl (depth-limited, robots.txt-aware, rate-limited) → extract **structured facts** →
owner approves (keep/edit/discard) → stored with source + date → optional re-visit schedule
to detect **changes** (prices, posts, offerings).

### M3 — Autonomous Research & Opportunity Engine (no prompting — default behavior)
- **Morning deep research** (~first thing daily): sweeps overnight, compiles briefing.
- **All-day background scan:** light polling; urgent signals escalate immediately.
- **Triggered dives:** investigates interesting signals on its own initiative.

Standing watch list:
| Stream | Opportunity type |
|---|---|
| New businesses opening (salons/spas/barbershops) | Brand-new lead, no website yet |
| Existing businesses with broken/outdated sites | Conversion-ready prospect |
| Competitor moves (pricing, offers, content) | Strategic response needed |
| SEO/ranking shifts in niche (incl. own site) | Visibility drifting up/down |
| Kisii/Kenya market & business news | New demand, new service idea |
| Emerging tech/tools | "Nexora could offer X now" |

**Opportunity rule:** anything that could produce revenue or force a strategic decision is
escalated prominently — never buried.

### M4 — Prospecting & Pipeline (CRM)
Finds + qualifies prospects (salons, barbershops, spas in Kisii/Nairobi/Kenya/etc. with weak
or no web presence), scores them (fit, budget signals, urgency), tracks every stage:
found → contacted → replied → briefed → proposal → won/lost.

### M5 — Outreach (channel routing per lead)
- **Email** → Gideon sends (after approval phase; later within rules). Needs a sending account
  (Gmail SMTP or Resend/Mailgun free tier) with SPF/DKIM/DMARC set, warm-up + daily caps.
- **WhatsApp / Instagram** → Gideon writes it, delivers pre-written message to owner's phone;
  owner taps send. *(Unofficial WhatsApp automation = ban risk — avoided by design.)*
- **Gideon chooses the channel per prospect** based on where that business is reachable.
- **Promise guardrail** on every draft: claim must map to Delivery Ledger or be removed.
- Follow-up scheduler: no lead forgotten.

### M6 — Sales, Psychology & Evidence Learning
- Playbook seeded with established frameworks: discovery, objection handling, social proof,
  trust triggers, clear single call-to-action — applied honestly.
- **Evidence loop:** reply rates rewrite the playbook permanently (A gets 3× replies of B → A wins).
- Owner edits/rejections teach taste and standards.

### M7 — Content Engine
Creates posts/blogs/case-study carousels **when the strategy calls for it** (segment heating up,
competitor move, strong proof point). Draft → owner approval → publish → engagement tracked →
learned. Grounded in Delivery Ledger.

### M8 — CEO Layer (plans & reports)
- **Morning plan:** pipeline targets, today's tasks, strategy-change suggestions with reasoning.
- **Evening report:** what it did, what it found, who replied, decisions made (+ why), tomorrow's plan.
- Suggests next steps like a chief of staff; big calls still come to the owner.

### M9 — Voice Interface
- Wake word ("Hey Nexora") or push-to-talk hotkey.
- **Local** STT (Whisper) + local TTS for replies — voice never leaves the machine.
- All commands available by voice or keyboard: *"What did you find this morning?"*,
  *"Send the proposal to Embarca."*, *"Add a feature that tracks my Google rankings."*

### M10 — Code Agent (site fixes → self-features)
- **Phase A — Nexora's site:** detects SEO/performance problems, proposes fixes, implements
  (new landing pages, meta, structure) → tests → owner approves → deploy (Vercel).
- **Phase B — self-features:** owner says *"add feature X"* → it writes a plan → builds module →
  runs test suite → shows result → registers skill → reported in evening brief.
- **Guardrails:** modular skills (never core engine), git versioning, pytest suite as ship gate,
  approval gate by severity, one-command rollback ("undo" → yesterday's agent).

---

## 4. Daily Rhythm (the Gideon day)

```
☀️ MORNING      Deep research sweep → briefing: findings, opportunities (max 2–3 escalated),
                overnight pipeline status, today's plan → owner approves/adjusts
⚙️ DAYTIME      Research background scan · outreach execution · follow-ups ·
                lead qualification · prepare closing briefs · content drafts when called for
🌙 EVENING      Report: actions taken · findings · replies · decisions (+why) · tomorrow's plan
🔁 ALWAYS       Learning loop: playbook, priorities, standards from evidence + owner feedback
```

**Sample morning briefing:**
> *"Good morning. Research complete — 47 sources scanned overnight.*
> *2 opportunities need you: (1) New salon 'Luxe Beauty Bar' opened in Kisii 3 days ago —
> Instagram only, no website. Outreach ready for approval. (2) Your 'barbershop website kenya'
> page moved #14 → #8; competitor published a pricing page — comparison attached.*
> *Pipeline: 3 new prospects added, Embarca awaiting proposal, no negative mentions.*
> *Today's plan: Embarca draft, 8 prospects, spa-targeted post. Proceed?"*

---

## 5. Tech Stack (local, Windows)

| Layer | Choice | Why |
|---|---|---|
| LLM | Ollama (Qwen/Llama-class model) | Free, private, local; optional hybrid API for hard tasks |
| Backend | Python 3.11+ / FastAPI | Fits scraping, scheduling, AI ecosystem |
| Memory | SQLite + local embeddings (chromadb/sqlite-vec) | Zero-infra, portable |
| Scraping | requests + BeautifulSoup / Playwright | robots.txt-aware, rate-limited |
| Search | DuckDuckGo/SearXNG (free), optional Tavily free tier | No-cost research |
| Scheduling | APScheduler | Morning/evening/background jobs |
| Voice | faster-whisper (STT) + Piper (TTS) | Fully offline |
| Email | Gmail SMTP or Resend (free tier) | With SPF/DKIM/DMARC + warm-up |
| UI | Local web dashboard (FastAPI + simple frontend) | Approvals, pipeline, reports |
| Code agent | Git + pytest + sandboxed exec | Ship gate = tests pass; rollback = git revert |
| PC scheduling | Windows Task Scheduler / service | Runs even when closed |

**Costs:** LLM local = $0. Optional hybrid API + email service free tiers = small monthly.
Search free tiers sufficient at start.

---

## 6. Build Phases (each ends with a working, testable milestone)

- [ ] **Phase 0 — Foundation:** repo, Python env, Ollama running, dashboard skeleton, git.
- [ ] **Phase 1 — Identity:** learn Nexora (site ingested), build Delivery Ledger, constitution
      (decision tiers, guardrails) encoded. *Test: ask it about Nexora → accurate, cited answers.*
- [ ] **Phase 2 — Learning:** target-driven learning loop with approval UI. *Test: give it a
      competitor URL → structured facts → approve → stored with source.*
- [ ] **Phase 3 — Research engine:** morning sweep + watch list + opportunity detector +
      first morning briefing. *Test: wake up to a real briefing.*
- [ ] **Phase 4 — Prospecting:** lead finder + scoring + pipeline/CRM. *Test: 10 real qualified
      prospects with reasons.*
- [ ] **Phase 5 — Outreach:** drafts + promise guardrail + approval flow + email sending +
      WhatsApp relay + follow-ups. *Test: first approved outreach goes out.*
- [ ] **Phase 6 — CEO reports:** evening report + morning plan/strategy suggestions. *Test: full
      day of autonomous action reported accurately.*
- [ ] **Phase 7 — Evidence learning:** reply-rate tracking rewrites playbook. *Test: measurable
      playbook change after enough replies.*
- [ ] **Phase 8 — Voice + Gideon persona:** wake word, STT/TTS, persona across all surfaces.
      *Test: voice briefing each morning.*
- [ ] **Phase 9 — Content engine:** strategy-driven drafts with approval + tracking.
- [ ] **Phase 10 — Code agent (site):** SEO audit → proposed fixes → approved changes to
      nexoraio.vercel.app.
- [ ] **Phase 11 — Code agent (self):** feature requests → plan → build → tests → register,
      with rollback.

---

## 7. Data Model (sketch)

- `facts(id, content, source_url, learned_at, approved_by, category, expires_at)`
- `ledger_claims(id, claim, evidence, status)` — the Delivery Ledger
- `leads(id, name, type, city, channels, score, stage, reasons, created_at)`
- `messages(id, lead_id, channel, body, status[draft/approved/sent], created_at, reply_count)`
- `conversations(lead_id, summary, temperature, next_action)`
- `playbook(id, pattern, evidence_rate, weight, updated_at)`
- `decisions(id, tier, action, rationale, result, decided_at)`
- `research_items(id, stream, content, opportunity_flag, briefing_date)`
- `tasks(id, plan_date, description, status)`
- `modules(id, name, version, tests_passed, enabled)` — self-added features registry

---

## 8. Open Decisions (confirm before build)

1. **Email identity:** which sending account? (e.g. hello@nexora domain vs Gmail)
2. **Research PC schedule:** hours Gideon runs daily (machine must be on).
3. **Hybrid API:** local-only to start, or add a small paid API budget for harder reasoning?
4. **WhatsApp relay form:** push notification to owner's phone vs. copy-paste tray in dashboard.
5. **Model choice:** benchmark 2–3 Ollama models on sales-writing quality before committing.

---

## 9. Honest Limits (kept visible on purpose)

- Local models are weaker than cloud ones — hybrid mode available if a task needs it.
- It books qualified conversations; humans still close deals.
- Learning happens within its design and evidence — it is a relentless specialist, not
  open-ended superintelligence.
- Research obeys robots.txt, site terms, and rate limits — protection for the business.
- Autonomy is earned, logged, and reversible at every step.

---

## 10. Build Schedule

- **Build sessions: weekends only** (owner works weekdays; Gideon grows on Saturdays/Sundays)
- Owner will remind at the start of each build session
- Each session targets the next unfinished phase — always leave with a tested, working milestone
- First session: **this weekend** → Phase 0 (Foundation)

---

*Status: PLAN ONLY. No code written. Awaiting "go" to begin Phase 0 — weekend session 1.*
