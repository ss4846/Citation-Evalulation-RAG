"""Quick check: what does the kpdate field actually look like?"""
import requests

SEARCH_URL = "https://hudoc.echr.coe.int/app/query/results"
query = '(doctypebranch="CHAMBER") AND (languageisocode="ENG") AND (article="5")'
params = {
    "query": query,
    "select": "itemid,docname,article,kpdate",
    "sort": "kpdate Ascending",
    "start": 0,
    "length": 10,
}

r = requests.get(SEARCH_URL, params=params, timeout=60)
data = r.json()

print("First 10 results - raw kpdate values:")
print("-" * 60)
for res in data.get("results", []):
    cols = res["columns"]
    print(f"kpdate = {cols.get('kpdate')!r}   |   {cols.get('docname','')[:40]}")