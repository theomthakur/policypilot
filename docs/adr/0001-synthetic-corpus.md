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

## Addendum (29 Oct 2026): a reference library

After the first evaluation, four real public documents were added next to the synthetic ones, so the system is also tested on pages it was not written for (real layout and vocabulary): NIST SP 800-61r3, NIST CSF 2.0, NIST SP 800-46r2 and FIPS 199. They are U.S. government publications, not subject to copyright in the United States, included unmodified with sources in `corpus/reference/SOURCES.md`. They are loaded as source `reference`, shown in the app as "public reference", and are outside the frozen evaluation anchors. The synthetic corpus is also regenerated with a more realistic layout, which moved some page numbers; `eval/cases.yaml` follows them.
