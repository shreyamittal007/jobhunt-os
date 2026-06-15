#!/usr/bin/env python3
"""Regenerate the daily outreach review surface.

Deterministic aggregation — no LLM. Builds
  active/job-hunt/outreach/REVIEW-DRAFTED-OUTREACH-<today>.md
from:
  - wiki/applications.md   (the tracker table; rows with Status == "Outreach Drafted")
  - outreach/<slug>/hm.md, ta.md   (verbatim messages, matched to rows by jd_url)

Checkbox handling (merge / preserve):
  - A box ticked in the most-recent prior dated review file stays ticked.
  - Plus, anything recorded as sent in the tracker's "HM Messaged" / "TA Messaged"
    columns is auto-ticked.
  - Union of the two; prior tick lines (with their ✅ date) are preserved verbatim.

Run unattended at 03:00 IST via cron so the file is ready for review by 10:00.
"""

from __future__ import annotations

import datetime as _dt
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JOBHUNT = os.path.dirname(HERE)                       # active/job-hunt
APPLICATIONS = os.path.join(JOBHUNT, "wiki", "applications.md")
OUTREACH_DIR = os.path.join(JOBHUNT, "outreach")      # generated review/followup files
COMPANIES_DIR = os.path.join(JOBHUNT, "companies")    # source: companies/*/outreach.md

TIER_ORDER = ["S", "A", "B", "C", "D"]
DRAFTED_STATUS = "outreach drafted"

INTRO = (
    "> Single send-ready review surface. Every section below is a role whose "
    "tracker status is **Outreach Drafted**. Messages are verbatim from each "
    "company's `outreach.md` file (`companies/<company>/outreach.md`), "
    "metadata stripped. **Nothing has been sent.** Review, tick the `[ ]` boxes as you send, "
    "and flag any recipient/fit concerns before contacting."
)


# --------------------------------------------------------------------------- #
# URL normalisation — join applications.md rows to outreach folders
# --------------------------------------------------------------------------- #
def normalize_url(url: str) -> str:
    """Collapse a job URL to a stable join key.

    LinkedIn job URLs vary (www. vs in., trailing slash, slug prefix) but carry a
    numeric job id — key on that. Otherwise lowercase + strip protocol/trailing slash.
    """
    if not url:
        return ""
    url = url.strip()
    m = re.search(r"linkedin\.com/jobs/view/(?:[^/]*-)?(\d+)", url)
    if m:
        return "li:" + m.group(1)
    # greenhouse / amazon.jobs / stripe.com etc — strip noise
    u = re.sub(r"^https?://", "", url).rstrip("/").lower()
    u = re.sub(r"^www\.", "", u)
    u = re.sub(r"\?.*$", "", u)
    return u


# --------------------------------------------------------------------------- #
# Parse companies/<company>/outreach.md
# --------------------------------------------------------------------------- #
def extract_message(body: str) -> str:
    """Strip trailing scaffold sections (Gaps to confirm, TA placeholder, etc.)."""
    # Drop everything from the first trailing section marker
    cut = re.search(r"\n\*\*Gaps to confirm", body)
    if cut:
        body = body[: cut.start()]
    cut = re.search(r"\n---", body)
    if cut:
        body = body[: cut.start()]
    return body.strip()


_ABBREV = {
    "sr": "senior", "mgr": "manager", "dir": "director", "eng": "engineering",
    "em": "engineering manager", "sdm": "software development manager",
    "ds": "data science", "ml": "machine learning", "plt": "platform",
}


def role_key(company: str, role: str) -> str:
    """Fuzzy join key: company+role, punctuation collapsed, abbreviations expanded."""
    s = f"{company} {role}".lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = [_ABBREV.get(t, t) for t in s.split()]
    return re.sub(r"\s+", " ", " ".join(toks)).strip()


def _parse_contact_section(section_text: str, header_name: str,
                            company: str, role: str, status: str, jd_url: str):
    """Parse an ## HM/TA section into {fm, msg} or None if empty/placeholder."""
    if not section_text.strip():
        return None
    # Skip TBD / placeholder sections
    first_line = section_text.strip().splitlines()[0] if section_text.strip() else ""
    if re.search(r"\bTBD\b|Add TA contact", first_line, re.I):
        return None

    fm = {"company": company, "role": role, "status": status,
          "recipient": header_name, "jd_url": jd_url}

    # Extract **Key:** Value metadata lines — leading block only (before first blank line)
    stripped = section_text.lstrip("\n")
    offset = len(section_text) - len(stripped)
    leading_block = re.split(r"\n\n", stripped, maxsplit=1)[0]
    meta_end = offset
    for mm in re.finditer(r"^\*\*([^*]+):\*\*\s+(.+)", leading_block, re.M):
        key = mm.group(1).strip().lower()
        val = mm.group(2).strip()
        if key == "title":
            fm["recipient_role"] = val
        elif key == "linkedin":
            fm["recipient_linkedin"] = val
        elif key == "channel":
            fm["channel"] = val
        meta_end = max(meta_end, offset + mm.end())

    body = section_text[meta_end:].strip()
    msg = extract_message(body)
    if not msg:
        return None
    return {"fm": fm, "msg": msg}


def parse_outreach_file(filepath: str):
    """Parse companies/<company>/outreach.md.

    Expected format:
        # Outreach — Company Name
        **Role:** Role Title
        **Status:** Outreach Drafted
        **JD:** https://...   (optional — used for tracker join)

        ## HM — Name
        **Title:** ...
        **LinkedIn:** ...
        **Channel:** LinkedIn

        message body

        ---

        ## TA — Name
        ...
    """
    with open(filepath, encoding="utf-8") as fh:
        text = fh.read()

    company = role = status = jd_url = ""

    m = re.search(r"^#\s+Outreach\s+[—\-]+\s+(.+)", text, re.M)
    if m:
        company = m.group(1).strip()

    m = re.search(r"^\*\*Role:\*\*\s+(.+)", text, re.M)
    if m:
        role = m.group(1).strip()

    m = re.search(r"^\*\*Status:\*\*\s+(.+)", text, re.M)
    if m:
        status = m.group(1).strip()

    m = re.search(r"^\*\*JD:\*\*\s+(\S+)", text, re.M)
    if m:
        jd_url = m.group(1).strip()

    hm_match = re.search(r"^##\s+HM\s+[—\-]+\s+(.+)$", text, re.M)
    ta_match = re.search(r"^##\s+TA\s+[—\-]+\s+(.+)$", text, re.M)

    hm_entry = ta_entry = None

    if hm_match:
        hm_name = hm_match.group(1).strip()
        hm_start = hm_match.end()
        hm_end = ta_match.start() if ta_match else len(text)
        hm_entry = _parse_contact_section(
            text[hm_start:hm_end], hm_name, company, role, status, jd_url)

    if ta_match:
        ta_name = ta_match.group(1).strip()
        ta_entry = _parse_contact_section(
            text[ta_match.end():], ta_name, company, role, status, jd_url)

    return company, role, status, jd_url, hm_entry, ta_entry


def load_outreach_index():
    """Return (by_url, by_role) lookup dicts scanning companies/*/outreach.md."""
    by_url, by_role = {}, {}
    for company_dir in sorted(glob.glob(os.path.join(COMPANIES_DIR, "*"))):
        if not os.path.isdir(company_dir):
            continue
        outreach_path = os.path.join(company_dir, "outreach.md")
        if not os.path.exists(outreach_path):
            continue
        slug = os.path.basename(company_dir)
        try:
            company, role, status, jd_url, hm_entry, ta_entry = parse_outreach_file(outreach_path)
        except Exception:
            continue
        if hm_entry is None and ta_entry is None:
            continue
        entry = {"slug": slug, "hm": hm_entry, "ta": ta_entry, "jd_url": jd_url}
        ukey = normalize_url(jd_url)
        if ukey:
            by_url[ukey] = entry
        if company and role:
            by_role.setdefault(role_key(company, role), entry)
    return by_url, by_role


# --------------------------------------------------------------------------- #
# Parse wiki/applications.md (markdown table)
# --------------------------------------------------------------------------- #
def parse_applications():
    rows = []
    with open(APPLICATIONS, encoding="utf-8") as fh:
        lines = fh.readlines()
    header = None
    for line in lines:
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):  # separator row
            continue
        row = dict(zip(header, cells))
        rows.append(row)
    return rows


def messaged_tick(cell: str):
    """From an applications 'HM Messaged'/'TA Messaged' cell, return (sent, date|None)."""
    if not cell or "✓" not in cell:  # ✓
        return False, None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", cell)
    return True, (m.group(1) if m else None)


# --------------------------------------------------------------------------- #
# Parse the most-recent prior review file for preserved ticks
# --------------------------------------------------------------------------- #
def load_prior_ticks(today_path: str):
    """Map normalized jd_url -> {'hm': line|None, 'ta': line|None} from latest prior file."""
    candidates = sorted(
        glob.glob(os.path.join(OUTREACH_DIR, "REVIEW-DRAFTED-OUTREACH-*.md"))
    )
    candidates = [c for c in candidates if os.path.abspath(c) != os.path.abspath(today_path)]
    if not candidates:
        return {}
    with open(candidates[-1], encoding="utf-8") as fh:
        text = fh.read()
    ticks = {}
    for block in text.split("\n### ")[1:]:
        jd = re.search(r"^JD:\s*(\S+)", block, re.M)
        if not jd:
            continue
        key = normalize_url(jd.group(1))
        hm = re.search(r"^- \[x\] HM sent.*$", block, re.M)
        ta = re.search(r"^- \[x\] TA sent.*$", block, re.M)
        ticks[key] = {
            "hm": hm.group(0) if hm else None,
            "ta": ta.group(0) if ta else None,
        }
    return ticks


# --------------------------------------------------------------------------- #
# Emit
# --------------------------------------------------------------------------- #
def checkbox_line(kind_label, prior_line, tracker_sent, tracker_date, today):
    """Return a '- [ ]/[x] <label> sent' line, merging prior + tracker state."""
    if prior_line:                      # preserve verbatim (keeps original ✅ date)
        return prior_line
    if tracker_sent:
        date = tracker_date or today
        return f"- [x] {kind_label} sent ✅ {date}"
    return f"- [ ] {kind_label} sent"


def contact_line(label, party):
    if party is None:
        return None
    fm = party["fm"]
    name = fm.get("recipient", "").strip()
    role = fm.get("recipient_role", "").strip()
    li = fm.get("recipient_linkedin", "").strip()
    if not li and fm.get("linkedin", "").strip():       # old format: bare handle
        handle = fm["linkedin"].strip().strip("/")
        li = handle if "linkedin.com" in handle else f"linkedin.com/in/{handle}/"
    bits = []
    if name:
        bits.append(name)
    if role:
        bits.append(role)
    text = " — ".join(bits) if bits else "(recipient not specified)"
    if li:
        text += f" ({li})"
    return f"**{label}:** ✓ {text}"


def build():
    today = _dt.date.today().isoformat()
    out_path = os.path.join(OUTREACH_DIR, f"REVIEW-DRAFTED-OUTREACH-{today}.md")

    apps = parse_applications()
    by_url, by_role = load_outreach_index()
    prior = load_prior_ticks(out_path)

    # Index tracker rows for folder->row lookup.
    rows_by_url, rows_by_role = {}, {}
    dropped = []
    for row in apps:
        status = row.get("status", "").lower()
        if status.startswith("dropped"):
            dropped.append(row)
        u = normalize_url(row.get("job url", ""))
        if u:
            rows_by_url.setdefault(u, row)
        rk = role_key(row.get("company", ""), row.get("role", ""))
        if rk:
            rows_by_role.setdefault(rk, row)

    # Folder-driven: each outreach folder with a draft is a candidate; include it
    # when its tracker row's status begins with "Outreach Drafted".
    all_folders = {**{e["slug"]: e for e in by_url.values()},
                   **{e["slug"]: e for e in by_role.values()}}
    drafted, no_row = [], []
    for slug, entry in sorted(all_folders.items()):
        row = by_url and rows_by_url.get(normalize_url(entry["jd_url"]))
        if not row:
            fm = (entry["hm"] or entry["ta"])["fm"]
            row = rows_by_role.get(role_key(fm.get("company", ""), fm.get("role", "")))
        if not row:
            no_row.append(entry)
            continue
        if not row.get("status", "").lower().startswith(DRAFTED_STATUS):
            continue
        drafted.append((row, entry))
    missing = no_row

    # ----- group by tier -----
    by_tier = {t: [] for t in TIER_ORDER}
    extra_tiers = {}
    for row, entry in drafted:
        tier = row.get("tier", "?").strip().upper()
        (by_tier if tier in by_tier else extra_tiers).setdefault(tier, []).append((row, entry))

    complete = sum(1 for _, e in drafted if e["hm"] and e["ta"])
    hm_only = sum(1 for _, e in drafted if e["hm"] and not e["ta"])

    confirm_flags = []  # roles whose message body carries a ⚠ annotation

    lines = []
    lines.append(f"# Drafted Outreach — Review Surface ({today})")
    lines.append("")
    lines.append(INTRO)
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total ready-to-review roles:** {len(drafted)}")
    lines.append(f"- **Complete (HM + TA both found):** {complete}")
    lines.append(f"- **HM-only (TA N/A / not found):** {hm_only}")
    lines.append(f"- **Dropped:** {len(dropped)} (see list at bottom)")
    if missing:
        lines.append(
            f"- **⚠ Drafts not found in tracker:** {len(missing)} "
            "(folders with no matching applications.md row — see bottom)"
        )
    lines.append("")

    def emit_role(row, entry):
        company = row.get("company", "").strip()
        role = row.get("role", "").strip()
        tier = row.get("tier", "?").strip().upper()
        bucket = row.get("bucket", "").strip()
        jd = row.get("job url", "").strip()
        key = normalize_url(jd)
        ptick = prior.get(key, {})

        lines.append(f"### {company} — {role}  [Tier {tier} · {bucket}]")
        lines.append(f"JD: {jd}")
        lines.append("")

        # Surface any ⚠ note carried in the tracker's Status suffix (location/elig).
        status = row.get("status", "")
        if "⚠" in status:
            note = status.split("⚠", 1)[1].strip()
            note = re.split(r"\s\$|\(", note, 1)[0].strip().rstrip(".;,—– ")
            if note:
                lines.append(f"⚠ {note} — confirm before sending.")
                lines.append("")
            if f"{company} — {role}" not in confirm_flags:
                confirm_flags.append(f"{company} — {role}")

        hm_line = contact_line("HM", entry["hm"])
        ta_line = contact_line("TA", entry["ta"])
        if hm_line:
            lines.append(hm_line)
        if ta_line:
            lines.append(ta_line)
        else:
            ta_found = row.get("ta found", "").strip() or "not found"
            lines.append(f"**TA:** {ta_found}")
            lines.append("_(HM-only — TA = N/A / not found)_")
        lines.append("")

        hm_sent, hm_date = messaged_tick(row.get("hm messaged", ""))
        ta_sent, ta_date = messaged_tick(row.get("ta messaged", ""))
        if entry["hm"]:
            lines.append(checkbox_line("HM", ptick.get("hm"), hm_sent, hm_date, today))
        if entry["ta"]:
            lines.append(checkbox_line("TA", ptick.get("ta"), ta_sent, ta_date, today))
        lines.append("")

        if entry["hm"]:
            lines.append("**HM message:**")
            lines.append("")
            lines.append(entry["hm"]["msg"])
            lines.append("")
            if "⚠" in entry["hm"]["msg"]:
                confirm_flags.append(f"{company} — {role}")
        if entry["ta"]:
            lines.append("**TA message:**")
            lines.append("")
            lines.append(entry["ta"]["msg"])
            lines.append("")
        lines.append("")

    for tier in TIER_ORDER:
        bucket_rows = by_tier.get(tier) or []
        if not bucket_rows:
            continue
        lines.append(f"## Tier {tier}")
        lines.append("")
        for row, entry in bucket_rows:
            emit_role(row, entry)
    for tier in sorted(extra_tiers):
        lines.append(f"## Tier {tier}")
        lines.append("")
        for row, entry in extra_tiers[tier]:
            emit_role(row, entry)

    # ----- ⚠ Confirm before send (deterministic, from ⚠ lines in messages) -----
    if confirm_flags:
        lines.append("## ⚠ Confirm before send")
        lines.append("")
        lines.append(
            "Roles whose drafted message carries a ⚠ annotation (usually location / "
            "relocation). Resolve before contacting:"
        )
        lines.append("")
        for name in dict.fromkeys(confirm_flags):   # dedupe, preserve order
            lines.append(f"- {name}")
        lines.append("")

    # ----- Dropped list -----
    lines.append("## Dropped (excluded from review)")
    lines.append("")
    lines.append('Rows whose tracker status begins with "Dropped":')
    lines.append("")
    for row in dropped:
        company = row.get("company", "").strip()
        role = row.get("role", "").strip()
        status = row.get("status", "").strip()
        reason = re.sub(r"^Dropped\b[^\(]*", "", status).strip().strip("()") or status
        lines.append(f"- **{company} — {role}:** {reason}")
    lines.append("")

    # ----- Drafts with no tracker row -----
    if missing:
        lines.append("## ⚠ Drafts not found in tracker")
        lines.append("")
        lines.append(
            "These `companies/<company>/outreach.md` files hold a draft but no row in "
            "`wiki/applications.md` matched by Job URL or company+role. Add the row "
            "(or fix the company/role) so they flow into the review:")
        lines.append("")
        for entry in missing:
            fm = (entry["hm"] or entry["ta"])["fm"]
            lines.append(
                f"- **{fm.get('company','').strip()} — {fm.get('role','').strip()}** "
                f"(`companies/{entry['slug']}/outreach.md`)")
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines).rstrip() + "\n")

    print(f"wrote {out_path}")
    print(
        f"  {len(drafted)} ready-to-review  ({complete} complete, {hm_only} HM-only)  "
        f"| {len(dropped)} dropped | {len(missing)} unmatched"
    )
    return out_path


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:  # surface to cron log
        print(f"build_outreach_review FAILED: {exc}", file=sys.stderr)
        raise
