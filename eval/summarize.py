"""Summarize several evaluation runs into the tables used by docs/evaluation.md.

    python eval/summarize.py eval/results/run-A eval/results/run-B ...

Prints, per case, how often each system passed across the runs, plus totals, median latency and token use.
Only reports; it never changes a result.
"""

import json
import statistics
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads((Path(path) / "results.json").read_text())


def main(paths: list[str]) -> None:
    runs = [load(p) for p in paths]
    ids = [c["id"] for c in runs[0]["cases"]]
    print(f"{len(runs)} run(s): " + ", ".join(Path(p).name for p in paths) + "\n")
    print("| Case | Category | Agent passes | Baseline passes | Agent failures (checks) |")
    print("|---|---|---:|---:|---|")
    totals = {"agent": [0, 0], "baseline": [0, 0]}
    metrics: dict[str, dict[str, list[float]]] = {s: {"latency_ms": [], "tokens": [], "cost": [], "calls": []} for s in totals}
    for case_id in ids:
        cells, fails = {}, set()
        category = ""
        for system in totals:
            ok = n = 0
            for run in runs:
                case = next(c for c in run["cases"] if c["id"] == case_id)
                category = case["category"]
                result = case["systems"].get(system)
                if not result or result.get("status") != "completed":
                    continue
                n += 1
                ok += bool(result["pass"])
                m = result["metrics"]
                metrics[system]["latency_ms"].append(m["latency_ms"])
                metrics[system]["tokens"].append(m["prompt_tokens"] + m["completion_tokens"])
                metrics[system]["cost"].append(m["estimated_cost_usd"])
                metrics[system]["calls"].append(m["tool_calls"])
                if system == "agent" and not result["pass"]:
                    fails |= {k.split(":")[0] for k in result["failure_note"].replace("Failed deterministic checks: ", "").split(", ")}
            totals[system][0] += ok
            totals[system][1] += n
            cells[system] = f"{ok}/{n}" if n else "n/a"
        print(f"| {case_id} | {category} | {cells['agent']} | {cells['baseline']} | {', '.join(sorted(fails)) or '-'} |")
    print()
    for system, (ok, n) in totals.items():
        m = metrics[system]
        if not n:
            continue
        print(
            f"- **{system}**: {ok}/{n} case-runs passed; median latency {statistics.median(m['latency_ms'])/1000:.1f} s, "
            f"median tokens {statistics.median(m['tokens']):.0f}, mean cost ${statistics.mean(m['cost']):.4f}, "
            f"median tool calls {statistics.median(m['calls']):.0f}"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
