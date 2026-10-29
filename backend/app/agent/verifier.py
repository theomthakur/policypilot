"""Citation verification (docs/adr/0007).

A claim is accepted only if every cited evidence ID came from a tool call in this turn and the claim's
quote appears on the cited page (exact normalized substring; token overlap only as a fallback signal).
This proves provenance and quoted support, not full logical entailment.
"""

import re
import unicodedata
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.tools.contracts import DraftClaim, FinalAnswerInput

_NON_WORD = re.compile(r"[^0-9a-z%$.]+")
_WORD_CHAR = re.compile(r"[0-9a-z%$.]")
OVERLAP_THRESHOLD = 0.9
MIN_OVERLAP_TOKENS = 4


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return _NON_WORD.sub(" ", text).strip()


def check_quote(quote: str, page_text: str) -> str:
    """Return 'exact_quote', 'overlap' or 'failed'."""
    q, page = normalize(quote), normalize(page_text)
    if not q:
        return "failed"
    if q in page:
        return "exact_quote"
    tokens = q.split()
    if len(tokens) >= MIN_OVERLAP_TOKENS:
        present = set(page.split())
        if sum(t in present for t in tokens) / len(tokens) >= OVERLAP_THRESHOLD:
            return "overlap"
    return "failed"


def locate_quote(quote: str, page_text: str) -> str | None:
    """The exact span of the page that matches `quote` under the verifier's normalization.

    Models wrap quotes in quotation marks, change dashes or whitespace, and drop trailing periods; storing
    the page's own text keeps every citation a literal substring of its page.
    """
    out: list[str] = []
    origin: list[int] = []
    for i, ch in enumerate(page_text):
        for c in unicodedata.normalize("NFKC", ch).casefold():
            if _WORD_CHAR.match(c):
                out.append(c)
                origin.append(i)
            elif out and out[-1] != " ":
                out.append(" ")
                origin.append(i)
    wanted = normalize(quote)
    position = "".join(out).find(wanted) if wanted else -1
    if position < 0:
        return None
    return page_text[origin[position] : origin[position + len(wanted) - 1] + 1]


def sanitize_final_answer(arguments: dict[str, Any]) -> dict[str, Any]:
    """Drop claims that cite nothing (models sometimes write "not found" as a claim).

    Such a statement is an absence, not a supported claim; when nothing else is left the answer is
    reported as missing evidence instead of failing validation.
    """
    args = dict(arguments)
    claims = args.get("claims")
    if not isinstance(claims, list):
        return args
    kept = [
        c for c in claims if isinstance(c, dict) and c.get("evidence_ids") and str(c.get("quote", "")).strip()
    ]
    if len(kept) != len(claims):
        args["claims"] = kept
        if not kept and not args.get("notices"):
            args["notices"] = [
                {"kind": "missing_evidence", "text": "The documents do not contain this information."}
            ]
    return args


@dataclass(frozen=True)
class EvidenceItem:
    key: str
    document_id: uuid.UUID
    title: str
    page: int


PageText = Callable[[uuid.UUID, int], Awaitable[str | None]]


@dataclass
class VerifiedAnswer:
    answer: dict[str, Any]
    failures: list[str]  # human-readable reasons, fed back to the model for one repair attempt

    @property
    def ok(self) -> bool:
        return not self.failures


async def verify_answer(
    draft: FinalAnswerInput, ledger: dict[str, EvidenceItem], page_text: PageText
) -> VerifiedAnswer:
    citations: list[dict[str, Any]] = []
    index_of: dict[tuple[uuid.UUID, int], int] = {}
    claims: list[dict[str, Any]] = []
    unverified: list[str] = []
    failures: list[str] = []

    async def verify_claim(claim: DraftClaim) -> list[int]:
        indexes: list[int] = []
        for key in claim.evidence_ids:
            item = ledger.get(key)
            if item is None:
                failures.append(
                    f'"{claim.text[:60]}": evidence {key} was not returned by a tool in this turn.'
                )
                continue
            text = await page_text(item.document_id, item.page)
            check = check_quote(claim.quote, text or "")
            if check == "failed":
                failures.append(
                    f'"{claim.text[:60]}": the quote was not found on {item.title} p.{item.page}. '
                    "Quote text exactly as it appears on the page."
                )
                continue
            slot = (item.document_id, item.page)
            if slot not in index_of:
                index_of[slot] = len(citations) + 1
                citations.append(
                    {
                        "index": index_of[slot],
                        "document_id": str(item.document_id),
                        "title": item.title,
                        "page": item.page,
                        "quote": (locate_quote(claim.quote, text or "") if check == "exact_quote" else None)
                        or claim.quote,
                        "verified": True,
                        "check": check,
                    }
                )
            indexes.append(index_of[slot])
        return indexes

    for claim in draft.claims:
        indexes = await verify_claim(claim)
        if indexes:
            claims.append({"text": claim.text, "citation_indexes": sorted(set(indexes))})
        else:
            unverified.append(claim.text)

    def indexes_for(keys: list[str]) -> list[int]:
        out = []
        for key in keys:
            item = ledger.get(key)
            if item and (item.document_id, item.page) in index_of:
                out.append(index_of[(item.document_id, item.page)])
        return out

    notices = [
        {"kind": n.kind, "text": n.text, "citation_indexes": indexes_for(n.evidence_ids)}
        for n in draft.notices
    ]
    if unverified:
        notices.append(
            {
                "kind": "partial",
                "text": "Some claims could not be verified and were removed.",
                "citation_indexes": [],
            }
        )
    no_support = not claims
    stop_reason = "insufficient_evidence" if no_support else "answered"
    answer = {
        "summary": draft.summary,
        "claims": claims,
        "citations": citations,
        "notices": notices,
        "unverified_claims": unverified,
        "stop_reason": stop_reason,
        "partial": bool(unverified),
    }
    return VerifiedAnswer(answer=answer, failures=failures)
