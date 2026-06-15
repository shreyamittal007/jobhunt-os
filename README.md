# JobHunt OS

> An AI-native job hunt operating system for ambitious professionals. Built with Claude/Opus agents, LinkedIn MCP, and Python automation. Designed to eventually become a public B2C SaaS product for job seekers.

---

## The problem

A serious job search is a full-time operational problem: 10+ active leads at different stages, tailored resumes per role, personalised outreach to hiring managers and recruiters, interview prep across multiple companies, behavioral story libraries, follow-up queues — all happening in parallel. There is no good tool for this. Most people use a spreadsheet and hope.

JobHunt OS is the tool I built for myself. It is now going public.

---

## What it does

Three engines working together:

### 1. Resume Engine
- Opus-powered tailoring from a base resume to any JD
- Independent Opus evaluation pass (scored /10 with top 3 fixes)
- 13-point preflight validator before PDF generation
- Density expansion agent: detects underfill, computes word budget, suggests JD-relevant bullets
- One-page PDF generation via headless Chrome

### 2. Outreach Engine
- Drafts personalised HM + TA messages per company
- Daily send-ready review surface (all "Outreach Drafted" roles in one file)
- Full lifecycle tracking: connect request → accepted → message sent → replied → nudged
- Follow-up queue with date-driven nudge scheduling
- LinkedIn automation via MCP (connect requests, DMs, inbox monitoring)

### 3. Interview Prep Engine
- Per-company prep workspace: JD gap analysis, round-by-round guide, prioritised TODO
- Behavioral story library by domain (STAR+C format)
- AI rubric generation + story evaluation
- Daily brief: AI synthesises today's focus across all active loops

---

## Architecture

```
User (Claude Code CLI)
    │
    ├── Intelligence Layer (Claude/Opus agents)
    │   ├── Resume tailoring agent
    │   ├── Resume evaluation agent (scores /10)
    │   ├── Preflight validator (13 checks)
    │   ├── Density expansion agent (JD-aware bullet suggestions)
    │   └── Daily brief agent
    │
    ├── Automation Layer (Python scripts)
    │   ├── build_outreach_review.py  — daily send surface
    │   ├── build_followups.py        — follow-up queue
    │   ├── build_resume_pdf.py       — headless Chrome PDF
    │   └── sync_pipeline_to_sheet.py — Google Sheets sync
    │
    ├── Integration Layer
    │   ├── LinkedIn MCP              — connect, DM, profile lookup
    │   └── Google Sheets API         — pipeline sync
    │
    └── Data Layer (Markdown + CSV)
        ├── companies/<company>/      — resume, outreach, prep per company
        ├── wiki/applications.md      — master pipeline table
        ├── answers/<domain>/         — behavioral story library
        └── briefs/                   — daily AI briefs
```

Full architecture doc (current system + future FE/BE product design): [`ARCHITECTURE.md`](./ARCHITECTURE.md)

---

## Tech stack

| Layer | Tech |
|---|---|
| AI | Anthropic Claude API (Opus 4 for tailoring/eval, Sonnet 4 for automation) |
| Outreach | LinkedIn MCP (linkedin-scraper-mcp) |
| PDF generation | Headless Chrome via Puppeteer/CDP |
| Automation | Python 3.11 + cron / launchd |
| Pipeline sync | Google Sheets API |
| Interface | Claude Code CLI (current); Next.js + FastAPI (roadmap) |

---

## Status

**Current:** Single-user, local, CLI-driven. Actively used in a real job search.

**Next:** Open-sourcing the framework. Building a public web product (Next.js FE + FastAPI BE) for anyone running a serious job search.

**Roadmap phases:**
1. Core — auth, resume tailoring, pipeline tracker, outreach drafts
2. Intelligence — evaluation agent, preflight, version history, JD gap analysis
3. Automation — daily brief, follow-up queue, LinkedIn integration
4. Public launch — multi-tenancy, onboarding, pricing

---

## Interest list

If you're actively job hunting and want early access when this goes public → [join the waitlist](#) *(link coming soon)*

---

## Built by

**Shreya Mittal** — Senior / Principal PM with 12+ years in ML-powered intelligence platforms (Simpl, Zepto, Mastercard). Building this in public.

[LinkedIn](https://www.linkedin.com/in/shreya-mittal-65404b4b/)
