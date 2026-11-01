"""Phase 2 acceptance demo: ask, approve, ask again — with citations + guardrail."""
import json

from gideon.core import guardrail
from gideon.knowledge import answer, store

print("=== 1) ASK BEFORE APPROVAL (gate must hold) ===")
r = answer.answer("what websites does nexora build for salons?")
print("answer:", r["answer"][:100])
print("needs_research:", r["needs_research"], "| citations:", len(r["citations"]))

# Simulate the owner approving every pending fact (in real use: one by one in the UI)
pending = store.list_facts(approved=False)
for f in pending:
    store.approve_fact(f["id"])
print(f"\n(owner approved {len(pending)} facts)")

print("\n=== 2) ASK AFTER APPROVAL ===")
for q in (
    "what websites does nexora build for salons?",
    "does nexora build payment systems?",
    "where is nexora based?",
):
    r = answer.answer(q)
    print(f"\nQ: {q}")
    print("A:", r["answer"][:160])
    print("confidence:", r["confidence"], "| citations:", len(r["citations"]))
    if r["citations"]:
        print("  source:", r["citations"][0]["source_url"])

print("\n=== 3) PROMISE GUARDRAIL ON OUTBOUND DRAFTS ===")
drafts = {
    "clean": "Hi Sarah, Nexora builds fast, mobile-first websites for salons in Kisii, "
            "including booking flows and WhatsApp enquiries.",
    "unbacked": "Our websites will double your bookings in 30 days.",
    "red_line": "We guarantee first page rankings on Google, money back if not.",
}
for name, text in drafts.items():
    check = guardrail.check_draft(text)
    print(f"\n[{name}] verdict: {check.verdict}")
    print(" ", check.to_dict()["message"])
