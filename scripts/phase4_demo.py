"""Phase 4 acceptance demo: resume target, real sweep, real briefing."""
from gideon.knowledge import targets
from gideon.research import briefing, sweep

# the paused target comes back
targets.resume_target(1)
print("resumed:", [t["name"] for t in targets.list_targets(active_only=True)])

# real sweep — studies nexoraio.vercel.app live
report = sweep.sweep()
studied = len(report["studied"])
total = report["targets_total"]
print(f"sweep: studied {studied}/{total} | new facts: {report['facts_learned']} "
      f"| pending: {report['facts_pending']}")
for f in report["failed"]:
    print("  FAILED:", f["name"], f["error"])

# the briefing the owner wakes up to
b = briefing.build_briefing()
print()
print(b["text"][:700])
