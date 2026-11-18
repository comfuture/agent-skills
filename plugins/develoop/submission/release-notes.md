# Develoop 0.1.4 — Workspace cleanup

Use `workspace-cleanup` to see which temporary worktrees, scratch files,
build products and processes a task left behind. An audit reports what still
depends on each path, what to preserve, and which actions are authorized.

- Find incoming references from hidden worktrees and preserve local-only
  commits, private configuration and verification artifacts before removal.
- Inspect process ownership and open files before stopping a task. Check
  for shared Cargo output and active builds while preserving dependency caches.
- Recheck each scratch file against its recorded identity before removal so an
  interrupted cleanup can resume without deleting a replacement file.
- Account for temporary resources at the end of implementation and review.

The package includes six skills for Codex, Claude Code, Antigravity and
standalone Agent Skills hosts.
