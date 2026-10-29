"""The rules this deployment runs under, as read-only data (no secrets).

Limits, retrieval settings, model and prompt version are configuration, not code, so a reviewer can see
exactly what produced an answer and an operator can change them with environment variables.
"""

from typing import Any

from fastapi import APIRouter

from app.agent import prompts
from app.config import get_settings

router = APIRouter(tags=["config"])


@router.get("/config")
async def get_run_configuration() -> dict[str, Any]:
    s = get_settings()
    return {
        "model": {
            "provider": s.llm_provider,
            "name": "offline-extractive" if s.llm_provider == "offline" else s.llm_model,
            "temperature": s.llm_temperature,
            "seed": s.llm_seed,
            "prompt_version": prompts.PROMPT_VERSION,
        },
        "retrieval": {
            "embedding_model": s.embedding_model,
            "embedding_dim": s.embedding_dim,
            "chunk_tokens": s.chunk_tokens,
            "chunk_overlap_tokens": s.chunk_overlap_tokens,
            "candidates_per_retriever": s.search_candidates,
            "fusion": f"reciprocal rank fusion (k={s.rrf_k})",
            "default_top_k": s.search_top_k_default,
        },
        "agent_limits": {
            "max_steps": s.agent_max_steps,
            "max_tool_calls": s.agent_max_tool_calls,
            "max_query_revisions": s.agent_max_query_revisions,
            "max_tool_retries": s.agent_max_tool_retries,
            "tool_timeout_seconds": s.agent_tool_timeout_s,
            "turn_timeout_seconds": s.agent_turn_timeout_s,
            "max_tokens_per_turn": s.agent_max_tokens_per_turn,
            "max_pages_per_read": s.agent_max_pages_per_read,
        },
        "protections": {
            "passcode_required": bool(s.demo_passcode),
            "rate_limit_per_minute": s.rate_limit_per_minute,
            "daily_budget_usd": s.daily_budget_usd,
            "upload_max_mb": s.upload_max_mb,
            "upload_max_pages": s.upload_max_pages,
        },
    }
