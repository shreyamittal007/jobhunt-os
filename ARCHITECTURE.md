# Job Hunt OS — Architecture

> Current system architecture and future product design for a public-facing job hunt intelligence platform.

---

## 1. What this system is today

A **file-based, AI-assisted job hunt operating system** running locally on one machine. It combines:
- Markdown files as the data layer
- Python scripts for deterministic daily automation
- Claude Code + Opus subagents as the intelligence layer
- LinkedIn MCP for outreach execution
- Skills (`.claude/skills/`) as reusable AI workflows

It is currently single-user (Shreya), CLI-driven, and has no web interface.

---

## 2. Current system architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User (Claude Code CLI)                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────────┐
        ▼                   ▼                       ▼
┌──────────────┐   ┌────────────────┐   ┌──────────────────────┐
│  Intelligence │   │  Automation    │   │  Integration Layer   │
│  Layer        │   │  Layer         │   │                      │
│               │   │                │   │  LinkedIn MCP        │
│  Opus agents  │   │  Python scripts│   │  (connect, DM,       │
│  - tailoring  │   │  - outreach    │   │   profile lookup)    │
│  - evaluation │   │    review      │   │                      │
│  - preflight  │   │  - followups   │   │  Google Sheets       │
│  - expansion  │   │  - PDF gen     │   │  (pipeline sync)     │
│  - brief      │   │  - daily brief │   │                      │
│               │   │  - sheet sync  │   │  Headless Chrome     │
│  Skills       │   │                │   │  (PDF generation)    │
│  (reusable    │   │  Cron / manual │   │                      │
│   workflows)  │   │  trigger       │   │                      │
└──────┬────────┘   └───────┬────────┘   └──────────────────────┘
       │                    │
       └──────────┬─────────┘
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer (Markdown + CSV + PDF)        │
│                                                                 │
│  companies/*/                  wiki/                            │
│  ├── outreach.md               ├── applications.md  ← master   │
│  ├── <company>-jd.md           ├── simpl-metrics.md            │
│  ├── <company>-prep-todo.md    └── resume-cuts.md              │
│  └── resume/Shreya_Mittal.md                                   │
│                                                                 │
│  answers/*/                    raw/                             │
│  ├── rubric.md                 └── Shreya_Mittal.pdf ← base    │
│  ├── candidates.md                                             │
│  ├── answer.md                 tracking/coding-log.csv         │
│  └── assessment.md                                             │
│                                                                 │
│  outreach/ (generated)         briefs/ (generated)             │
│  ├── REVIEW-DRAFTED-*.md       └── YYYY-MM-DD.md              │
│  └── FOLLOWUPS-*.md                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Current modules

| Module | What it does | Key files |
|---|---|---|
| **Resume Engine** | Tailor → evaluate → preflight → PDF | `build_resume_pdf.py`, skills: `resume-review`, `resume-preflight` |
| **Outreach Engine** | Draft → review → send → track lifecycle | `build_outreach_review.py`, `build_followups.py`, LinkedIn MCP |
| **Interview Prep** | Per-company guides, gap analysis, daily brief | `job-hunt-update-oc.sh`, `companies/*/` |
| **Behavioral Prep** | STAR+C answers by domain | `answers/*/` |
| **Pipeline Tracker** | Master applications table | `wiki/applications.md`, `sync_pipeline_to_sheet.py` |
| **Coding Practice** | Log and track DSA problems | `tracking/coding-log.csv` |

### AI agent workflows

```
Resume Tailoring:
  User pastes JD
    → Opus tailors from raw/Shreya_Mittal.pdf
    → Opus evaluates (score /10, top 3 fixes)
    → User picks fixes → apply
    → Preflight agent (Opus, 13 checks)
      → If underfilled: Expansion agent (Opus) suggests bullets
    → build_resume_pdf.py → Shreya_Mittal.pdf

Outreach:
  User identifies HM/TA
    → Draft outreach.md (HM + TA sections)
    → build_outreach_review.py aggregates all "Outreach Drafted" roles
    → User reviews surface → approves
    → LinkedIn MCP sends connect request
    → build_followups.py tracks acceptance / nudge timing
    → LinkedIn MCP sends full message on acceptance

Daily Brief:
  job-hunt-update-oc.sh
    → Scans companies/*/prep-todo.md for active cycles
    → Claude synthesises today's focus
    → Writes briefs/YYYY-MM-DD.md
```

---

## 3. Current data model (flat files)

### `wiki/applications.md` — Pipeline table

| Column | Type | Notes |
|---|---|---|
| Tier | S/A/B/C/D | Priority tier |
| Bucket | string | Domain / category |
| Company | string | Company name |
| Role | string | Job title |
| Job URL | url | Used for tracker joins |
| Applied | date | |
| HM | string | Hiring manager name |
| TA | string | Talent partner name |
| HM Messaged | lifecycle string | e.g. `✓ connect req 2026-06-01; accepted 2026-06-03; msg sent` |
| TA Messaged | lifecycle string | Same format |
| Status | enum | `Outreach Drafted`, `Outreach Sent`, `Applied`, `Interview Scheduled`, `Dropped` |

### `companies/<company>/outreach.md` — Outreach messages

Sections: `## HM — Name` and `## TA — Name`, each with `**Title:**`, `**LinkedIn:**`, `**Channel:**` metadata and a free-form message body.

### `companies/<company>/resume/Shreya_Mittal.md` — Resume source

Markdown with custom parser conventions: `#` name, `##` section, `###` company, `####` role, `-` bullets, `*italic*` context paragraphs.

---

## 4. Limitations of the current architecture (why to productise)

| Limitation | Impact |
|---|---|
| Single user, single machine | Not shareable, not accessible from browser |
| Markdown as database | No querying, filtering, or analytics |
| No auth / multi-tenancy | Can't serve other job seekers |
| AI runs synchronously in CLI | No background processing, no notifications |
| Cron-based automation | Fragile, hard to monitor, not portable |
| No resume version history | Can't compare across tailoring iterations |
| No outreach analytics | Can't see response rates, open rates, conversion |
| Manual pipeline updates | Every status change is a manual file edit |

---

## 5. Future product architecture

### Vision

A **job hunt intelligence platform** that turns any PM / product professional's job search into a managed, data-driven funnel — from resume tailoring to offer negotiation.

### Target users (v1)

- Senior PMs / Directors actively job hunting
- People who do proactive outreach (not just apply-and-wait)
- Users comfortable with AI-assisted workflows

---

### High-level product architecture (FE + BE)

```
┌────────────────────────────────────────────────────────────────────┐
│                         Web Application (FE)                       │
│                                                                    │
│  React / Next.js                                                   │
│                                                                    │
│  ┌─────────────┐  ┌───────────────┐  ┌──────────────────────────┐ │
│  │ Resume      │  │ Outreach      │  │ Pipeline                 │ │
│  │ Builder     │  │ Manager       │  │ Tracker                  │ │
│  └─────────────┘  └───────────────┘  └──────────────────────────┘ │
│  ┌─────────────┐  ┌───────────────┐  ┌──────────────────────────┐ │
│  │ Interview   │  │ Behavioral    │  │ Analytics                │ │
│  │ Prep Hub    │  │ Prep          │  │ Dashboard                │ │
│  └─────────────┘  └───────────────┘  └──────────────────────────┘ │
└───────────────────────────┬────────────────────────────────────────┘
                            │ REST / GraphQL
┌───────────────────────────▼────────────────────────────────────────┐
│                         API Server (BE)                            │
│                                                                    │
│  Node.js / FastAPI                                                 │
│                                                                    │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │ Resume        │  │ Outreach      │  │ Pipeline             │  │
│  │ Service       │  │ Service       │  │ Service              │  │
│  └───────────────┘  └───────────────┘  └──────────────────────┘  │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │ AI Orchestr.  │  │ Scheduler     │  │ Auth / User          │  │
│  │ Service       │  │ Service       │  │ Service              │  │
│  └───────────────┘  └───────────────┘  └──────────────────────┘  │
└───┬───────────────┬──────────────────────────────────────────┬────┘
    │               │                                          │
    ▼               ▼                                          ▼
┌────────┐   ┌────────────────┐                    ┌──────────────────┐
│Postgres│   │  AI Layer      │                    │ Integrations     │
│        │   │                │                    │                  │
│ Users  │   │ Anthropic API  │                    │ LinkedIn API     │
│ Apps   │   │ (Claude Opus/  │                    │ Google Sheets    │
│ Resume │   │  Sonnet)       │                    │ Gmail (optional) │
│  vers. │   │                │                    │ Calendar (opt.)  │
│ Msgs   │   │ Background     │                    │                  │
│ Events │   │ job queue      │                    │                  │
└────────┘   │ (BullMQ /      │                    └──────────────────┘
   +S3       │  Celery)       │
  (PDFs,     └────────────────┘
   resumes)
```

---

### Core modules (product)

#### 1. Resume Builder
- Upload base resume (PDF/DOCX)
- Paste JD → AI tailors to role
- Independent AI evaluator scores and suggests fixes
- Preflight validator checks formatting before download
- PDF generation (one-page enforced)
- Version history per company — compare iterations
- Metrics wiki per user (verified numbers pulled into tailoring, no fabrication)

#### 2. Outreach Manager
- Draft HM + TA messages per company (AI-assisted)
- Daily send queue — grouped by tier
- Lifecycle tracker: connect sent → accepted → messaged → replied → nudged
- Follow-up queue with configurable nudge windows
- LinkedIn integration for sending (connection + DM)
- Response rate analytics per outreach template

#### 3. Pipeline Tracker
- Kanban + table view of all applications
- Status: Identified → Outreach → Applied → Interviewing → Offer → Dropped
- Per-company timeline and notes
- Auto-updates from outreach lifecycle events
- Tier / priority management

#### 4. Interview Prep Hub
- Per-company prep workspace: JD analysis, gap analysis, round guide, prep TODO
- AI gap analysis against JD (what's strong, what to address)
- Round-by-round question predictions
- Daily brief: AI synthesises today's focus across all active loops

#### 5. Behavioral Prep
- Domain-based story library (Leadership, Growth, Risk, Conflict, etc.)
- AI rubric generation per domain
- User submits stories; AI evaluates against rubric (STAR+C scoring)
- Tracks delivery-ready vs. in-progress vs. backlog per domain

#### 6. Analytics Dashboard
- Pipeline funnel: applications → interviews → offers
- Outreach conversion: connect rate → acceptance rate → reply rate
- Response time by tier / company size
- Resume score trends across iterations

---

### Proposed tech stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | Next.js (React) + Tailwind | Fast to build, SSR for SEO, Vercel deploy |
| Backend | FastAPI (Python) | AI/ML ecosystem, existing scripts in Python |
| Database | PostgreSQL (Supabase) | Relational, real-time, easy auth |
| File storage | S3 / Supabase Storage | Resumes, PDFs, base documents |
| AI | Anthropic API (Claude Opus 4 / Sonnet 4) | Already the core intelligence layer |
| Job queue | Celery + Redis | Background tailoring, daily brief, PDF gen |
| Auth | Supabase Auth (OAuth via Google/LinkedIn) | Fast to ship |
| PDF generation | Headless Chrome (existing) or Puppeteer | Already working locally |
| LinkedIn | linkedin-scraper-mcp or LinkedIn API | MCP works today; official API for scale |
| Hosting | Vercel (FE) + Railway/Render (BE) | Low ops overhead |

---

### Phased roadmap

#### Phase 1 — Core (single user, private beta)
- [ ] Auth (Google OAuth)
- [ ] Resume upload + tailoring (AI, one-page PDF)
- [ ] Pipeline tracker (CRUD, status management)
- [ ] Outreach draft + review surface
- [ ] Basic analytics (counts, statuses)

#### Phase 2 — Intelligence layer
- [ ] Resume evaluation + scoring
- [ ] Preflight + density expansion agent
- [ ] Resume version history + comparison
- [ ] JD gap analysis
- [ ] Behavioral prep workspace (rubric + STAR+C scoring)

#### Phase 3 — Automation
- [ ] Daily brief generation (background job)
- [ ] Follow-up queue with nudge scheduling
- [ ] LinkedIn integration (connect + DM)
- [ ] Daily outreach review surface (auto-generated)

#### Phase 4 — Multi-user + public launch
- [ ] Multi-tenancy (user isolation, data scoping)
- [ ] Onboarding flow (base resume upload, target role, tier setup)
- [ ] Analytics dashboard
- [ ] Pricing / subscription model
- [ ] Public launch

---

### Data model (relational, v1)

```sql
users (id, email, name, linkedin_url, created_at)
resumes (id, user_id, base_pdf_url, parsed_text, created_at)
companies (id, user_id, name, slug, tier, bucket, jd_url, status, created_at)
resume_versions (id, user_id, company_id, md_content, pdf_url, score, created_at)
outreach_messages (id, company_id, contact_type [HM/TA], recipient_name,
                   recipient_linkedin, message_body, status, sent_at, replied_at)
outreach_events (id, message_id, event_type [sent/accepted/replied/nudged], event_date)
applications (id, company_id, applied_date, current_status, notes)
behavioral_domains (id, user_id, domain_name, rubric_md, state [drafted/ready/backlog])
behavioral_stories (id, domain_id, star_c_md, score, assessment_md, is_delivery_ready)
prep_todos (id, company_id, item, priority, due_date, completed)
briefs (id, user_id, date, content_md)
```

---

### Key product decisions to make before building

1. **LinkedIn integration strategy** — scraper MCP works for personal use but won't scale to multi-user without official LinkedIn API access (Partner Program). Decide early.
2. **AI cost model** — Opus tailoring per resume + evaluation is ~$0.50–$1.00 per run. Factor into pricing.
3. **Resume parsing** — need a reliable base resume parser (PDF → structured JSON) before tailoring can work at scale.
4. **One-page enforcement** — headless Chrome PDF works locally; for a hosted BE, need a Chrome/Puppeteer service or switch to a PDF library.
5. **Multi-tenancy** — user data isolation must be airtight from day one. Each user's resumes, pipeline, and outreach are completely private.
