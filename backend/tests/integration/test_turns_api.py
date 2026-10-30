"""Turn endpoints end to end: real Postgres and Redis, scripted model, no network."""

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agent.prompts import PROMPT_VERSION
from tests.integration.conftest import clear_caches, new_session
from tests.integration.test_agent import QUOTE_MBPS, _answer_step, _load


def _boot(
    monkeypatch: pytest.MonkeyPatch, model: Any, make_pdf: Callable[..., Path], tmp_path: Path, **env: str
) -> TestClient:
    from app.main import create_app

    _load(make_pdf, tmp_path)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    clear_caches()
    monkeypatch.setattr("app.turns.service.get_model", lambda: model)
    client = TestClient(create_app())
    client.__enter__()
    passcode = env.get("DEMO_PASSCODE")
    if passcode:
        assert client.post("/api/v1/sessions", headers={"X-Demo-Passcode": passcode}).status_code == 201
        return client
    return new_session(client)


def _session_id(client: TestClient) -> str:
    return client.cookies["pp_session"]


def _send(client: TestClient, content: str, **extra: Any) -> Any:
    return client.post(f"/api/v1/sessions/{_session_id(client)}/messages", json={"content": content, **extra})


def _wait(client: TestClient, turn_id: str, timeout: float = 15) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        turn = client.get(f"/api/v1/turns/{turn_id}").json()
        if turn["status"] != "running":
            return turn  # type: ignore[no-any-return]
        time.sleep(0.1)
    raise AssertionError("turn did not finish")


def _lookup_model() -> Any:
    from app.llm.client import ScriptedModel, respond

    return ScriptedModel(
        [
            respond(("plan", {"sub_questions": ["Guest bandwidth"]})),
            respond(("search_documents", {"query": "guest network bandwidth limit mbps"})),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )


def test_turn_runs_in_the_background_and_persists_everything(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    with _boot(monkeypatch, _lookup_model(), make_pdf, tmp_path) as client:
        started = _send(client, "What is the guest bandwidth limit?")
        assert started.status_code == 202
        turn = _wait(client, started.json()["turn_id"])
        assert turn["status"] == "completed" and turn["stop_reason"] == "answered"
        assert turn["answer"]["citations"][0]["verified"] is True
        seqs = [e["seq"] for e in turn["events"]]
        assert seqs == list(range(len(seqs)))
        assert turn["events"][0]["type"] == "turn_started" and turn["events"][-1]["type"] == "turn_completed"
        totals = turn["totals"]
        assert totals["tool_calls"] == 1 and totals["latency_ms"] >= 0
        assert totals["prompt_version"] == PROMPT_VERSION and totals["model"] == "scripted"
        assert totals["estimated_cost_usd"] > 0
        listed = client.get(f"/api/v1/sessions/{_session_id(client)}").json()["turns"]
        assert [t["id"] for t in listed] == [turn["id"]]


def test_events_stream_over_sse_and_end_at_turn_completed(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    with _boot(monkeypatch, _lookup_model(), make_pdf, tmp_path) as client:
        turn_id = _send(client, "What is the guest bandwidth limit?").json()["turn_id"]
        with client.stream("GET", f"/api/v1/turns/{turn_id}/events") as response:
            assert response.headers["content-type"].startswith("text/event-stream")
            body = "".join(response.iter_text())
        events = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
        assert [e["seq"] for e in events] == list(range(len(events)))
        assert events[-1]["type"] == "turn_completed" and "tool_call" in {e["type"] for e in events}
        assert all(e["turn_id"] == turn_id and "ts" in e for e in events)


def test_clarification_reply_continues_the_same_question(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "network bandwidth"})),
            respond(("ask_clarification", {"question": "Which network?", "options": ["Guest", "Staff"]})),
            respond(("search_documents", {"query": "guest network bandwidth limit mbps"})),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    with _boot(monkeypatch, model, make_pdf, tmp_path) as client:
        first = _wait(client, _send(client, "How fast is it?").json()["turn_id"])
        assert first["stop_reason"] == "clarification_needed"
        assert first["clarification"]["options"] == ["Guest", "Staff"]
        bad = _send(client, "Guest", reply_to_clarification="00000000-0000-0000-0000-000000000000")
        assert bad.status_code == 400
        second = _wait(client, _send(client, "Guest", reply_to_clarification=first["id"]).json()["turn_id"])
        assert second["stop_reason"] == "answered"
        opening = next(m["content"] for m in model.calls[2] if m["role"] == "user")
        assert "How fast is it?" in opening and "Which network?" in opening and "Guest" in opening
        again = _send(client, "Guest", reply_to_clarification=first["id"])
        assert again.status_code == 400  # a clarification can be answered only once


def test_baseline_mode_is_single_pass(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    def answer(messages: list[dict[str, Any]]) -> Any:
        shown = json.loads(messages[-1]["content"].rsplit("\n", 1)[-1])
        key = next(i["evidence_id"] for i in shown if i["page"] == 1 and "Guest" in i["title"])
        return respond(
            (
                "final_answer",
                {
                    "summary": "10 Mbps",
                    "claims": [{"text": "10 Mbps.", "evidence_ids": [key], "quote": QUOTE_MBPS}],
                },
            )
        )

    with _boot(monkeypatch, ScriptedModel([answer]), make_pdf, tmp_path) as client:
        turn = _wait(client, _send(client, "Guest bandwidth limit?", mode="baseline").json()["turn_id"])
        assert turn["mode"] == "baseline" and turn["stop_reason"] == "answered"
        assert turn["totals"]["steps"] == 1 and "plan" not in {e["type"] for e in turn["events"]}


def test_passcode_is_enforced_when_configured(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    with _boot(monkeypatch, _lookup_model(), make_pdf, tmp_path, DEMO_PASSCODE="letmein") as client:
        assert client.post("/api/v1/sessions").status_code == 401  # no session without the passcode
        assert client.post("/api/v1/documents", files={"file": ("a.pdf", b"%PDF-")}).status_code == 401
        assert _send(client, "q").status_code == 401
        sid = _session_id(client)
        ok = client.post(
            f"/api/v1/sessions/{sid}/messages", json={"content": "q"}, headers={"X-Demo-Passcode": "letmein"}
        )
        assert ok.status_code == 202
        _wait(client, ok.json()["turn_id"])


def test_rate_limit_returns_429(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel

    with _boot(monkeypatch, ScriptedModel([]), make_pdf, tmp_path, RATE_LIMIT_PER_MINUTE="2") as client:
        codes = [_send(client, f"q{i}").status_code for i in range(3)]
        assert codes == [202, 202, 429]
        assert client.post("/api/v1/sessions").status_code == 201  # only messages are limited


def test_daily_budget_cap_stops_new_turns_without_calling_the_model(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    model = _lookup_model()
    with _boot(monkeypatch, model, make_pdf, tmp_path, DAILY_BUDGET_USD="0") as client:
        turn = _wait(client, _send(client, "What is the guest bandwidth limit?").json()["turn_id"])
        assert turn["stop_reason"] == "budget_exhausted" and turn["answer"]["partial"] is True
        assert model.calls == []


def test_unknown_session_and_turn_are_404(
    monkeypatch: pytest.MonkeyPatch, make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel

    with _boot(monkeypatch, ScriptedModel([]), make_pdf, tmp_path) as client:
        nil = "00000000-0000-0000-0000-000000000000"
        assert client.post(f"/api/v1/sessions/{nil}/messages", json={"content": "q"}).status_code == 404
        assert client.get(f"/api/v1/turns/{nil}").status_code == 404
        assert client.get(f"/api/v1/turns/{nil}/events").status_code == 404
        assert _send(client, "").status_code == 400
