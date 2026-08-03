# Develoop 0.1.1 — Quota-safe Automated Review

Develoop 0.1.1 makes the bounded automated-review workflow observable,
pagination-complete, and safe under constrained shared GitHub GraphQL quota.

Highlights:

- Reports per-query GraphQL cost, remaining quota, usage, and reset guidance.
- Fails closed when quota preflight is unavailable or the configured reserve
  cannot be preserved.
- Follows cursors for all review-classification connections, including nested
  review-thread comments and complete check-context verification.
- Replaces fixed full-snapshot polling with adaptive backoff, periodic
  authoritative refreshes, and single-observer coordination.
- Preserves current-head anchoring, unresolved-thread precedence, bounded
  re-review, and duplicate-request prevention.
- Adds deterministic coverage for pagination, rate limits, time and request
  ceilings, response headers, observer locks, and partial-data failure modes.

Reviewer notes:

- Submission type: Skills only
- Version: 0.1.1
- Publisher: Changkyun Kim
- Category: Developer Tools
- Support: https://develoop.comfuture.chatgpt.site/support
- Test coverage: five positive and three negative reviewer scenarios, plus 36
  repository regression tests
- License: MIT AND CC-BY-NC-SA-4.0
