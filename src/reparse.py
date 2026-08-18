"""Re-parse all cached HTML cases with the updated ingest logic.
No downloading - uses the HTML already saved in data/raw/cases/."""
import os, json
from ingest import parse_judgment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw", "cases")
CHUNKS_PATH = os.path.join(ROOT, "data", "processed", "chunks.jsonl")

all_chunks = []
files = [f for f in os.listdir(RAW_DIR) if f.endswith(".html")]
print(f"Re-parsing {len(files)} cached cases...")

for fname in files:
    itemid = fname.replace(".html", "")
    with open(os.path.join(RAW_DIR, fname), encoding="utf-8") as f:
        html = f.read()
    # case name is recovered from the <title> or falls back to itemid
    chunks = parse_judgment(html, None, itemid)
    all_chunks.extend(chunks)

with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
    for ch in all_chunks:
        f.write(json.dumps(ch, ensure_ascii=False) + "\n")

print(f"Done. {len(all_chunks)} chunks (was 9511).")