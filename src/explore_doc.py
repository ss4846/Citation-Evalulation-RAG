"""
Fetches the full judgment text for one known case, with a long timeout
and retries. We already have the itemid from the previous step.
"""

import requests
import time

# The itemid we already found in the previous run
ITEMID = "001-251251"

# HUDOC's full-text endpoint (HTML body of the judgment)
DOC_URL = f"https://hudoc.echr.coe.int/app/conversion/docx/html/body?library=ECHR&id={ITEMID}"

print("Fetching full text for:", ITEMID)
print("URL:", DOC_URL)
print()

# Retry up to 3 times with a long timeout - HUDOC is slow
doc_resp = None
for attempt in range(1, 4):
    try:
        print(f"Attempt {attempt} (timeout=90s)...")
        doc_resp = requests.get(DOC_URL, timeout=90)
        print("Success. Status code:", doc_resp.status_code)
        break
    except requests.exceptions.ReadTimeout:
        print(f"  Attempt {attempt} timed out.")
        if attempt < 3:
            print("  Waiting 5s before retrying...")
            time.sleep(5)
    except Exception as e:
        print(f"  Attempt {attempt} failed: {e}")
        if attempt < 3:
            time.sleep(5)

if doc_resp is None:
    raise SystemExit(
        "\nAll attempts timed out. HUDOC may be slow right now - "
        "try running this script again in a minute, or paste this back."
    )

print("Content length:", len(doc_resp.text), "characters")

# Save the full document
with open("data/raw/sample_case.html", "w", encoding="utf-8") as f:
    f.write(doc_resp.text)
print("Saved to: data/raw/sample_case.html")

print("\nFirst 3000 characters:")
print("-" * 70)
print(doc_resp.text[:3000])
print("-" * 70)