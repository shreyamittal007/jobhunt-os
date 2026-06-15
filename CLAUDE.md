# JobHunt OS — Claude Code Instructions

**Operating Mode:** Career Engine — decision-driving (what to focus on today), not judgement-forming.

## Setup

Before using, update the following in this file:
- Replace `[YOUR NAME]` with your full name
- Replace `[YOUR EMAIL]` with your email
- Replace `[YOUR LINKEDIN]` with your LinkedIn URL
- Replace `[YOUR PHONE]` with your phone number

Your base resume lives at `raw/[YOUR NAME].pdf`. All tailored resumes output to `companies/<company>/resume/[YOUR NAME].md` and `.pdf`.

---

## What this is

A personal AI-powered job hunt operating system. Three engines:
1. **Resume Engine** — AI tailors, evaluates, and validates your resume per role
2. **Outreach Engine** — AI drafts and tracks personalised HM + TA outreach
3. **Interview Prep Engine** — per-company prep, behavioral stories, daily brief

---

## Directory Layout

```
Job hunt/
├── CLAUDE.md                          # this file
├── raw/[YOUR NAME].pdf                # base resume — canonical, never edit directly
├── wiki/
│   ├── applications.md                # master pipeline table
│   └── index.md                       # content catalog
├── companies/                         # one folder per company
│   └── <company>/
│       ├── <company>-prep-todo.md
│       ├── <company>-jd.md
│       ├── outreach.md                # HM + TA messages in one file
│       └── resume/
│           ├── [YOUR NAME].md
│           └── [YOUR NAME].pdf
├── answers/                           # behavioral prep by domain
│   └── <domain>/
│       ├── rubric.md
│       ├── candidates.md
│       ├── answer.md
│       └── assessment.md
├── briefs/                            # daily brief output
├── outreach/                          # generated review/followup surfaces
└── scripts/                           # automation scripts
```

---

## Resume Rules

**Always one page.** Every tailored resume must fit on a single A4 page.

**No fabrication.** All bullets must come from your actual experience.

**Always run resume-review** after every tailoring session (skill: `resume-review`).

**Always run resume-preflight** before every PDF generation (skill: `resume-preflight`).

---

## Resume Tailoring Protocol

1. Paste the JD
2. AI tailors from `raw/[YOUR NAME].pdf`
3. AI evaluates (score /10, top 3 fixes)
4. Apply fixes
5. Run `/resume-preflight` → fix any failures → generate PDF

After **every** tailoring session, invoke the `resume-review` skill.
Before **every** PDF generation, invoke the `resume-preflight` skill.

---

## Outreach Format (`companies/<company>/outreach.md`)

```markdown
# Outreach — Company Name

**Role:** Role Title
**Status:** Outreach Drafted

---

## HM — Full Name
**Title:** Their role
**LinkedIn:** https://www.linkedin.com/in/...
**Channel:** LinkedIn

Message body.

**Gaps to confirm:** anything to verify before sending

---

## TA — Full Name
**Title:** Their role  
**LinkedIn:** https://...
**Channel:** LinkedIn

Message body.
```

---

## Pipeline (`wiki/applications.md`)

| Tier | Bucket | Company | Role | Job URL | Applied | HM | TA | HM Messaged | TA Messaged | Status |
|------|--------|---------|------|---------|---------|----|----|-------------|-------------|--------|

**Status values:** `Outreach Drafted` → `Outreach Sent` → `Applied` → `Interview Scheduled` → `Dropped`

---

## Key Conventions

- **Answer format:** STAR+C — Situation, Task, Action, Result, Complication/Learning
- **Coding practice:** log to `tracking/coding-log.csv` with date, pattern, difficulty, time
- **Never send outreach** without explicit approval
- **Resume files** always named `[YOUR NAME].md` / `[YOUR NAME].pdf`
