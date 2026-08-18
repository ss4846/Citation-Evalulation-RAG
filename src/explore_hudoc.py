# """
# Reconnaissance script - fetches ONE ECHR case from HUDOC
# so we can see the raw data format before building the real ingester.
# This does NOT save anything to your dataset. It just shows us what we get.
# """

# import requests
# import json

# # HUDOC's search API endpoint - returns metadata + document IDs
# SEARCH_URL = "https://hudoc.echr.coe.int/app/query/results"

# # Ask for just 1 English-language Grand Chamber/Chamber judgment.
# # We keep the query deliberately simple for this test.
# params = {
#     "query": 'contenttype:"JUDGMENTS" AND languageisocode:"ENG"',
#     "select": "itemid,docname,appno,article,kpdate,doctype",
#     "sort": "kpdate Descending",
#     "start": 0,
#     "length": 1,  # <-- ONLY ONE CASE
# }

# print("=" * 70)
# print("STEP 1: Querying HUDOC search API for one case...")
# print("=" * 70)

# resp = requests.get(SEARCH_URL, params=params, timeout=30)
# print("Status code:", resp.status_code)
# print("Request URL:", resp.url)
# print()

# # Show the raw metadata response
# try:
#     data = resp.json()
#     print("Raw search response (metadata):")
#     print(json.dumps(data, indent=2)[:3000])  # first 3000 chars only
#     print()
# except Exception as e:
#     print("Could not parse JSON. Raw text (first 2000 chars):")
#     print(resp.text[:2000])
#     raise SystemExit("Stopping so we can inspect the format above.")

# # Try to pull the document ID of the first result
# try:
#     results = data.get("results", [])
#     print(f"Number of results returned: {len(results)}")
#     if not results:
#         raise SystemExit("No results came back - we'll adjust the query.")

#     first = results[0]
#     print("\nFirst result's fields:")
#     print(json.dumps(first, indent=2))

#     columns = first.get("columns", first)
#     itemid = columns.get("itemid")
#     docname = columns.get("docname")
#     print("\nExtracted itemid:", itemid)
#     print("Extracted docname:", docname)
# except Exception as e:
#     print("Couldn't navigate the response structure:", e)
#     raise SystemExit("Stopping so we can inspect the format above.")

# # Now try to fetch the FULL TEXT of that one case
# print()
# print("=" * 70)
# print("STEP 2: Fetching the full judgment text for that case...")
# print("=" * 70)

# # HUDOC serves full document text from this pattern
# DOC_URL = f"https://hudoc.echr.coe.int/app/conversion/docx/html/body?library=ECHR&id={itemid}"

# doc_resp = requests.get(DOC_URL, timeout=30)
# print("Status code:", doc_resp.status_code)
# print("Content length:", len(doc_resp.text), "characters")
# print()
# print("First 3000 characters of the full document:")
# print("-" * 70)
# print(doc_resp.text[:3000])
# print("-" * 70)

# # Save the full raw document so we can examine it properly
# with open("data/raw/sample_case.html", "w", encoding="utf-8") as f:
#     f.write(doc_resp.text)

# print()
# print("Full raw document saved to: data/raw/sample_case.html")
# print("Open that file to see the complete structure.")


"""
Reconnaissance script v2 - tries several HUDOC query formats to find
one that actually returns results. Still fetching only ONE case.
"""

import requests
import json

SEARCH_URL = "https://hudoc.echr.coe.int/app/query/results"

# HUDOC is fussy about quoting. We'll try several query strings and
# see which ones return a non-zero resultcount.
QUERIES_TO_TRY = [
    'contenttype:"JUDGMENTS"',
    '(contenttype="JUDGMENTS")',
    '(contenttype:"JUDGMENTS") AND (languageisocode:"ENG")',
    '(contenttype="JUDGMENTS") AND (languageisocode="ENG")',
    'doctypebranch:"CHAMBER"',
    '(doctypebranch="CHAMBER") AND (languageisocode="ENG")',
    '(kpthesaurus="Article 8")',
]

# The 'select' fields we want back for each result
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
    print("None returned results. Paste this whole output back.")
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