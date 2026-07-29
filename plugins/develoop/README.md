# Develoop

Develoop packages a continuous GitHub delivery loop for Codex, Claude Code,
Antigravity, and Agent Skills-compatible hosts.

## Included skills

- `gh-create-issue`: research and create an implementation-ready issue.
- `gh-implement-issue`: carry one issue through a validated pull request.
- `gh-autoreview-resolve`: run a bounded automated-review and resolution loop.
- `writing-strategy`: separately licensed writing structure guidance included
  for bundle compatibility, but not part of Develoop's product positioning.

## Install

### Codex

From a repository checkout:

```bash
codex plugin marketplace add /absolute/path/to/agent-skills
codex plugin add develoop@develoop
```

Start a new task after installation. Invoke skills as `$gh-create-issue`,
`$gh-implement-issue`, and `$gh-autoreview-resolve`.

### Claude Code

```bash
claude plugin marketplace add comfuture/agent-skills
claude plugin install develoop@develoop --scope user
```

Reload plugins or start a new session. Invoke namespaced skills such as
`/develoop:gh-create-issue`.

### Antigravity

```bash
agy plugins install https://github.com/comfuture/agent-skills
agy plugin list
```

Invoke installed skills by their frontmatter names, such as
`/gh-implement-issue`.

### Standalone Agent Skills

The repository root keeps the same four skills in the open Agent Skills layout:

```bash
npx skills add comfuture/agent-skills --skill '*' --agent '*' -y
```

## Public information

- Website: https://develoop.comfuture.chatgpt.site
- Support: https://develoop.comfuture.chatgpt.site/support
- Privacy: https://develoop.comfuture.chatgpt.site/privacy
- Terms: https://develoop.comfuture.chatgpt.site/terms
- Releases: https://develoop.comfuture.chatgpt.site/releases
- Source: https://github.com/comfuture/agent-skills

Repository code and the GitHub workflow skills are licensed under MIT.
`writing-strategy` is licensed separately under CC-BY-NC-SA-4.0.
