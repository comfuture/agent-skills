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
TEXT_FILENAMES = {
    "LICENSE",
}
TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}
OPENAI_INTERFACE_FIELDS = (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "composerIcon",
    "logo",
)
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


def validated_output_path(output: Path) -> Path:
    resolved = output.expanduser().resolve()
    try:
        resolved.relative_to(PLUGIN.resolve())
    except ValueError:
        return resolved
    raise SystemExit("--output must be outside plugins/develoop")


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


def openai_submission_manifest() -> dict[str, object]:
    manifest = json.loads((PLUGIN / MANIFEST).read_text(encoding="utf-8"))
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        raise SystemExit(".codex-plugin/plugin.json interface must be an object")

    missing = [field for field in OPENAI_INTERFACE_FIELDS if field not in interface]
    if missing:
        raise SystemExit(
            "OpenAI bundle interface is missing required fields: "
            + ", ".join(missing)
        )

    return {
        **manifest,
        "interface": {
            field: interface[field]
            for field in OPENAI_INTERFACE_FIELDS
        },
    }


def validate_payload(paths: list[Path]) -> None:
    openai_submission_manifest()

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


def archive_directories(paths: list[Path]) -> list[Path]:
    directories = {
        parent
        for path in paths
        for parent in path.parents
        if parent != Path(".")
    }
    return sorted(directories, key=lambda path: path.as_posix())


def is_text_payload(path: Path) -> bool:
    return path.name in TEXT_FILENAMES or path.suffix in TEXT_SUFFIXES


def write_zip(output: Path, paths: list[Path]) -> None:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative in archive_directories(paths):
            info = zipfile.ZipInfo(f"{relative.as_posix()}/", date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = ((stat.S_IFDIR | 0o755) << 16) | 0x10
            archive.writestr(info, b"")

        for relative in paths:
            source = PLUGIN / relative
            info = zipfile.ZipInfo(relative.as_posix(), date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.internal_attr = 1 if is_text_payload(relative) else 0
            permissions = 0o755 if source.stat().st_mode & 0o111 else 0o644
            info.external_attr = (stat.S_IFREG | permissions) << 16
            if relative == MANIFEST:
                payload = (
                    json.dumps(
                        openai_submission_manifest(),
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n"
                ).encode("utf-8")
            else:
                payload = source.read_bytes()
            archive.writestr(info, payload)


def main() -> None:
    args = parse_args()
    output = validated_output_path(args.output)
    paths = included_files()
    validate_payload(paths)
    write_zip(output, paths)
    print(f"Wrote {output} ({len(paths)} files)")


if __name__ == "__main__":
    main()
