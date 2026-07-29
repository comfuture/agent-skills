# Agent Harness Adaptation

Keep the workflow invariant across hosts: inspect the exact pull request,
observe the current automated-review state, validate every finding, bound the
loop, and verify the final head and unresolved-thread count. Adapt the mechanism
to the capabilities available in the current agent.

## Codex

- Invoke the skill as `$gh-autoreview-resolve`.
- Prefer connected GitHub tools when they expose review threads and reactions;
  use the bundled inspection script and `gh` for normalized or missing state.
- `@codex review` addresses the GitHub reviewer account, not the local Codex
  task.

## Claude Code

- In the Develoop plugin, invoke
  `/develoop:gh-autoreview-resolve`. A standalone installation may expose
  `/gh-autoreview-resolve` instead.
- Prefer a configured GitHub MCP server when it preserves reactions, reviews,
  and thread-resolution state; otherwise use the inspection script and `gh`.
- The GitHub `@codex review` mention remains literal when that reviewer is
  configured even though Claude Code is executing the workflow.

## Antigravity

- Invoke the installed skill as `/gh-autoreview-resolve`.
- Use an available GitHub integration or the inspection script plus `gh`.
- The GitHub `@codex review` mention remains literal when that reviewer is
  configured even though Antigravity is executing the workflow.

## Standalone Agent Skills

- Load the directory from the host's Agent Skills location and invoke it by the
  frontmatter name, `gh-autoreview-resolve`, using that host's syntax.
- If the host cannot read GraphQL review-thread state, use the bundled script
  with authenticated `gh`. Flat pull-request comments are not an equivalent
  source of truth.
- If reaction, thread, or check state cannot be verified, report the missing
  capability and do not claim the review loop is complete or merge-ready.
