"""
Parse Fisher Scientific SDS PDFs into chunks.jsonl.

One chunk = one SDS section on one page:
    {"id", "doc", "chemical", "section", "section_title", "page", "text"}

Usage (Windows):
    python parse_sds.py
    python parse_sds.py --data "D:\\fall26\\ml-industry\\project\\data" --out chunks.jsonl
"""
import argparse
import json
import re
import sys
from pathlib import Path

import pdfplumber  # pip install pdfplumber

# Fisher's 16 section titles. Each header must be number + start of the expected title.
# This prevents false positives from body lines that happen to start with "3. Something".
SECTION_TITLES = {
    1: "Identification",
    2: "Hazard(s) identification",
    3: "Composition/information on Ingredients",
    4: "First-aid measures",
    5: "Fire-fighting measures",
    6: "Accidental release measures",
    7: "Handling and Storage",
    8: "Exposure controls / personal protection",
    9: "Physical and chemical properties",
    10: "Stability and reactivity",
    11: "Toxicological information",
    12: "Ecological information",
    13: "Disposal considerations",
    14: "Transport information",
    15: "Regulatory Information",
    16: "Other Information",
}

HEADER_RE = re.compile(r"^\s*(\d{1,2})\.\s+([A-Z][^\n]*)$")
PAGE_FOOTER_RE = re.compile(r"^\s*Page\s+\d+\s*/\s*\d+\s*$")
RULE_RE = re.compile(r"^\s*_{10,}")  # the long underscore lines
RUNNING_HEADER_RE = re.compile(r"Revision Date\s+\d{2}-[A-Za-z]{3}-\d{4}\s*$")


def norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def match_header(line: str, expected: int):
    """Return section number if `line` is the header for the expected next section."""
    m = HEADER_RE.match(line)
    if not m:
        return None
    num = int(m.group(1))
    if num != expected or num not in SECTION_TITLES:
        return None
    want = norm(SECTION_TITLES[num])[:8]
    if not norm(m.group(2)).startswith(want):
        return None
    return num


def clean_lines(text: str, page_no: int):
    out = []
    for i, line in enumerate(text.splitlines()):
        line = RULE_RE.sub("", line).rstrip()
        if not line.strip():
            continue
        if PAGE_FOOTER_RE.match(line):
            continue
        # running header "Acetic acid   Revision Date 18-Dec-2025" on pages 2+
        if page_no > 1 and i < 3 and RUNNING_HEADER_RE.search(line):
            continue
        out.append(line)
    return out


def cell(v) -> str:
    return " ".join((v or "").split("\n")).strip() if v else ""


def render_table(rows):
    """Render a table as one labeled line per data row so values keep their column:
    'Methyl alcohol | OSHA PEL: (Vacated) TWA: 200 ppm; TWA: 260 mg/m3 | NIOSH: ...'"""
    rows = [r for r in rows if any(c and c.strip() for c in r)]
    if not rows:
        return []
    head = [cell(c) for c in rows[0]]
    has_header = head and head[0].lower() == "component"
    if not has_header:  # continuation of a table from the previous page
        return [" | ".join(
            "; ".join(s.strip() for s in (c or "").split("\n") if s.strip())
            for c in r if c and c.strip()) for r in rows]
    lines = []
    for r in rows[1:]:
        parts = []
        for name, val in zip(head, r):
            val = "; ".join(s.strip() for s in (val or "").split("\n") if s.strip())
            if not val:
                continue
            parts.append(val if name.lower() == "component" else f"{name}: {val}")
        if parts:
            lines.append(" | ".join(parts))
    return lines


def page_lines(page):
    """Text lines in reading order, with tables replaced by labeled rows."""
    tables = page.find_tables()
    boxes = [t.bbox for t in tables]

    def outside(obj):
        cx = (obj["x0"] + obj["x1"]) / 2
        cy = (obj["top"] + obj["bottom"]) / 2
        return not any(x0 <= cx <= x1 and t <= cy <= b for x0, t, x1, b in boxes)

    items = []  # (top, text)
    for ln in page.filter(lambda o: o.get("object_type") != "char" or outside(o)).extract_text_lines():
        items.append((ln["top"], ln["text"]))
    for t in tables:
        for k, line in enumerate(render_table(t.extract())):
            items.append((t.bbox[1] + k * 0.01, line))
    items.sort(key=lambda x: x[0])
    return "\n".join(txt for _, txt in items)


def get_chemical_name(first_page_text: str, fallback: str) -> str:
    m = re.search(r"Product Name\s+(.+)", first_page_text)
    return m.group(1).strip() if m else fallback


def parse_pdf(path: Path):
    doc = path.name
    chunks, problems = [], []
    current = 0  # 0 = before section 1 (title block)
    buf = {}     # (section, page) -> list of lines

    with pdfplumber.open(path) as pdf:
        chemical = get_chemical_name(pdf.pages[0].extract_text() or "", path.stem)
        for page_no, page in enumerate(pdf.pages, start=1):
            text = page_lines(page) or ""
            if not text.strip():
                problems.append(f"page {page_no}: no text (scanned?)")
            for line in clean_lines(text, page_no):
                hit = match_header(line, current + 1)
                if hit:
                    current = hit
                    continue
                if current == 0:
                    continue  # title block before section 1
                buf.setdefault((current, page_no), []).append(line)

    found = sorted({s for s, _ in buf})
    missing = [s for s in SECTION_TITLES if s not in found]
    if missing:
        problems.append(f"missing sections: {missing}")

    for (section, page), lines in sorted(buf.items()):
        text = "\n".join(lines).strip()
        if not text:
            continue
        chunks.append({
            "id": f"{path.stem}_s{section:02d}_p{page:02d}",
            "doc": doc,
            "chemical": chemical,
            "section": section,
            "section_title": SECTION_TITLES[section],
            "page": page,
            "text": text,
        })
    return chunks, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=r"D:\fall26\ml-industry\project\data")
    ap.add_argument("--out", default="chunks.jsonl")
    args = ap.parse_args()

    pdfs = sorted(Path(args.data).glob("*_fisher.pdf"))
    if not pdfs:
        sys.exit(f"No *_fisher.pdf files in {args.data}")

    all_chunks, bad = [], 0
    for p in pdfs:
        chunks, problems = parse_pdf(p)
        all_chunks.extend(chunks)
        n_sec = len({c["section"] for c in chunks})
        status = "OK" if not problems else "CHECK"
        bad += bool(problems)
        print(f"[{status}] {p.name}: {n_sec}/16 sections, {len(chunks)} chunks")
        for pr in problems:
            print(f"        - {pr}")

    with open(args.out, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(all_chunks)} chunks from {len(pdfs)} PDFs to {args.out}")
    if bad:
        print(f"{bad} file(s) need a manual look.")


if __name__ == "__main__":
    main()