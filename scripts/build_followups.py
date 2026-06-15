#!/usr/bin/env python3
"""Regenerate the daily outreach FOLLOW-UP surface.

Deterministic aggregation — no LLM, no LinkedIn. Builds
  active/job-hunt/outreach/FOLLOWUPS-<today>.md
from the lifecycle recorded in wiki/applications.md's "HM Messaged" / "TA Messaged"
columns. Those cells are a mini-log, e.g.:
    ✓ connect req 2026-05-31; accepted 2026-06-03; msg sent 2026-06-03; replied
    ✓ DM 2026-05-31
    ⚠ failed 2026-05-31 (follow-only)

This script only reads dates/stages already recorded and computes *what is due*:
  - connect req sent >= ACCEPT_CHECK_DAYS ago, not yet accepted  -> acceptance check due
  - accepted but no message sent                                  -> send the full drafted message
  - message sent >= NUDGE_DAYS ago, no reply, not yet nudged      -> nudge due
Detecting acceptance/replies and actually sending are a SEPARATE interactive
Claude step (LinkedIn MCP) — this surface just tells that step what to work on.

Run unattended via cron; the acting step ("run follow-ups") updates the cells back.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Reuse the review builder's tracker parser + outreach-folder index.
import build_outreach_review as br  # noqa: E402

OUTREACH_DIR = br.OUTREACH_DIR
TIER_ORDER = br.TIER_ORDER

# --- tunables -------------------------------------------------------------- #
ACCEPT_CHECK_DAYS = 3   # poll a pending connect for acceptance after this many days
NUDGE_DAYS = 7          # nudge a delivered message with no reply after this many days
# --------------------------------------------------------------------------- #

DATE_RE = r"(\d{4}-\d{2}-\d{2})"


def _date(seg: str):
    m = re.search(DATE_RE, seg)
    if not m:
        return None
    try:
        return _dt.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def parse_lifecycle(cell: str) -> dict:
    """Parse a 'HM/TA Messaged' cell into lifecycle flags + dates.

    Recognised tokens (semicolon-separated segments, order-independent):
      connect req <date> | connected <date>  -> connect_sent
      DM <date> | msg sent <date> | message sent <date> -> msg_sent
      accepted <date>                         -> accepted
      nudge[d] <date>                         -> nudged
      replied                                 -> replied=True
      failed | off-target | unavailable | manual -> failed=True (needs human/fix)
    """
    out = {
        "raw": cell.strip(),
        "connect_sent": None,
        "msg_sent": None,
        "accepted": None,
        "nudged": None,
        "replied": False,
        "failed": False,
    }
    if not cell:
        return out
    low = cell.lower()
    if "✓" not in cell and not re.search(r"connect req|connected|\bdm\b|msg sent|message sent", low):
        # Nothing actionable recorded (blank / "not found" / "needs search" / "N/A")
        if any(w in low for w in ("failed", "off-target", "unavailable", "manual", "needs fix")):
            out["failed"] = True
        return out
    for seg in re.split(r"[;|]", cell):
        s = seg.strip()
        sl = s.lower()
        if re.search(r"connect req|connected", sl):
            out["connect_sent"] = _date(s) or out["connect_sent"]
        elif re.search(r"\bdm\b|msg sent|message sent", sl):
            out["msg_sent"] = _date(s) or out["msg_sent"]
        elif "accepted" in sl:
            out["accepted"] = _date(s) or out["accepted"]
        elif "nudge" in sl:
            out["nudged"] = _date(s) or out["nudged"]
        if "replied" in sl:
            out["replied"] = True
        if any(w in sl for w in ("failed", "off-target", "unavailable", "manual", "needs fix")):
            out["failed"] = True
    return out


def classify(lc: dict, today: _dt.date):
    """Return (bucket, detail) for a parsed lifecycle, or (None, None) if nothing to do."""
    if lc["replied"]:
        return None, None  # converted — done
    # A message was actually delivered (DM to 1st-degree, or post-accept message).
    if lc["msg_sent"]:
        if lc["nudged"]:
            return None, "nudged — awaiting reply"
        age = (today - lc["msg_sent"]).days if lc["msg_sent"] else 0
        if age >= NUDGE_DAYS:
            return "nudge", f"message sent {lc['msg_sent']} ({age}d ago), no reply"
        return None, f"awaiting reply ({age}d)"
    if lc["accepted"]:
        return "send", f"accepted {lc['accepted']} — send the full drafted message"
    if lc["connect_sent"]:
        age = (today - lc["connect_sent"]).days
        if age >= ACCEPT_CHECK_DAYS:
            return "check", f"connect req {lc['connect_sent']} ({age}d ago) — check if accepted"
        return None, f"connect req {lc['connect_sent']} ({age}d) — too recent"
    if lc["failed"]:
        return "manual", lc["raw"]
    return None, None


def main():
    today = _dt.date.today() if "--today" not in sys.argv else _dt.date.fromisoformat(
        sys.argv[sys.argv.index("--today") + 1]
    )
    rows = br.parse_applications()
    by_url, by_role = br.load_outreach_index()

    buckets = {"send": [], "check": [], "nudge": [], "manual": []}
    waiting = 0

    for row in rows:
        company = row.get("company", "")
        role = row.get("role", "")
        jd = row.get("job url", "")
        if not company:
            continue
        entry = by_url.get(br.normalize_url(jd)) or by_role.get(br.role_key(company, role))
        for kind, col in (("HM", "hm messaged"), ("TA", "ta messaged")):
            lc = parse_lifecycle(row.get(col, ""))
            bucket, detail = classify(lc, today)
            if bucket is None:
                if detail:
                    waiting += 1
                continue
            party = (entry or {}).get(kind.lower()) if entry else None
            contact = ""
            if party and party.get("fm"):
                contact = party["fm"].get("recipient", "")
            buckets[bucket].append({
                "tier": row.get("tier", ""),
                "company": company,
                "role": role,
                "jd": jd,
                "kind": kind,
                "contact": contact,
                "detail": detail,
                "msg": (party or {}).get("msg", "") if party else "",
            })

    def tkey(it):
        t = it["tier"]
        return (TIER_ORDER.index(t) if t in TIER_ORDER else 99, it["company"].lower())

    for b in buckets.values():
        b.sort(key=tkey)

    out = [f"# Outreach Follow-ups — {today}", ""]
    out.append(
        "> Date-driven follow-up queue derived from `wiki/applications.md`. "
        "**This file is built by cron (no LinkedIn).** The acting step is interactive: "
        "say *“run follow-ups”* in a Claude session with LinkedIn connected to poll "
        "acceptances/replies, send the queued messages, and write results back to the tracker. "
        f"Thresholds: acceptance check after **{ACCEPT_CHECK_DAYS}d**, nudge after **{NUDGE_DAYS}d**."
    )
    out.append("")
    out.append(
        f"**Queue:** {len(buckets['send'])} ready-to-message · "
        f"{len(buckets['check'])} acceptance-checks · "
        f"{len(buckets['nudge'])} nudges · "
        f"{len(buckets['manual'])} manual/needs-fix · {waiting} awaiting (not yet due)"
    )
    out.append("")

    sections = [
        ("send", "✅ Accepted → send the full drafted message",
         "These connections were accepted. Send the real `hm.md`/`ta.md` message (below), "
         "then record `; msg sent <date>` on the tracker cell."),
        ("check", "⏳ Acceptance check due",
         "Connect requests old enough to check. Poll each profile — if now 1st-degree, "
         "record `; accepted <date>` (they move to the send queue); else leave pending."),
        ("nudge", "🔔 No reply → nudge due",
         "A message was delivered but no reply within the window. Send one short nudge, "
         "then record `; nudged <date>`."),
        ("manual", "⚠ Manual / needs fix",
         "Not auto-actionable — 1st-degree-but-tool-blocked (DM manually), follow-only "
         "(no connect), wrong-slug, or other. Handle by hand."),
    ]
    for key, title, blurb in sections:
        items = buckets[key]
        out.append(f"## {title}  ({len(items)})")
        out.append("")
        out.append(f"_{blurb}_")
        out.append("")
        if not items:
            out.append("_none today_")
            out.append("")
            continue
        for it in items:
            who = f"{it['contact']}" if it["contact"] else "(contact in tracker)"
            out.append(f"### [{it['tier']}] {it['company']} — {it['role']} · {it['kind']}: {who}")
            out.append(f"- JD: {it['jd']}")
            out.append(f"- Status: {it['detail']}")
            if key == "send" and it["msg"]:
                out.append("- Message to send:")
                out.append("")
                for ln in it["msg"].splitlines():
                    out.append(f"  > {ln}" if ln.strip() else "  >")
            out.append("")

    out_path = os.path.join(OUTREACH_DIR, f"FOLLOWUPS-{today}.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out).rstrip() + "\n")
    print(f"wrote {out_path}")
    print(
        f"  {len(buckets['send'])} send | {len(buckets['check'])} check | "
        f"{len(buckets['nudge'])} nudge | {len(buckets['manual'])} manual | {waiting} waiting"
    )


if __name__ == "__main__":
    main()
