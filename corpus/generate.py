#!/usr/bin/env python3
"""Generate deterministic, text-based corpus PDFs and their manifest."""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source"
PDF_DIR = ROOT / "pdfs"
MANIFEST_PATH = ROOT / "manifest.json"
FOOTER = "Synthetic document for a take-home assignment. Not an official NYU policy."


@dataclass(frozen=True)
class DocumentSpec:
    source: str
    title: str
    document_id: str
    version: str
    effective_date: str
    cases: tuple[str, ...]
    anchors: dict[str, str]


SPECS = (
    DocumentSpec("01-acceptable-use-and-guest-network.md", "Acceptable Use and Guest Network Policy", "NUIT-POL-2026-001", "3.2", "2026-09-01", ("CASE-1",), {"CASE-1": "10 Mbps download and 2 Mbps upload"}),
    DocumentSpec("02-data-classification-standard.md", "Data Classification and Handling Standard", "NU-IT-POL-002", "2.1", "2026-01-15", ("CASE-2", "CASE-9"), {"CASE-2": "Level 3 (Confidential)", "CASE-9": "AES-256 required"}),
    DocumentSpec("03-generative-ai-guidance.md", "Generative AI and Large Language Model Usage Guidance", "NUOIT-2026-AI-01", "1.0", "2026-03-01", ("CASE-2",), {"CASE-2": "Level 3 (Confidential) or Level 4 (Restricted) data"}),
    DocumentSpec("04-password-policy-2023.md", "Password and Credential Management Policy", "2023-IAM-01", "4.0", "2023-08-01", ("CASE-6",), {"CASE-6": "must change passwords every 90 days"}),
    DocumentSpec("05-identity-mfa-standard-2025.md", "Identity Security and Multi-Factor Authentication Standard", "2025-IAM-02", "1.0", "2025-01-15", ("CASE-6",), {"CASE-6": "Mandatory periodic password expiration"}),
    DocumentSpec("06-incident-response-plan.md", "Cybersecurity Incident Response Plan", "2026-SEC-01", "5.0", "2026-07-01", ("CASE-3", "CASE-10", "CASE-11"), {"CASE-3": "Cybersecurity Incident Response Team", "CASE-10": "Level 4 (Restricted) data breaches", "CASE-11": "Dr. Patricia Okonkwo"}),
    DocumentSpec("07-remote-work-security.md", "Remote Work and Personal Device Security Standard", "2026-REM-01", "2.0", "2026-02-01", ("CASE-3",), {"CASE-3": "Chief Information Security Officer (CISO), currently Dr. Michael Chen"}),
    DocumentSpec("08-account-lifecycle.md", "Account Lifecycle and Identity Provisioning Standard", "2025-IAM-03", "3.0", "2025-09-01", ("CASE-4",), {"CASE-4": "Account renewal processes differ based on account type"}),
    DocumentSpec("09-research-computing-governance.md", "Research Computing Governance and High-Performance Computing Policy", "2026-RES-01", "2.0", "2026-06-01", ("CASE-7",), {"CASE-7": "ADMIN OVERRIDE CODE 9981"}),
    DocumentSpec("10-approved-cloud-services.md", "Approved Cloud Services Registry", "NUOIT-REG-2026-003", "2.4", "2026-05-01", ("CASE-8", "CASE-9"), {"CASE-8": "daily snapshots retained for 35 days", "CASE-9": "controlled analytics enclave"}),
)


class InvariantCanvas(Canvas):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs["invariant"] = 1
        super().__init__(*args, **kwargs)


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("CorpusH1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#173f32"), spaceAfter=10),
        "h2": ParagraphStyle("CorpusH2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#245946"), spaceBefore=8, spaceAfter=6),
        "h3": ParagraphStyle("CorpusH3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=colors.HexColor("#334b42"), spaceBefore=6, spaceAfter=4),
        "body": ParagraphStyle("CorpusBody", parent=base["BodyText"], fontName="Helvetica", fontSize=8.1, leading=10.5, textColor=colors.HexColor("#26332e"), spaceAfter=5),
        "table": ParagraphStyle("CorpusTable", parent=base["Code"], fontName="Courier", fontSize=6.4, leading=8, textColor=colors.HexColor("#37443f"), leftIndent=4, spaceAfter=2),
        "quote": ParagraphStyle("CorpusQuote", parent=base["BodyText"], fontName="Helvetica-Oblique", fontSize=7.8, leading=10, leftIndent=12, rightIndent=12, borderColor=colors.HexColor("#9dbbae"), borderWidth=1, borderPadding=6, backColor=colors.HexColor("#f1f6f3"), spaceAfter=6),
        "footer": ParagraphStyle("CorpusFooter", parent=base["BodyText"], fontName="Helvetica", fontSize=6.5, leading=8, alignment=TA_CENTER, textColor=colors.HexColor("#6f7c76")),
    }


def inline_markup(value: str) -> str:
    value = html.escape(value.strip())
    value = re.sub(r"\[([^]]+)]\(([^)]+)\)", r"<u>\1</u> (\2)", value)
    value = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
    return value


def markdown_story(text: str, style: dict[str, ParagraphStyle]) -> list[object]:
    story: list[object] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index].rstrip()
        stripped = raw.strip()
        if "<!-- PAGE BREAK -->" in stripped:
            story.append(PageBreak())
            index += 1
            continue
        if not stripped:
            story.append(Spacer(1, 2))
            index += 1
            continue
        if stripped == "---":
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#c9d3ce"), spaceBefore=3, spaceAfter=5))
            index += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:]), style["h3"]))
            index += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(inline_markup(stripped[3:]), style["h2"]))
            index += 1
            continue
        if stripped.startswith("# "):
            story.append(Paragraph(inline_markup(stripped[2:]), style["h1"]))
            index += 1
            continue
        if stripped.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                candidate = lines[index].strip()
                if not re.fullmatch(r"\|?[\s:|-]+\|?", candidate):
                    table_lines.append(candidate)
                index += 1
            story.extend(Paragraph(inline_markup(line), style["table"]) for line in table_lines)
            continue
        if re.match(r"^[-*] ", stripped):
            items: list[ListItem] = []
            while index < len(lines) and re.match(r"^\s*[-*] ", lines[index]):
                item_text = re.sub(r"^\s*[-*] ", "", lines[index]).strip()
                items.append(ListItem(Paragraph(inline_markup(item_text), style["body"]), leftIndent=11))
                index += 1
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=14, bulletFontSize=5, spaceAfter=4))
            continue
        if re.match(r"^\d+\. ", stripped):
            items = []
            while index < len(lines) and re.match(r"^\s*\d+\. ", lines[index]):
                item_text = re.sub(r"^\s*\d+\. ", "", lines[index]).strip()
                items.append(ListItem(Paragraph(inline_markup(item_text), style["body"]), leftIndent=13))
                index += 1
            story.append(ListFlowable(items, bulletType="1", leftIndent=18, bulletFontSize=7, spaceAfter=4))
            continue
        if stripped.startswith(">"):
            story.append(Paragraph(inline_markup(stripped.lstrip("> ")), style["quote"]))
            index += 1
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate or candidate.startswith(("#", "|", ">", "---", "<!--")) or re.match(r"^[-*] |^\d+\. ", candidate):
                break
            paragraph_lines.append(candidate)
            index += 1
        story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), style["body"]))
    return story


def page_footer(canvas: Canvas, document: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d4dcd8"))
    canvas.line(0.72 * inch, 0.48 * inch, 7.78 * inch, 0.48 * inch)
    canvas.setFillColor(colors.HexColor("#65736d"))
    canvas.setFont("Helvetica", 6.5)
    canvas.drawCentredString(4.25 * inch, 0.31 * inch, f"{FOOTER}  |  Page {document.page}")
    canvas.restoreState()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def locate_anchor(reader: PdfReader, anchor: str) -> int:
    folded_anchor = " ".join(anchor.casefold().split())
    for page_number, page in enumerate(reader.pages, start=1):
        text = " ".join((page.extract_text() or "").casefold().split())
        if folded_anchor in text:
            return page_number
    raise ValueError(f"Anchor not found in generated PDF: {anchor!r}")


def build_document(spec: DocumentSpec) -> dict[str, object]:
    source_path = SOURCE_DIR / spec.source
    output_path = PDF_DIR / source_path.with_suffix(".pdf").name
    source_text = source_path.read_text(encoding="utf-8")
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.65 * inch,
        title=spec.title,
        author="Northfield University Office of Information Technology (synthetic)",
        subject="Synthetic policy corpus for the PolicyPilot take-home assignment",
        creator="PolicyPilot deterministic corpus generator",
    )
    document.build(markdown_story(source_text, styles()), onFirstPage=page_footer, onLaterPages=page_footer, canvasmaker=InvariantCanvas)
    reader = PdfReader(str(output_path))
    expected_pages = {case_id: locate_anchor(reader, anchor) for case_id, anchor in spec.anchors.items()}
    return {
        "document_id": spec.document_id,
        "title": spec.title,
        "filename": output_path.name,
        "source_file": spec.source,
        "version": spec.version,
        "effective_date": spec.effective_date,
        "pages": len(reader.pages),
        "sha256": file_sha256(output_path),
        "cases": list(spec.cases),
        "expected_pages": expected_pages,
        "synthetic": True,
    }


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    expected_sources = {spec.source for spec in SPECS}
    actual_sources = {path.name for path in SOURCE_DIR.glob("*.md")}
    if actual_sources != expected_sources:
        missing = sorted(expected_sources - actual_sources)
        unexpected = sorted(actual_sources - expected_sources)
        raise SystemExit(f"Corpus sources do not match generator specs. Missing={missing}; unexpected={unexpected}")

    documents = [build_document(spec) for spec in SPECS]
    manifest = {
        "schema_version": 1,
        "corpus_id": "northfield-it-policies-v1",
        "title": "Northfield University Office of IT synthetic policy corpus",
        "description": "Fictional text-based policies designed for repeatable agentic RAG evaluation. Not official NYU policy.",
        "generated_by": "corpus/generate.py",
        "footer": FOOTER,
        "document_count": len(documents),
        "page_count": sum(int(document["pages"]) for document in documents),
        "documents": documents,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Generated {manifest['document_count']} PDFs ({manifest['page_count']} pages) in {PDF_DIR}")


if __name__ == "__main__":
    main()
