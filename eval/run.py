#!/usr/bin/env python3
"""Run PolicyPilot's API-level agent and baseline evaluation."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "eval" / "cases.yaml"
DEFAULT_SCHEMA = ROOT / "contracts" / "eval-case.schema.json"
DEFAULT_MANIFEST = ROOT / "corpus" / "manifest.json"
DEFAULT_PRICING = ROOT / "eval" / "pricing.yaml"
TRACE_CASES = {"CASE-2", "CASE-4", "CASE-6", "CASE-7", "CASE-8", "CASE-9"}
SECRET_FRAGMENTS = ("api_key", "passcode", "authorization", "secret", "password", "token")


@dataclass(frozen=True)
class Config:
    base_url: str
    passcode: str | None
    timeout_seconds: float
    poll_interval_seconds: float


class EvaluationError(RuntimeError):
    """Raised when the API cannot complete a reproducible evaluation action."""


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise EvaluationError(f"Expected a mapping in {path}")
    return value


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise EvaluationError(f"Expected an object in {path}")
    return value


def validate_dataset(cases_path: Path, schema_path: Path, manifest_path: Path) -> list[dict[str, Any]]:
    dataset = load_yaml(cases_path)
    schema = load_json(schema_path)
    manifest = load_json(manifest_path)
    cases = dataset.get("cases")
    if not isinstance(cases, list):
        raise EvaluationError("eval/cases.yaml must contain a cases list")

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors: list[str] = []
    ids: set[str] = set()
    documents = {item["filename"]: item for item in manifest.get("documents", [])}

    for index, case in enumerate(cases):
        case_id = case.get("id", f"index {index}") if isinstance(case, dict) else f"index {index}"
        for error in validator.iter_errors(case):
            location = ".".join(str(part) for part in error.absolute_path)
            errors.append(f"{case_id}{'.' + location if location else ''}: {error.message}")
        if not isinstance(case, dict):
            continue
        if case_id in ids:
            errors.append(f"Duplicate case ID: {case_id}")
        ids.add(case_id)
        if not case.get("applies_to_baseline") and not case.get("baseline_exclusion_reason"):
            errors.append(f"{case_id}: a baseline exclusion needs a reason")
        for source in case.get("expected_sources", []):
            filename = source.get("document_file")
            page = source.get("page")
            document = documents.get(filename)
            if document is None:
                errors.append(f"{case_id}: unknown expected source {filename}")
            elif not isinstance(page, int) or page < 1 or page > int(document["pages"]):
                errors.append(f"{case_id}: page {page} is outside {filename} (1-{document['pages']})")

    held_out = bool(ids) and all(case_id.startswith("HELD-") for case_id in ids)
    if not held_out:  # the held-out file is a separate set: it has no mandatory-case requirement
        required_ids = {f"CASE-{number}" for number in range(1, 9)}
        if missing := sorted(required_ids - ids):
            errors.append(f"Missing required cases: {', '.join(missing)}")
        if len(cases) < 8:
            errors.append("At least eight evaluation cases are required")
    if dataset.get("corpus_id") != manifest.get("corpus_id"):
        errors.append("Dataset corpus_id does not match corpus/manifest.json")

    if errors:
        raise EvaluationError("Dataset validation failed:\n- " + "\n- ".join(errors))
    return cases


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def matches(text: str, expression: str) -> bool:
    try:
        return re.search(expression, text, flags=re.IGNORECASE) is not None
    except re.error:
        return normalized(expression) in normalized(text)


def redact(value: Any, key: str = "") -> Any:
    if any(fragment in key.casefold() for fragment in SECRET_FRAGMENTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {name: redact(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class ApiEvaluationClient:
    def __init__(self, config: Config) -> None:
        headers = {"Accept": "application/json"}
        if config.passcode:
            headers["X-Demo-Passcode"] = config.passcode
        self.config = config
        self.client = httpx.Client(base_url=config.base_url.rstrip("/"), headers=headers, timeout=30.0)

    def __enter__(self) -> "ApiEvaluationClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.client.close()

    def checked_json(self, response: httpx.Response, action: str) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            body = response.text[:500]
            raise EvaluationError(f"{action} failed with HTTP {response.status_code}: {body}") from error
        value = response.json()
        if not isinstance(value, dict):
            raise EvaluationError(f"{action} returned a non-object response")
        return value

    def create_session(self) -> str:
        payload = self.checked_json(self.client.post("/sessions"), "create session")
        session_id = payload.get("session_id")
        if not isinstance(session_id, str):
            raise EvaluationError("create session response has no session_id")
        return session_id

    def documents(self) -> dict[str, dict[str, Any]]:
        payload = self.checked_json(self.client.get("/documents"), "list documents")
        return {item["id"]: item for item in payload.get("items", []) if isinstance(item, dict) and "id" in item}

    def run_turn(
        self,
        session_id: str,
        content: str,
        mode: str,
        *,
        reply_to_clarification: str | None,
        fault_inject: str | None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {"content": content, "mode": mode}
        if reply_to_clarification:
            request["reply_to_clarification"] = reply_to_clarification
        if fault_inject:
            request["fault_inject"] = fault_inject
        started = self.checked_json(
            self.client.post(f"/sessions/{session_id}/messages", json=request),
            f"start {mode} turn",
        )
        turn_id = started.get("turn_id")
        if not isinstance(turn_id, str):
            raise EvaluationError("message response has no turn_id")

        deadline = time.monotonic() + self.config.timeout_seconds
        while time.monotonic() < deadline:
            turn = self.checked_json(self.client.get(f"/turns/{turn_id}"), f"poll turn {turn_id}")
            if turn.get("status") in {"completed", "failed"}:
                return turn
            time.sleep(self.config.poll_interval_seconds)
        raise EvaluationError(f"Turn {turn_id} did not finish in {self.config.timeout_seconds:.0f}s")

    def citation_supported(self, citation: dict[str, Any]) -> bool:
        document_id = citation.get("document_id")
        page = citation.get("page")
        quote = citation.get("quote")
        if not isinstance(document_id, str) or not isinstance(page, int) or not isinstance(quote, str) or not quote.strip():
            return False
        payload = self.checked_json(
            self.client.get(f"/documents/{document_id}/pages/{page}"),
            f"read cited page {document_id}/{page}",
        )
        page_text = payload.get("text")
        return isinstance(page_text, str) and normalized(quote) in normalized(page_text)


def answer_text(turn: dict[str, Any]) -> str:
    answer = turn.get("answer") or {}
    parts = [answer.get("summary", "")]
    parts.extend(claim.get("text", "") for claim in answer.get("claims", []) if isinstance(claim, dict))
    parts.extend(notice.get("text", "") for notice in answer.get("notices", []) if isinstance(notice, dict))
    clarification = turn.get("clarification") or {}
    parts.append(clarification.get("question", ""))
    return "\n".join(part for part in parts if isinstance(part, str))


def estimate_cost(turn: dict[str, Any], pricing: dict[str, Any]) -> float:
    totals = turn.get("totals") or {}
    reported = totals.get("estimated_cost_usd")
    if isinstance(reported, (int, float)):
        return float(reported)
    model = str(totals.get("model", "fake"))
    rates = pricing.get("models", {}).get(model, {})
    prompt = float(totals.get("prompt_tokens", 0))
    completion = float(totals.get("completion_tokens", 0))
    return round(
        prompt * float(rates.get("input_per_million_tokens", 0)) / 1_000_000
        + completion * float(rates.get("output_per_million_tokens", 0)) / 1_000_000,
        8,
    )


def evaluate_result(
    api: ApiEvaluationClient,
    case: dict[str, Any],
    turns: list[dict[str, Any]],
    documents: dict[str, dict[str, Any]],
    pricing: dict[str, Any],
) -> dict[str, Any]:
    final_turn = turns[-1]
    text = answer_text(final_turn)
    answer = final_turn.get("answer") or {}
    citations = answer.get("citations", []) if isinstance(answer, dict) else []
    events = [event for turn in turns for event in turn.get("events", []) if isinstance(event, dict)]
    totals = final_turn.get("totals") or {}
    checks = case.get("checks", {})
    check_results: dict[str, bool] = {}

    for expression in checks.get("required_facts", []):
        check_results[f"required_fact:{expression}"] = matches(text, expression)
    # Wording of an explicit abstention: broad on purpose (any clear statement that the documents lack it).
    if expression := checks.get("abstention_wording"):
        check_results["abstention_wording"] = matches(text, expression)
    # Older, stricter wording checks stay visible but no longer decide pass/fail (see docs/evaluation.md).
    legacy_checks = {
        f"legacy_required_fact:{expression}": matches(text, expression)
        for expression in checks.get("legacy_required_facts", [])
    }
    for expression in checks.get("forbidden_text", []):
        check_results[f"forbidden_text:{expression}"] = not matches(text, expression)

    final_stop = final_turn.get("stop_reason") or answer.get("stop_reason")
    if expected := checks.get("expect_stop_reason"):
        check_results["stop_reason"] = final_stop == expected

    if checks.get("expect_clarification") is not None:
        saw_clarification = any(
            turn.get("stop_reason") == "clarification_needed" or turn.get("clarification")
            for turn in turns
        )
        check_results["clarification"] = saw_clarification == bool(checks["expect_clarification"])

    cited_document_ids = {item.get("document_id") for item in citations if isinstance(item, dict)}
    if minimum := checks.get("min_distinct_documents_cited"):
        check_results["distinct_documents_cited"] = len(cited_document_ids - {None}) >= int(minimum)

    if expected_notice := checks.get("expect_notice_kind"):
        notice_kinds = {notice.get("kind") for notice in answer.get("notices", []) if isinstance(notice, dict)}
        check_results["notice_kind"] = expected_notice in notice_kinds

    if checks.get("expect_query_revision") is not None:
        revised = any(event.get("type") == "query_revised" for event in events)
        check_results["query_revision"] = revised == bool(checks["expect_query_revision"])

    if maximum := checks.get("max_tool_calls"):
        check_results["tool_call_limit"] = int(totals.get("tool_calls", 0)) <= int(maximum)

    if checks.get("expect_retry") is not None:
        retried = any(event.get("status") == "retried" or int(event.get("attempt", 1)) > 1 for event in events)
        check_results["retry"] = retried == bool(checks["expect_retry"])

    if checks.get("no_citations") is not None:
        check_results["no_citations"] = (len(citations) == 0) == bool(checks["no_citations"])

    citation_checks: list[dict[str, Any]] = []
    for citation in citations:
        supported = False
        error: str | None = None
        try:
            supported = api.citation_supported(citation)
        except (EvaluationError, httpx.HTTPError) as exception:
            error = str(exception)
        citation_checks.append(
            {
                "index": citation.get("index"),
                "document_id": citation.get("document_id"),
                "page": citation.get("page"),
                "quote_supported_on_page": supported,
                "reported_verified": citation.get("verified"),
                "error": error,
            }
        )

    if citations and not checks.get("no_citations"):
        check_results["citation_quotes_supported"] = all(item["quote_supported_on_page"] for item in citation_checks)

    cited_file_pages = {
        (documents.get(citation.get("document_id"), {}).get("filename"), citation.get("page"))
        for citation in citations
        if isinstance(citation, dict)
    }
    expected_file_pages = {
        (source["document_file"], source["page"]) for source in case.get("expected_sources", [])
    }
    if expected_file_pages:
        check_results["expected_sources"] = expected_file_pages.issubset(cited_file_pages)

    fact_keys = [key for key in check_results if key.startswith(("required_fact:", "forbidden_text:"))]
    correctness = sum(check_results[key] for key in fact_keys) / len(fact_keys) if fact_keys else 1.0
    citation_support = (
        sum(item["quote_supported_on_page"] for item in citation_checks) / len(citation_checks)
        if citation_checks
        else (1.0 if checks.get("no_citations") else 0.0)
    )
    task_completion = sum(check_results.values()) / len(check_results) if check_results else 0.0
    passed = bool(check_results) and all(check_results.values())
    failed_checks = [name for name, value in check_results.items() if not value]

    return {
        "status": "completed",
        "pass": passed,
        "expected_behavior": case["expected_behavior"],
        "legacy_checks": legacy_checks,
        "expected_sources": case.get("expected_sources", []),
        "actual_answer": answer,
        "checks": check_results,
        "citation_checks": citation_checks,
        "metrics": {
            "correctness": round(correctness, 3),
            "citation_support": round(citation_support, 3),
            "task_completion": round(task_completion, 3),
            "tool_calls": sum(int((turn.get("totals") or {}).get("tool_calls", 0)) for turn in turns),
            "query_revisions": sum(int((turn.get("totals") or {}).get("query_revisions", 0)) for turn in turns),
            "latency_ms": sum(int((turn.get("totals") or {}).get("latency_ms", 0)) for turn in turns),
            "prompt_tokens": sum(int((turn.get("totals") or {}).get("prompt_tokens", 0)) for turn in turns),
            "completion_tokens": sum(int((turn.get("totals") or {}).get("completion_tokens", 0)) for turn in turns),
            "estimated_cost_usd": round(sum(estimate_cost(turn, pricing) for turn in turns), 8),
            "stop_reason": final_stop,
        },
        "failure_note": "" if passed else f"Failed deterministic checks: {', '.join(failed_checks)}",
        "trace": redact(events),
    }


INFRASTRUCTURE_STOPS = {"error", "budget_exhausted"}
MAX_CONSECUTIVE_INVALID = 3


def run_case(
    api: ApiEvaluationClient,
    case: dict[str, Any],
    mode: str,
    documents: dict[str, dict[str, Any]],
    pricing: dict[str, Any],
) -> dict[str, Any]:
    if mode == "baseline" and not case["applies_to_baseline"]:
        return {
            "status": "excluded",
            "pass": None,
            "reason": case.get("baseline_exclusion_reason"),
            "expected_behavior": case["expected_behavior"],
        }

    session_id = api.create_session()
    turns: list[dict[str, Any]] = []
    clarification_turn_id: str | None = None
    try:
        for turn_spec in case["turns"]:
            turn = api.run_turn(
                session_id,
                turn_spec["content"],
                mode,
                reply_to_clarification=clarification_turn_id if turn_spec.get("is_clarification_reply") else None,
                fault_inject=turn_spec.get("fault_inject") if mode == "agent" else None,
            )
            turns.append(turn)
            if turn.get("stop_reason") in INFRASTRUCTURE_STOPS:
                # The model provider or the app's own spending cap stopped this turn. That says nothing about
                # the system under test, so it is never scored as a failure.
                return {
                    "status": "invalid",
                    "pass": None,
                    "expected_behavior": case["expected_behavior"],
                    "failure_note": f"invalid: the turn ended with {turn.get('stop_reason')} (provider error or budget cap)",
                }
            clarification_turn_id = turn.get("id") if turn.get("stop_reason") == "clarification_needed" else None
        return evaluate_result(api, case, turns, documents, pricing)
    except (EvaluationError, httpx.HTTPError) as error:
        return {
            "status": "error",
            "pass": False,
            "expected_behavior": case["expected_behavior"],
            "expected_sources": case.get("expected_sources", []),
            "actual_answer": turns[-1].get("answer") if turns else None,
            "checks": {},
            "citation_checks": [],
            "metrics": {},
            "failure_note": str(error),
            "trace": redact([event for turn in turns for event in turn.get("events", [])]),
        }


def markdown_report(run: dict[str, Any]) -> str:
    lines = [
        "# PolicyPilot evaluation report",
        "",
        f"- Run ID: `{run['run_id']}`",
        f"- Started: {run['started_at']}",
        f"- API: `{run['configuration']['base_url']}`",
        f"- Corpus: `{run['configuration']['corpus_id']}`",
        "",
        "## Comparison",
        "",
        "| Case | Category | Agent | Baseline | Agent tools | Baseline tools | Agent latency | Baseline latency |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in run["cases"]:
        agent = result["systems"]["agent"]
        baseline = result["systems"]["baseline"]
        def verdict(item: dict[str, Any]) -> str:
            if item["status"] == "excluded":
                return "n/a"
            if item["status"] == "invalid":
                return "invalid"
            return "pass" if item.get("pass") else "fail"
        def metric(item: dict[str, Any], name: str) -> str:
            value = item.get("metrics", {}).get(name)
            return "n/a" if value is None else str(value)
        lines.append(
            f"| {result['id']} | {result['category']} | {verdict(agent)} | {verdict(baseline)} | "
            f"{metric(agent, 'tool_calls')} | {metric(baseline, 'tool_calls')} | "
            f"{metric(agent, 'latency_ms')} ms | {metric(baseline, 'latency_ms')} ms |"
        )

    lines.extend(["", "## Case notes", ""])
    for result in run["cases"]:
        lines.append(f"### {result['id']}: {result['expected_behavior']}")
        lines.append("")
        for mode in ("agent", "baseline"):
            item = result["systems"][mode]
            if item["status"] == "excluded":
                lines.append(f"- **{mode}: n/a.** {item['reason']}")
            elif item["status"] == "invalid":
                lines.append(f"- **{mode}: invalid.** {item['failure_note']}")
            elif item.get("pass"):
                lines.append(f"- **{mode}: pass.** All deterministic checks passed; manual source review is still required.")
            else:
                lines.append(f"- **{mode}: fail.** {item.get('failure_note') or 'See raw results.'}")
        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "Deterministic checks measure required facts, prohibited text, citations, stop behavior, tool limits, and observable adaptive actions. They do not prove semantic entailment. Complete the manual page-check log before treating citation support as final.",
            "",
            "The agent should be judged on whether iteration improves completion or grounding for each case, while tool calls, latency, token use, and cost show its overhead. The report does not assume the agent wins every case.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("POLICYPILOT_BASE_URL", "http://localhost:8000/api/v1"))
    parser.add_argument("--passcode", default=os.getenv("POLICYPILOT_DEMO_PASSCODE"))
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--case", action="append", dest="case_ids", help="Run only this case ID; repeatable")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--timeout", type=float, default=90.0, help="Maximum seconds per turn")
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        cases = validate_dataset(args.cases, DEFAULT_SCHEMA, DEFAULT_MANIFEST)
    except EvaluationError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.case_ids:
        requested = set(args.case_ids)
        cases = [case for case in cases if case["id"] in requested]
        missing = requested - {case["id"] for case in cases}
        if missing:
            print(f"Unknown case IDs: {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
    print(f"Validated {len(cases)} evaluation cases against the contract and corpus manifest.")
    if args.validate_only:
        return 0

    pricing = load_yaml(DEFAULT_PRICING)
    manifest = load_json(DEFAULT_MANIFEST)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or ROOT / "eval" / "results" / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    config = Config(args.base_url, args.passcode, args.timeout, args.poll_interval)
    run: dict[str, Any] = {
        "schema_version": 1,
        "run_id": timestamp,
        "started_at": datetime.now(UTC).isoformat(),
        "configuration": {
            "base_url": args.base_url,
            "corpus_id": manifest["corpus_id"],
            "corpus_manifest_sha256": __import__("hashlib").sha256(DEFAULT_MANIFEST.read_bytes()).hexdigest(),
            "passcode_configured": bool(args.passcode),
        },
        "cases": [],
    }

    try:
        with ApiEvaluationClient(config) as api:
            documents = api.documents()
            invalid_in_a_row = 0
            for case in cases:
                print(f"Running {case['id']}...", flush=True)
                systems = {
                    mode: run_case(api, case, mode, documents, pricing)
                    for mode in ("agent", "baseline")
                }
                result = {
                    "id": case["id"],
                    "category": case["category"],
                    "expected_behavior": case["expected_behavior"],
                    "systems": systems,
                }
                run["cases"].append(result)
                invalid_in_a_row = (
                    invalid_in_a_row + 1 if any(r["status"] == "invalid" for r in systems.values()) else 0
                )
                if invalid_in_a_row >= MAX_CONSECUTIVE_INVALID:
                    raise EvaluationError(
                        f"{invalid_in_a_row} cases in a row ended with a provider error or budget stop: "
                        "this run is invalid (check the model key's limit and DAILY_BUDGET_USD). Aborting."
                    )
                if case["id"] in TRACE_CASES:
                    for mode, system_result in systems.items():
                        if system_result.get("trace"):
                            trace_path = output_dir / f"{case['id'].lower()}-{mode}-trace.json"
                            trace_path.write_text(json.dumps(system_result["trace"], indent=2) + "\n", encoding="utf-8")
    except (EvaluationError, httpx.HTTPError) as error:
        run["fatal_error"] = str(error)
        run["finished_at"] = datetime.now(UTC).isoformat()
        (output_dir / "results.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
        print(f"Evaluation stopped: {error}", file=sys.stderr)
        return 1

    run["finished_at"] = datetime.now(UTC).isoformat()
    (output_dir / "results.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    (output_dir / "report.md").write_text(markdown_report(run), encoding="utf-8")
    failures = sum(
        system.get("pass") is False
        for case in run["cases"]
        for system in case["systems"].values()
        if system.get("status") != "excluded"
    )
    print(f"Wrote results to {output_dir}; {failures} evaluated system-case result(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
