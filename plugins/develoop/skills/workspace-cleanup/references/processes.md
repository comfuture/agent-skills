# Check process ownership and open handles

Start from the task or service manager's record of the session that created the
candidate. Capture its host, user, launch time, session/job ID, control channel,
CLI/broker and expected children. Read the exact worktree's lock reason and
owner metadata. A lock can protect an offline volume or another host. A
missing local PID or a PID whose start time differs is grounds to investigate
the lock while leaving both it and the current occupant alone.

## Inspect

On macOS or Linux with `ps` and `lsof`, run the bundled helper from a retained
directory. Supply the exact absolute directory and suspected owner PID. Add
`--protect-pid` for active sessions that run outside the invoking shell's
ancestry.

```sh
python3 "$skill_dir/scripts/inspect_processes.py" --path "$candidate" \
  --owner-pid "$broker_pid" --protect-pid "$current_cli_pid"
```

`owner_tree` includes the suspected owner and its observed descendants.
`owner_ancestry` traces that process back to its visible launchers.
Supply `--expected-start` with a previously recorded `start` value to
check for PID reuse. A false match result disqualifies the process. A null
result means the recorded or observed start was unavailable.
`protected_ancestry` includes the helper's own chain and supplied sessions'
ancestors. `visible_path_holders` lists PIDs seen by a recursive `lsof +D`
query. When refining the query on a build that advertises device-cache
support in `lsof -h`, include `-Di` to suppress cache writes. Inspect their
working directories and descriptors locally, e.g.
`lsof -nP -a -p "$pid" -d cwd` and `lsof -nP -a -p "$pid" +D "$candidate"`.
Keep command arguments, environment values and private filenames out of
published evidence.

Correlate each row with task-manager ownership and active jobs. Hold the
candidate if an owner tree intersects protected ancestry, shares a broker with
another task, has new or unexplained children, or an unrelated process holds
the path. A matching PID, executable and second-resolution start time can
still collide. Prefer a launch handle, service instance ID or authenticated
control channel associated with the recorded task. Confirm reparented children
against recorded identities. Preserve their identities across snapshots.

These are observations available to the invoking user. PID namespaces, macOS
permissions, inaccessible files, unlinked open files and mount boundaries can
hide handles. `+D` can be slow on a large tree. A warning, a timeout, an
unobserved protected session, or an inaccessible owner calls for a host-native
process/handle inspector or deferral. On a host without these tools, obtain
equivalent start/ancestry, job ownership and handle evidence there. An empty
list alone cannot establish exclusive use.
The helper exits nonzero for inspection errors, warnings or unobserved
protected PIDs. Keep any partial JSON for diagnosis.

## Stop only within the authorized plan

Immediately before stopping a task, repeat the owner, active-job, identity
and handle checks. Prefer its graceful shutdown channel. Wait for the known
children to exit and the broker to reap them. If the channel times out, check
each survivor again. Use a targeted graceful signal only with independently
verified identity and ownership. Reserve stronger escalation for a verified
survivor within the authorization. Defer when the host cannot safely target
the same process instance. Avoid name, group or PID-only signalling.

Repeat the directory-wide handle scan from outside the candidate after
shutdown. Compare recorded children by identity even if they have a new
parent. Record unrelated or inaccessible holders and keep their paths.
Resolve a stale worktree lock through the owning repository's exact worktree
only after establishing why it was set, confirming exclusive use and checking
authorization for unlocking.

When a restart check is needed, start a fresh instance in a retained
directory using its documented idle startup or initialization handshake. Use
a bounded readiness check and shut the probe down gracefully. Resuming the
old session, sending a prompt or replaying jobs would run additional work.
If the CLI has no idle probe, record restart as unverified. Report the
identities stopped, lingering handles, readiness result, released probe and
continued availability of the original active session.
