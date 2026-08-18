"""
fetch_cases.py - builds the full ECHR corpus.

1. Searches HUDOC for Chamber judgments in English mentioning Article 5 or 8.
2. Filters to 2010-2020 in Python (avoids HUDOC's fussy date-query syntax).
3. Downloads each judgment's HTML (with retries - HUDOC is slow).
4. Parses each into paragraph chunks using ingest.py.
5. Saves everything to data/processed/chunks.jsonl.

Resumes automatically: already-downloaded cases are skipped, so you can
stop (Ctrl+C) and restart without losing progress.
"""

import os
import json
import time
import requests
from ingest import parse_judgment

# ---- Config ----
TARGET_CASES = 80
START_YEAR = 2010
END_YEAR = 2020
ARTICLES = ["5", "8"]
SEARCH_URL = "https://hudoc.echr.coe.int/app/query/results"
DOC_URL_TMPL = "https://hudoc.echr.coe.int/app/conversion/docx/html/body?library=ECHR&id={itemid}"

# ---- Paths (anchored to project root) ----
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
RAW_DIR = os.path.join(ROOT, "data", "raw", "cases")
PROC_DIR = os.path.join(ROOT, "data", "processed")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROC_DIR, exist_ok=True)
CHUNKS_PATH = os.path.join(PROC_DIR, "chunks.jsonl")


def search_cases(article, page_size=500, max_pages=8):
    """
    Page through HUDOC results for one article, newest first.
    Stops early once results get older than our window.
    Returns list of column-dicts.
    """
    all_cols = []
    for page in range(max_pages):
        query = (f'(doctypebranch="CHAMBER") AND (languageisocode="ENG") '
                 f'AND (article="{article}")')
        params = {
            "query": query,
            "select": "itemid,docname,article,kpdate",
            "sort": "kpdate Descending",   # newest first
            "start": page * page_size,
            "length": page_size,
        }
        r = requests.get(SEARCH_URL, params=params, timeout=90)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            break

        cols = [res["columns"] for res in results]
        all_cols.extend(cols)

        # Newest-first: once the LAST item on the page is before 2010,
        # every later page is even older - stop paging.
        oldest_on_page = cols[-1].get("kpdate", "9999")
        try:
            if int(oldest_on_page[:4]) < START_YEAR:
                break
        except (ValueError, TypeError):
            pass

        time.sleep(1)  # polite pause between pages

    print(f"  Article {article}: pulled {len(all_cols)} results across pages")
    return all_cols


def in_date_range(kpdate):
    """kpdate looks like '2015-03-12T00:00:00'. Keep 2010-2020."""
    try:
        year = int(kpdate[:4])
        return START_YEAR <= year <= END_YEAR
    except (ValueError, TypeError):
        return False


def download_html(itemid, retries=3):
    """Download one judgment's HTML with retries. Returns text or None."""
    url = DOC_URL_TMPL.format(itemid=itemid)
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and len(r.text) > 1000:
                return r.text
            print(f"      status {r.status_code}, len {len(r.text)} - retrying")
        except requests.exceptions.RequestException as e:
            print(f"      attempt {attempt} failed ({type(e).__name__})")
        if attempt < retries:
            time.sleep(5)
    return None


def main():
    # --- Step 1: gather candidate cases from both articles ---
    print("Searching HUDOC for Article 5 and Article 8 cases...")
    seen_ids = set()
    candidates = []
    for article in ARTICLES:
        try:
            cases = search_cases(article)
            print(f"  Article {article}: {len(cases)} raw results")
        except Exception as e:
            print(f"  Article {article}: search failed ({e})")
            continue
        for c in cases:
            itemid = c.get("itemid")
            if not itemid or itemid in seen_ids:
                continue
            if not in_date_range(c.get("kpdate", "")):
                continue
            seen_ids.add(itemid)
            candidates.append(c)

    print(f"\n{len(candidates)} unique cases in {START_YEAR}-{END_YEAR} after filtering.")
    if not candidates:
        print("No candidates found - something's off with the search. Stop and check.")
        return

    # --- Step 2: download + parse until we hit the target ---
    all_chunks = []
    saved_cases = 0

    for i, c in enumerate(candidates, 1):
        if saved_cases >= TARGET_CASES:
            break

        itemid = c["itemid"]
        case_name = c.get("docname", itemid)
        raw_path = os.path.join(RAW_DIR, f"{itemid}.html")

        # Resume: use cached HTML if we already downloaded it
        if os.path.exists(raw_path):
            with open(raw_path, encoding="utf-8") as f:
                html = f.read()
            print(f"[{i}/{len(candidates)}] cached: {case_name[:55]}")
        else:
            print(f"[{i}/{len(candidates)}] downloading: {case_name[:55]}")
            html = download_html(itemid)
            if html is None:
                print("      FAILED - skipping this case")
                continue
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(html)
            time.sleep(2)  # polite delay between downloads

        # Parse into chunks
        chunks = parse_judgment(html, case_name, itemid)
        if len(chunks) < 3:
            print(f"      only {len(chunks)} chunks parsed - skipping (odd format)")
            continue

        all_chunks.extend(chunks)
        saved_cases += 1
        print(f"      -> {len(chunks)} chunks  (cases saved: {saved_cases}/{TARGET_CASES})")

    # --- Step 3: write the combined chunks file ---
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for ch in all_chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    print("\n" + "=" * 60)
    print(f"DONE. {saved_cases} cases, {len(all_chunks)} total chunks.")
    print(f"Saved to: {CHUNKS_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()