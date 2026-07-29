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

    def test_managed_install_removes_retired_issue_creator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            codex_home = Path(temporary)
            retired = codex_home / "skills" / "issue-creator"
            unrelated = codex_home / "skills" / "user-skill"
            retired.mkdir(parents=True)
            unrelated.mkdir(parents=True)
            (retired / "SKILL.md").write_text("retired\n", encoding="utf-8")
            (unrelated / "SKILL.md").write_text("keep\n", encoding="utf-8")

            result = self.run_install(codex_home)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(retired.exists())
            self.assertTrue((codex_home / "skills" / "gh-create-issue" / "SKILL.md").is_file())
            self.assertTrue((unrelated / "SKILL.md").is_file())

    def test_dry_run_reports_migration_without_removing_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            codex_home = Path(temporary)
            retired = codex_home / "skills" / "issue-creator"
            retired.mkdir(parents=True)

            result = self.run_install(codex_home, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(
                f"Would remove retired managed skill {retired}/",
                result.stdout,
            )
            self.assertTrue(retired.is_dir())


if __name__ == "__main__":
    unittest.main()
