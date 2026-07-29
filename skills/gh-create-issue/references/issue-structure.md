# Issue Structure

Use this structure as the default for implementation issues. Omit or merge sections only when the issue is simple and the repository's existing issue style is shorter.

## Recommended Sections

### Summary

State the desired change and why it matters in one to three short paragraphs. Name the affected product, module, API, or workflow.

### Background

Explain the context needed by someone who did not participate in the conversation. Include upstream docs, related issues, current architecture, user workflow, or operational history when relevant.

### Current implementation facts

List facts discovered during investigation. These should be evidence-backed and concrete:

- current files and functions involved
- current command or workflow behavior
- current API or payload shape
- current error text or logs
- relevant primary documentation facts

Avoid mixing proposed fixes into this section.

### Problem statement

Describe the concrete failure mode or missing capability. If useful, write a short scenario showing how a user or system reaches the problem.

### Goal

Define the end state in one or two paragraphs. The goal should be narrower than the whole problem space.

### Scope

List what should be changed or investigated as part of this issue.

### Non-goals

List adjacent changes that should not be pulled into this issue. Use this to protect implementation focus.

### Suggested direction

Provide a plausible implementation path. Keep it directive enough to save time, but leave room for better findings during implementation.

Good suggested directions include:

- likely files or modules to edit
- APIs or events to use
- migration or compatibility strategy
- validation sequence
- known edge cases

### Acceptance criteria

Use verifiable criteria. Each item should be checkable by code review, tests, CI, manual smoke test, or operational evidence.

Include:

- positive behavior checks
- regression checks
- platform or environment checks
- validation commands
- documentation updates when needed

### Suggested smoke test

Include this when behavior is UI-heavy, platform-dependent, hardware-dependent, workflow-dependent, or hard to prove through unit tests alone.

### Documentation follow-up

Include this when the implementation changes user-facing behavior, developer workflow, public API, release process, or operational runbooks.

## Title Guidance

Use an imperative or outcome-focused title:

- `Rebind loopback capture when the default render device changes`
- `Gate native C FFI exports for downstream builds`
- `Add stateful FeatureExtractor support to Python afpgen binding`

Avoid vague titles:

- `Audio issue`
- `Improve Windows`
- `Follow-up`

## Label Guidance

Use the repository's existing labels when available.

- `bug`: current behavior is wrong, broken, or regressed.
- `enhancement`: new capability or intentional improvement.
- `documentation`: docs-only issue.
- `question`: needs product or technical decision before implementation.

If labels are unavailable or unclear, create the issue without labels rather than inventing taxonomy.
