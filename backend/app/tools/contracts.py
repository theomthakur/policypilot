"""Tool input and output models. These mirror contracts/tools.schema.json."""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ErrorCode = Literal[
    "INVALID_ARGUMENT",
    "DOCUMENT_NOT_FOUND",
    "DOCUMENT_NOT_READY",
    "OUT_OF_RANGE",
    "TIMEOUT",
    "DEPENDENCY_UNAVAILABLE",
    "OUTPUT_LIMIT_REACHED",
]


class ToolError(BaseModel):
    code: ErrorCode
    message: str
    retryable: bool = False


class ToolResult(BaseModel):
    status: Literal["ok", "empty", "error"]
    data: dict[str, Any] | None = None
    error: ToolError | None = None
    summary: str
    suggestion: str | None = None


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListDocumentsInput(_Strict):
    status: Literal["ready", "any"] = "ready"
    title_contains: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)


class SearchDocumentsInput(_Strict):
    query: str = Field(min_length=3, max_length=300)
    document_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=15,
        description=(
            "Optional filter: document_id UUIDs from list_documents or search results, "
            "never evidence IDs like E1."
        ),
    )
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    top_k: int = Field(default=6, ge=1, le=10)

    @model_validator(mode="after")
    def _page_range(self) -> "SearchDocumentsInput":
        if self.page_start and self.page_end and self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        return self


class ReadDocumentPagesInput(_Strict):
    document_id: uuid.UUID
    page_start: int = Field(ge=1)
    page_end: int | None = Field(default=None, ge=1)


class GetDocumentOutlineInput(_Strict):
    document_id: uuid.UUID


class PlanInput(_Strict):
    sub_questions: list[str] = Field(min_length=1, max_length=5)


class AskClarificationInput(_Strict):
    question: str = Field(min_length=3, max_length=300)
    options: list[str] = Field(default_factory=list, max_length=5)


class AssessQuestionInput(_Strict):
    """Structured result of the post-retrieval ambiguity check. The loop, not the model, acts on it."""

    answerable: bool
    missing_slot: str = Field(default="", max_length=120)
    candidate_interpretations: list[str] = Field(default_factory=list, max_length=5)
    clarification_question: str = Field(default="", max_length=300)


class ChatReplyInput(_Strict):
    message: str = Field(min_length=1, max_length=800)


class DraftClaim(_Strict):
    text: str = Field(min_length=1, max_length=600)
    evidence_ids: list[str] = Field(min_length=1, max_length=4)
    quote: str = Field(min_length=1, max_length=400)


class Notice(_Strict):
    kind: Literal["conflict", "missing_evidence", "partial", "assumption"]
    text: str = Field(max_length=500)
    evidence_ids: list[str] = Field(default_factory=list)


class FinalAnswerInput(_Strict):
    summary: str = Field(min_length=1, max_length=1500)
    claims: list[DraftClaim] = Field(default_factory=list, max_length=12)
    notices: list[Notice] = Field(default_factory=list)


ASSESS_TOOL_SPEC: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "assess_question",
        "description": "Report whether the question can be answered the same way for every user.",
        "parameters": {
            "type": "object",
            "properties": {
                "answerable": {"type": "boolean"},
                "missing_slot": {"type": "string"},
                "candidate_interpretations": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                "clarification_question": {"type": "string"},
            },
            "required": ["answerable"],
        },
    },
}

DATA_TOOLS = ("list_documents", "search_documents", "read_document_pages", "get_document_outline")
CONTROL_ACTIONS = ("plan", "ask_clarification", "chat_reply", "final_answer")

INPUT_MODELS: dict[str, type[BaseModel]] = {
    "list_documents": ListDocumentsInput,
    "search_documents": SearchDocumentsInput,
    "read_document_pages": ReadDocumentPagesInput,
    "get_document_outline": GetDocumentOutlineInput,
    "plan": PlanInput,
    "ask_clarification": AskClarificationInput,
    "chat_reply": ChatReplyInput,
    "final_answer": FinalAnswerInput,
}

DESCRIPTIONS = {
    "plan": "Record the sub-questions you will answer. Call this first, once.",
    "list_documents": "List the documents you may search. Use to learn the corpus scope.",
    "search_documents": (
        "Hybrid keyword and semantic search. Returns excerpts with document and page, and weak=true when "
        "results look unconvincing. If weak or empty, rephrase using the documents' own vocabulary."
    ),
    "read_document_pages": "Read the full text of up to 3 consecutive pages of one document.",
    "get_document_outline": "Headings of a document with their page numbers.",
    "ask_clarification": "Ask the user one targeted question instead of guessing. Ends the turn.",
    "chat_reply": (
        "Reply directly, without searching, to a greeting, thanks, or a question about what you can do. "
        "Never use it for any question about accounts, access, data, security or other university "
        "policy. Ends the turn."
    ),
    "final_answer": (
        "Submit the answer. Each claim must cite evidence IDs from this turn and quote the supporting text "
        "verbatim from the cited page. Use notices for conflicts, missing evidence and partial answers."
    ),
}


def openai_tool_specs(include_outline: bool = True) -> list[dict[str, Any]]:
    names = [n for n in INPUT_MODELS if include_outline or n != "get_document_outline"]
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": DESCRIPTIONS[name],
                "parameters": INPUT_MODELS[name].model_json_schema(),
            },
        }
        for name in names
    ]
