"""Exercise worktree inspection and selected removal recipes in local-only repos."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSPECT = ROOT / "skills/workspace-cleanup/scripts/inspect_worktrees.py"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(tree):
    """Include Git indexes, lock files, refs, stash, remote, paths and working bytes."""
    result = {}
    for path in tree.rglob("*"):
        if path.is_symlink():
            value = os.readlink(path)
        elif path.is_file():
            value = sha256(path)
        else:
            value = None
        result[str(path.relative_to(tree))] = (path.lstat().st_mode, value)
    return result


class WorktreeFixtures(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.env = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.root),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_ALLOW_PROTOCOL": "file",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
        self.saved = self.root / "project"
        self.candidate = self.root / "SDK checkout"
        self.remote = self.root / "remote.git"
        self.git(self.root, "init", "--bare", str(self.remote))
        self.git(self.root, "init", "-b", "main", str(self.saved))
        (self.saved / "version").write_text("1.0\n")
        (self.saved / ".gitignore").write_text(".env*\n.runtime\nreceipts/\n")
        self.git(self.saved, "add", ".")
        self.git(self.saved, "commit", "-m", "initial")
        self.base = self.git(self.saved, "rev-parse", "HEAD")
        self.git(self.saved, "remote", "add", "origin", str(self.remote))
        self.git(self.saved, "push", "origin", "main")
        self.git(self.saved, "worktree", "add", "-b", "sdk", str(self.candidate))

    def git(self, cwd, *args):
        result = subprocess.run(
            ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
             "-c", f"core.hooksPath={os.devnull}", "-C", cwd, *args],
            env=self.env, check=True, capture_output=True, text=True,
        )
        return result.stdout.rstrip("\n")

    def inspect(self, *roots, expected_code):
        command = [sys.executable, "-B", INSPECT, "--candidate", self.candidate]
        for root in roots:
            command.extend(["--root", root])
        result = subprocess.run(command, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_plan_preserves_dirty_ignored_stash_lock_indexes_and_remote(self):
        (self.saved / "old.txt").write_text("stashed")
        self.git(self.saved, "stash", "push", "-u", "-m", "old experiment")
        (self.candidate / "version").write_text("staged")
        self.git(self.candidate, "add", "version")
        (self.candidate / "version").write_text("unstaged")
        (self.candidate / ".env.local").write_text("private setting")
        (self.candidate / "raw.csv").write_text("measurement")
        self.git(self.saved, "worktree", "lock", "--reason", "retained by fixture",
                 str(self.candidate))
        before = snapshot(self.root)
        registrations = self.git(self.saved, "worktree", "list", "--porcelain", "-z")
        self.assertIn("locked retained by fixture\0", registrations)
        common = self.git(self.candidate, "rev-parse", "--path-format=absolute", "--git-common-dir")
        self.assertEqual(Path(common), self.saved / ".git")
        state = self.git(self.candidate, "--no-optional-locks", "-c", "core.fsmonitor=false",
                         "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored")
        self.assertEqual(set(state.split("\0")[:-1]), {"MM version", "?? raw.csv", "!! .env.local"})
        stash = self.git(self.candidate, "stash", "list", "--format=%H")
        self.assertEqual(self.git(self.candidate, "show", f"{stash}^3:old.txt"), "stashed")
        self.assertIn(self.base, self.git(self.saved, "ls-remote", "origin", "refs/heads/main"))
        self.inspect(self.saved, expected_code=0)
        self.assertEqual(snapshot(self.root), before)

    def test_open_pr_worktree_waits_for_hidden_consumer_and_revalidation(self):
        # Local bare refs stand in for the remote branch and a read-only open PR head.
        self.git(self.candidate, "push", "origin", "sdk", "HEAD:refs/pull/11/head")
        self.assertEqual(
            self.git(self.saved, "ls-remote", "origin", "refs/heads/sdk", "refs/pull/11/head"),
            f"{self.base}\trefs/heads/sdk\n{self.base}\trefs/pull/11/head",
        )
        consumer_repo = self.root / "application"
        self.git(self.root, "init", "-b", "main", str(consumer_repo))
        (consumer_repo / "pubspec.yaml").write_text("name: fixture\n")
        self.git(consumer_repo, "add", ".")
        self.git(consumer_repo, "commit", "-m", "initial")
        hidden = self.root / ".active" / "app"
        self.git(consumer_repo, "worktree", "add", "-b", "feature", str(hidden))
        manifest = hidden / "pubspec.yaml"
        lockfile = hidden / "pubspec.lock"
        link = hidden / "sdk-link"
        manifest.write_text(f'path: "{os.path.relpath(self.candidate, hidden)}"\n')
        lockfile.write_text(f'path: "{self.candidate}"\n')
        link.symlink_to(self.candidate / "version")
        marker = hidden / "script-ran"
        (hidden / "Makefile").write_text("X := $(shell touch script-ran)\n")
        before = snapshot(self.root)
        report = self.inspect(self.root / ".active", consumer_repo, expected_code=1)
        self.assertEqual({row["path"] for row in report["references"]},
                         {str(manifest), str(lockfile), str(link)})
        self.assertEqual(report["incomplete"], [])
        self.assertEqual(snapshot(self.root), before)

        # Authorized dependency migration into the durable checkout at the same revision.
        for config in (manifest, lockfile):
            config.write_text(f'path: "{os.path.relpath(self.saved, hidden)}"\n')
        link.unlink()
        link.symlink_to(self.saved / "version")
        self.inspect(hidden, consumer_repo, expected_code=0)
        # Simulate a racing task adding a local override after the plan was prepared.
        override = hidden / ".env.local"
        override.write_text(f"SDK={self.candidate}\n")
        report = self.inspect(hidden, consumer_repo, expected_code=1)
        self.assertEqual(report["references"], [{"path": str(override), "line": 1}])
        self.assertTrue(self.candidate.is_dir())
        override.write_text(f"SDK={self.saved}\n")
        self.inspect(hidden, consumer_repo, expected_code=0)
        self.git(self.saved, "worktree", "remove", str(self.candidate))
        self.inspect(hidden, consumer_repo, expected_code=0)
        for config in (manifest, lockfile):
            resolved = (hidden / json.loads(config.read_text().removeprefix("path: "))).resolve()
            self.assertEqual(resolved, self.saved)
            self.assertEqual((resolved / "version").read_text(), "1.0\n")
        self.assertEqual(link.read_text(), "1.0\n")
        stale = hidden / "stale-link"
        stale.symlink_to(self.candidate / "version")
        self.assertEqual(self.inspect(hidden, expected_code=1)["references"],
                         [{"path": str(stale), "kind": "symlink"}])
        self.assertEqual(self.git(self.saved, "rev-parse", "sdk"), self.base)
        self.assertIn(self.base, self.git(self.saved, "ls-remote", "origin", "refs/pull/11/head"))
        self.assertFalse(marker.exists())

    def test_incomplete_scan_has_distinct_exit_and_visible_path(self):
        cfg = self.saved / "package-lock.json"
        with cfg.open("wb") as stream:
            stream.truncate(17 * 1024 * 1024)
        report = self.inspect(self.saved, expected_code=2)
        self.assertEqual(report["incomplete"], [{"path": str(cfg), "reason": "large config"}])

    def test_local_only_tip_and_newer_payload_survive_selective_relocation(self):
        (self.saved / "version").write_text("2.0\n")
        self.git(self.saved, "commit", "-am", "update primary version")
        primary_tip = self.git(self.saved, "rev-parse", "HEAD")
        (self.saved / "report.md").write_text("older experiment")
        self.git(self.saved, "stash", "push", "-u", "-m", "older report")
        stash = self.git(self.saved, "rev-parse", "refs/stash")
        for name in (".runtime", ".env.local", "working.txt", "staged.txt"):
            (self.saved / name).write_text(name)
        self.git(self.saved, "add", "staged.txt")
        original_index = self.git(self.saved, "ls-files", "--stage", "staged.txt")
        (self.candidate / "report.md").write_text("newer complete report")
        self.git(self.candidate, "add", "report.md")
        self.git(self.candidate, "commit", "-m", "unpublished report")
        tip = self.git(self.candidate, "rev-parse", "HEAD")
        self.assertNotIn(tip, self.git(self.saved, "ls-remote", "origin"))
        self.assertEqual(self.git(self.saved, "show", f"{stash}^3:report.md"), "older experiment")
        self.assertNotEqual(self.git(self.saved, "rev-parse", f"{stash}^3:report.md"),
                            self.git(self.saved, "rev-parse", f"{tip}:report.md"))
        receipts = self.saved / "receipts"
        receipts.mkdir()
        bundle = receipts / "report.bundle"
        self.git(self.saved, "bundle", "create", str(bundle), "refs/heads/sdk")
        recovery_repo = self.root / "recovery.git"
        self.git(self.root, "init", "--bare", str(recovery_repo))
        self.git(recovery_repo, "bundle", "verify", str(bundle))
        self.git(recovery_repo, "fetch", str(bundle), "refs/heads/sdk:refs/heads/recovered")
        self.assertEqual(self.git(recovery_repo, "rev-parse", "recovered"), tip)
        self.assertEqual(self.git(recovery_repo, "show", "recovered:report.md"), "newer complete report")
        self.git(recovery_repo, "fsck", "--full")

        self.git(self.saved, "switch", "-c", "integrate-report")
        self.git(self.saved, "--literal-pathspecs", "restore", "--source", tip, "--worktree",
                 "--", "report.md")
        receipt = self.candidate / "verification.csv"
        receipt.write_bytes(b"sample,result\nfixture,pass\n")
        shutil.copy2(receipt, receipts / receipt.name)
        self.assertEqual(sha256(receipts / receipt.name), sha256(receipt))
        self.assertEqual(sha256(self.saved / "report.md"), sha256(self.candidate / "report.md"))
        receipt.unlink()  # exact authorized intermediate, after verifying its project copy
        self.assertEqual(self.git(self.candidate, "status", "--porcelain", "--ignored"), "")
        self.git(self.saved, "worktree", "remove", str(self.candidate))
        self.assertEqual(self.git(self.saved, "rev-parse", "refs/stash"), stash)
        self.assertEqual(self.git(self.saved, "rev-parse", "main"), primary_tip)
        self.assertEqual(self.git(self.saved, "rev-parse", "sdk"), tip)
        self.assertEqual(self.git(self.saved, "ls-files", "--stage", "staged.txt"), original_index)
        self.assertEqual((self.saved / "version").read_text(), "2.0\n")
        for name in (".runtime", ".env.local", "working.txt", "staged.txt"):
            self.assertEqual((self.saved / name).read_text(), name)
        self.assertEqual((self.saved / "report.md").read_text(), "newer complete report")

    def test_squash_merge_identity_does_not_require_commit_ancestry(self):
        (self.candidate / "sdk.txt").write_text("first")
        self.git(self.candidate, "add", "sdk.txt")
        self.git(self.candidate, "commit", "-m", "first SDK change")
        (self.candidate / "sdk.txt").write_text("second")
        self.git(self.candidate, "commit", "-am", "complete SDK change")
        pr_head = self.git(self.candidate, "rev-parse", "HEAD")
        self.git(self.candidate, "push", "origin", "HEAD:refs/pull/12/head")
        self.git(self.saved, "merge", "--squash", "sdk")
        self.git(self.saved, "commit", "-m", "squashed SDK change")
        merged = self.git(self.saved, "rev-parse", "HEAD")
        self.git(self.saved, "push", "origin", "main")
        self.assertNotEqual(pr_head, merged)
        self.assertIn(pr_head, self.git(self.saved, "ls-remote", "origin", "refs/pull/12/head"))
        self.assertIn(merged, self.git(self.saved, "ls-remote", "origin", "refs/heads/main"))
        self.assertEqual(self.git(self.saved, "merge-base", pr_head, merged), self.base)
        self.assertEqual(self.git(self.saved, "diff", "--name-only", self.base, pr_head), "sdk.txt")
        self.assertEqual(self.git(self.saved, "diff", "--exit-code", pr_head, merged), "")
        self.git(self.saved, "worktree", "remove", str(self.candidate))
        self.assertEqual(self.git(self.saved, "rev-parse", "sdk"), pr_head)
