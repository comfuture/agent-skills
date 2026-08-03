from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "develoop"


class DeveloopPluginPackageTests(unittest.TestCase):
    def test_plugin_skill_payload_is_in_sync(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/sync_develoop_plugin.py", "--check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("self-contained, and in sync", result.stdout)

    def test_host_adapters_share_identity_and_version(self) -> None:
        codex = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        claude = json.loads(
            (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        antigravity = json.loads(
            (PLUGIN / "plugin.json").read_text(encoding="utf-8")
        )

        self.assertEqual(codex["name"], "develoop")
        self.assertEqual(claude["name"], "develoop")
        self.assertEqual(marketplace["plugins"][0]["name"], "develoop")
        self.assertEqual(antigravity["name"], "develoop")
        self.assertEqual(codex["version"], "0.1.1")
        self.assertEqual(claude["version"], "0.1.1")
        self.assertEqual(marketplace["version"], "0.1.1")
        self.assertEqual(marketplace["plugins"][0]["version"], "0.1.1")
        self.assertEqual(
            set(antigravity),
            {"$schema", "name", "description"},
        )

    def test_writing_strategy_is_included_but_not_marketed(self) -> None:
        self.assertTrue((PLUGIN / "skills" / "writing-strategy" / "SKILL.md").is_file())
        codex = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        claude = json.loads(
            (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketing = " ".join(
            [
                codex["description"],
                codex["interface"]["shortDescription"],
                codex["interface"]["longDescription"],
                *codex["keywords"],
                *codex["interface"]["defaultPrompt"],
                claude["description"],
                *claude["keywords"],
            ]
        ).lower()
        self.assertNotIn("writing", marketing)
        self.assertNotIn("strategy", marketing)

    def test_public_urls_are_consistent(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        interface = manifest["interface"]
        self.assertEqual(
            interface["websiteURL"],
            "https://develoop.comfuture.chatgpt.site",
        )
        self.assertEqual(
            interface["privacyPolicyURL"],
            f"{interface['websiteURL']}/privacy",
        )
        self.assertEqual(
            interface["termsOfServiceURL"],
            f"{interface['websiteURL']}/terms",
        )


if __name__ == "__main__":
    unittest.main()
