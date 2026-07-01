---
name: gh-implement-issue
description: Implement GitHub issues through a complete branch-to-PR workflow. Use when the user asks an agent to implement, fix, or ship a specific GitHub issue, including reading issue comments, confirming the implementation contract, creating a branch, making atomic commits, validating, pushing, opening or updating a PR, and handling issue-linked review/CI follow-up. Use related skills or integrations when available; otherwise inspect the repository, issue, PR, CI, and review context directly with the available tools.
license: MIT
---

# GH Implement Issue

## Overview

Use this when the job is not just "make a patch", but "implement the GitHub issue and carry it to a validated PR-ready state". The output should be a branch/commit/PR state that matches the issue scope and a closeout that names validation and unresolved risk.

## Workflow

1. Establish context before editing.
   - Read repo `AGENTS.md` / local instructions.
   - Run `git status --short --branch` and protect unrelated dirty work.
   - Fetch the issue/PR/source-of-truth first: `gh issue view`, `gh pr view`, linked comments, upstream PRs, docs, or paired repositories.
   - If the issue touches separable surfaces, use subagents for independent discovery, such as backend contract vs frontend UI vs upstream library behavior.

2. Confirm the implementation contract.
   - Restate the concrete behavior, non-goals, and expected output.
   - Check whether the issue number is actually an issue, PR, duplicate, stale branch, or follow-up.
   - When the target is a GitHub issue you will implement, assign yourself before branch planning or code edits: `gh issue edit <issue-number-or-url> --add-assignee "@me"` (or an equivalent GitHub API/UI action). Do not remove existing assignees. If assignment is impossible because the target is not an issue or permissions are missing, stop and report the blocker before implementation.
   - For cross-repo changes, inspect the upstream contract before patching the downstream repo.

3. Plan the branch and commit slices.
   - Create or switch to the requested feature branch before editing.
   - Keep commits aligned with real task boundaries: core behavior, UI, docs, release/version, review fix.
   - If branch scope grows beyond its name or PR text, rename or update the branch/PR instead of letting metadata drift.

4. Implement narrowly.
   - Follow local patterns and repo validation style.
   - Stage only requested files; leave unrelated worktree noise unstaged.
   - Add focused regression tests when behavior is testable.
   - For user-facing UI or runtime behavior, verify with a real browser, device, deployment, or output surface when feasible.

5. Validate in layers.
   - Run the smallest focused test first.
   - Then run the repo-expected checks for the touched surface, such as typecheck, lint, build, unit tests, dry-run deploy, or package metadata checks.
   - If a command cannot run because an environment dependency is missing, record the exact blocker and continue with the strongest available narrower proof.

6. Publish.
   - Push with upstream tracking once the local branch is coherent.
   - Create a draft PR for substantial or still-reviewing work unless the user asked otherwise.
   - Write PR titles and bodies in English. The PR body must be English even when the issue or conversation is in another language.
   - Translate the implemented issue requirements into clear English in the PR body, while preserving exact non-English UI labels, product names, error text, commands, and quoted literals when they are part of the change or evidence.
   - PR body should match the actual diff and include summary, validation, risks/known gaps, and GitHub closing keywords such as `Closes #123` when the PR fully implements the target issue.
   - Do not close the implemented target issue manually after opening the PR. Leave it open so GitHub closes it automatically when the PR with the closing keyword is merged.
   - If a related issue is duplicate or stale rather than implemented by the PR, close it manually only when the user explicitly asked for duplicate/stale issue cleanup and the evidence is verified; otherwise explain the stale/duplicate assessment in the PR body or final response.
   - Re-check CI or PR checks before claiming status in the PR body.

7. Follow up on review/CI.
   - If review-thread helper skills or GitHub integrations are available, use them to inspect unresolved review threads and preserve thread state. If they are not available, use `gh pr view`, `gh api`, or the available GitHub interface to identify unresolved review comments before patching.
   - If CI-debugging helper skills or integrations are available, use them to inspect failing GitHub Actions or external check details. If they are not available, use `gh pr checks`, `gh run view`, linked check URLs, or local reproduction commands to collect the failure evidence.
   - For valid review comments or CI failures, patch, validate, push, reply where appropriate, and re-check the unresolved thread or check status.
   - For invalid or deferred comments, explain concretely before resolving only if that matches the user's hygiene rule.

## Closeout Checklist

- Branch name and PR number.
- Target issue closure path: confirm the PR body contains the right closing keyword, or explain why the issue should remain open.
- Commits made, grouped by intent when more than one.
- Validation commands run and their result.
- Commands not run and why.
- Unrelated dirty files left untouched.
- Remaining risks or follow-up issues.

## Pitfalls

- Do not infer scope from a title alone; issue comments and paired upstream code often change the real contract.
- Do not let generated or placeholder PR bodies survive after implementation.
- Do not resolve review threads from flat PR comments alone; thread state matters.
- Do not call a feature done from tests only when the user asked for real UI, device, deployment, or artifact verification.
- Do not combine unrelated cleanup with issue work just because it is nearby.
- Do not run `gh issue close` for an issue implemented by the current PR. Use PR closing keywords and let merge close the issue.
