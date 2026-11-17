"""Native process smoke tests. Only fixture-owned pipes control fixture services."""

import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import unittest


INSPECT = (Path(__file__).resolve().parents[1] / "skills" / "workspace-cleanup"
           / "scripts" / "inspect_processes.py")

# A new instance initializes, publishes its tree and waits for input. Each
# broker reaps its own child. Closing the instance pipe gracefully stops all
# three, including when a test assertion interrupts the normal sequence.
SERVICE = """\
import json
import os
import subprocess
import sys

role, resource, ledger = sys.argv[1:]
child = None
held = None
pids = {}
try:
    if role == "worker":
        held = open(resource, "rb")
    else:
        next_role = {"cli": "broker", "broker": "worker"}[role]
        child = subprocess.Popen(
            [sys.executable, __file__, next_role, resource, ledger],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        pids.update(json.loads(child.stdout.readline()))
    pids[role] = os.getpid()
    print(json.dumps(pids), flush=True)
    for request in sys.stdin:
        if request.strip() == "run" and role == "cli":
            with open(ledger, "a") as log:
                log.write("ran task\\n")
            print("done", flush=True)
finally:
    if child is not None:
        child.stdin.close()
        if child.wait(timeout=5):
            raise SystemExit(1)
    if held is not None:
        held.close()
"""


@unittest.skipUnless(sys.platform in ("darwin", "linux"), "native ps smoke uses macOS/Linux")
class WorkspaceProcessTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.scratch = Path(scratch.name).resolve()
        self.candidate = self.scratch / "checkout"
        self.candidate.mkdir()
        self.resource = self.candidate / "service.db"
        self.resource.write_bytes(b"fixture database")
        self.ledger = self.scratch / "task.log"
        self.program = self.scratch / "service.py"
        self.program.write_text(SERVICE)
        self.env = {**os.environ, "HOME": str(self.scratch), "PYTHONDONTWRITEBYTECODE": "1"}

    def read_reply(self, service):
        ready, _, _ = select.select([service.stdout], [], [], 10)
        self.assertTrue(ready, "fixture initialization or control reply timed out")
        return service.stdout.readline().strip()

    def stop(self, service):
        if not service.stdin.closed:
            service.stdin.close()
        self.assertEqual(service.wait(timeout=10), 0)

    def launch(self, role, resource):
        service = subprocess.Popen(
            [sys.executable, str(self.program), role, str(resource), str(self.ledger)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
            env=self.env, cwd=self.scratch,
        )
        self.addCleanup(service.stdout.close)
        self.addCleanup(self.stop, service)
        return service, json.loads(self.read_reply(service))

    def snapshot(self, owner_pid, *options, env=None):
        result = subprocess.run(
            [sys.executable, str(INSPECT), "--path", str(self.candidate),
             "--owner-pid", str(owner_pid), *options],
            capture_output=True, text=True, env=env or self.env, cwd=self.scratch, timeout=40,
        )
        self.assertTrue(result.stdout, result.stderr)
        snapshot = json.loads(result.stdout)
        partial = bool(snapshot["handle_scan_warning"] or snapshot["unobserved_protected_pids"])
        self.assertEqual(result.returncode, int(partial))
        return snapshot

    def test_unavailable_handle_inspection_returns_partial_evidence(self):
        # Keep native ps available, isolate the lookup of the unavailable lsof.
        bin_dir = self.scratch / "bin"
        bin_dir.mkdir()
        (bin_dir / "ps").symlink_to(shutil.which("ps"))
        snapshot = self.snapshot(os.getpid(), env={**self.env, "PATH": str(bin_dir)})
        self.assertIn("lsof", snapshot["handle_scan_warning"])
        self.assertIn(os.getpid(), snapshot["protected_ancestry"])

    def test_read_only_snapshot_with_reused_lock_pid_and_protected_session(self):
        unrelated, _ = self.launch("worker", self.resource)
        # The new occupant is real. The simulated lock has the previous
        # occupant's start identity, deliberately distinct at the same PID.
        lock = self.candidate / "worktree.lock"
        recorded = {"pid": unrelated.pid, "start": "Tue Jan 1 01:02:03 2002"}
        lock.write_text(json.dumps(recorded))
        before = self.snapshot(recorded["pid"], "--expected-start", recorded["start"],
                               "--protect-pid", str(unrelated.pid))
        self.assertIs(before["owner_start_matches"], False)
        self.assertIn(unrelated.pid, before["protected_ancestry"])
        self.assertIn(os.getpid(), before["protected_ancestry"])
        self.assertIn(os.getpid(), before["owner_ancestry"])
        self.assertIn(unrelated.pid, before["owner_tree"])
        self.assertIsNone(unrelated.poll())
        self.assertEqual(json.loads(lock.read_text()), recorded)
        self.assertEqual(self.resource.read_bytes(), b"fixture database")
        self.assertFalse(self.ledger.exists())

    @unittest.skipUnless(shutil.which("lsof"), "directory handle inspection requires lsof")
    def test_graceful_shutdown_residual_handles_and_idle_restart(self):
        owner, owned = self.launch("cli", self.resource)
        other, _ = self.launch("worker", self.resource)
        owner.stdin.write("run\n")
        owner.stdin.flush()
        self.assertEqual(self.read_reply(owner), "done")

        plan = self.snapshot(owner.pid, "--protect-pid", str(other.pid))
        self.assertEqual(set(plan["owner_tree"]), set(owned.values()))
        self.assertFalse(set(plan["owner_tree"]).intersection(plan["protected_ancestry"]))
        self.assertIn(os.getpid(), plan["protected_ancestry"])
        self.assertIn(other.pid, plan["protected_ancestry"])
        self.assertIn(owned["worker"], plan["visible_path_holders"])
        self.assertIn(other.pid, plan["visible_path_holders"])
        identities = {row["pid"]: row for row in plan["processes"]}
        self.assertEqual(identities[owned["worker"]]["ppid"], owned["broker"])
        self.assertEqual(identities[owned["broker"]]["ppid"], owner.pid)

        checked = self.snapshot(owner.pid, "--expected-start", identities[owner.pid]["start"],
                                "--protect-pid", str(other.pid))
        self.assertIs(checked["owner_start_matches"], True)
        for row in checked["processes"]:
            if row["pid"] in owned.values():
                self.assertEqual(row, identities[row["pid"]])
        self.assertEqual(set(checked["owner_tree"]), set(owned.values()))
        self.stop(owner)
        survivors = subprocess.run(
            ["ps", "-p", ",".join(str(pid) for pid in owned.values()), "-o", "pid="],
            capture_output=True, text=True,
        )
        self.assertEqual(survivors.returncode, 1, survivors.stderr)
        self.assertFalse(survivors.stdout.strip())
        after = self.snapshot(owner.pid)
        self.assertEqual(after["owner_tree"], [])
        self.assertIn(other.pid, after["visible_path_holders"])
        self.assertFalse(set(owned.values()).intersection(after["visible_path_holders"]))
        self.assertIsNone(other.poll())

        # The independent task releases its own handle. Only then can the
        # path be retired. Restart in a retained path using the idle handshake.
        self.stop(other)
        released = self.snapshot(owner.pid)
        self.assertFalse(released["handle_scan_warning"], released["handle_scan_warning"])
        self.assertFalse(released["visible_path_holders"])
        self.resource.unlink()
        self.candidate.rmdir()
        retained = self.scratch / "retained.db"
        retained.write_bytes(b"new service")
        probe, fresh = self.launch("cli", retained)
        self.assertEqual(set(fresh), {"cli", "broker", "worker"})
        self.stop(probe)
        self.assertEqual(self.ledger.read_text(), "ran task\n")
