#!/usr/bin/env python3
"""Describe a suspected task process tree and visible holders of one directory."""

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import subprocess


def process_table():
    # comm excludes arguments and environment values that may contain credentials.
    result = subprocess.run(
        ["ps", "-ax", "-o", "pid=,ppid=,uid=,lstart=,comm="],
        capture_output=True, text=True, errors="replace", check=True,
        env={**os.environ, "LC_ALL": "C", "TZ": "UTC"},
    )
    table = {}
    for line in result.stdout.splitlines():
        pid, parent, uid, day, month, date, time, year, command = line.split(None, 8)
        table[int(pid)] = {
            "pid": int(pid), "ppid": int(parent), "uid": int(uid),
            "start": " ".join((day, month, date, time, year)), "command": command,
        }
    return table


def path_holders(directory):
    # lsof can return 1 for no visible matches. Keep diagnostics and avoid a
    # system-wide listing of unrelated open filenames.
    try:
        help_text = subprocess.run(
            ["lsof", "-h"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", timeout=5, env={**os.environ, "LC_ALL": "C"},
        ).stdout
        # Some builds advertise a writable device cache. Ignore it during audits.
        cache_option = ["-Di"] if "-D" in help_text else []
        result = subprocess.run(
            ["lsof", *cache_option, "-nP", "-Fp", "+D", str(directory)],
            capture_output=True, text=True, errors="replace", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return [], str(error)
    pids = sorted({int(line[1:]) for line in result.stdout.splitlines() if line.startswith("p")})
    warning = result.stderr.strip()
    if result.returncode not in (0, 1) and not warning:
        warning = f"lsof exited with status {result.returncode}"
    return pids, warning


def ancestry(table, pids):
    result = set()
    for pid in pids:
        while pid in table and pid not in result:
            result.add(pid)
            pid = table[pid]["ppid"]
    return result


def inspect(directory, owner_pid, protect_pids, expected_start):
    holders, warning = path_holders(directory)
    table = process_table()
    protected = ancestry(table, [os.getpid(), *protect_pids])
    owner_ancestry = ancestry(table, [owner_pid])

    children = defaultdict(list)
    for pid, row in table.items():
        children[row["ppid"]].append(pid)
    descendants = set()
    pending = [owner_pid] if owner_pid in table else []
    while pending:
        pid = pending.pop()
        if pid not in descendants:
            descendants.add(pid)
            pending.extend(children[pid])

    relevant = protected | owner_ancestry | descendants | set(holders)
    observed_start = table.get(owner_pid, {}).get("start")
    start_matches = None
    if observed_start and expected_start:
        start_matches = observed_start == expected_start
    return {
        "directory": str(directory),
        "owner_pid": owner_pid,
        "owner_tree": sorted(descendants),
        "owner_ancestry": sorted(owner_ancestry),
        "owner_start_matches": start_matches,
        "protected_ancestry": sorted(protected),
        "unobserved_protected_pids": sorted(set(protect_pids) - table.keys()),
        "visible_path_holders": holders,
        "handle_scan_warning": warning,
        "processes": [table[pid] for pid in sorted(relevant & table.keys())],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, type=Path, help="Absolute candidate directory")
    parser.add_argument("--owner-pid", required=True, type=int, help="Suspected broker or CLI PID")
    parser.add_argument("--protect-pid", action="append", default=[], type=int,
                        help="Additional live session to protect (repeatable)")
    parser.add_argument("--expected-start", help="Owner start value from an earlier snapshot")
    args = parser.parse_args()
    if not args.path.is_absolute() or not args.path.is_dir():
        parser.error("--path must name an existing absolute directory")
    if any(pid < 1 for pid in [args.owner_pid, *args.protect_pid]):
        parser.error("PIDs must be positive")
    try:
        snapshot = inspect(args.path.resolve(strict=True), args.owner_pid,
                           args.protect_pid, args.expected_start)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        parser.exit(1, f"Incomplete process snapshot: {error}\n")
    print(json.dumps(snapshot, indent=2))
    if snapshot["handle_scan_warning"] or snapshot["unobserved_protected_pids"]:
        parser.exit(1)


if __name__ == "__main__":
    main()
