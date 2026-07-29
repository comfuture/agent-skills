# Agent Harness Adaptation

Keep the workflow invariant across hosts: inspect evidence, preserve scope,
verify the target repository, and perform only authorized GitHub writes.
Adapt the mechanism to the capabilities available in the current agent.

## Codex

- Invoke the skill as `$gh-create-issue`.
- Prefer an available GitHub integration for issue, repository, and history
  reads. Use `gh` for operations the integration does not expose.
- Use connected browser or document tools only when the evidence source
  requires them.

## Claude Code

- In the Develoop plugin, invoke
  `/develoop:gh-create-issue`. A standalone installation may expose
  `/gh-create-issue` instead.
- Prefer a configured GitHub MCP server when it supports the required
  operation; otherwise use `gh` through the shell.
- Follow Claude Code permission prompts and repository instructions before
  state-changing commands.

## Antigravity

- Invoke the installed skill as `/gh-create-issue`.
- Use an available GitHub integration or `gh`. Treat any named Codex or Claude
  tool in supporting material as a capability description and select the
  Antigravity equivalent.

## Standalone Agent Skills

- Load the directory from the host's Agent Skills location and invoke it by the
  frontmatter name, `gh-create-issue`, using that host's syntax.
- If no authenticated GitHub write capability exists, return the reviewed
  title, body, labels, and target repository as a draft. Never claim the issue
  was created.
- If live web access is unavailable, distinguish repository evidence from
  unverified external assumptions and identify what still needs confirmation.
