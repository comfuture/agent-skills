#!/usr/bin/env python3
"""Synchronize and validate Develoop's self-contained plugin skill payload."""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STANDALONE_SKILLS = ROOT / "skills"
PLUGIN = ROOT / "plugins" / "develoop"
PLUGIN_SKILLS = PLUGIN / "skills"
EXPECTED_SKILLS = {
    "gh-autoreview-resolve",
    "gh-create-issue",
    "gh-implement-issue",
    "writing-strategy",
}
IGNORED_NAMES = {"__pycache__"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write or verify the Develoop plugin skill payload."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Refresh plugin copies.")
    mode.add_argument("--check", action="store_true", help="Verify exact parity.")
    return parser.parse_args()


def skill_names(root: Path) -> set[str]:
    if not root.is_dir():
        return set()
    return {
        path.name
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".") and not path.is_symlink()
    }


def relative_files(root: Path) -> set[Path]:
    if not root.is_dir():
        return set()
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and path.suffix != ".pyc"
        and not IGNORED_NAMES.intersection(path.parts)
    }


def symlinks(root: Path) -> set[Path]:
    if not root.is_dir():
        return set()
    return {path.relative_to(root) for path in root.rglob("*") if path.is_symlink()}


def write_payload() -> None:
    PLUGIN_SKILLS.mkdir(parents=True, exist_ok=True)
    for unexpected in skill_names(PLUGIN_SKILLS) - EXPECTED_SKILLS:
        shutil.rmtree(PLUGIN_SKILLS / unexpected)
    for name in sorted(EXPECTED_SKILLS):
        source = STANDALONE_SKILLS / name
        destination = PLUGIN_SKILLS / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    shutil.copy2(ROOT / "LICENSE", PLUGIN / "LICENSE")


def check_payload() -> list[str]:
    errors: list[str] = []

    for label, root in (
        ("standalone skills", STANDALONE_SKILLS),
        ("plugin skills", PLUGIN_SKILLS),
    ):
        names = skill_names(root)
        for missing in sorted(EXPECTED_SKILLS - names):
            errors.append(f"{label} missing {missing}")
        for unexpected in sorted(names - EXPECTED_SKILLS):
            errors.append(f"{label} has unexpected {unexpected}")
        for link in sorted(symlinks(root)):
            errors.append(f"{label} must not contain symlink: {link}")

    for name in sorted(EXPECTED_SKILLS):
        source = STANDALONE_SKILLS / name
        destination = PLUGIN_SKILLS / name
        source_files = relative_files(source)
        destination_files = relative_files(destination)
        for missing in sorted(source_files - destination_files):
            errors.append(f"plugin copy missing {name}/{missing}")
        for extra in sorted(destination_files - source_files):
            errors.append(f"plugin copy has extra {name}/{extra}")
        for relative in sorted(source_files & destination_files):
            if not filecmp.cmp(source / relative, destination / relative, shallow=False):
                errors.append(f"plugin copy differs: {name}/{relative}")

    license_path = PLUGIN / "LICENSE"
    if not license_path.is_file():
        errors.append("plugin LICENSE is missing")
    elif not filecmp.cmp(ROOT / "LICENSE", license_path, shallow=False):
        errors.append("plugin LICENSE differs from repository LICENSE")

    return errors


def main() -> None:
    args = parse_args()
    if args.write:
        write_payload()
    errors = check_payload()
    if errors:
        print("Develoop plugin payload validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Develoop plugin skills are complete, self-contained, and in sync.")


if __name__ == "__main__":
    main()
