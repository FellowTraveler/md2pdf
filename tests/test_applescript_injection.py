"""Untrusted text (filenames, voice names) must reach AppleScript only via argv.

Splicing it into the script source let a file named like
  report" & (do shell script "...") & ".md
run arbitrary commands when a Quick Action showed its notification.
"""
import importlib.machinery
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = 'x" & (do shell script "cd;touch injected") & "'


def load_script(name):
    """These scripts have no .py extension, so load them with an explicit source loader."""
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader(name, str(REPO_ROOT / name))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


audio2md = load_script("audio2md")
md2audio = load_script("md2audio")


class AppleScriptArgvTest(unittest.TestCase):
    def assert_payload_only_in_argv(self, run):
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[:2], ["osascript", "-e"])
        script, argv = cmd[2], cmd[3:]
        self.assertTrue(script.startswith("on run argv"))
        self.assertNotIn(PAYLOAD, script)
        self.assertTrue(any(PAYLOAD in arg for arg in argv))

    def test_audio2md_notify(self):
        with mock.patch.object(audio2md.subprocess, "run") as run:
            audio2md.notify("Transcription Complete", f"Saved: {PAYLOAD}.md")
        self.assert_payload_only_in_argv(run)

    def test_audio2md_error_dialog(self):
        with mock.patch.object(audio2md.subprocess, "run") as run:
            audio2md.error_dialog("Transcribe to MD", f"{PAYLOAD} is not supported")
        self.assert_payload_only_in_argv(run)

    def test_md2audio_error_dialog(self):
        with mock.patch.object(md2audio.subprocess, "run") as run:
            md2audio.error_dialog(f"No voices found for '{PAYLOAD}'.")
        self.assert_payload_only_in_argv(run)

    def test_md2audio_choose_from_list_with_untrusted_voice_name(self):
        with mock.patch.object(md2audio.subprocess, "run") as run:
            run.return_value = mock.Mock(stdout=PAYLOAD + "\n", returncode=0)
            chosen = md2audio.choose_from_list("Voice Search Results", "Results:", [PAYLOAD, "Rachel"])
        self.assert_payload_only_in_argv(run)
        self.assertEqual(chosen, PAYLOAD)


if __name__ == "__main__":
    unittest.main()
