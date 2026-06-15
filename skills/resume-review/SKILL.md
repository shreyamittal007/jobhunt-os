---
name: resume-review
description: |
  Quality gate for a tailored resume before applying or sending outreach. Use this skill when:
  - A resume has just been tailored for a specific role
  - The user asks to evaluate or review a resume
  - Before drafting outreach for a role (to confirm the resume is ready)
  - The user types /resume-review
---

# Resume Review

Evaluate a tailored resume against a specific job posting. Always run as a **subagent** so the evaluation is independent and uncontaminated by the tailoring session context.

## Trigger

This skill MUST be invoked after every resume tailoring task. Do not skip it. The user has set up this process explicitly.

## Workflow

1. **Identify inputs** — Confirm the resume file path (`raw/<name>.md`) and gather the JD context (role title, company, key signals from the JD or prior conversation)
2. **Spawn evaluation subagent** — Use the Agent tool with the prompt template below. Run in background if other work is in progress.
3. **Present findings** — When the agent returns, surface the output to the user in full. Do NOT summarise it — the user needs the detail to decide what to rewrite.
4. **Offer to apply fixes** — Ask which of the top 3 changes the user wants to implement. Do not auto-apply — wait for explicit confirmation.

## Subagent Prompt Template

```
Evaluate the resume at `{RESUME_PATH}` against the **{ROLE_TITLE}** role at **{COMPANY}**.

**Role context:**
{JD_SIGNALS}

**Evaluate across these 8 dimensions:**

1. **JD keyword match (score /10)** — which target keywords appear, which are missing/weak. List both.

2. **Impact metrics quality (score /10)** — are results quantified, outcome-focused, and unambiguous? Flag vague or unverifiable claims.

3. **Role-specific signal strength** — score 1–5 for each key signal domain from the JD. List the domains.

4. **Bullet quality** — are bullets action-led and result-anchored? Identify the 3 weakest bullets. Quote the current line and give a specific rewrite suggestion.

5. **Summary alignment** — does the summary open with the right framing for this role? What's missing or wrongly foregrounded?

6. **ATS / parsing risk** — any formatting, special characters, or missing fields that hurt automated screening.

7. **Overall fit score (X/10)** with one-sentence rationale.

8. **Top 3 highest-impact changes** — ranked. Quote the current line, suggest the replacement or direction.

Be direct. Treat this as a hiring manager review, not a resume coach review. Do NOT rewrite the resume — evaluate and recommend only.
```

## Output format

The subagent returns a structured markdown evaluation. Present it verbatim under a heading:

```markdown
## Resume Evaluation: {RESUME_FILENAME} → {COMPANY} {ROLE}

{full subagent output}

---
*Evaluated by subagent on {date}. Apply changes? Tell me which of the Top 3 you want to implement.*
```

## After presenting the evaluation

- Ask: "Which of the Top 3 changes do you want to apply?"
- Wait for the user to answer before touching the resume file
- Apply only the changes the user confirms
- Regenerate the PDF after any edits: `python3 scripts/build_resume_pdf.py {RESUME_PATH} -o {PDF_PATH}`

## File location convention

Resumes live under `companies/<company>/resume/<company>-resume.md`, not `raw/`.
The base (un-tailored) resume is the only file that stays in `raw/` (`Shreya_Mittal.pdf`).

## What this skill does NOT do

- Does not rewrite the resume without user confirmation
- Does not skip the subagent and do the evaluation inline — independence matters
- Does not summarise the evaluation before the user has read it
