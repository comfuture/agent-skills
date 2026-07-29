from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install.sh"


class InstallScriptTests(unittest.TestCase):
    def run_install(self, codex_home: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(codex_home)
        return subprocess.run(
            [str(INSTALL), "--no-agents", *arguments],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def make_legacy_issue_creator(self, codex_home: Path) -> Path:
        retired = codex_home / "skills" / "issue-creator"
        references = retired / "references"
        references.mkdir(parents=True)
        (retired / "SKILL.md").write_text(
            """---
name: issue-creator
description: Create high-quality GitHub issues or issue drafts from repository evidence.
---

# Issue Creator
""",
            encoding="utf-8",
        )
        for name in ("checklist.md", "issue-structure.md", "research-and-evidence.md"):
            (references / name).write_text(f"# {name}\n", encoding="utf-8")
        return retired

    def test_managed_install_archives_recognizable_issue_creator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            codex_home = Path(temporary)
            retired = self.make_legacy_issue_creator(codex_home)
            unrelated = codex_home / "skills" / "user-skill"
            unrelated.mkdir(parents=True)
            (unrelated / "SKILL.md").write_text("keep\n", encoding="utf-8")

            result = self.run_install(codex_home)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(retired.exists())
            self.assertTrue(
                (codex_home / "retired-skills" / "issue-creator" / "SKILL.md").is_file()
            )
            self.assertTrue((codex_home / "skills" / "gh-create-issue" / "SKILL.md").is_file())
            self.assertTrue((unrelated / "SKILL.md").is_file())

    def test_dry_run_reports_archive_without_moving_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            codex_home = Path(temporary)
            retired = self.make_legacy_issue_creator(codex_home)
            destination = codex_home / "retired-skills" / "issue-creator"

            result = self.run_install(codex_home, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(
                f"Would archive retired managed skill {retired}/ -> {destination}/",
                result.stdout,
            )
            self.assertTrue(retired.is_dir())
            self.assertFalse(destination.exists())

    def test_managed_install_preserves_unrecognized_issue_creator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            codex_home = Path(temporary)
            existing = codex_home / "skills" / "issue-creator"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text(
                "---\nname: issue-creator\n---\n\n# A different skill\n",
                encoding="utf-8",
            )

            result = self.run_install(codex_home)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((existing / "SKILL.md").is_file())
            self.assertIn("Preserving unrecognized skill directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
