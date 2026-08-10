# Develoop 0.1.2 — Head-aware Bounded Re-review

Develoop 0.1.2 makes ready-triggered review passes and follow-up re-review
decisions explicit, current-head-aware, and causally bounded.

Highlights:

- Records both the ready-transition time and full head OID so implicit review
  reactions can be tied to unchanged code.
- Accepts a ready-triggered unanchored thumbs-up only when it is post-ready,
  the pre-ready and current heads match, pagination is complete, and no review
  thread remains unresolved.
- Avoids redundant explicit review requests made solely to add a missing
  `Review head:` marker.
- Keeps one focused verification re-review as the normal path while allowing
  another only for a concrete in-scope regression risk caused or exposed by
  the preceding fix.
- Requires every additional re-review to name the exact current head and
  affected contract, stay within the original scope, and wait for any active
  review request to finish.
- Stops reassurance-only, duplicate, and scope-expanding review loops.

Reviewer notes:

- Submission type: Skills only
- Version: 0.1.2
- Publisher: Changkyun Kim
- Category: Developer Tools
- Support: https://develoop.comfuture.chatgpt.site/support
- Test coverage: five positive and three negative reviewer scenarios, plus 36
  repository regression tests
- License: MIT AND CC-BY-NC-SA-4.0
