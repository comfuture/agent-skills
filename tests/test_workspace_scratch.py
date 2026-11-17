from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "skills/workspace-cleanup/scripts/scratch_file.py"


class ScratchCloseoutTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name).resolve()
        self.scratch = self.project / ".task"
        self.scratch.mkdir(mode=0o700)

    def invoke(self, action, path, *arguments, check=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), action, str(path), *arguments],
            check=False, capture_output=True, text=True,
        )
        if check:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_partial_closeout_and_retry_preserve_replacements_and_receipts(self):
        log = self.scratch / "build log"
        database = self.scratch / "test.sqlite"
        receipt = self.project / "verified.json"
        for path in (log, database, receipt):
            path.write_text("original")
        plan = [self.invoke("plan", path) for path in (log, database)]
        self.assertEqual([p.read_text() for p in (log, database, receipt)], ["original"] * 3)

        # Cancel after item one. Resume with the saved plan in a new process.
        self.assertEqual(self.invoke("remove", log, "--match", plan[0]["token"])["status"], "removed")
        self.assertEqual(self.invoke("remove", log, "--match", plan[0]["token"])["status"], "absent")
        database.rename(self.scratch / "original.sqlite")
        database.write_text("replacement")
        self.invoke("remove", database, "--match", plan[1]["token"], check=False)
        self.assertEqual(database.read_text(), "replacement")
        self.assertEqual(receipt.read_text(), "original")
        self.assertTrue(self.scratch.is_dir())

    def test_plan_is_bound_to_file_and_parent_identity(self):
        output = self.scratch / "output"
        output.write_text("old output")
        token = self.invoke("plan", output)["token"]
        self.scratch.rename(self.project / "old-directory")
        self.scratch.mkdir(mode=0o700)
        (self.project / "old-directory" / "output").rename(output)
        self.invoke("remove", output, "--match", token, check=False)
        self.assertEqual(output.read_text(), "old output")
        token = self.invoke("plan", output)["token"]
        output.write_text("new output")
        self.invoke("remove", output, "--match", token, check=False)
        self.assertEqual(output.read_text(), "new output")

    def test_shared_paths_links_and_directories_are_deferred(self):
        target = self.project / "preserved"
        target.write_text("receipt")
        alias = self.scratch / "link"
        alias.symlink_to(target)
        hardlink = self.scratch / "hardlink"
        os.link(target, hardlink)
        for candidate in (alias, hardlink, self.scratch):
            self.invoke("plan", candidate, check=False)
        linkdir = self.project / "alias"
        linkdir.symlink_to(self.scratch, target_is_directory=True)
        owned = self.scratch / "owned"
        owned.touch()
        self.invoke("plan", linkdir / "owned", check=False)
        token = self.invoke("plan", owned)["token"]
        self.scratch.chmod(0o770)
        self.invoke("remove", owned, "--match", token, check=False)
        self.assertTrue(owned.exists())
        self.assertEqual(target.read_text(), "receipt")
