"""Chat model abstraction. `OpenAICompatibleModel` talks to OpenRouter or OpenAI; `ScriptedModel` replays
scripted responses so agent behavior is tested deterministically and CI needs no API key."""

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from app.config import Settings, get_settings


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelResponse:
    content: str | None
    tool_calls: list[ToolCall]
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def as_message(self) -> dict[str, Any]:
        message: dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                }
                for c in self.tool_calls
            ]
        return message


class ChatModel(Protocol):
    name: str

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], force_tool: str | None = None
    ) -> ModelResponse: ...


class OpenAICompatibleModel:
    def __init__(self, settings: Settings) -> None:
        from openai import AsyncOpenAI

        self.name = settings.llm_model
        self._settings = settings
        self._client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_request_timeout_s,
            max_retries=1,
        )

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], force_tool: str | None = None
    ) -> ModelResponse:
        tool_choice: Any = {"type": "function", "function": {"name": force_tool}} if force_tool else "auto"
        kwargs: dict[str, Any] = {
            "model": self._settings.llm_model,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "temperature": self._settings.llm_temperature,
        }
        if self._settings.llm_seed is not None:
            kwargs["seed"] = self._settings.llm_seed
        response = await self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"_invalid_json": call.function.arguments}
            calls.append(
                ToolCall(call.id, call.function.name, arguments if isinstance(arguments, dict) else {})
            )
        usage = response.usage
        return ModelResponse(
            content=message.content,
            tool_calls=calls,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )


Step = ModelResponse | Callable[[list[dict[str, Any]]], ModelResponse]


@dataclass
class ScriptedModel:
    """Returns the next scripted response on every call. A step may be a function of the messages."""

    steps: list[Step]
    name: str = "scripted"
    calls: list[list[dict[str, Any]]] = field(default_factory=list)
    forced: list[str | None] = field(default_factory=list)

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], force_tool: str | None = None
    ) -> ModelResponse:
        self.calls.append([dict(m) for m in messages])
        self.forced.append(force_tool)
        if not self.steps:
            raise AssertionError("ScriptedModel ran out of scripted responses")
        step = self.steps.pop(0)
        return step(messages) if callable(step) else step


def respond(
    *calls: tuple[str, dict[str, Any]], content: str | None = None, tokens: int = 100
) -> ModelResponse:
    """Build a scripted response with the given (tool name, arguments) calls."""
    return ModelResponse(
        content=content,
        tool_calls=[ToolCall(f"call_{uuid.uuid4().hex[:8]}", n, a) for n, a in calls],
        prompt_tokens=tokens,
        completion_tokens=tokens // 4,
    )


@lru_cache
def get_model() -> ChatModel:
    settings = get_settings()
    if settings.llm_provider == "fake":
        # No scripted behavior in a running server: any turn will say the model is not configured.
        return ScriptedModel([])
    if settings.llm_provider == "offline":
        from app.llm.offline import OfflineModel

        return OfflineModel()
    return OpenAICompatibleModel(settings)


@lru_cache
def get_assess_model() -> ChatModel | None:
    """The stronger model used only for the ambiguity judgment, or None to reuse the main model."""
    settings = get_settings()
    if settings.llm_provider != "openai_compatible":
        return None
    if not settings.agent_assess_model or settings.agent_assess_model == settings.llm_model:
        return None
    return OpenAICompatibleModel(settings.model_copy(update={"llm_model": settings.agent_assess_model}))


def estimate_cost(settings: Settings, prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        prompt_tokens / 1e6 * settings.llm_price_input_per_million
        + completion_tokens / 1e6 * settings.llm_price_output_per_million,
        6,
    )
