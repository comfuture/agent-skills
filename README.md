# Agent Skills

Private, allowlisted source for portable Codex skills that are personally
maintained and not already provided by Codex, OpenAI-curated plugins, or system
skill bundles.

## Chosen Layout

This repository intentionally stays closer to `comfuture/agent-skills` than a
full `comfuture/codex-settings` mirror.

- Each immediate directory with a `SKILL.md` is a personally managed Codex
  skill.
- `managed-skills.txt` is the default install/export allowlist.
- `AGENTS.md` is the only managed global Codex instruction at the moment.
- `scripts/install.sh` copies managed content into `~/.codex`.
- `scripts/export-from-codex.sh` copies selected local skills back into this
  repository before committing.

Do not clone this repository directly as `~/.codex`. The real `~/.codex`
directory contains auth, machine state, caches, session history, generated
plugin data, browser integration state, and memories. Those should not be
versioned here unless they are first turned into scrubbed templates.

Do not vendor OpenAI/system/plugin-provided skills here just because they exist
under the local `~/.codex/skills` directory. If Codex already provides a skill
through the runtime, a plugin, or an installable bundle, use that source instead
of carrying a stale copy in this repository.

## Current Managed Skills

- `gh-implement-issue`
- `issue-creator`

These skills are synced from this machine with their `agents/` and `references/`
subfiles.

## Install On Another Machine

```bash
git clone git@github.com:comfuture/agent-skills.git ~/Project/agent-skills
~/Project/agent-skills/scripts/install.sh
```

Install only selected skills:

```bash
~/Project/agent-skills/scripts/install.sh issue-creator gh-implement-issue
```

Preview without writing:

```bash
~/Project/agent-skills/scripts/install.sh --dry-run
```

The installer uses `--delete` only inside each managed skill directory. It never
deletes the whole `~/.codex/skills` tree.

## Export Local Edits Back To The Repo

After editing a skill locally under `~/.codex/skills`, copy it back here before
committing:

```bash
~/Project/agent-skills/scripts/export-from-codex.sh issue-creator
git -C ~/Project/agent-skills diff -- issue-creator
```

Export every currently tracked root-level skill:

```bash
~/Project/agent-skills/scripts/export-from-codex.sh
```

Before committing a new or edited skill, check for machine-local paths, secrets,
and likely vendored/system skill copies:

```bash
git -C ~/Project/agent-skills grep -nE '(/Users/|gho_|sk-|BEGIN .*PRIVATE KEY|auth.json)'
cat ~/Project/agent-skills/managed-skills.txt
find ~/Project/agent-skills -maxdepth 2 -name SKILL.md -print
```

## Future Expansion

Prefer adding explicit, scrubbed payloads over broad mirrors:

- `profiles/` for optional Codex profiles or AGENTS variants.
- `templates/` for settings snippets that must be copied manually.
- `scripts/` for one-way sync helpers with narrow allowlists.

Keep private state out of Git by default.
