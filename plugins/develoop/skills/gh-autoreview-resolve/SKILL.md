---
name: gh-autoreview-resolve
description: Run a bounded GitHub automated-review and resolution loop for a specified pull request. Use when an agent must mark a PR ready for review, confirm the automated reviewer started through an eyes reaction, wait for a thumbs-up or concrete review response, validate and address review threads, request a narrowly focused `@codex review` follow-up when warranted, prevent review scope creep through PR comments or a gh-create-issue follow-up, and optionally merge with the user's preferred strategy.
license: MIT
---

# GitHub Auto Review Resolve

Move one specified pull request from draft through a conservative automated-review loop. Keep the PR's original implementation goal authoritative; do not turn review follow-up into an open-ended audit.

## Adapt to the agent host

Read [references/agent-harnesses.md](references/agent-harnesses.md) before
choosing GitHub, waiting, or user-interaction tools. The `@codex review`
mention in this workflow addresses GitHub's configured Codex reviewer; it does
not require the agent executing this skill to be Codex. Do not post the mention
unless the repository actually uses that reviewer.

## Establish the contract

1. Read repository instructions, the linked issue, PR body, changed files, current head, checks, and existing review threads.
2. Record the original goal, acceptance criteria, explicit non-goals, requested review focus, whether merge is authorized, and the user's preferred merge strategy.
3. Verify `gh auth status`, the repository, PR number, local checkout, and unrelated working-tree changes before mutations.
4. Run `scripts/inspect_review_state.py <PR> --repo OWNER/REPO` for one normalized, fully paginated baseline. Treat its GraphQL `reviewThreads` result as the source of truth for unresolved work. The inspector first reads `gh api rate_limit`, preserves 200 GraphQL points plus a five-point next-query buffer by default, and reports every query's `cost`, `remaining`, `used`, and `reset_at` values.
5. Use only one active observer for an `OWNER/REPO#PR`. When waiting is required, give the loop to one `--watch` process and let other agents or tasks reuse its result instead of polling independently. The watcher enforces this on the same host with a process lock; operators must preserve the same single-observer contract across hosts.

Do not merge unless the user explicitly requested it. If merge was requested but the strategy is neither stated nor reliably discoverable, ask rather than guess.

## Start review

1. If the PR is a draft, run `gh pr ready <PR> --repo OWNER/REPO`. Do nothing if it is already ready.
2. Record the UTC time immediately before the ready transition and inspect with `--after <ISO_TIME>` so old bot activity is not mistaken for the new review.
3. Confirm review start from an `eyes` reaction on the PR or the active `@codex review...` comment. If feedback or a pass response arrives before eyes is sampled, accept that as a completed start race.
4. If no start signal appears after a reasonable bounded wait, confirm there is no active request, then post exactly one `@codex review` comment. Include the current full head OID on its own `Review head:` line so a later reaction can be tied to that exact code. Never post another request while eyes is present.
5. When the user supplied a review target, request it narrowly and keep the head marker:

   ```text
   @codex review
   Review head: `<full head OID>`

   Focus on <specific contract, regression, or risk>.
   ```

Avoid leading the reviewer toward a predetermined implementation or inviting a repository-wide audit.

## Wait and classify

Use `inspect_review_state.py <PR> --repo OWNER/REPO --watch --after <ISO_TIME>` for a bounded wait. It takes one authoritative snapshot, then uses a lightweight transition fingerprint instead of repeatedly loading every thread and check. An unchanged fingerprint backs off from 60 to 120 to 240 seconds and then caps at 300 seconds, with jitter. A transition resets the backoff and triggers another fully paginated snapshot; even without a detected transition, the watcher forces an authoritative refresh every 10 minutes. Defaults cap a watcher at 20 minutes, 40 GraphQL requests, 20 pages per connection, and 90 seconds of actual GraphQL execution. Each `gh` request receives the remaining execution/deadline timeout. Adjust a ceiling only for a concrete PR-size or latency reason.

Do not run a separate shell polling loop around the inspector. Keep the user informed during longer waits while the one watcher owns observation.

- `eyes > 0`: review is still running; keep waiting.
- `thumbs_up > 0`: no-issue pass tied to the current head, unless unresolved threads still exist.
- `ignored_thumbs_up > 0`: a thumbs-up was observed without a matching `Review head:` anchor. Do not treat it as a pass; if the bounded explicit request has not been used, request review once with the current full head OID.
- `outcome: passed`: accept either thumbs-up or an explicit connector response such as “Didn't find any major issues,” provided the response applies to the current head.
- `outcome: review_feedback`: inspect every unresolved thread.
- `outcome: review_response`: inspect the response and thread state; do not assume pass or failure.
- `outcome: not_started_or_pending`: allow short propagation time, then diagnose configuration or request state without posting duplicates.
- `outcome: pagination_incomplete` or `pagination_incomplete: true`: stop. The inspector already followed cursors until an explicit ceiling or a missing/repeated cursor prevented progress. Read `pagination.unfinished`, raise a justified ceiling if safe, and resume only after checking the reported cursor and quota.
- `outcome: rate_limited`: this is an operational pause, not review failure. The inspector reads included response headers, so honor `retry_after_seconds` for secondary limits or wait until the reported `reset_at`; do not immediately retry.
- `outcome: budget_exhausted`: stop the observer and inspect its request, page, or execution-time ceiling before deciding whether one bounded rerun is justified.
- `observer.outcome: watch_timeout`: the review is still non-terminal. Report the current state and decide whether another bounded observation window is warranted.
- `observer.outcome: observer_active`: reuse the existing observer. Do not start another watcher for the same PR.

Check that the review applies to the current head. A stale or outdated anchor is evidence to reassess, not a reason to edit blindly. Never report `passed`, ready, or zero unresolved threads unless `pagination.complete` is `true`.

## Resolve feedback

For each unresolved thread:

1. Reproduce or disprove the claim against current code, tests, runtime behavior, and the PR's original contract.
2. Classify it as:
   - **valid and in scope**: caused by the PR or violates its acceptance criteria;
   - **valid but out of scope**: pre-existing or an adjacent enhancement not needed for the PR goal;
   - **invalid, duplicate, or stale**: contradicted by evidence, already handled, or based on an obsolete head.
3. For valid in-scope findings, make the smallest coherent fix. Preserve unrelated work, follow repository instructions, add focused regressions, and run validation proportional to risk.
4. Commit and push normally. Update the PR body when the new commit materially changes its described behavior or validation evidence.
5. Reply on the exact thread with concise evidence: validity decision, root cause, fix or rejection rationale, tests, and commit when applicable.
6. Resolve the thread only after the reply is posted. Re-fetch the current head, checks, reactions, and unresolved thread count.

Do not silently resolve a substantive thread and do not equate reviewer priority labels with proven validity.

## Bound the loop

Use one initial review and at most one explicit focused re-review by default. Request that re-review only when the fix changed a sensitive reviewed boundary, evidence leaves a concrete in-scope doubt, or the user explicitly asked for another pass.

Do not automatically start a third explicit review round. Stop or split follow-up when any of these occurs:

- new comments move beyond the PR's original goal;
- the concern is pre-existing and non-blocking for this PR;
- fixes begin spreading into unrelated modules or architectural redesign;
- the reviewer repeats an already answered behavior without new evidence;
- the acceptance criteria and required regression coverage are already satisfied.

When stopping:

1. If no separate issue is warranted, comment on the PR with the scope decision and evidence, then stop the loop.
2. If the finding is real and deserves implementation, invoke `gh-create-issue` using the current agent host's skill syntax. Research primary evidence, check for duplicates, create an implementation-ready English follow-up issue, comment its link and why it is separated, then stop this review line.
3. If an in-scope release blocker remains unresolved, do not merge. Report the blocker.
4. If only a non-blocking out-of-scope follow-up remains, the PR may proceed after the comment or issue link is recorded.

## Finish and optionally merge

Before declaring the loop complete, verify the exact final head, required checks, no active eyes request, and zero unresolved review threads. A pass response is sufficient; do not manufacture extra review rounds merely to obtain a different reaction shape.

Also verify `pagination.complete: true` and `rate_limit.status: ok`. Partial data may contain useful feedback, but it is never terminal success.

If merge was requested:

1. Reconfirm the PR is ready, mergeable, current checks are green, and no in-scope blocker remains.
2. Use the user's preferred method: `--rebase`, `--squash`, or `--merge`.
3. Merge in any user-specified dependency order. Do not delete branches or worktrees unless requested.
4. Re-fetch and report the merged state, resulting commit, linked issue state, and any follow-up issue.

If merge was not requested, stop at the verified ready-to-merge state.

## Inspection script

Run from this skill directory:

```bash
python scripts/inspect_review_state.py 123 --repo owner/repository
python scripts/inspect_review_state.py https://github.com/owner/repository/pull/123 --after 2026-07-23T00:00:00Z
python scripts/inspect_review_state.py 123 --repo owner/repository --watch --after 2026-07-23T00:00:00Z
gh api rate_limit --jq '.resources.graphql'
```

The inspector fetches top-level comments without nested reactions, identifies the latest active anchored review request, and then fetches reactions only for that comment. It follows cursors for PR reactions, comments, reviews, threads, active-request reactions, check contexts, and nested thread comments. Missing or non-advancing cursors fail closed with the exact unfinished connection.

Use `--self-test` to validate the script's state classifier without GitHub access. Use `--reserve`, `--query-cost-buffer`, `--max-requests`, `--max-pages`, `--max-seconds`, or the watch timing flags only when the defaults do not fit a verified repository constraint.
