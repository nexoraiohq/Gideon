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

## 2A. The Brain — Gideon's Own Mind (owner decision: build from scratch)

**Decision:** No paid APIs. No downloaded pre-trained models. Gideon thinks with a brain
**built in this repo** using standard ML libraries (PyTorch, CPU build), trained from
random initialization on text we gather ourselves. Libraries are tools — like textbooks
for a child — not someone else's mind.

**Architecture (all written here):**
- **Own tokenizer:** byte-pair encoding implemented in-repo, trained on our corpus
- **Decoder-only transformer** (GPT-style), PyTorch, from-scratch initialization
- **GPU-ready from day one:** everything config-driven (`device: cpu|cuda`); when a GPU
  is purchased, the same code trains bigger models with zero rewrite
- Checkpoints live in `data/brain/` — our disk, our weights, ours

**Training data (the curriculum):** Nexora's own materials → publicly available text we
collect → Gideon's own approved messages + outcomes (what actually earned replies).
Like a human: it becomes *unique* by being raised on Nexora's way of thinking.

**Growth path:**
| Stage | Params | Hardware | Trains in | Can do |
|---|---|---|---|---|
| v0-nano | ~1–3M | your CPU, 6 GB RAM | hours per run | grammar, short phrases, scoring |
| v1 | ~10–50M | CPU (slow) / small GPU | days | short messages, summaries |
| v2 | ~100M–1B | the GPU you buy | days–week | real writing & reasoning |

**Honest expectations:** v0 is an *infant*. Early phases lean on rules, retrieval and
statistical modules — also ours, also trained here — while the brain grows. Fluency
ramps with data + scale; the Gideon voice emerges from the curriculum, not from a vendor.
**Cost forever: $0 + electricity.**

---

## 3. Core Modules

### M1 — Brain & Memory
- **Gideon's own brain** (Phase 1 — built from scratch) + SQLite knowledge store with
  locally computed retrieval (TF-IDF/bag-of-words now, brain embeddings later —
  no external embedding APIs, ever).
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
| **Brain** | **Own transformer (PyTorch CPU)** — built from scratch in-repo | $0 forever: no API, no downloaded weights; `cuda` switch ready for future GPU |
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

**Costs:** brain = **$0 forever** (electricity only; PyTorch is a free pip-installable
library, not a model). Email free tiers sufficient to start. GPU purchase optional later.
Search free tiers sufficient at start.

---

## 6. Build Phases (each ends with a working, testable milestone)

- [x] **Phase 0 — Foundation:** project structure, storage layout, constitution, test suite,
      git safety net, React+TS dashboard. **COMPLETE — 24/24 tests, build + serve smoke green.**
- [x] **Phase 1 — The Brain v0:** our own tokenizer + decoder-only transformer trained from
      scratch on CPU, `device: cpu|cuda` switch built in. **COMPLETE — 1.97M params born from
      random init, loss 6.14 → 1.90 in 250 steps on the Nexora curriculum; 57/57 tests; pushed
      to GitHub (`86e9583`).** Newborn's first words logged; checkpoints in `data/brain/`.
- [x] **Phase 2 — Identity:** learn Nexora (site ingested), build Delivery Ledger, constitution
      (decision tiers, guardrails) encoded. **COMPLETE — 177 facts ingested from
      nexoraio.vercel.app with sources + approval gate; cited answers API (/api/ask);
      promise guardrail green/yellow/red (/api/check); 83/83 tests; pushed (`47a78e5`).**
- [x] **Phase 3 — Learning:** target-driven learning loop with approval UI. **COMPLETE —
      research targets (competitor/market/prospect/resource), targeted study → facts land
      unapproved, approval queue API + dashboard panel, hunger reporting; live smoke: 134
      new facts from a real site study; 96/96 tests; pushed (`d55008e`).**
      *Test passed: URL → structured facts → approve → stored with source.*
- [ ] **Phase 4 — Research engine:** morning sweep + watch list + opportunity detector +
      first morning briefing. *Test: wake up to a real briefing.*
- [ ] **Phase 5 — Prospecting:** lead finder + scoring + pipeline/CRM. *Test: 10 real qualified
      prospects with reasons.*
- [ ] **Phase 6 — Outreach:** drafts + promise guardrail + approval flow + email sending +
      WhatsApp relay + follow-ups. *Test: first approved outreach goes out.*
- [ ] **Phase 7 — CEO reports:** evening report + morning plan/strategy suggestions. *Test: full
      day of autonomous action reported accurately.*
- [ ] **Phase 8 — Gideon Display:** data screens — charts, tables, evidence panels pulled up
      when explaining "why" or reporting; saved to `data/screens/`. *Test: briefing with a
      pull-up evidence screen.*
- [ ] **Phase 9 — Evidence learning:** reply-rate tracking rewrites playbook. *Test: measurable
      playbook change after enough replies.*
- [ ] **Phase 10 — Voice + Gideon persona:** wake word, STT/TTS, persona across all surfaces.
      *Test: voice briefing each morning.*
- [ ] **Phase 11 — Content engine:** strategy-driven drafts with approval + tracking.
- [ ] **Phase 12 — Code agent (site):** SEO audit → proposed fixes → approved changes to
      nexoraio.vercel.app.
- [ ] **Phase 13 — Code agent (self):** feature requests → plan → build → tests → register,
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
3. **GPU purchase (later, optional):** a NVIDIA card with 12GB+ VRAM unlocks v2 brain
   training — until then the CPU path runs v0/v1 slowly.
4. **WhatsApp relay form:** push notification to owner's phone vs. copy-paste tray in dashboard.
5. **Brain v0 size:** confirm target parameters (1M vs 3M) against CPU training-time budget.

---

## 9. Honest Limits (kept visible on purpose)

- The brain starts infant-level (built from scratch, CPU-only for now) — Gideon's early
  strength is rules, retrieval and statistics; fluent writing grows as training data and
  GPU scale grow. No API payments, no downloaded models — ever.
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

*Status: Phase 3 COMPLETE — learning loop live (targets → study → approval queue → memory),
96/96 tests, dashboard UI with approval panel, pushed to GitHub. Next: Phase 4 — Research
engine (morning sweep + watch list + first briefing). Workflow: pytest green → commit → push.*
