#!/usr/bin/env python3
"""Build a manual citation spot-check sheet: N random verified citations from evaluation results, each with
the claim, the quote, and the real text of the cited page read from the running database.

Usage: /tmp/evalvenv/bin/python scripts/make_citation_sheet.py OUTPUT.md eval/results/<run> [more runs ...] [--n 20]

The reviewer ticks two things per item: the quote really is on that page, and the claim follows from it.
"""

import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def questions() -> dict[str, str]:
    """case id -> the first question, from the case files (needs PyYAML: use the evaluation environment)."""
    import yaml

    found: dict[str, str] = {}
    for name in ("cases.yaml", "heldout.yaml", "heldout2.yaml"):
        for case in yaml.safe_load((ROOT / "eval" / name).read_text())["cases"]:
            found[case["id"]] = case["turns"][0]["content"]
    return found


def page_text(document_id: str, page: int) -> str:
    sql = f"SELECT text FROM document_pages WHERE document_id = '{document_id}' AND page_number = {int(page)}"
    cmd = ["docker", "compose", "exec", "-T", "postgres", "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "{sql}"']
    done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    return done.stdout.strip()


def collect(runs: list[Path]) -> list[dict]:
    by_case = questions()
    items: dict[tuple[str, int, str], dict] = {}
    for run in runs:
        data = json.loads((run / "results.json").read_text())
        for case in data["cases"]:
            result = case["systems"].get("agent")
            answer = (result or {}).get("actual_answer") or {}
            citations = {c["index"]: c for c in answer.get("citations", [])}
            question = by_case.get(case["id"], "")
            for claim in answer.get("claims", []):
                for index in claim.get("citation_indexes", []):
                    c = citations.get(index)
                    if not c or not c.get("verified"):
                        continue
                    key = (c["document_id"], c["page"], claim["text"][:60])
                    items.setdefault(
                        key,
                        {
                            "case": case["id"],
                            "question": question,
                            "claim": claim["text"],
                            "title": c["title"],
                            "page": c["page"],
                            "document_id": c["document_id"],
                            "quote": " ".join(str(c.get("quote", "")).split()),
                        },
                    )
    return list(items.values())


def main() -> None:
    args = sys.argv[1:]
    n = 20
    if "--n" in args:
        i = args.index("--n")
        n = int(args[i + 1])
        del args[i : i + 2]
    if len(args) < 2:
        raise SystemExit(__doc__)
    out, runs = Path(args[0]), [Path(a) for a in args[1:]]
    pool = collect(runs)
    random.Random(31).shuffle(pool)
    picked: list[dict] = []
    seen_cases: dict[str, int] = {}
    for item in sorted(pool, key=lambda x: seen_cases.setdefault(x["case"], 0)):  # stable: spreads across cases
        if len(picked) >= n:
            break
        if sum(1 for p in picked if p["case"] == item["case"]) >= 3:
            continue
        picked.append(item)
    lines = [
        "# Citation spot-check",
        "",
        f"{len(picked)} citations picked at random from the final evaluation runs, spread across different questions. "
        "For each one, open the page in the app (Knowledge base, View, go to the page) or read the page text below, then tick:",
        "",
        "- **A:** the quote really is on that page.",
        "- **B:** the claim follows from the quote (nothing added, no number changed).",
        "",
        "Note anything wrong at the bottom of the item. A single failure is worth writing into `docs/evaluation.md`.",
        "",
    ]
    for number, item in enumerate(picked, start=1):
        text = page_text(item["document_id"], item["page"])
        lines += [
            f"## {number}. {item['case']}: {item['title']}, page {item['page']}",
            "",
            f"**Question:** {item['question']}",
            "",
            f"**Claim shown to the user:** {item['claim']}",
            "",
            f"**Quote the system cited:** \"{item['quote']}\"",
            "",
            "- [ ] A: the quote is on this page",
            "- [ ] B: the claim follows from the quote",
            "",
            "<details><summary>Page text</summary>",
            "",
            "```",
            text[:2500] + ("\n[page continues]" if len(text) > 2500 else ""),
            "```",
            "",
            "</details>",
            "",
            "Notes:",
            "",
        ]
    out.write_text("\n".join(lines))
    print(f"wrote {out} with {len(picked)} citations from {len(pool)} available")


if __name__ == "__main__":
    main()
