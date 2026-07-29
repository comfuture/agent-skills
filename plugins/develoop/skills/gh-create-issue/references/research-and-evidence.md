# Research and Evidence

An issue is useful when it preserves investigation results. Do enough research that the next implementer does not need to rediscover the same facts.

## Evidence Sources

Prefer these sources, in roughly this order:

1. Existing issues, PRs, review comments, and release notes in the target repository.
2. Current source code, tests, docs, workflows, configuration, logs, and generated artifacts.
3. Primary upstream documentation, specifications, API references, or source code.
4. Reproduction steps, screenshots, traces, CI logs, or command output.
5. Secondary explanations only when primary sources are unavailable, and label them as secondary.

## Repository Style Check

Before drafting, inspect recent issues in the target repository or a closely related sibling repository. Capture:

- typical section headings
- typical amount of background detail
- whether acceptance criteria are used
- whether issues include non-goals or suggested direction
- whether labels are consistently applied

Mirror the level of detail that made those issues effective. Do not preserve poor style just because it exists.

## Primary Documentation

Browse or inspect primary docs when the issue depends on:

- operating system APIs
- cloud provider behavior
- language or framework behavior
- protocol semantics
- package manager behavior
- security, auth, secret, or deployment rules
- anything likely to have changed recently

Mention source names or URLs in the issue when they materially affect the implementation.

## Wording Rules

Use these distinctions:

- `Observed facts`: things verified in code, logs, docs, or commands.
- `Inferred behavior`: likely conclusions drawn from facts.
- `Suggested direction`: one implementation path, not the only possible path.
- `Open question`: a decision or unknown that could change scope.

Avoid:

- vague claims like "probably broken" without a scenario
- hidden reasoning that only appears in chat
- acceptance criteria that merely say "works correctly"
- implementation details that contradict existing repository patterns

## Command and Tool Notes

When creating GitHub issues with `gh`, verify the target repository:

```bash
git remote -v
gh repo view OWNER/REPO --json nameWithOwner,url
gh issue list --repo OWNER/REPO --limit 10 --state all
```

For issue creation:

```bash
gh issue create --repo OWNER/REPO --title "Title" --body-file issue.md --label enhancement
```

If writing temporary drafts, use a safe temp path and remove it after issue creation unless the user asked to keep the draft.
