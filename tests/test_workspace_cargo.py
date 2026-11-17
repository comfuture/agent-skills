import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = (Path(__file__).resolve().parents[1] / "skills/workspace-cleanup/scripts"
          / "compare_cargo_roots.py")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CargoCleanupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.project = self.create_package("example")
        self.target = self.project / "target"
        self.cargo_home = self.root / "cargo-home"
        self.rustup_home = self.root / "rustup-home"
        self.env = {
            "HOME": str(self.root),
            "CARGO_HOME": str(self.cargo_home),
            "RUSTUP_HOME": str(self.rustup_home),
            "PATH": os.environ["PATH"],
            "TMPDIR": str(self.root),
        }

    def create_package(self, name):
        path = self.root / name
        (path / "src").mkdir(parents=True)
        (path / "Cargo.toml").write_text(
            f'[package]\nname="{name}"\nversion="0.1.0"\nedition="2021"\n')
        (path / "src/lib.rs").write_text("pub const EXAMPLE: u8 = 1;\n")
        return path

    def assess(self, target, build, *options):
        result = subprocess.check_output([
            sys.executable, SCRIPT, "--workspace", self.project,
            "--target-dir", target, "--build-dir", build,
            "--cargo-home", self.cargo_home, "--rustup-home", self.rustup_home,
            *options,
        ], text=True, env=self.env, cwd=self.root)
        return json.loads(result)

    def require_toolchain(self):
        # Use installed binaries directly, so a private rustup home needs no downloads.
        for name in ("cargo", "rustc"):
            binary = shutil.which(name)
            if shutil.which("rustup"):
                which = subprocess.run(["rustup", "which", name], capture_output=True,
                                       text=True, cwd=self.root)
                if which.returncode != 0:
                    self.skipTest(f"rustup has no installed {name} for this toolchain")
                binary = which.stdout.strip()
            if not binary:
                self.skipTest("Cargo native smoke requires an installed Rust toolchain")
            if name == "cargo":
                self.cargo_bin = binary
            else:
                self.env["RUSTC"] = binary

    def cargo(self, *args, package=None):
        return subprocess.run([self.cargo_bin, *args], env=self.env,
                              cwd=package or self.project, capture_output=True,
                              text=True, check=True, timeout=45).stdout

    def metadata(self, **kwargs):
        return json.loads(self.cargo("metadata", "--format-version", "1",
                                     "--no-deps", "--frozen", **kwargs))

    def sentinels(self):
        retained = {}
        for path in (self.cargo_home / "registry/cache/sample/example.crate",
                     self.cargo_home / "registry/src/sample/example/lib.rs",
                     self.cargo_home / "git/db/sample/HEAD",
                     self.cargo_home / "bin/sample",
                     self.cargo_home / "credentials.toml",
                     self.rustup_home / "toolchains/sample/bin/rustc"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# fixture\n")
            retained[path] = digest(path)
        return retained

    def test_protected_overlap_and_redundant_worktree_clean(self):
        self.cargo_home.mkdir()
        alias = self.project / "alias"
        alias.symlink_to(self.cargo_home, target_is_directory=True)
        for output in (alias / "registry", self.rustup_home, self.project, self.root):
            with self.subTest(output=output):
                plan = self.assess(output, self.target, "--removing-worktree", self.project)
                self.assertEqual(plan["assessment"], "defer")

        removal = ["--removing-worktree", self.project]
        self.assertEqual(self.assess(self.target, self.target, *removal)["assessment"], "redundant")
        self.assertEqual(self.assess(self.target, self.root / "external", *removal)["assessment"], "review")
        plan = self.assess(self.target, self.root / "split",
                           "--other-output", self.root / "split" / "owner")
        self.assertEqual(plan["assessment"], "defer")
        self.assertFalse(self.target.exists())

    def test_native_preview_then_full_clean_preserves_evidence_and_caches(self):
        self.require_toolchain()
        (self.project / ".gitignore").write_text("/target/\n")
        subprocess.run(["git", "init", "--quiet"], cwd=self.project, env=self.env, check=True)
        meta = self.metadata()
        self.assertEqual(Path(meta["target_directory"]), self.target)
        self.assertEqual(Path(meta.get("build_directory", self.target)), self.target)
        # Pin both destinations inside the fixture for the native mutation.
        self.env.update(CARGO_TARGET_DIR=str(self.target), CARGO_BUILD_BUILD_DIR=str(self.target))
        self.cargo("build", "--offline")
        evidence = self.target / "criterion/sample/new/sample.json"
        evidence.parent.mkdir(parents=True)
        evidence.write_text('{"measurements":[1,2,3]}\n')
        subprocess.run(["git", "check-ignore", "--quiet", str(evidence)],
                       cwd=self.project, env=self.env, check=True)
        retained = self.sentinels()
        lock = self.project / "Cargo.lock"
        retained[lock] = digest(lock)
        before = {p: digest(p) for p in self.target.rglob("*") if p.is_file()}
        self.assertEqual(self.assess(self.target, self.target)["assessment"], "review")
        if "--dry-run" in self.cargo("clean", "--help"):
            self.cargo("clean", "--frozen", "--dry-run", "--verbose")
        self.assertEqual({p: digest(p) for p in self.target.rglob("*") if p.is_file()}, before)

        delivery = self.project / "verification/sample.json"
        delivery.parent.mkdir()
        shutil.copy2(evidence, delivery)
        retained[delivery] = before[evidence]
        self.assertEqual(digest(delivery), before[evidence])
        self.cargo("clean", "--frozen")
        self.assertFalse(self.target.exists())
        self.assertEqual({p: digest(p) for p in retained}, retained)

    def test_shared_config_and_active_native_build_defer_clean(self):
        self.require_toolchain()
        other = self.create_package("consumer")
        shared_target = self.root / "shared-target"
        shared_build = self.root / "shared-build"
        (self.root / ".cargo").mkdir()
        (self.root / ".cargo/config.toml").write_text(
            '[build]\ntarget-dir="shared-target"\nbuild-dir="shared-build"\n')
        first = self.metadata()
        second = self.metadata(package=other)
        self.assertEqual(first["target_directory"], str(shared_target))
        self.assertEqual(second["target_directory"], str(shared_target))
        (other / "build.rs").write_text("""
fn main() {
    std::fs::write("ready", []).unwrap();
    let start = std::time::Instant::now();
    while !std::path::Path::new("release").exists() {
        assert!(start.elapsed().as_secs() < 40);
        std::thread::sleep(std::time::Duration::from_millis(10));
    }
}
""")
        with subprocess.Popen([self.cargo_bin, "build", "--offline"], env=self.env, cwd=other,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
            try:
                deadline = time.monotonic() + 30
                while not (other / "ready").exists() and proc.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue((other / "ready").exists(), "fixture build failed to reach its gate")
                self.assertIsNone(proc.poll())
                # Some Cargo versions honor the split setting without publishing
                # build_directory. Use the observed build, including on older Cargo.
                build = shared_build if shared_build.is_dir() else shared_target
                for metadata in (first, second):
                    if "build_directory" in metadata:
                        self.assertEqual(Path(metadata["build_directory"]), build)
                retained = self.sentinels()
                plan = self.assess(shared_target, build, "--other-output", second["target_directory"],
                                   "--busy-output", build)
                self.assertEqual(plan["assessment"], "defer")
                self.assertTrue(any("another workspace" in reason for reason in plan["reasons"]))
                self.assertTrue(any("active build" in reason for reason in plan["reasons"]))
                self.assertEqual({p: digest(p) for p in retained}, retained)
            finally:
                (other / "release").touch()
                output = proc.communicate(timeout=45)[0]
        self.assertEqual(proc.returncode, 0, output)
        self.assertTrue((shared_target / "debug/libconsumer.rlib").is_file())
        self.assertTrue((build / "debug/deps").is_dir())
