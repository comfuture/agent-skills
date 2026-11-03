---
name: cleanup-slops
description: Find and simplify implicit state machines across a repository or a specified pull request without regressing behavior. Use for requests such as "find all of the implicit state machines in my app" or a cleanup pass that removes redundant state and consolidates scattered transitions for readability and maintenance.
license: MIT
---

# Cleanup Slops

Start from this prompt:

> find all of the implicit state machines in my app

Use it as a discovery lens for a behavior-preserving cleanup. Find lifecycle
rules hidden across mutable flags, nullable values, effects, callbacks, and
duplicated status fields. Remove unnecessary stored state and scattered
coordination; make essential transitions easier to understand and maintain.

An implicit state machine exists when the meaning or legality of an operation
depends on prior events and combinations of state, while its transitions and
invariants are distributed across the code. Multiple booleans alone are not
evidence: independent settings may legitimately vary independently.

## Establish the boundary

- For a repository-wide request, map application entry points and runtime
  modules, then track which areas were inspected. Start with first-party code;
  exclude generated, vendored, and build output unless they own relevant
  behavior. Do not claim exhaustive discovery from a few keyword searches.
- For a specified PR, resolve the target repository, base, and head. Inspect the
  merge-base-to-head diff and the full enclosing implementations, callers,
  consumers, and tests needed to understand it. Address machines introduced,
  modified, or relied on by that implementation; record unrelated discoveries
  without expanding the patch. Keep findings tied to the inspected head.
- Honor explicit inspection-only or planning requests. When cleanup is
  requested, carry supported fixes through implementation and validation.
  Local cleanup does not itself authorize remote comments, push, merge,
  deployment, or changes to external data.
- Read repository guidance and preserve unrelated working changes. For a new
  cleanup branch, use the existing checkout unless isolation is required or
  requested. Keep an existing PR's branch context when working on that PR.

## Discover and reconstruct

Trace behavior from entry points and state owners, using searches only as
leads. Inspect loading and error flags, selected IDs plus cached objects,
status enums, mirrored props or store values, subscription and connection
lifecycles, pending promises, timers, retries, queues, persistence, and cleanup
handlers. Follow reads, writes, reset paths, and async completions across
module boundaries. Include server, worker, and client paths where present.

Keep a compact inventory for each candidate:

| Evidence | What to establish |
| --- | --- |
| Owner and locations | Who owns the state, who writes it, and who observes it |
| Effective states | Reachable combinations and combinations ruled out by code or contracts |
| Events and transitions | Entry, success, failure, cancellation, retry, reset, and disposal paths |
| Invariants and effects | What must remain true, including observable output and side effects |
| Decision | Derive or remove redundant state, consolidate essential transitions, preserve, or defer with a reason |

Distinguish demonstrated behavior from inferred intent. A suspicious combination
is a candidate until its producers, consumers, and reachable transitions are
understood. Prioritize redundant sources of truth, impossible combinations,
duplicated transition logic, and effects that synchronize state with other
state. Preserve independent axes such as cached data and an in-flight refresh.

## Establish regression evidence

Before editing a candidate, identify its observable contract and run the
relevant existing checks. Record baseline failures separately. Where coverage
does not establish that contract, add focused characterization tests at the
public behavior boundary; confirm they pass before refactoring. Test outcomes
and transitions, rather than private field names or the new representation.

Include the failure and recovery paths the candidate actually supports. For
async work, exercise overlapping requests completing out of order,
cancellation, retry, and disposal where relevant. Preserve side-effect count
and ordering, error propagation, and resource release. For UI paths, exercise
the affected interaction in the available browser or device as well as tests.

Check external consumers and persisted state before removing or renaming a
field. Preserve public APIs, serialized representations, event payloads, and
storage compatibility unless a contract change is explicitly in scope. An
internal simplification may need an adapter at that boundary.

## Simplify one candidate at a time

Choose the smallest representation that expresses the existing contract:

- Derive values from an authoritative source instead of storing and
  synchronizing equivalent flags or copied objects.
- Remove unreachable branches or obsolete transitions only after tracing
  their producers and externally supplied or restored state.
- Group states that are demonstrably mutually exclusive when that prevents
  invalid combinations. Keep independent facts independent.
- Give essential lifecycle transitions one clear owner. A local transition
  function, reducer, or discriminated union may help when the lifecycle cannot
  be eliminated; do not add a framework or universal state-machine layer by
  default.
- Keep guards that enforce timing, request ownership, idempotency, cleanup,
  or consistency. Fewer flags or lines are not sufficient evidence of a safe
  simplification.

Use [references/decision-examples.md](references/decision-examples.md) when
deciding whether state is redundant or protects meaningful history.

Keep edits reviewable and run the focused checks after each coherent change.
Do not quietly fix a pre-existing behavioral bug as part of an equivalence
refactor. Record it separately unless the requested scope includes its fix.
If a candidate's contract is ambiguous or cannot be verified, defer that
candidate with concrete missing evidence and continue with supported cleanup.

## Verify and report

Run the repository's required checks and the tests for affected consumers.
Revisit the inventory: verify that removed state has no remaining writers or
consumers and that essential transitions still have an owner. Review the diff
for unrelated churn, changed defaults, altered event ordering, and accidental
API or persistence changes.

Report the inspected scope and PR head when applicable, the machines found,
what was simplified, what was preserved or deferred and why, and the checks
actually run. Identify baseline failures and untested behavior explicitly;
do not claim regression freedom from passing unrelated checks. State any
uninspected areas when reporting repository-wide coverage. Finish when the
in-scope inventory is addressed or explicitly deferred with evidence; do not
keep rewriting adjacent code merely to reduce the machine count.
