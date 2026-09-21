import plistlib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_NAME = "Decode QR Code On Screen"
NO_INPUT_TYPE = "com.apple.Automator.nothing"


def load_plist(workflow_dir, file_name):
    with open(workflow_dir / "Contents" / file_name, "rb") as plist_file:
        return plistlib.load(plist_file)


class QrWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow_dir = REPO_ROOT / f"{WORKFLOW_NAME}.workflow"

    def test_service_menu_name_matches_existing_hotkey_binding(self):
        service = load_plist(self.workflow_dir, "Info.plist")["NSServices"][0]
        self.assertEqual(service["NSMenuItem"]["default"], WORKFLOW_NAME)
        self.assertEqual(service["NSMessage"], "runWorkflowAsService")

    def test_service_takes_no_input_and_is_not_limited_to_finder(self):
        info = load_plist(self.workflow_dir, "Info.plist")
        service = info["NSServices"][0]
        self.assertNotIn("NSSendTypes", service)
        self.assertNotIn("NSRequiredContext", service)
        self.assertNotIn("ShortcutInputClasses", info)
        metadata = load_plist(self.workflow_dir, "document.wflow")["workflowMetaData"]
        self.assertEqual(metadata["serviceInputTypeIdentifier"], NO_INPUT_TYPE)
        self.assertNotIn("serviceApplicationBundleID", metadata)

    def test_workflow_runs_qr2clip(self):
        document = load_plist(self.workflow_dir, "document.wflow")
        command = document["actions"][0]["action"]["ActionParameters"]["COMMAND_STRING"]
        self.assertIn('export PATH="$HOME/bin:', command)
        self.assertEqual(command.strip().splitlines()[-1], "qr2clip")

    def test_it_is_the_only_no_input_workflow(self):
        """install.sh skips the pbs write and Shortcut generation for no-input
        workflows; this guards every file-based workflow from being skipped."""
        no_input_workflows = [
            workflow_dir.name
            for workflow_dir in sorted(REPO_ROOT.glob("*.workflow"))
            if load_plist(workflow_dir, "document.wflow")["workflowMetaData"][
                "serviceInputTypeIdentifier"
            ] == NO_INPUT_TYPE
        ]
        self.assertEqual(
            no_input_workflows,
            [f"{WORKFLOW_NAME}.workflow"],
            "The set of no-input workflows changed. install.sh treats these specially "
            "(no pbs write, no Shortcut, always a Service) — re-check those paths.",
        )


if __name__ == "__main__":
    unittest.main()
