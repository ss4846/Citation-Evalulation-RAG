"""
Reconnaissance script v2 - tries several HUDOC query formats to find
one that actually returns results. Still fetching only ONE case.
"""

import requests
import json

SEARCH_URL = "https://hudoc.echr.coe.int/app/query/results"

QUERIES_TO_TRY = [
    'contenttype:"JUDGMENTS"',
    '(contenttype="JUDGMENTS")',
    '(contenttype:"JUDGMENTS") AND (languageisocode:"ENG")',
    '(contenttype="JUDGMENTS") AND (languageisocode="ENG")',
    'doctypebranch:"CHAMBER"',
    '(doctypebranch="CHAMBER") AND (languageisocode="ENG")',
    '(kpthesaurus="Article 8")',
]

# The 'select' fields for each result
SELECT = "itemid,docname,appno,article,kpdate,doctypebranch,languageisocode"

print("Testing multiple query formats against HUDOC...\n")

working = []

for i, q in enumerate(QUERIES_TO_TRY, 1):
    params = {
        "query": q,
        "select": SELECT,
        "sort": "kpdate Descending",
        "start": 0,
        "length": 1,
    }
    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=30)
        data = resp.json()
        count = data.get("resultcount", 0)
        print(f"[{i}] resultcount={count:<8} query: {q}")
        if count and count > 0:
            working.append((q, data))
    except Exception as e:
        print(f"[{i}] ERROR ({e}) query: {q}")

print()

if not working:
    print("None returned results.")
    raise SystemExit()

# Use the first working query and show its full structure
best_query, best_data = working[0]
print("=" * 70)
print("Using first working query:", best_query)
print("=" * 70)

first = best_data["results"][0]
print("\nFull structure of the first result:")
print(json.dumps(first, indent=2))

# Pull the itemid out of wherever it lives
columns = first.get("columns", first)
itemid = columns.get("itemid")
docname = columns.get("docname")
print("\nExtracted itemid:", itemid)
print("Extracted docname:", docname)

if not itemid:
    print("\nCouldn't find itemid - paste the structure above back to me.")
    raise SystemExit()

# Fetch the full judgment text for that one case
print("\n" + "=" * 70)
print("Fetching full judgment text...")
print("=" * 70)

DOC_URL = f"https://hudoc.echr.coe.int/app/conversion/docx/html/body?library=ECHR&id={itemid}"
doc_resp = requests.get(DOC_URL, timeout=30)
print("Status code:", doc_resp.status_code)
print("Content length:", len(doc_resp.text), "characters")

with open("data/raw/sample_case.html", "w", encoding="utf-8") as f:
    f.write(doc_resp.text)

print("\nFirst 2500 characters of the document:")
print("-" * 70)
print(doc_resp.text[:2500])
print("-" * 70)
print("\nFull document saved to: data/raw/sample_case.html")