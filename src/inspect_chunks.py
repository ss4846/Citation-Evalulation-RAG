"""Quick health check on the parsed chunks before we build the index."""
import os, json
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_PATH = os.path.join(ROOT, "data", "processed", "chunks.jsonl")

chunks = [json.loads(l) for l in open(CHUNKS_PATH, encoding="utf-8")]

print(f"Total chunks: {len(chunks)}")
print(f"Unique cases: {len(set(c['itemid'] for c in chunks))}")
print()

# Chunks per case - are any cases suspiciously thin?
per_case = Counter(c['case'] for c in chunks)
counts = sorted(per_case.values())
print(f"Chunks per case - min: {counts[0]}, max: {counts[-1]}, median: {counts[len(counts)//2]}")
print()

# Section breakdown - do we have both FACTS and LAW content?
sections = Counter(c['section'] for c in chunks)
print("Section breakdown:")
for sec, n in sections.most_common():
    print(f"  {sec}: {n}")
print()

# Text length sanity - any empty or tiny chunks that slipped through?
lengths = [len(c['text']) for c in chunks]
print(f"Text length - min: {min(lengths)}, max: {max(lengths)}, avg: {sum(lengths)//len(lengths)}")
tiny = sum(1 for l in lengths if l < 30)
print(f"Chunks under 30 chars (possible junk): {tiny}")
print()

# Show a couple of real examples
print("=== 2 sample chunks ===")
for c in chunks[:2]:
    print(f"[{c['case'][:45]} §{c['para']}] ({c['section']})")
    print(f"  {c['text'][:180]}")
    print()