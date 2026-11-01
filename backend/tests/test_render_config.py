"""The Render deployment follows model choices made in the application configuration."""

from pathlib import Path

import pytest
import yaml

from app.auth.service import validate_settings
from app.config import Settings


def test_render_preserves_application_model_and_pricing_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("LLM_MODEL", "LLM_PRICE_INPUT_PER_MILLION", "LLM_PRICE_OUTPUT_PER_MILLION"):
        monkeypatch.delenv(key, raising=False)
    defaults = Settings(_env_file=None)
    blueprint = yaml.safe_load((Path(__file__).parents[2] / "render.yaml").read_text())
    web = next(service for service in blueprint["services"] if service["type"] == "web")
    for variable in web["envVars"]:
        if "value" in variable:
            monkeypatch.setenv(variable["key"], str(variable["value"]))
    monkeypatch.setenv("DEMO_PASSCODE", "render-configuration-test")
    monkeypatch.setenv("LLM_API_KEY", "configuration-test-only")

    configured = Settings(_env_file=None)
    validate_settings(configured)
    assert configured.llm_model == defaults.llm_model
    assert configured.llm_price_input_per_million == defaults.llm_price_input_per_million
    assert configured.llm_price_output_per_million == defaults.llm_price_output_per_million
