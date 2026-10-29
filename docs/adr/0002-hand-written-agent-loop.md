# 0002. Hand-written, typed agent state machine

**Status:** Accepted, 2026-10-29

## Context
The brief requires an LLM-driven tool loop that decomposes questions, revises queries after weak results, asks for clarification and stops within limits. Reviewers may ask for a live code change, so the loop must be easy to read and modify.

## Decision
Implement the agent as an explicit state machine in plain Python with Pydantic-typed state, using the model's native tool calling. States: `PLAN`, `ACT`, `OBSERVE`, `EVALUATE`, `REVISE`, `CLARIFY`, `SYNTHESIZE`, `VERIFY`, `EMIT`, `PARTIAL_ANSWER`. Stop reasons are machine-readable.

## Alternatives considered
- **LangGraph:** a good fit for graph-shaped workflows with checkpointing, but it adds a framework layer to explain for a single small loop.
- **LangChain agents:** hide the loop behind abstractions, which makes the required behaviors harder to prove and trace.

## Consequences
- Every transition is visible in code and in the trace.
- Behavior is tested deterministically with a scripted fake LLM.
- We own the edge cases a framework would otherwise handle (retries, budgets), which the tests cover.
