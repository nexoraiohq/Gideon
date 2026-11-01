"""Phase 5 acceptance (real data): ingest the Kisii salon research corpus,
then mine it with the lead finder. 10 real qualified prospects expected."""
from pathlib import Path

from gideon.knowledge import store
from gideon.memory import db
from gideon.sales import leads, pipeline

db.init_db()

corpus = Path("data/corpus/kisii_salon_watch.txt").read_text(encoding="utf-8")

added = 0
for line in corpus.splitlines():
    line = line.strip()
    if not line or line.startswith(("Source:", "Fetched:", "Topic:")):
        continue
    source = None
    text = line
    if "Source: " in line:
        text, source = line.rsplit("Source: ", 1)
        text = text.rstrip(". ").strip() + "."
        source = source.strip()
    store.add_fact(text, category="market", source_url=source)
    added += 1

print(f"ingested {added} researched facts (pending owner approval)\n")

report = leads.find_leads(min_score=30)
print(f"finder: {report['candidates']} candidates, {len(report['added'])} new leads, "
      f"{report['below_threshold']} below threshold\n")

items = leads.list_leads(min_score=30)
print(f"{len(items)} QUALIFIED PROSPECTS (score >= 30):")
for i, lead in enumerate(items[:12], 1):
    loc = f" — {lead['location']}" if lead["location"] else ""
    print(f"{i:2}. {lead['name']}{loc}  [{lead['grade']}] score {lead['score']}  ({lead['stage']})")
    for reason in lead["reasons"]:
        print(f"      {reason}")
print()
print("PIPELINE:", pipeline.pipeline_report()["counts"])
