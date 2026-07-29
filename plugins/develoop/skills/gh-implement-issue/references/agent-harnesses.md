# Agent Harness Adaptation

Keep the workflow invariant across hosts: establish the issue contract, protect
unrelated work, implement on a branch, validate, publish, and verify review or
CI state. Adapt the mechanism to the capabilities available in the current
agent.

## Codex

- Invoke the skill as `$gh-implement-issue`.
- Prefer connected GitHub tools for issue, pull-request, review-thread, and
  check reads when available; use `gh` for missing operations.
- Use Codex browser, device, deployment, or subagent capabilities only when the
  requested verification and repository instructions justify them.

## Claude Code

- In the Develoop plugin, invoke
  `/develoop:gh-implement-issue`. A standalone installation may expose
  `/gh-implement-issue` instead.
- Prefer a configured GitHub MCP server when it preserves the required state;
  otherwise use `gh` through the shell.
- Use Claude Code task delegation only when repository instructions allow it
  and the work can be split without overlapping edits.

## Antigravity

- Invoke the installed skill as `/gh-implement-issue`.
- Use an available GitHub integration or `gh`. Map browser, device, deployment,
  and delegation requirements to Antigravity capabilities rather than skipping
  the underlying evidence.

## Standalone Agent Skills

- Load the directory from the host's Agent Skills location and invoke it by the
  frontmatter name, `gh-implement-issue`, using that host's syntax.
- When a host lacks a named helper skill, perform the same inspection directly
  with its GitHub integration, GitHub API, or `gh`.
- When a required mutation or real-runtime verification is unavailable, stop
  at the strongest honest intermediate state and report the exact missing
  capability. Never invent a push, pull request, check result, or runtime test.
