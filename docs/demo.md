# Demo and reviewer walkthrough

**Video (about 5 minutes):** https://youtu.be/njw7qmk8aTQ

The video shows the full local stack with sign-in, then the hosted version. This page lets you try the same things yourself.

## Two ways to try it

| | Hosted demo | Local full stack with sign-in |
|---|---|---|
| Where | https://policypilot-om-thakur.onrender.com | http://localhost:8080 |
| Branch | `main` | `local-sign-in` |
| Access | Shared access code (from the author) | Keycloak sign-in: test users `alice` and `bob`, or **Create account** |
| Start | Already running (an idle service takes about a minute to wake) | `git checkout local-sign-in` then `scripts/run_with_sign_in.sh` |

The code is the same in both; sign-in is a setting (`AUTH_MODE=oidc`). Render's free plan runs one web service, so the hosted version uses an access code, a rate limit and a daily spending cap instead of an identity server. For the local stack, the passwords for `alice` and `bob` are written to `.env.auth-demo` on the first run.

Wait until the **Knowledge base** shows 14 ready documents before asking questions.

## Things to try

1. **A one-document question.** For example: *What bandwidth limits apply to unregistered guest devices?* Open **Agent activity** to see the plan, the searches and the pages read.
2. **A two-document question.** *A researcher has Level 3 confidential pre-publication data. What encryption is required at rest, and may the researcher paste it into a public consumer AI tool?* The answer cites the Data Classification Standard and the Generative AI Guidance.
3. **Check a citation.** Click a numbered citation chip to see the exact quote, then **View** to open the PDF at that page. Every quote is checked against the page text before the answer is shown.
4. **A question the documents don't answer.** *How many vacation days do staff receive each year?* The assistant says the documents don't contain it, and makes no claims.
5. **Upload a PDF** from **Knowledge base**, wait for it to show as ready, and ask about it. Uploads are private to the browser session (hosted) or the signed-in user (local).
6. **Around the app:** **History** and clearing it, **System design** (the architecture on one page), **Presentation** (a short built-in deck), dark mode (moon icon) and developer mode (code icon: steps, searches, tokens, time and estimated cost per answer).
7. **Local only:** sign out from the account menu. This revokes the server-side session.

## Behaviours that are hard to trigger live

Saved traces in [`demo-evidence/`](demo-evidence/) show:

- a multi-document answer,
- a search revised because the first results did not cover part of the question,
- a clarifying question followed by an answer that keeps the original context,
- a tool timeout with one bounded retry (`FAULT_INJECTION_ENABLED=true`, test environments only; reproduce with `python eval/run.py --case CASE-8`).

## Known limits

- Deciding when to ask a clarifying question is the least reliable behaviour. It works on the tested questions but is not claimed beyond them.
- The evaluation sets are small and were partly used to guide fixes, so the results in [`evaluation.md`](evaluation.md) are indicative, not proof.
- On the local stack, signing out ends the app's session but not the Keycloak session, so signing in as a different user in the same browser needs a private window.
