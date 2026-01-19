---
name: issue-resolver
description: "Resolve GitHub issues end-to-end using gh CLI: read issue title/body/comments, draft an implementation plan, request decisions, implement on a fresh feature/fix branch from up-to-date main with atomic commits, run tests via uv, update docs/examples, and report results. Use when a user asks to implement or fix a tracked GitHub issue in the current repo."
---

# Issue Resolver

## Overview

Plan and implement GitHub issues from discovery through code changes, using gh CLI for issue context and uv for Python workflows, with clean branching and atomic commits.

## Workflow

### 1) Inspect the issue first
- Verify gh auth: `gh auth status`.
- Read issue title/body/comments: `gh issue view <id> --json title,body,comments`.
- Summarize the problem and acceptance criteria in 3-6 bullets.

### 2) Draft the implementation plan
- Identify likely files, tests, docs, and examples to touch.
- Note any breaking changes or migrations.
- If any decisions are required (behavioral policy, API shape, edge-case rules), ask the user before coding.

### 3) Prepare the branch (always from updated main)
- `git checkout main`
- `git pull origin main`
- Create a branch named `feat/<feature>` or `fix/<what-to-fix>`.

### 4) Implement with atomic commits
- Break changes into small, logical commits.
- Use commit messages like `feat: ...` or `fix: ...`.
- Update tests and docs as needed.
- If examples exist, update or validate them.

### 5) Run tests with uv (Python)
- Use `uv sync` if needed for deps.
- Run tests with `uv run pytest`.

### 6) Report results
- Summarize changes with file paths.
- Note test commands and outcomes.
- Mention any follow-ups or open questions.

## Notes and conventions
- Always ask for decisions before proceeding if the issue requires policy choices.
- Keep context small; quote only what’s needed from issue comments.
- Prefer minimal, targeted code changes.
- Do not add extra documentation files beyond what the repo expects.
