# Worktrees, consumers and recovery

## Inspect without changing Git state

Start in each known project. Record the absolute saved checkout and Git common directory (`git rev-parse --path-format=absolute --git-common-dir`). Run `git worktree list --porcelain -z` there to find registered checkouts, including hidden, nested, detached, locked and missing ones. Enumerate neighboring projects and their worktrees inside the user's scope too. Each repository has its own registry. Check for nested repositories, submodules, mounts and directory symlinks before treating a directory as disposable.

For each candidate, record its exact path, owner/task, size, branch or detached HEAD, commit, lock reason, local branches and upstreams. Run the following inspection commands in a trusted checkout.

```sh
git --no-optional-locks -c core.fsmonitor=false status --porcelain=v1 -z --untracked-files=all --ignored
git ls-files -z --others --ignored --exclude-standard
git for-each-ref --format='%(refname) %(objectname) %(upstream)' refs/heads refs/remotes
git stash list --format='%gd %H'
```

Run these in the intended checkout and parse NUL-delimited paths. Account for staged and unstaged content, conflicts, in-progress Git operations, ignored directories, nested repositories, sparse checkouts and local-only submodule changes as applicable. `--no-optional-locks` avoids an index refresh. Git may invoke configured clean filters or helper programs when inspecting a working tree. Review local/included config and attributes before using commands that could execute them, and defer if the repository or its tooling is untrusted. Keep settings and credential values out of the report.

Stashes are shared across linked worktrees. Inspect relevant entries by **object ID**, including their base, index and optional untracked snapshot. Compare the actual paths, modes and blob IDs with the candidate's HEAD, index and working files. Leave the stash intact. Record partial, older or unrelated stash contents explicitly.

Establish remote state with a trusted read-only service/API or `git ls-remote` against a verified remote and exact refs. A fetch can update local refs and `FETCH_HEAD` during an audit. Record the PR URL, state, head, base and merge OIDs. A matching remote branch plus retained local branch can make a clean worktree disposable even with its PR open. For a squash merge, match the original head to the merged PR and its merge commit and inspect the landed changes against the intended base. An ancestry check alone misses equivalent squashed changes. Landed content and recovery of exact historical commits are separate questions. If upstream evidence is unavailable, mark it unknown.

## Trace consumers before removing a provider

Inspect retained checkouts of *all* relevant repositories, including hidden sibling worktrees. Search their working copies, untracked/ignored manifests and lockfiles, build settings, environment files and symlinks. Include nested packages and local overrides. Treat even a clean, uploaded provider as **deferred** while a consumer still resolves a dependency through its path.

Use the installed skill's read-only helper for literal path evidence. Pass exact absolute directories for the provider and each suspected consumer.

```sh
python3 "$skill_dir/scripts/inspect_worktrees.py" --candidate "$provider" \
  --root "$saved_consumer" --root "$hidden_consumer"
```

The helper walks the supplied roots (including hidden children), skips Git metadata and the provider itself, examines symlink targets and common text config formats up to 16 MiB, and reports paths and line numbers. It uses POSIX directory descriptors and opens regular config files without following symlinks. A directory symlink can be reported as a reference. Its children are outside the walk. Supply relevant external config roots separately. Exit 1 means matches need investigation. Exit 2 means coverage is incomplete or arguments failed. Exit 0 means no literal hit in the covered inputs. Inspect the actual configuration, package-relative path bases, runtime environment, path aliases, generated/oversize configs and any includes outside the scan before authorizing removal. Interpolated, escaped and tool-specific references require their native resolution rules. It never sources environment files, runs a build or calls discovered cleanup scripts.

For a confirmed dependency, identify the intended durable replacement and its revision. Within authorization update the exact override and lock entry, preserving the consumer's other edits. Compare the resolved path and content/revision from the consumer before and after the move, using its normal offline read-only resolver when available. After removal repeat the literal search with the former provider path to catch new or dangling references. If migration or verification is outside the task's authorization, retain the provider.

## Preserve and relocate

1. Separate committed history from staged/working bytes and ignored local evidence. Select explicit paths, modes, symlink targets, versions and hashes. Identify the destination under its originating project or the user's chosen location. Check for destination collisions (including staged changes and ignored files) and defer any unresolved overwrite.
2. Retain a named branch at the exact local-only tip, including for a detached HEAD. During authorized preservation use a verified remote branch or create a Git bundle of the full retained ref at the chosen destination. For a bundle, record its SHA-256 and advertised refs. Run `git bundle verify` and recover the named ref in an isolated empty repository, then check its exact tip and required objects. An incremental bundle needs its prerequisites. Verification in the source repository alone can mask missing bases. Account separately for submodule and external/LFS objects and uncommitted files.
3. Record the primary checkout's branch OID, index/working changes, application/package version, private configuration and runtime state. For an authorized migration, a new branch off the primary HEAD can retain the original branch ref. Restore only the reviewed payload. For vetted, collision-free tracked paths, `git --literal-pathspecs restore --source="$tip" --worktree -- "$path"` selects a committed version. Preserve separately any newer working/index data needed there. Keep secrets in the intended private storage. Compare hashes and modes at the destination and verify the application version, original refs, unrelated edits and stash OIDs before releasing the source.

## Apply one planned removal

Recheck candidate identity (exact path, filesystem identity, Git common dir, branch/HEAD), locks, working and ignored data, consumer resolution, process handles and recovery evidence immediately before the operation. Pause on drift. Keep the saved checkout and any parent containing a repository. Quiesce owners with write access because another task can write after a successful status check.

From a surviving checkout run `git worktree remove "$candidate"` only on the authorized, quiescent linked worktree. Handle a refusal by inspecting the reason. Unlock only an individually identified stale lock under the applicable authorization. Preserve or explicitly handle every local byte first, including ignored files that ordinary removal can discard. Leave unrelated registrations, branches, stash, parent directories and remotes alone. Check the surviving checkout's worktree registry, retained refs, backup recovery, dependency resolution and surviving local state afterward. On retry after interruption, re-read the registry and filesystem and reconcile any mismatch before acting again.
