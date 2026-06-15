# resume-preflight

**Purpose:** Validate a resume `.md` file for formatting correctness and completeness before PDF generation. Catches issues that cause silent rendering failures (dropped education, broken links, missing sections, line overflow, header/footer truncation).

---

## When to invoke

Always invoke this skill **before** running `build_resume_pdf.py`. Do not generate a PDF until preflight passes.

---

## How to run

Spawn a subagent with the checklist below. Pass the resume file path. The subagent reads the file and reports PASS/FAIL per check.

```
Agent({
  description: "Resume preflight check",
  prompt: <preflight prompt below>,
  model: "opus"
})
```

Show the full preflight report to the user. If any check FAILs, fix it before generating the PDF. Only proceed to PDF generation after all checks PASS (or user explicitly waives a check).

---

## Preflight prompt (pass to subagent)

```
You are a resume formatting validator. Read the file at <PATH> and run every check below.
Report PASS or FAIL for each. For every FAIL, quote the exact offending line(s) and state the fix.

FILE: <PATH>

CHECKS:

1. CONTACT LINE (HEADER)
   - Phone number present
   - Email is a markdown link: [text](mailto:...) — not a bare email address
   - LinkedIn is a markdown link: [LinkedIn](https://...) — not a bare URL
   - Total character length of the contact line must be under 120 characters (rendered length, excluding markdown syntax). If longer, it will overflow the right-aligned header block in the PDF.
   FAIL if any element is bare text/URL, or if the line is too long.

2. EDUCATION LINE (FOOTER)
   - Education must be on ONE line: `## Education : <content>`
   - FAIL if education content is on a separate line below `## Education`
   - FAIL if education section is missing entirely
   - The content after `## Education : ` must be under 100 characters. If longer, it will wrap and break the footer layout.

3. WORK EXPERIENCE SECTION
   - `## WORK EXPERIENCE` header must be present
   - FAIL if missing

4. COMPANY ENTRIES
   - Each company must use: `### Company | Location | Date`
   - FAIL if any company line is missing the location or date column (pipe-separated, 3 parts)

5. ROLE ENTRIES
   - Each role must use: `#### Role Title` or `#### Role Title | Date`
   - FAIL if any role header uses a different format (e.g., plain text, bold, or ##)

6. NO EMPTY COMPANIES
   - Every company entry must have at least one bullet (`- `)
   - FAIL if a company block has a header but no bullets beneath it

7. EXPECTED COMPANIES PRESENT
   Check that ALL of these appear (case-insensitive):
   - Zepto
   - Simpl
   - Mastercard
   - Snapdeal
   - Musigma
   FAIL for any that are missing.

8. SUMMARY PRESENT
   - A non-empty summary paragraph must appear between the contact line and `## WORK EXPERIENCE`
   - FAIL if missing or empty

9. BARE URLS
   - Scan the entire file for raw https:// or http:// URLs NOT wrapped in a markdown link `[text](url)`
   - FAIL if any found — they render as broken or doubled text in the PDF

10. ITALIC CONTEXT PARAGRAPHS
    - Lines starting with `*` must also end with `*` on the same line
    - FAIL if any italic paragraph is split across multiple lines (parser only handles single-line italics)

11. BULLET LINE LENGTH
    - Each bullet (`- `) should be under 200 characters of actual text (excluding the `- ` prefix)
    - Bullets over 200 characters risk awkward 3-line wrapping at 9pt in A4 column width
    - WARN (not FAIL) for bullets between 180–200 characters
    - FAIL for bullets over 200 characters

12. LINE SPACING — CSS CHECK
    Read the file `/Users/harshmittal/Documents/Job hunt/scripts/build_resume_pdf.py` and verify the CSS contains these values (current documented defaults):
    - `line-height: 1.38` on body
    - `li { margin-bottom: 2pt`
    - `company-row { margin-top: 6pt`
    - `h2 { margin-top: 5pt`
    - `summary { margin-bottom: 6pt`
    - `.education { margin-top: 8pt`
    FAIL if any of these are missing or set to a value that would cause the page to overflow (li margin-bottom > 3pt, line-height > 1.45) or leave excessive bottom whitespace (li margin-bottom < 1pt, line-height < 1.3).

13. PAGE DENSITY ESTIMATE
    Estimate how well the resume fills an A4 page using this heuristic:

    Count:
    - Total bullets (lines starting with `- `)
    - Total bullet characters (sum of all bullet text lengths)
    - Non-bullet content lines: summary, context paragraphs (*...*), company rows, role rows, section headers

    Density thresholds (calibrated for 9.5pt, line-height 1.38, 10mm/16mm padding on A4):
    - UNDERFILLED: fewer than 13 bullets OR total bullet chars < 1,400  → flag as ⚠️ UNDERFILLED
    - WELL FILLED: 13–18 bullets AND total bullet chars 1,400–2,200     → PASS
    - OVERFILLED: more than 18 bullets OR total bullet chars > 2,200    → flag as ⚠️ OVERFILLED (risk of 2-page spill)

    For UNDERFILLED: report estimated fill % and which company sections have the fewest bullets (most room to expand).

Report format:
- ✅ CHECK NAME — PASS
- ⚠️ CHECK NAME — WARN: <reason + offending line + suggestion>
- ❌ CHECK NAME — FAIL: <reason + offending line + exact fix>

End with one of:
  🟢 ALL CHECKS PASSED — safe to generate PDF
  🟡 PASSED WITH WARNINGS — review warnings, then generate PDF
  🔴 X CHECK(S) FAILED — fix before generating PDF
```

---

## After preflight — density expansion flow

If check 13 returns ⚠️ UNDERFILLED, compute the word budget first, then spawn the expansion agent.

### Step 1 — compute the budget (you do this, not the agent)

Using the counts from check 13:
- `current_chars` = total bullet character count
- `current_bullets` = total bullet count
- `target_chars` = 1,800 (midpoint of well-filled range)
- `target_bullets` = 15 (midpoint of well-filled range)
- `chars_needed` = target_chars − current_chars
- `bullets_needed` = target_bullets − current_bullets  (use the larger of the two gaps as the guide)
- `chars_per_bullet` = chars_needed ÷ bullets_needed  (round to nearest 10)

Example: 10 bullets, 1,100 chars → need 5 bullets, 700 chars → ~140 chars per bullet.

### Step 2 — derive JD path from resume path

The resume is always at `companies/<company>/resume/<company>-resume.md`.
Extract `<company>` from the path. The JD is at `companies/<company>/<company>-jd.md`.

Pass both paths to the expansion agent.

### Step 3 — spawn Opus expansion agent with exact budget + JD context

```
Agent({
  description: "Resume density expansion — suggest additional bullets",
  model: "opus",
  prompt: "
The resume at <RESUME_PATH> is underfilled.

PAGE FILL BUDGET (computed by preflight):
- Current bullets: <current_bullets> | Target: <target_bullets> | Need: <bullets_needed> more
- Current bullet chars: <current_chars> | Target: 1,800 | Need: <chars_needed> more chars
- Target length per new bullet: ~<chars_per_bullet> characters (hard cap: 200)
- Sparsest sections (most room): <SPARSE_SECTIONS>

ROLE CONTEXT:
- JD file: <JD_PATH>
- Tailored resume: <RESUME_PATH>
- Base resume (full experience bank): /Users/harshmittal/Documents/Job hunt/raw/Shreya_Mittal.pdf
- Simpl metrics: /Users/harshmittal/Documents/Job hunt/wiki/simpl-metrics.md

Read all four files before doing anything else.

STEP 1 — FEASIBILITY CHECK:
Evaluate whether <chars_per_bullet> characters is enough to write a meaningful, JD-relevant bullet.
- If <chars_per_bullet> < 80: the budget is too tight for a useful bullet. 
  Respond: 'DENSITY EXPANSION NOT FEASIBLE — bullet budget of <chars_per_bullet> chars is too short 
  for meaningful content. Recommend tightening CSS spacing instead (reduce li margin-bottom or 
  line-height) to create room for shorter additions, or accept the current page fill.'
  Then STOP — do not suggest bullets.
- If <chars_per_bullet> >= 80: proceed to Step 2.

STEP 2 — REDUNDANCY SCAN:
Before suggesting anything, extract and list every distinct theme, metric, and achievement already 
present in the tailored resume. Examples of themes to track:
- CAC reduction, conversion uplift, payment success, fraud detection, DLQ improvement, 
  ATO reduction, credit limit expansion, underwriting quality, GMV growth, 0→1 launch, 
  ML/AI product, cross-functional collaboration, GTM, compliance, etc.

Build a DO-NOT-REPEAT list: any theme, metric, or achievement already covered — even if 
framed differently — must not appear in a suggested bullet. A new bullet that makes the same 
point as an existing bullet in different words is redundant and must be rejected.

STEP 3 — SUGGEST BULLETS:
Suggest exactly <bullets_needed> bullets. Each bullet must:
- Be grounded only in the base resume or simpl-metrics.md — no fabrication
- Address a JD-required skill or experience NOT already covered by existing bullets (check DO-NOT-REPEAT list)
- Introduce a genuinely new dimension: a different skill, a different result, or a different context
- Be written for <COMPANY> specifically — not generic PM language
- Target approximately <chars_per_bullet> characters (±20). Do not exceed 200.
- Be placed in one of the sparsest sections: <SPARSE_SECTIONS>

If you cannot find <bullets_needed> non-redundant bullets that are both JD-relevant and grounded 
in real experience, suggest fewer and explain why the remainder cannot be filled without redundancy 
or fabrication. Do not pad with weak or repetitive bullets.

Format each suggestion as:
  [COMPANY / ROLE] bullet text
  JD signal: <what JD requirement this addresses>
  New dimension added: <what this covers that no existing bullet does>
  Chars: N

Do NOT edit the file. The user decides which bullets to add.
"
})
```

Show the expansion output to the user in full. If the agent returned NOT FEASIBLE, relay that recommendation (CSS tightening vs. accepting current fill). If suggestions were returned, ask which to add. Apply chosen bullets, then re-run preflight to confirm density landed in the well-filled range before generating the PDF.

---

## After preflight

- If 🟢 or 🟡: proceed to `python3 scripts/build_resume_pdf.py <file> -o <output.pdf>`
- If 🔴: fix each failing check, then re-run preflight before generating PDF
- Do not skip preflight even if "just a small change was made" — formatting bugs are silent and only appear after the PDF is opened
