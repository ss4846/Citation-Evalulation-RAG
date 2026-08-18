"""
ingest.py - parses a saved ECHR judgment HTML file into clean
paragraph chunks. Each chunk keeps its paragraph number (the citable §)
and the section it belongs to (FACTS, LAW, etc).

This module is imported by fetch_cases.py - you don't usually run it directly,
but running it on the sample file is a good test.
"""

import re
from bs4 import BeautifulSoup

def extract_case_name(soup, fallback):
    """Pull the case name from the judgment HTML."""
    for p in soup.find_all("p"):
        text = p.get_text().replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text).strip()
        # The case name line contains "CASE OF" and "v." and is short
        if "CASE OF" in text.upper() and " V. " in text.upper() and len(text) < 120:
            return text
    return fallback

# Section headings we care about tagging
SECTION_HEADERS = {
    "INTRODUCTION", "THE FACTS", "THE LAW", "PROCEDURE",
    "RELEVANT LEGAL FRAMEWORK", "RELEVANT DOMESTIC LAW",
}


def clean_text(text):
    """Remove Word's non-breaking spaces and collapse whitespace."""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_judgment(html, case_name, itemid):
    """
    Parse one judgment's HTML into a list of paragraph-chunk dicts.
    Returns: [{case, itemid, para, section, text}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    # If no case name was passed (re-parsing from cached HTML), extract it
    if case_name is None:
        case_name = extract_case_name(soup, itemid)
    paras = soup.find_all("p")

    chunks = []
    current_section = "HEADER"

    for p in paras:
        text = clean_text(p.get_text())
        if not text:
            continue

        # Is this a section heading? Must be a known header, or a
        # Roman-numeral-prefixed heading like "I. THE FACTS".
        # This avoids treating stray initials / acronyms as sections.
        upper = text.upper()
        is_known = upper in SECTION_HEADERS
        is_roman_heading = bool(re.match(r"^[IVX]+\.\s+[A-Z]", text)) and len(text) < 80
        if is_known or is_roman_heading:
            current_section = upper
            continue

        # Is this a numbered judgment paragraph? starts with "NN."
        m = re.match(r"^(\d+)\.\s+(.*)", text)
        if m:
            para_num = int(m.group(1))
            para_text = m.group(2).strip()
            # Filter out stray short fragments
            if len(para_text) >= 40:
                chunks.append({
                    "case": case_name,
                    "itemid": itemid,
                    "para": para_num,
                    "section": current_section,
                    "text": para_text,
                })

    return chunks


# If run directly, test on the sample file
if __name__ == "__main__":
    import os
    sample_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "raw", "sample_case.html"
    )
    with open(sample_path, encoding="utf-8") as f:
        html = f.read()

    chunks = parse_judgment(html, "CASE OF KOLESNYK AND SMELNYTSKYY v. UKRAINE", "001-251251")
    print(f"Extracted {len(chunks)} paragraph chunks")
    print()
    for c in chunks[:3]:
        print(f"[§{c['para']}] ({c['section']}) {c['text'][:150]}")
        print()