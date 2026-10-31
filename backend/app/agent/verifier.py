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
YEAR = re.compile(r"^(19|20)\d\d$")  # a year often comes from a document's title or date, not its page text


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


def closest_text(quote: str, page_text: str, limit: int = 2) -> str | None:
    """The one or two sentences of the page that share the most words with `quote`, copied as written, so a
    failed quote can be repaired from the page's own words."""
    wanted = set(normalize(quote).split())
    if not wanted:
        return None
    sentences = [" ".join(part.split()) for part in re.split(r"(?<=[.!?])\s+|\n\s*\n", page_text)]
    scored = [
        (len(wanted & set(normalize(sentence).split())) / len(wanted), sentence)
        for sentence in sentences
        if len(sentence.split()) >= 4
    ]
    scored = [item for item in scored if item[0] >= 0.5]
    best = [text for _, text in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]
    return " ".join(best)[:500] if best else None


def strip_evidence_ids(text: str) -> str:
    """Evidence IDs (E3) are bookkeeping for the verifier; people read citations as chips, not as codes."""
    text = re.sub(r"\s*[\(\[]\s*E\d+(?:\s*[,;]\s*E\d+)*\s*[\)\]]", "", text)
    text = re.sub(r",\s*E\d+(?:\s*,\s*E\d+)*(?=\s*[)\].;])", "", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


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


def nearest_span(quote: str, page_text: str) -> str | None:
    """The page's own text (1 to 3 consecutive sentences) that best covers an inexact quote.

    Used when the model's quote is a few words off: the citation then shows what the page really says.
    Returns None when nothing on the page covers at least OVERLAP_THRESHOLD of the quote's words.
    """
    wanted = normalize(quote).split()
    if len(wanted) < MIN_OVERLAP_TOKENS:
        return None
    sentences = [m.span() for m in re.finditer(r"[^.!?\n]+[.!?]?", page_text) if m.group().strip()]
    best: tuple[float, int, str] | None = None
    for i in range(len(sentences)):
        for j in range(i, min(i + 3, len(sentences))):
            span = page_text[sentences[i][0] : sentences[j][1]].strip()
            present = set(normalize(span).split())
            coverage = sum(w in present for w in wanted) / len(wanted)
            if coverage >= OVERLAP_THRESHOLD and (
                best is None or (coverage, -len(span)) > (best[0], -best[1])
            ):
                best = (coverage, len(span), span)
    return best[2] if best else None


def _clip(text: str, limit: int) -> str:
    """Cut at a word boundary so a slightly long field is shortened, not rejected."""
    text = str(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return cut or text[:limit]


def sanitize_final_answer(arguments: dict[str, Any]) -> dict[str, Any]:
    """Make a model's final_answer fit the contract instead of failing the whole turn over a formatting slip.

    - Fields over their length limits are shortened at a word boundary (a quote cut this way is still a
      literal prefix of the page, so verification is unaffected).
    - Claims that cite nothing (models sometimes write "not found" as a claim) are dropped; when nothing
      else is left the answer is reported as missing evidence.
    """
    # Keep only the fields the contract defines. A stray field (for example a top-level "missing_evidence")
    # used to fail the whole turn; a missing-evidence note becomes a proper notice instead.
    args = {k: v for k, v in arguments.items() if k in ("summary", "claims", "notices")}
    stray = arguments.get("missing_evidence")
    if stray:
        text = stray.get("text") if isinstance(stray, dict) else stray
        notices = list(args.get("notices") or [])
        notices.append(
            {"kind": "missing_evidence", "text": str(text or "The documents do not contain this.")}
        )
        args["notices"] = notices
    if isinstance(args.get("summary"), str):
        args["summary"] = _clip(args["summary"], 1500)
    raw_notices = args.get("notices")
    if isinstance(raw_notices, list):
        args["notices"] = [
            {
                "kind": n.get("kind")
                if n.get("kind") in ("conflict", "missing_evidence", "partial", "assumption")
                else "partial",
                "text": _clip(n.get("text", ""), 500),
                **({"evidence_ids": n["evidence_ids"]} if isinstance(n.get("evidence_ids"), list) else {}),
            }
            for n in raw_notices
            if isinstance(n, dict)
        ]
    claims = args.get("claims")
    if not isinstance(claims, list):
        return args
    cleaned = []
    for claim in claims:
        if (
            not isinstance(claim, dict)
            or not claim.get("evidence_ids")
            or not str(claim.get("quote", "")).strip()
        ):
            continue
        ids = claim["evidence_ids"]
        cleaned.append(
            {
                "text": _clip(claim.get("text", ""), 600),
                "quote": _clip(str(claim["quote"]), 400),
                "evidence_ids": list(ids)[:4] if isinstance(ids, list) else ids,
            }
        )
    cleaned = cleaned[:12]
    if len(cleaned) != len(claims):
        args["claims"] = cleaned
        if not cleaned and not args.get("notices"):
            args["notices"] = [
                {"kind": "missing_evidence", "text": "The documents do not contain this information."}
            ]
    else:
        args["claims"] = cleaned
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


def figure_in_text(figure: str, text: str) -> bool:
    """Is this number on the page as a whole number? "20" is not on a page that says "2024" or "120", and "10"
    is not on a page that says "10.5". Thousands separators are ignored on both sides."""
    wanted = re.sub(r"\s+", "", figure).replace(",", "").rstrip(".")
    if not wanted:
        return True
    plain = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    return re.search(r"(?<![\d.])" + re.escape(wanted) + r"(?!\d)(?!\.\d)", plain) is not None


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
            literal = (
                locate_quote(claim.quote, text or "")
                if check == "exact_quote"
                else nearest_span(claim.quote, text or "")
                if check == "overlap"
                else None
            )
            if literal is None:  # every verified citation quote is a literal substring of its page
                check = "failed"
            if check == "failed":
                nearby = closest_text(claim.quote, text or "")
                failures.append(
                    f'"{claim.text[:60]}": the quote was not found on {item.title} p.{item.page}. '
                    "Quote text exactly as it appears on the page."
                    + (f' The closest text on that page is: "{nearby}"' if nearby else "")
                )
                continue
            absent = [
                f
                for f in re.findall(r"\d[\d,.]*\d|\d", claim.text)
                if not YEAR.match(f) and not figure_in_text(f, text or "")
            ]
            if absent:  # a quote that is on the page does not make a figure the claim adds true
                failures.append(
                    f'"{claim.text[:60]}": the figure {absent[0]} is not on {item.title} p.{item.page}. '
                    "State only figures that the cited page contains."
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
                        "quote": literal,
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
        {"kind": n.kind, "text": strip_evidence_ids(n.text), "citation_indexes": indexes_for(n.evidence_ids)}
        for n in draft.notices
    ]
    # A draft can mix supported and unsupported claims. Never leave the unsupported assertions in
    # the reader-facing summary and then merely label the response partial. The retained claims
    # are model-written prose, backed by literal page quotes, so they are a safe complete answer.
    summary = strip_evidence_ids(draft.summary)
    if unverified and claims:
        summary = " ".join(str(claim["text"]) for claim in claims)
    no_support = not claims
    stop_reason = "insufficient_evidence" if no_support else "answered"
    answer = {
        "summary": summary,
        "claims": claims,
        "citations": citations,
        "notices": notices,
        "unverified_claims": unverified,
        "stop_reason": stop_reason,
        "partial": False,
    }
    return VerifiedAnswer(answer=answer, failures=failures)
