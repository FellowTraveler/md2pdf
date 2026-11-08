"""Open Folder with Devin (Windsurf was renamed Devin) and cleanup of the retired name."""
import os
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / "Open Folder with Devin.workflow"
RETIRED_NAME = "Open Folder with Windsurf"


def load_plist(file_name):
    with open(WORKFLOW_DIR / "Contents" / file_name, "rb") as plist_file:
        return plistlib.load(plist_file)


class DevinWorkflowTests(unittest.TestCase):
    def test_service_is_named_for_devin(self):
        info = load_plist("Info.plist")
        self.assertEqual(info["NSServices"][0]["NSMenuItem"]["default"], "Open Folder with Devin")
        self.assertEqual(info["CFBundleIdentifier"], "com.apple.automator.open-folder-with-devin")

    def test_prefers_devin_launcher_and_falls_back_to_windsurf(self):
        document = load_plist("document.wflow")
        command = document["actions"][0]["action"]["ActionParameters"]["COMMAND_STRING"]
        self.assertIn('for f in "$@"', command)
        self.assertIn('"$candidate" --new-window "$f"', command)
        self.assertLess(command.index("devin-desktop"), command.index("bin/windsurf"))

    def test_retired_windsurf_workflow_is_gone_from_repo(self):
        self.assertFalse((REPO_ROOT / f"{RETIRED_NAME}.workflow").exists())


class UninstallRetiredWorkflowTests(unittest.TestCase):
    def test_uninstall_removes_retired_service_and_lists_its_shortcut(self):
        with tempfile.TemporaryDirectory() as home:
            stub_bin = Path(home) / "stub-bin"
            stub_bin.mkdir()
            # Stubs keep the test from restarting the real Finder/pbs.
            (stub_bin / "killall").write_text("#!/bin/sh\nexit 0\n")
            (stub_bin / "shortcuts").write_text(f'#!/bin/sh\necho "{RETIRED_NAME}"\n')
            for stub in stub_bin.iterdir():
                stub.chmod(0o755)
            retired_service = Path(home) / "Library" / "Services" / f"{RETIRED_NAME}.workflow"
            retired_service.mkdir(parents=True)

            result = subprocess.run(
                ["/bin/bash", str(REPO_ROOT / "uninstall.sh")],
                env={**os.environ, "HOME": home, "PATH": f"{stub_bin}:/usr/bin:/bin"},
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(retired_service.exists())
            self.assertIn(f"  - {RETIRED_NAME}", result.stdout)


if __name__ == "__main__":
    unittest.main()
