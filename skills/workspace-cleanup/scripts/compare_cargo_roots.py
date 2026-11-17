#!/usr/bin/env python3
"""Compare explicit Cargo output roots against known users and protected paths."""

import argparse
import json
from pathlib import Path


def absolute_path(value):
    path = Path(value)
    if not path.is_absolute():
        raise argparse.ArgumentTypeError("supply an absolute path")
    return path.resolve()


def contains(root, path):
    # samefile also detects case aliases on case-insensitive volumes.
    for ancestor in (path, *path.parents):
        if ancestor == root:
            return True
        try:
            if root.samefile(ancestor):
                return True
        except FileNotFoundError:
            continue
    return False


def overlaps(left, right):
    return contains(left, right) or contains(right, left)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "target-dir", "build-dir", "cargo-home", "rustup-home"):
        parser.add_argument("--" + name, required=True, type=absolute_path)
    parser.add_argument("--other-output", action="append", type=absolute_path, default=[],
                        help="resolved output of another workspace (repeatable)")
    parser.add_argument("--busy-output", action="append", type=absolute_path, default=[],
                        help="output used by an active build (repeatable)")
    parser.add_argument("--removing-worktree", type=absolute_path,
                        help="worktree root already planned for removal")
    args = parser.parse_args()

    outputs = {args.target_dir, args.build_dir}
    reasons = []
    for path in sorted(outputs):
        if contains(path, args.workspace):
            reasons.append(f"{path} contains the workspace {args.workspace}")
        for kind, roots in (("protected home", [args.cargo_home, args.rustup_home]),
                            ("another workspace output", args.other_output),
                            ("active build output", args.busy_output)):
            for root in roots:
                if overlaps(path, root):
                    reasons.append(f"{path} overlaps {kind} {root}")

    if reasons:
        assessment = "defer"
    elif args.removing_worktree and all(contains(args.removing_worktree, p) for p in outputs):
        assessment = "redundant"
        reasons.append("Both output roots fall under the proposed worktree removal.")
    else:
        assessment = "review"
        reasons.append("Check ownership, incoming references, handles and evidence before selecting a scope.")
    print(json.dumps({"target_dir": str(args.target_dir), "build_dir": str(args.build_dir),
                      "assessment": assessment, "reasons": reasons}, indent=2))


if __name__ == "__main__":
    main()
