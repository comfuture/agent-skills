#!/usr/bin/env python3
"""Find literal path references in candidate consumers without running project code."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import stat
from pathlib import Path


CONFIG_SUFFIXES = {
    ".cfg", ".cmake", ".conf", ".config", ".env", ".gradle", ".ini", ".json",
    ".jsonc", ".kts", ".lock", ".mod", ".pbxproj", ".properties", ".sh",
    ".toml", ".txt", ".work", ".xcconfig", ".xml", ".yaml", ".yml",
}
CONFIG_NAMES = {"Dockerfile", "Gemfile", "Makefile", "Podfile", ".npmrc", ".yarnrc"}
MAX_CONFIG_SIZE = 16 * 1024 * 1024


def is_config(path: Path) -> bool:
    return (
        path.suffix.lower() in CONFIG_SUFFIXES
        or path.name in CONFIG_NAMES
        or path.name == ".env"
        or path.name.startswith(".env.")
    )


def reference_pattern(candidate: Path, parent: Path, root: Path) -> re.Pattern[bytes]:
    spellings = {str(candidate), candidate.as_uri(), "file://" + str(candidate)}
    for base in (parent, root):
        relative = os.path.relpath(candidate, base)
        spellings.update((relative, "./" + relative))
    alternatives = b"|".join(re.escape(os.fsencode(s)) for s in spellings)
    return re.compile(rb"(?<![\w./-])(?:" + alternatives + rb")(?![\w.-])")


def read_config(parent_fd: int, name: str, info: os.stat_result) -> bytes:
    # Resolve against the directory being walked, even if a parent pathname moves.
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(info, opened):
            raise ValueError("config replaced during scan")
        if opened.st_size > MAX_CONFIG_SIZE:
            raise ValueError("large config")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(MAX_CONFIG_SIZE + 1)
        if len(data) > MAX_CONFIG_SIZE:
            raise ValueError("large config")
        return data
    finally:
        os.close(fd)


def scan(candidate: Path, roots: list[Path]) -> dict:
    hits = []
    incomplete = []

    def record_error(error: OSError) -> None:
        incomplete.append({"path": error.filename, "reason": error.strerror})

    for root in roots:
        if root == candidate or candidate in root.parents:
            raise ValueError(f"consumer root is inside the candidate: {root}")
        for directory, dirs, files, parent_fd in os.fwalk(root, onerror=record_error):
            parent = Path(directory)
            pattern = None
            for name in sorted(dirs + files):
                path = parent / name
                if name == ".git" or path == candidate:
                    if name in dirs:
                        dirs.remove(name)
                    continue
                try:
                    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode):
                        target = (parent / os.readlink(name, dir_fd=parent_fd)).resolve()
                        if target == candidate or candidate in target.parents:
                            hits.append({"path": str(path), "kind": "symlink"})
                    elif stat.S_ISREG(info.st_mode) and is_config(path):
                        if pattern is None:
                            pattern = reference_pattern(candidate, parent, root)
                        data = read_config(parent_fd, name, info)
                        for line_number, line in enumerate(io.BytesIO(data), start=1):
                            if pattern.search(line):
                                hits.append({"path": str(path), "line": line_number})
                except OSError as error:
                    incomplete.append({"path": str(path), "reason": error.strerror})
                except (ValueError, RuntimeError) as error:
                    incomplete.append({"path": str(path), "reason": str(error)})
    return {
        "candidate": str(candidate),
        "roots": [str(root) for root in roots],
        "references": hits,
        "incomplete": incomplete,
    }


def directory(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        raise argparse.ArgumentTypeError(f"expected an existing absolute directory: {value}")
    return path.resolve()


def candidate_directory(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or (path.exists() and not path.is_dir()):
        raise argparse.ArgumentTypeError(f"expected an absolute directory path: {value}")
    return path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=candidate_directory, required=True,
                        help="Exact provider path (may be absent on a post-removal check)")
    parser.add_argument("--root", type=directory, action="append", required=True,
                        help="Explicit consumer checkout or workspace to inspect (repeatable)")
    args = parser.parse_args()
    if not hasattr(os, "fwalk") or not hasattr(os, "O_NOFOLLOW"):
        parser.error("directory-relative no-follow scanning requires a POSIX host")
    try:
        report = scan(args.candidate, args.root)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    if report["incomplete"]:
        return 2
    return 1 if report["references"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
