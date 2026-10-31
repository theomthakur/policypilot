from app.agent import prompts


def test_system_prompt_preserves_named_context_evidence_rule() -> None:
    prompt = prompts.load("system")

    assert "named environment, system, role, or service" in prompt
    assert "prefer the passage that actually applies" in prompt
