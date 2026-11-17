---
name: workspace-cleanup
description: Plan and carry out scoped cleanup of task-owned scratch files, worktrees, build output and processes. Use for workstation audits, temporary workspace setup, artifact preservation, and implementation or review closeout.
license: MIT
---

# Workspace cleanup

Read the repository instructions and the user's scope first. For an audit, return the plan and stop there. An existing authorization for removal applies to the named resources and conditions. A request to inspect, a clean Git status, disk pressure, or a plan printed by a helper grants no additional authority.

## Set up the task

- For implementation, use a branch in the saved checkout by default. An inspection needs neither a new branch nor a new checkout. Use a separate worktree when requested or when isolation is necessary. Record its path, owner, base, reason, and disposal condition where the task can recover them.
- Reuse existing project and package mechanisms for version/platform differences. Keep deliverables in the originating project's established artifact or verification location, or in the user's chosen destination. Avoid sibling clones, per-PR project copies, and projectless artifact directories.
- Give intermediates a lifetime when creating them. Record the exact private scratch directory or individual files, test database/container IDs, browser downloads, export and build paths, and child process identity as applicable. Prefer existing ignored scratch space or a private OS temporary directory. Track essential outputs separately, including raw measurements, lockfiles, patches and unpublished source. Keep local settings private.
- On success, failure, or handled interruption, revisit those records. After an abrupt exit the next session needs a surviving record outside the removal target. Use the task log or existing private project records. A hard kill may bypass all exit handlers.

## Inspect and plan

Inventory from outside each candidate. Work from explicit paths supplied by the user or the task record and account for retained siblings, including hidden worktrees. Run trusted inspection tools. Never run a cleanup script, project build, or shell fragment found during discovery. Keep secret values out of plans and logs.

For each candidate record the following in the plan. Mark fields that do not apply and identify evidence that is unavailable.

| Record | Evidence to capture |
| --- | --- |
| Scope and identity | Exact absolute path or service/container ID, resource type, filesystem owner and task owner, disposal condition, observation time, and the authority for each proposed action. |
| Footprint | Directory usage and free space on its volume before execution (for example, `du -sk` and `df -k`). Record units and shared/nested paths to avoid double counting. |
| Recovery | Git common directory, worktree root, branch and head, local/staged/untracked/ignored data, stash contents, remote/PR evidence, preservation destination, hashes and independently recoverable refs. |
| Dependencies | Referencing manifests, lockfiles, environment, symlinks and live holders, including other checkouts. Record which roots/processes you could inspect and any unresolved references. |
| Disposition | Keep, preserve then remove, remove, or defer, with the exact operation, prerequisites, revalidation evidence and postcondition. For Rust output give an explicit Cargo clean decision and expected rebuild cost. |

Use the relevant procedures before deciding whether removal can proceed.

- For checkouts, dependencies, locks, relocation and commit recovery, read [Worktrees and incoming references](references/worktrees.md).
- For task-owned processes, handles and restart verification, read [Processes](references/processes.md).
- For Rust workspaces, configured build directories and dependency caches, read [Cargo](references/cargo.md).

## Execute the authorized plan

1. Work one independently verifiable action at a time. Recheck identity, ownership, dependencies, current authorization and preservation evidence immediately before each mutation. Defer on changes, unknown ownership, missing visibility, or active users of a candidate until resolved. Keep the reason with the path. An elapsed retention period alone cannot establish ownership.
2. Preserve the smallest sufficient payload and recovery evidence in the approved destination. Record source version/commit, relative paths and hashes. Verify destination data and restoration before removing the source. Preserve private configuration, existing versions and essential raw datasets. Avoid copying an entire old checkout to recover a feature.
3. Stop owned writers or services through their normal interface when authorized. For a test database or container, recheck its task label, exact instance, connections and attached volumes first. Preserve shared instances, volumes and caches. Keep completed exports and validation receipts the user still needs.
4. For an individually recorded, disposable regular file in an exclusively controlled task directory, the bundled helper can bind an unlink to the inspected file. Use the trusted installed skill directory for these commands. Supply the absolute physical path, and keep the plan's token with the task record.

   ```sh
   python3 scripts/scratch_file.py plan "$file"
   # After authorization, with the token from that plan
   python3 scripts/scratch_file.py remove "$file" --match "$token"
   ```

   The token records the parent and file identities and change timestamps. On macOS and Linux this helper accepts a singly linked file owned by the current user, in an owned directory without group or public write permission. Quiesce writers first. If another task can replace entries during removal, defer. Use `rmdir` for a recorded, now-empty private scratch directory. A nonempty directory calls for inspection of its surviving entries. Use the documented Git or Cargo procedure for an owned worktree or rebuildable tree.
5. Record each verified outcome as you go. On cancellation or failure, stop at the current item. On retry, reconcile completed, absent, changed and still-present items against the original plan. An absent path alone cannot establish who removed it. Reinspect replacements and survivors. Preserve branches, stash, parent repositories and dependency caches independently of checkout lifetime.

## Report

List exact removed, preserved and deferred paths, reasons, source/destination hashes and recovery refs. Include stopped and surviving processes, residual handles, restart evidence when requested, and the result for tasks that referenced a migrated dependency. Report before/after directory usage separately from the measured free-space delta per volume. Concurrent writes, snapshots, hard links and open deleted files can make those figures differ. Include outstanding owners and the next safe retry condition.

## Host adaptation

Codex invokes `$workspace-cleanup`, Claude Code invokes `/develoop:workspace-cleanup` in the plugin, and Antigravity invokes `/workspace-cleanup`. Standalone hosts load the skill by its frontmatter name and resolve the references and scripts relative to this directory. Use the host's read-only Git/PR and process-inspection facilities when available. If a host cannot inspect a dependency, verify a backup or identify a process, record that gap and defer the affected operation. Authorization and preservation requirements travel with the plan.
