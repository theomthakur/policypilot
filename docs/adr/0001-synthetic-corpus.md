# 0001. Synthetic fictional university IT corpus

**Status:** Accepted, 2026-10-29

## Context
The app needs 8 to 15 text-based PDFs from one domain that support cross-document questions. The evaluation also needs a conflicting pair of sources, a fact that is absent, an ambiguous question and a document containing a prompt injection, each at a known page.

## Decision
Use a synthetic corpus of 10 policy documents from a fictional organization, "Northfield University Office of Information Technology". Documents are written in Markdown and rendered to PDF by a committed generator, with a manifest recording titles, page counts and SHA-256 hashes. Every page carries the footer "Synthetic document for a take-home assignment. Not an official NYU policy."

## Alternatives considered
- **Public documents** (for example NIST guidance): realistic, but conflicts and injections would have to be found or inserted, and expected pages in long documents are harder to pin down.
- **A mix of public and synthetic:** two document styles to explain, with little benefit.

## Consequences
- Every evaluation case has a planted, checkable answer at a known page.
- The domain matches a university IT setting without imitating any real institution.
- Users can still upload their own PDFs; the synthetic corpus is the default demo set.
