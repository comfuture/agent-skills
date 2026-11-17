#!/usr/bin/env python3
"""Inspect one scratch file, or unlink the exact entry named in a reviewed plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path


def scratch_file(path: Path, expected: str | None) -> dict:
    if not path.is_absolute() or path.parent.resolve(strict=True) != path.parent:
        raise ValueError("use an absolute path with physical parent directories")
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parent = os.fstat(directory)
        if parent.st_uid != os.geteuid() or parent.st_mode & 0o022:
            raise ValueError("requires an owned directory without group or public write access")
        try:
            item = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            if expected is None:
                raise
            return {"path": str(path), "status": "absent"}
        if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1 or item.st_uid != os.geteuid():
            raise ValueError("requires a singly linked regular file owned by the current user")

        identity = {
            "path": str(path),
            "parent": [parent.st_dev, parent.st_ino],
            "file": [item.st_dev, item.st_ino],
            "uid": item.st_uid,
            "mode": item.st_mode,
            "bytes": item.st_size,
            "mtime_ns": item.st_mtime_ns,
            "ctime_ns": item.st_ctime_ns,
        }
        token = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        if expected is None:
            return {**identity, "token": token}
        if token != expected:
            raise ValueError("the planned entry changed; inspect again")
        # The caller must have exclusive control of this directory. POSIX unlink
        # has no atomic compare-inode-and-unlink operation.
        os.unlink(path.name, dir_fd=directory)
        return {"path": str(path), "status": "removed"}
    finally:
        os.close(directory)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    plan = actions.add_parser("plan", help="print a metadata token for one scratch file")
    plan.add_argument("path", type=Path)
    remove = actions.add_parser("remove", help="unlink a previously planned and authorized file")
    remove.add_argument("path", type=Path)
    remove.add_argument("--match", required=True, help="token recorded during planning")
    args = parser.parse_args()
    try:
        result = scratch_file(args.path, getattr(args, "match", None))
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
