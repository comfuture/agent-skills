#!/usr/bin/env python3
"""Build a deterministic, OpenAI-only Develoop submission ZIP."""

from __future__ import annotations

import argparse
import json
import stat
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "develoop"
MANIFEST = Path(".codex-plugin/plugin.json")
INCLUDED_ROOT_FILES = {
    MANIFEST,
    Path("LICENSE"),
    Path("README.md"),
}
INCLUDED_DIRECTORIES = {
    "assets",
    "skills",
}
IGNORED_NAMES = {
    ".DS_Store",
    "__pycache__",
}
IGNORED_SUFFIXES = {
    ".pyc",
}
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an OpenAI Marketplace submission ZIP for Develoop."
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination ZIP path.",
    )
    return parser.parse_args()


def included_files() -> list[Path]:
    paths = set(INCLUDED_ROOT_FILES)
    for directory in INCLUDED_DIRECTORIES:
        for path in (PLUGIN / directory).rglob("*"):
            if (
                path.is_file()
                and not path.is_symlink()
                and not IGNORED_NAMES.intersection(path.parts)
                and path.suffix not in IGNORED_SUFFIXES
            ):
                paths.add(path.relative_to(PLUGIN))
    return sorted(paths, key=lambda path: path.as_posix())


def validate_payload(paths: list[Path]) -> None:
    manifest = json.loads((PLUGIN / MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(manifest.get("interface"), dict):
        raise SystemExit(".codex-plugin/plugin.json interface must be an object")

    required = {
        MANIFEST,
        Path("LICENSE"),
        Path("README.md"),
    }
    missing = required.difference(paths)
    if missing:
        names = ", ".join(path.as_posix() for path in sorted(missing))
        raise SystemExit(f"OpenAI bundle is missing required files: {names}")

    skill_manifests = [
        path
        for path in paths
        if len(path.parts) == 3
        and path.parts[0] == "skills"
        and path.name == "SKILL.md"
    ]
    if not skill_manifests:
        raise SystemExit("OpenAI bundle must include at least one skills/*/SKILL.md")

    forbidden = {
        Path("plugin.json"),
        Path(".claude-plugin/plugin.json"),
    }
    unexpected = forbidden.intersection(paths)
    if unexpected:
        names = ", ".join(path.as_posix() for path in sorted(unexpected))
        raise SystemExit(f"OpenAI bundle includes compatibility manifests: {names}")


def write_zip(output: Path, paths: list[Path]) -> None:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative in paths:
            source = PLUGIN / relative
            info = zipfile.ZipInfo(relative.as_posix(), date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, source.read_bytes())


def main() -> None:
    args = parse_args()
    paths = included_files()
    validate_payload(paths)
    write_zip(args.output, paths)
    print(f"Wrote {args.output.resolve()} ({len(paths)} files)")


if __name__ == "__main__":
    main()
