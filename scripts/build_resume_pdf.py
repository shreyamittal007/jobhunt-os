#!/usr/bin/env python3
"""Convert a markdown resume to a single-page PDF via headless Chrome.

Markdown format expected:
  # Full Name
  contact line
  summary paragraph
  ## WORK EXPERIENCE
  ### Company | Location | Date range
  #### Role Title            (single role under company)
  #### Role Title | Date     (multiple roles under same company)
  *context paragraph*
  - bullet
  ## Education : one line

Usage:
  python3 scripts/build_resume_pdf.py raw/Shreya_Mittal_Stripe_Risk.md
  python3 scripts/build_resume_pdf.py raw/resume.md -o raw/output.pdf
"""

import sys
import re
import argparse
import subprocess
import tempfile
import os
from pathlib import Path


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
@page { size: A4; margin: 0; }
body {
    font-family: Calibri, Arial, sans-serif;
    font-size: 9.5pt;
    color: #111;
    background: #fff;
    line-height: 1.38;
    padding: 10mm 16mm;
    width: 210mm;
}

/* ── Header ── */
.header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 3pt;
}
.name {
    font-size: 24pt;
    font-weight: 700;
    color: #111;
    line-height: 1;
}
.contact {
    font-size: 9pt;
    color: #111;
    text-align: right;
    line-height: 1.34;
}

/* ── Summary ── */
.summary {
    font-size: 9pt;
    color: #111;
    margin-bottom: 6pt;
    line-height: 1.4;
}

/* ── Skills line ── */
.skills {
    font-size: 9pt;
    color: #111;
    margin-bottom: 4pt;
    line-height: 1.36;
}

/* ── Section header ── */
h2 {
    font-size: 10.5pt;
    font-weight: 700;
    color: #111;
    margin-bottom: 0;
    margin-top: 5pt;
    text-transform: uppercase;
}

/* ── Company row (bottom line only) ── */
.company-row {
    width: 100%;
    border-collapse: collapse;
    margin-top: 6pt;
    border-bottom: 1px solid #111;
}
.company-row td {
    font-size: 10pt;
    font-weight: 700;
    padding: 1.5pt 0;
    vertical-align: middle;
}
.company-row .co-name { text-align: left; width: 35%; }
.company-row .co-loc  { text-align: center; width: 35%; font-weight: 400; }
.company-row .co-date { text-align: right; width: 30%; font-weight: 400; }

/* ── Role title row ── */
.role-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-top: 1.5pt;
    margin-bottom: 0.5pt;
}
.role-title { font-size: 9.5pt; font-weight: 700; }
.role-date  { font-size: 9pt; color: #111; }

/* ── Context paragraph ── */
.context {
    font-size: 9pt;
    color: #111;
    margin-bottom: 1.5pt;
    font-style: normal;
    line-height: 1.34;
}

/* ── Bullets ── */
ul {
    padding-left: 14pt;
    margin-top: 1pt;
    margin-bottom: 2pt;
    list-style-type: disc;
}
li {
    font-size: 9pt;
    margin-bottom: 2pt;
    color: #111;
    line-height: 1.35;
}
li strong { color: #111; }

/* ── Links ── */
a { color: #111; text-decoration: underline; }

/* ── Education ── */
.education {
    font-size: 9.5pt;
    font-weight: 700;
    margin-top: 8pt;
}
"""


def inline(text: str) -> str:
    # Extract markdown links before escaping so URLs aren't mangled
    links = {}
    def stash_link(m):
        key = f'\x00LINK{len(links)}\x00'
        links[key] = f'<a href="{m.group(2)}">{m.group(1)}</a>'
        return key
    text = re.sub(r'\[([^\]]+)\]\(((?:https?|mailto):[^\)]+)\)', stash_link, text)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    for key, val in links.items():
        text = text.replace(key, val)
    return text


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # H1 — name + contact + summary
        if re.match(r'^# (?!#)', line):
            name = line[2:].strip()
            i += 1
            contact = ''
            if i < len(lines) and lines[i].strip() and not lines[i].startswith('#'):
                contact = lines[i].strip()
                i += 1
            # summary lines until first ##; skills line handled separately
            summary_lines = []
            skills_line = ''
            while i < len(lines) and not re.match(r'^##', lines[i]):
                if lines[i].strip():
                    if lines[i].strip().startswith('**Skills:**'):
                        skills_line = lines[i].strip()
                    else:
                        summary_lines.append(lines[i].strip())
                i += 1
            out.append('<div class="header">')
            out.append(f'  <div class="name">{inline(name)}</div>')
            out.append(f'  <div class="contact">{inline(contact)}</div>')
            out.append('</div>')
            if summary_lines:
                out.append(f'<p class="summary">{inline(" ".join(summary_lines))}</p>')
            if skills_line:
                out.append(f'<p class="skills">{inline(skills_line)}</p>')
            continue

        # H2 — section header (Education handled specially)
        if re.match(r'^## ', line):
            section = line[3:].strip()
            if section.upper().startswith('EDUCATION') or section.upper().startswith('EDU'):
                out.append(f'<div class="education">{inline(section)}</div>')
            else:
                out.append(f'<h2>{section}</h2>')
            i += 1
            continue

        # H3 — company row: ### Company | Location | Date
        if re.match(r'^### ', line):
            parts = [p.strip() for p in line[4:].split('|')]
            company = parts[0] if len(parts) > 0 else ''
            location = parts[1] if len(parts) > 1 else ''
            date = parts[2] if len(parts) > 2 else ''
            out.append('<table class="company-row"><tr>')
            out.append(f'  <td class="co-name">{inline(company)}</td>')
            out.append(f'  <td class="co-loc">{inline(location)}</td>')
            out.append(f'  <td class="co-date">{inline(date)}</td>')
            out.append('</tr></table>')
            i += 1
            continue

        # H4 — role title row: #### Role Title | Date  or  #### Role Title
        if re.match(r'^#### ', line):
            role_raw = line[5:].strip()
            if '|' in role_raw:
                role_title, role_date = [p.strip() for p in role_raw.split('|', 1)]
            else:
                role_title, role_date = role_raw, ''
            out.append('<div class="role-row">')
            out.append(f'  <span class="role-title">{inline(role_title)}</span>')
            if role_date:
                out.append(f'  <span class="role-date">{inline(role_date)}</span>')
            out.append('</div>')
            i += 1
            continue

        # *italic context paragraph*
        if re.match(r'^\*[^*]', line) and line.rstrip().endswith('*'):
            text = line.strip().lstrip('*').rstrip('*').strip()
            out.append(f'<p class="context">{inline(text)}</p>')
            i += 1
            continue

        # bullet block
        if line.startswith('- '):
            out.append('<ul>')
            while i < len(lines) and lines[i].rstrip().startswith('- '):
                bullet = lines[i].rstrip()[2:].strip()
                out.append(f'  <li>{inline(bullet)}</li>')
                i += 1
            out.append('</ul>')
            continue

        i += 1

    return '\n'.join(out)


def build(md_path: Path, pdf_path: Path):
    md = md_path.read_text(encoding='utf-8')
    body = md_to_html(md)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
{CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""

    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
        f.write(html)
        tmp_html = f.name

    chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    cmd = [
        chrome,
        '--headless',
        '--disable-gpu',
        '--no-sandbox',
        '--run-all-compositor-stages-before-draw',
        f'--print-to-pdf={pdf_path}',
        '--print-to-pdf-no-header',
        tmp_html,
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(tmp_html)

    if pdf_path.exists():
        print(f'Saved: {pdf_path}')
    else:
        print('PDF generation failed', file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='Path to .md resume file')
    parser.add_argument('-o', '--output', help='Output .pdf path')
    args = parser.parse_args()

    md_path = Path(args.input)
    if not md_path.exists():
        print(f'Error: {md_path} not found', file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(args.output) if args.output else md_path.with_suffix('.pdf')
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    build(md_path, pdf_path)


if __name__ == '__main__':
    main()
