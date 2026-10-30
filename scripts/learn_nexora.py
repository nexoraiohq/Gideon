"""One-time Phase 2 demo: ingest Nexora's own materials, show pending facts."""
from pathlib import Path

from gideon.knowledge import ingest, store

sources = {
    "nexora_home.txt": "https://nexoraio.vercel.app/",
    "nexora_services.txt": "https://nexoraio.vercel.app/services",
    "nexora_about.txt": "https://nexoraio.vercel.app/about",
}

total_added = 0
for fname, url in sources.items():
    text = (Path("data/corpus") / fname).read_text(encoding="utf-8")
    result = ingest.ingest_text(text, source=url)
    added = len(result["added"])
    total_added += added
    print(f"{fname}: {added} new facts, {result['skipped']} duplicates skipped")

print(f"TOTAL: {total_added} facts learned (all unapproved - awaiting owner)")
print(f"pending: {store.count_facts(approved=False)} | approved: {store.count_facts(approved=True)}")
