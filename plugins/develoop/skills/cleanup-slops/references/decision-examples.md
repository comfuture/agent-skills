# State cleanup decisions

These examples are decision aids, not templates to apply mechanically. Trace
the actual lifecycle and consumers before choosing a representation.

## Derive a redundant flag

An editor stores both `selectedId` and `hasSelection`. Every selection and reset
updates both, and all consumers define selection as a non-null ID.

Derive `hasSelection` from `selectedId != null` and remove the duplicate writes.
Verify select, replace, deselect, and restored-selection behavior. If selection
can remain pending while an ID is unresolved, those are different facts and
this derivation may be invalid. Check serialized consumers before removing a
persisted flag.

## Consolidate a genuinely exclusive lifecycle

A subscription coordinates `connecting`, `connected`, and `closed` in several
callbacks. Tracing proves there is one lifecycle with exclusive phases and no
consumer that relies on intermediate flag combinations.

Keep one phase with a clear transition owner, and derive display flags where
needed. Preserve late-callback guards, disposal, and any supported reconnect
path. Verify failure during connect, close during connect, and late completion
after close. Renaming three flags to a phase without tracing these events does
not establish equivalence.

## Preserve independent axes

A search view retains successful results while refreshing. It can display old
data with an active request, or old data with a refresh error. Request status
and cached data therefore express independent facts.

Replacing them with `idle | loading | success | error`, where only `success`
carries data, would erase supported combinations. Remove duplicate predicates
or clarify the request owner if useful, while retaining stale results, empty
success, refresh failure, and retry behavior. An empty result is not evidence
that no successful request has completed.

## Preserve request ownership

Request A starts, then B starts; B resolves before A. A generation counter or
request token prevents A from replacing B's results, error, or loading state.

Keep that ownership check unless the replacement provides the same guarantee.
An abort call alone does not prove that already queued continuations cannot
run. Exercise both completion orders, cancellation, and disposal; check
`finally` and error handlers as well as the success handler.

## Respect a PR's implementation boundary

A PR changes a request hook used by two screens. Inspect the hook, both
consumers, and their relevant tests even if only the hook appears in the diff.
Fix redundant state tied to that implementation. A separate upload queue found
elsewhere belongs in the report unless it is a necessary dependency of the PR's
behavior. Record the inspected base and head so later PR updates are not
silently treated as reviewed.
