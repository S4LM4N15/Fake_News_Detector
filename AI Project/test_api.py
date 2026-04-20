"""Quick smoke test for the /api/check endpoint."""
import requests
import json

def test(query):
    print(f"\n{'='*55}")
    print(f"QUERY: {query}")
    print('='*55)
    r = requests.post(
        "http://127.0.0.1:5000/api/check",
        json={"query": query},
        timeout=30,
    )
    d = r.json()
    print(f"Score  : {d['score']}/100")
    print(f"Verdict: {d.get('verdict_label')} {d.get('verdict_emoji')}")
    print(f"Search : {d.get('search_time_seconds')}s  |  {d.get('total_results_found')} results")
    print("\nSignals:")
    for k, v in d.get("breakdown", {}).items():
        icon = "PASS" if v["passed"] else "FAIL"
        print(f"  [{icon}] {v['label']}: {v['points']}/{v['max']} — {v['detail']}")
    print("\nTop sources:")
    for s in d.get("matched_sources", [])[:4]:
        trust = "TRUSTED" if s.get("is_trusted") else "      "
        print(f"  [{trust}] {s.get('domain','?')} — {s.get('title','')[:60]}")

if __name__ == "__main__":
    test("Scientists discover dragons in Antarctica")
    test("Ukraine war latest 2025")
    test("Bangladesh election 2024 results")
