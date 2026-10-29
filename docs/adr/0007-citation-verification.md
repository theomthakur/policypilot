# 0007. Three-check citation verification

**Status:** Accepted, 2026-10-29

## Context
The brief requires grounded answers and citation verification against actual supporting passages. Models can cite pages they never read, or attach a real page to a claim it doesn't support.

## Decision
The agent's final answer lists atomic claims, each with evidence IDs and a short supporting quote. Before an answer is shown:
1. **Provenance:** each evidence ID was returned by a successful tool call in this turn.
2. **Location:** the cited document and page match the stored evidence.
3. **Support:** the quote is an exact normalized substring of that page's text; a token-overlap score is used only as a fallback signal.

A failed check triggers one repair attempt using only existing evidence. Claims still unsupported are removed and listed as not verified.

## Alternatives considered
- **Overlap score only:** can pass a claim that shares words with a page but says something different.
- **An LLM judge at runtime:** slower and costlier; used optionally in evaluation instead.

## Consequences
- Citations are guaranteed to point to text the agent actually read.
- This proves provenance and quoted support, not full logical entailment; the evaluation adds a manual page check for every case.
