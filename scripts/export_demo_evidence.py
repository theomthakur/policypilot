#!/usr/bin/env python3
"""Write the saved trace and answer of the four demo moments from evaluation results into docs/demo-evidence/.

Usage: scripts/export_demo_evidence.py eval/results/<run> [eval/results/<run> ...]

The first run in which a case passed is used for each moment, so the evidence shows a real, passing result.
"""

import json
import sys
from pathlib import Path

MOMENTS = [
    ("01-multi-document", "CASE-2", "Multi-document grounded answer"),
    ("02-re-retrieval", "CASE-3", "Evidence-driven re-retrieval"),
    ("03-clarification", "CASE-4", "Clarification with retained context"),
    ("04-tool-failure", "CASE-8", "Failed tool call, handled within limits"),
]
OUT = Path(__file__).resolve().parent.parent / "docs" / "demo-evidence"


def find(runs: list[Path], case_id: str) -> tuple[Path, dict] | None:
    fallback = None
    for run in runs:
        data = json.loads((run / "results.json").read_text())
        for case in data["cases"]:
            if case["id"] != case_id or "agent" not in case["systems"]:
                continue
            result = case["systems"]["agent"]
            if result.get("pass"):
                return run, case
            fallback = fallback or (run, case)
    return fallback


def steps(trace: list[dict]) -> list[str]:
    lines: list[str] = []
    turn = 0
    for e in trace:
        kind = e.get("type")
        if kind == "turn_started":
            turn += 1
            lines.append(f"**Turn {turn}**")
        elif kind == "plan":
            lines.append(f"- Plan: {e.get('summary', '')[:200]}")
        elif kind == "tool_call":
            note = f" ({e['scope'].replace('_', ' ')})" if e.get("scope") else ""
            args = json.dumps(e.get("input", {}), ensure_ascii=False)[:140]
            retry = f", attempt {e['attempt']}" if e.get("attempt", 1) > 1 else ""
            lines.append(f"- Tool call `{e.get('tool')}`{note}{retry}: `{args}`")
        elif kind == "tool_result":
            pages = ", ".join(
                f"{p['title'][:34]} p.{p['page']}" for p in (e.get("result") or {}).get("pages", [])[:4]
            )
            lines.append(f"  - Result [{e.get('status')}]: {e.get('summary', '')[:90]}" + (f" ({pages})" if pages else ""))
        elif kind == "query_revised":
            r = e.get("revision", {})
            lines.append(f"- **Search revised** ({r.get('reason')}): `{r.get('previous_query')}` -> `{r.get('new_query')}`")
        elif kind == "assessment":
            a = e.get("assessment", {})
            lines.append(f"- Ambiguity check: {a.get('supported', 0)} verified readings, asks: {not a.get('answerable', True)}")
        elif kind == "clarification_requested":
            lines.append(f"- **Clarifying question:** {e.get('clarification', {}).get('question', e.get('summary', ''))}")
        elif kind == "verify":
            lines.append(f"- Citation check: {e.get('summary')}")
        elif kind == "turn_completed":
            lines.append(f"- Finished: `{e.get('stop_reason')}`")
    return lines


def render(case: dict, run: Path, title: str) -> str:
    result = case["systems"]["agent"]
    answer = result.get("actual_answer") or {}
    metrics = result.get("metrics", {})
    questions = [t["content"] for t in case.get("turns", []) if isinstance(t, dict) and t.get("content")]
    out = [f"# {title}", "", f"Case {case['id']}, from `{run.relative_to(run.parent.parent.parent)}`. Result: {'pass' if result.get('pass') else 'did not pass in this run'}.", ""]
    for q in questions:
        out += [f"> {q}", ""]
    out += ["## What the agent did", "", *steps(result.get("trace", [])), ""]
    out += ["## The answer", "", answer.get("summary", "(no answer: it asked a question or stopped)"), ""]
    if answer.get("citations"):
        out += ["## Citations (each quote verified against its page)", ""]
        for c in answer["citations"]:
            quote = " ".join(str(c.get("quote", "")).split())[:240]
            out.append(f"{c['index']}. {c['title']}, page {c['page']}: \"{quote}\"")
        out.append("")
    out += [
        "## Run totals",
        "",
        f"Tool calls {metrics.get('tool_calls')}, tokens "
        f"{(metrics.get('prompt_tokens') or 0) + (metrics.get('completion_tokens') or 0)}, "
        f"latency {round((metrics.get('latency_ms') or 0) / 1000, 1)} s, estimated cost ${metrics.get('estimated_cost_usd')}.",
        "",
    ]
    return "\n".join(out)


def main() -> None:
    runs = [Path(a) for a in sys.argv[1:]]
    if not runs:
        raise SystemExit(__doc__)
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, case_id, title in MOMENTS:
        found = find(runs, case_id)
        if not found:
            print(f"{case_id}: not found")
            continue
        run, case = found
        (OUT / f"{slug}.md").write_text(render(case, run, title))
        print(f"{case_id}: wrote {slug}.md from {run.name} ({'pass' if case['systems']['agent'].get('pass') else 'NOT PASSING'})")


if __name__ == "__main__":
    main()
