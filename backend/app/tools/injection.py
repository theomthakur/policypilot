"""Detect instruction-like text inside retrieved documents (REQ-F5). Detection only flags it in the trace;
the real defence is that tools are read-only and retrieved text is wrapped as untrusted data."""

import re

_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|the)\s+(instructions|rules)", re.I),
    re.compile(r"system\s+override", re.I),
    re.compile(r"override\s+code", re.I),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(admin|developer|dan)\b", re.I),
    re.compile(r"reveal\s+(your|the)\s+(system\s+prompt|api\s+key|secrets?)", re.I),
]


def find_injection(text: str) -> str | None:
    for pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            start = max(0, match.start() - 20)
            return text[start : match.end() + 40].replace("\n", " ")
    return None
