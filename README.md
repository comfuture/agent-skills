# Agent Skills

Personal Agent Skills for GitHub issue creation and issue-to-PR workflows.

This repository is maintained primarily so I can sync my own agent skills across
machines. It is public so other people can inspect, adapt, or install the
skills if they are useful, but it is not a supported product or service.

## Before You Install

Review the skills before using them. Agent skills are executable instructions
for coding agents and may cause file changes, shell commands, network requests,
GitHub writes, or other state-changing actions depending on the agent and task.

Use this repository at your own risk. I do not provide warranty, support
guarantees, or compensation for damage, data loss, incorrect output, security
issues, costs, or any other loss caused by using these skills without verifying
that they are appropriate for your environment.

The contents may change at any time. Pin a tag or commit if you need stable
behavior.

## Install For Codex

Codex supports the open Agent Skills format and can read user-level skills from
`~/.agents/skills`. For my own local Codex setup, this repository also includes
a helper that syncs the managed skills into `~/.codex/skills`.

```bash
git clone git@github.com:comfuture/agent-skills.git ~/Project/agent-skills
~/Project/agent-skills/scripts/install.sh
```

Install only one managed skill:

```bash
~/Project/agent-skills/scripts/install.sh issue-creator
```

Preview without writing:

```bash
~/Project/agent-skills/scripts/install.sh --dry-run
```

## Install With `npx skills`

The cross-agent `skills` CLI can install these skills into many supported agent
hosts.

List available skills:

```bash
npx skills add comfuture/agent-skills --list
```

Install `issue-creator` globally for Claude Code:

```bash
npx skills add comfuture/agent-skills --skill issue-creator -g -a claude-code -y
```

Install every skill for every detected agent:

```bash
npx skills add comfuture/agent-skills --skill '*' --agent '*' -y
```

During local development:

```bash
npx skills add . --list
```

## Install With GitHub CLI

GitHub CLI v2.90.0+ includes `gh skill`.

```bash
gh skill install comfuture/agent-skills issue-creator --agent claude-code --scope user
gh skill install comfuture/agent-skills gh-implement-issue --agent codex --scope user
```

Install every skill:

```bash
gh skill install comfuture/agent-skills --all --agent universal --scope user
```

Pin a version when repeatability matters:

```bash
gh skill install comfuture/agent-skills issue-creator --pin <tag-or-commit>
```

## Install In Claude Code As A Plugin

Claude Code plugins are namespaced, so installed skills are invoked as
`/comfuture-agent-skills:issue-creator` and
`/comfuture-agent-skills:gh-implement-issue`.

Add this repository as a plugin marketplace:

```text
/plugin marketplace add comfuture/agent-skills
```

Install the plugin:

```text
/plugin install comfuture-agent-skills@comfuture-skills
```

For local plugin development:

```bash
claude --plugin-dir .
```

Then run `/reload-plugins` inside Claude Code after edits.

## Install In Gemini CLI

Gemini CLI discovers skills from `~/.gemini/skills/`, `~/.agents/skills/`, and
workspace-level `.gemini/skills/` or `.agents/skills/`.

```bash
gemini skills install https://github.com/comfuture/agent-skills.git --consent
```

## Included Skills

- `issue-creator`: Research context and draft or create implementation-ready
  GitHub issues.
- `gh-implement-issue`: Implement a GitHub issue through a validated
  branch-to-PR workflow.

These are personally maintained skills. This repository intentionally excludes
copies of skills already provided by Codex, Claude Code, OpenAI-curated plugins,
or other agent runtimes.

## Updating Local Edits

If you edit a skill locally under `~/.codex/skills`, export it back to this
repository before committing:

```bash
~/Project/agent-skills/scripts/export-from-codex.sh issue-creator
git -C ~/Project/agent-skills diff -- skills/issue-creator
```

The helper script allowlist is `managed-skills.txt`. `--delete` is applied only
inside each managed skill directory, never against all of `~/.codex`.

## Maintenance Checks

Before committing a new or edited skill:

```bash
git grep -nE '(/Users/|gho_|sk-|BEGIN .*PRIVATE KEY|auth.json)' -- . ':!README.md' ':!scripts/*' ':!.gitignore'
npx skills add . --list
gh skill publish --dry-run
claude plugin validate --strict .
```

When adding new skills, keep the folder name, `name` frontmatter, and
`managed-skills.txt` entry in sync.

When publishing a Claude Code plugin update, bump the `version` in both
`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

## License

MIT. See `LICENSE`.
