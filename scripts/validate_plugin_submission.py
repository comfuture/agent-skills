#!/usr/bin/env python3
"""Validate Develoop's public Marketplace submission payload."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "develoop"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"
TEST_CASES = PLUGIN / "submission" / "test-cases.json"
RELEASE_NOTES = PLUGIN / "submission" / "release-notes.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = json.loads(TEST_CASES.read_text(encoding="utf-8"))
    interface = manifest["interface"]

    require(manifest["name"] == "develoop", "plugin name mismatch")
    require(manifest["version"] == "0.1.0", "submission version mismatch")
    require(
        manifest["license"] == "MIT AND CC-BY-NC-SA-4.0",
        "mixed-license declaration mismatch",
    )
    require(manifest["author"]["name"] == "Changkyun Kim", "publisher mismatch")
    require(
        manifest["author"]["email"] == "comfuture@gmail.com",
        "publisher email mismatch",
    )
    require(interface["category"] == "Developer Tools", "category mismatch")
    require(
        1 <= len(interface["shortDescription"]) <= 30,
        "short description must be 1-30 characters",
    )
    require(bool(interface["longDescription"]), "long description is required")

    for key in ("websiteURL", "privacyPolicyURL", "termsOfServiceURL"):
        require(interface[key].startswith("https://"), f"{key} must use HTTPS")
    for key in ("composerIcon", "logo"):
        require((PLUGIN / interface[key]).is_file(), f"missing asset: {interface[key]}")

    marketing = " ".join(
        [
            manifest["description"],
            interface["shortDescription"],
            interface["longDescription"],
            *manifest["keywords"],
            *interface["defaultPrompt"],
        ]
    ).lower()
    require("writing" not in marketing, "writing-strategy is marketed in the manifest")
    require("strategy" not in marketing, "writing-strategy is marketed in the manifest")

    require(cases["plugin"] == "develoop", "test-case plugin mismatch")
    require(cases["submissionType"] == "skills_only", "submission type mismatch")
    require(len(cases["positive"]) == 5, "exactly five positive cases are required")
    require(len(cases["negative"]) == 3, "exactly three negative cases are required")
    all_cases = cases["positive"] + cases["negative"]
    require(len({case["id"] for case in all_cases}) == 8, "test IDs must be unique")
    for case in all_cases:
        for key in ("title", "prompt", "expectedBehavior", "validation"):
            require(bool(case.get(key)), f"{case['id']} is missing {key}")
        require(
            (ROOT / case["validation"]).is_file(),
            f"missing validation evidence for {case['id']}",
        )

    require(RELEASE_NOTES.is_file(), "release notes are required")
    require(RELEASE_NOTES.stat().st_size > 0, "release notes cannot be empty")

    sync = subprocess.run(
        [sys.executable, "scripts/sync_develoop_plugin.py", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    require(sync.returncode == 0, sync.stdout + sync.stderr)

    print("Develoop public-submission payload is valid (5 positive, 3 negative).")


if __name__ == "__main__":
    main()
