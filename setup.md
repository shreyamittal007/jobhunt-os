# Setup Guide

Get JobHunt OS running in under 15 minutes.

---

## Prerequisites

- [Claude Code CLI](https://claude.ai/code) — the AI layer (requires Anthropic API access)
- Python 3.11+
- Google Chrome (for PDF generation)
- `gh` CLI (optional, for GitHub integration)

---

## Step 1 — Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/jobhunt-os ~/Documents/Job\ hunt
cd ~/Documents/Job\ hunt
```

Open `CLAUDE.md` and replace all `[YOUR NAME]`, `[YOUR EMAIL]`, `[YOUR LINKEDIN]`, `[YOUR PHONE]` placeholders with your details.

---

## Step 2 — Add your base resume

```bash
mkdir -p raw
# Copy your resume PDF here
cp ~/Downloads/your-resume.pdf raw/[YOUR NAME].pdf
```

This is the canonical source. All tailored resumes are generated from it. Never edit it directly.

---

## Step 3 — Install skills (Claude Code)

```bash
mkdir -p ~/.claude/skills/resume-preflight
mkdir -p ~/.claude/skills/resume-review
cp skills/resume-preflight/SKILL.md ~/.claude/skills/resume-preflight/SKILL.md
cp skills/resume-review/SKILL.md ~/.claude/skills/resume-review/SKILL.md
```

---

## Step 4 — Install LinkedIn MCP (optional, for outreach automation)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install linkedin-scraper-mcp
claude mcp add linkedin -- ~/.local/bin/linkedin-scraper-mcp
```

Then in a Claude Code session, type `/mcp` and log in to LinkedIn once.

---

## Step 5 — Set up your pipeline tracker

```bash
cp templates/wiki/applications.md wiki/applications.md
```

Edit it to add your first target companies.

---

## Step 6 — Add your first company

```bash
mkdir -p companies/acme
cp templates/company/COMPANY-prep-todo.md companies/acme/acme-prep-todo.md
cp templates/company/COMPANY-jd.md companies/acme/acme-jd.md
cp templates/company/outreach.md companies/acme/outreach.md
```

Fill in the JD and outreach templates, add a row to `wiki/applications.md`, and you're live.

---

## Step 7 — Tailor your first resume

Open Claude Code in your `Job hunt/` directory and say:

> "Tailor my resume for [Company]. Here's the JD: [paste JD]"

The AI will tailor, evaluate, run preflight, and generate the PDF.

---

## Daily workflow

```bash
# Generate outreach review surface
python3 scripts/build_outreach_review.py

# Generate follow-up queue
python3 scripts/build_followups.py
```

Open `outreach/REVIEW-DRAFTED-OUTREACH-<today>.md` and send what's ready.

---

## PDF generation

```bash
python3 scripts/build_resume_pdf.py companies/<company>/resume/[YOUR NAME].md \
  -o companies/<company>/resume/[YOUR NAME].pdf
```

**Chrome path:** the script defaults to macOS. For Linux, update `CHROME_BIN` at the top of `build_resume_pdf.py`.

---

## Google Sheets sync (optional)

1. Create a Google Sheet for your pipeline
2. Set up a service account at `~/.config/gcp/jobhunt-sa.json`
3. Add your sheet ID to `data/pipeline_sheet_id.txt`
4. Run `python3 scripts/sync_pipeline_to_sheet.py`
