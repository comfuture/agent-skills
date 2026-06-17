# Agent Skills

Portable Agent Skills for GitHub issue creation and issue-to-PR workflows.

This repository follows the open [Agent Skills specification](https://agentskills.io/specification):
each skill is a folder under `skills/` with a required `SKILL.md`, YAML
frontmatter, and optional supporting files such as `references/`, `scripts/`,
`assets/`, or agent-specific metadata.

## Skills

- `issue-creator`: Research context and draft or create implementation-ready
  GitHub issues.
- `gh-implement-issue`: Implement a GitHub issue through a validated
  branch-to-PR workflow.

These are personally maintained skills. The repository intentionally excludes
copies of skills already provided by Codex, Claude Code, OpenAI-curated plugins,
or other agent runtimes.

## Repository Layout

```text
.
├── .claude-plugin/
│   ├── marketplace.json
│   └── plugin.json
├── skills/
│   ├── gh-implement-issue/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   └── issue-creator/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       └── references/
├── scripts/
│   ├── export-from-codex.sh
│   └── install.sh
├── AGENTS.md
├── LICENSE
├── README.md
└── managed-skills.txt
```

## Install With `npx skills`

List available skills:

```bash
npx skills add comfuture/agent-skills --list
```

Install one skill globally for Claude Code:

```bash
npx skills add comfuture/agent-skills --skill issue-creator -g -a claude-code -y
```

Install every skill for every detected agent:

```bash
npx skills add comfuture/agent-skills --skill '*' --agent '*' -y
```

The `skills` CLI also supports local paths while developing:

```bash
npx skills add . --list
```

## Install With GitHub CLI

GitHub CLI v2.90.0+ includes `gh skill`:

```bash
gh skill install comfuture/agent-skills issue-creator --agent claude-code --scope user
gh skill install comfuture/agent-skills gh-implement-issue --agent codex --scope user
```

Install every skill:

```bash
gh skill install comfuture/agent-skills --all --agent universal --scope user
```

Preview repository validity before publishing a release:

```bash
gh skill publish --dry-run
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

You can also use the interoperable `.agents/skills/` path through `npx skills`
or `gh skill`.

## Codex Local Helpers

Codex reads the open Agent Skills locations, and this repository also keeps
small helper scripts for syncing with a local `~/.codex/skills` setup.

Install managed skills into `~/.codex/skills`:

```bash
~/Project/agent-skills/scripts/install.sh
```

Export local edits from `~/.codex/skills` back to this repository:

```bash
~/Project/agent-skills/scripts/export-from-codex.sh issue-creator
git -C ~/Project/agent-skills diff -- skills/issue-creator
```

The script allowlist is `managed-skills.txt`. `--delete` is applied only inside
each managed skill directory, never against all of `~/.codex`.

## Maintenance Checks

Before committing a new or edited skill:

```bash
git grep -nE '(/Users/|gho_|sk-|BEGIN .*PRIVATE KEY|auth.json)' -- . ':!README.md' ':!scripts/*' ':!.gitignore'
npx skills add . --list
gh skill publish --dry-run
```

When adding new skills, keep the folder name, `name` frontmatter, and
`managed-skills.txt` entry in sync.

When publishing a Claude Code plugin update, bump the `version` in both
`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

## Security

Skills are executable agent instructions. Review third-party skills before
installing them, especially if they include scripts, shell commands, network
access, package installation, or credential handling.
