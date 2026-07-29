# Develoop

Develoop closes the loop on GitHub work with portable Agent Skills for
evidence-backed issue creation, issue-to-PR implementation, and bounded
automated-review resolution.

The same workflows are packaged for Codex, Claude Code, Antigravity, and the
open Agent Skills layout. Each host uses its own GitHub integration, shell,
browser, delegation, and approval capabilities without changing the workflow
contract.

Public information, support, and policies are available at
[develoop.comfuture.chatgpt.site](https://develoop.comfuture.chatgpt.site).

## Core Skills

- `gh-create-issue`: Research context and create an implementation-ready
  GitHub issue or reviewed issue draft.
- `gh-implement-issue`: Implement one GitHub issue through a narrow branch,
  atomic commits, validation, push, and an accurate pull request.
- `gh-autoreview-resolve`: Run a bounded automated-review loop, validate
  findings, resolve in-scope feedback, and prevent review scope creep.

The repository also includes `writing-strategy`, a separately licensed writing
structure skill. It remains installable and bundled, but is intentionally not
part of Develoop's product description, search keywords, or starter prompts.

## Install Develoop

### OpenAI / Codex

Install Develoop from the OpenAI Curated Directory:

[Open Develoop in the OpenAI Plugins Directory](https://chatgpt.com/plugins/plugins_6a69ee33e3048191ab7da89ec70dbbe2)
and select **Add** after signing in.

Start a new task after installation. Codex invokes skills as
`$gh-create-issue`, `$gh-implement-issue`, and
`$gh-autoreview-resolve`.

### Claude Code

```bash
claude plugin marketplace add comfuture/agent-skills
claude plugin install develoop@develoop --scope user
```

Reload plugins or start a new session. Claude Code invokes namespaced skills
such as `/develoop:gh-create-issue`.

For local plugin development:

```bash
claude --plugin-dir plugins/develoop
```

### Antigravity

```bash
agy plugins install https://github.com/comfuture/agent-skills
agy plugin list
```

Antigravity invokes installed skills by their frontmatter names, such as
`/gh-implement-issue`.

## Install Standalone Skills

The root `skills/` directory preserves the open Agent Skills structure for
hosts that do not install plugins.

List the available skills:

```bash
npx skills add comfuture/agent-skills --list
```

Install every skill for every detected agent:

```bash
npx skills add comfuture/agent-skills --skill '*' --agent '*' -y
```

Install one skill for a specific host:

```bash
npx skills add comfuture/agent-skills --skill gh-create-issue -g -a claude-code -y
```

GitHub CLI v2.90.0 or later can also install skills:

```bash
gh skill install comfuture/agent-skills gh-create-issue --agent claude-code --scope user
gh skill install comfuture/agent-skills gh-implement-issue --agent codex --scope user
gh skill install comfuture/agent-skills gh-autoreview-resolve --agent universal --scope user
```

For a user-level Codex mirror, the repository helper copies only the
allowlisted skills from `managed-skills.txt`:

```bash
scripts/install.sh
scripts/install.sh gh-create-issue
scripts/install.sh --dry-run
```

## Safety

Review the skills before installing them. They may read local repositories and
GitHub state or, when the user authorizes it, create issues, branches, commits,
pull requests, review replies, thread resolutions, and merges.

Develoop does not operate a backend or receive GitHub credentials. Your agent
host, GitHub integration, GitHub CLI, and model provider process data under
their own policies. Use least-privilege credentials, protect unrelated work,
review diffs and remote writes, and remove secrets or private data from public
issues and comments.

This repository is personally maintained and provided without support
guarantees or warranty. Pin a tag or commit when repeatability matters.

## Package Layout

- `skills/`: canonical standalone Agent Skills.
- `plugins/develoop/`: self-contained Codex, Claude Code, and Antigravity
  plugin payload.
- `.agents/plugins/marketplace.json`: Codex repository marketplace.
- `.claude-plugin/marketplace.json`: Claude Code repository marketplace.
- `scripts/sync_develoop_plugin.py`: exact standalone-to-plugin sync and parity
  check.
- `scripts/build_develoop_openai_bundle.py`: deterministic OpenAI submission
  ZIP that excludes Claude Code and Antigravity compatibility manifests.
- `website/`: public product, support, privacy, terms, and release pages.

When a canonical standalone skill changes, refresh and verify the plugin copy:

```bash
python3 scripts/sync_develoop_plugin.py --write
python3 scripts/sync_develoop_plugin.py --check
```

If you edit a managed skill under `~/.codex/skills`, export it back before
refreshing the plugin:

```bash
scripts/export-from-codex.sh gh-create-issue
python3 scripts/sync_develoop_plugin.py --write
```

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 python3 skills/gh-autoreview-resolve/scripts/inspect_review_state.py --self-test
python3 scripts/sync_develoop_plugin.py --check
python3 scripts/build_develoop_openai_bundle.py \
  --output /tmp/develoop-openai.zip
npx skills add . --list
gh skill publish --dry-run
claude plugin validate plugins/develoop --strict
claude plugin validate . --strict
agy plugin validate plugins/develoop
```

Codex plugin validation uses the validator bundled with `plugin-creator` and
requires PyYAML:

```bash
uv run --with PyYAML python \
  /path/to/plugin-creator/scripts/validate_plugin.py \
  plugins/develoop
```

## License

Repository code, scripts, supporting metadata, and the three GitHub workflow
skills are licensed under MIT unless otherwise stated. See `LICENSE`.

The `writing-strategy` skill content is licensed separately under
CC-BY-NC-SA-4.0. See `skills/writing-strategy/LICENSE.md`.
