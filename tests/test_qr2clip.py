import contextlib
import importlib.machinery
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
PLAIN_QR_TEXT = "https://example.com/qr2clip-plain-fixture"
CENTER_LOGO_QR_TEXT = "https://drodom.substack.com/p/the-truth-about-women-not-losing"


def load_qr2clip():
    """qr2clip has no .py extension, so it is loaded with an explicit source loader."""
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader("qr2clip", str(REPO_ROOT / "qr2clip"))
    spec = importlib.util.spec_from_loader("qr2clip", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


qr2clip = load_qr2clip()


class DecodeQrTests(unittest.TestCase):
    def test_plain_qr_decodes(self):
        self.assertEqual(qr2clip.decode_qr(str(FIXTURES_DIR / "qr_plain.png")), PLAIN_QR_TEXT)

    def test_center_logo_qr_decodes(self):
        self.assertEqual(
            qr2clip.decode_qr(str(FIXTURES_DIR / "qr_center_logo.jpg")), CENTER_LOGO_QR_TEXT
        )

    def test_image_without_qr_returns_none(self):
        self.assertIsNone(qr2clip.decode_qr(str(FIXTURES_DIR / "no_qr.png")))


class DecodeFileTests(unittest.TestCase):
    def run_decode_file(self, image_path):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = qr2clip.decode_file(str(image_path))
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_prints_payload_and_exits_zero(self):
        exit_code, stdout, _ = self.run_decode_file(FIXTURES_DIR / "qr_plain.png")
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.strip(), PLAIN_QR_TEXT)

    def test_no_qr_exits_one(self):
        exit_code, stdout, stderr = self.run_decode_file(FIXTURES_DIR / "no_qr.png")
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("No QR code found", stderr)

    def test_missing_file_exits_one(self):
        exit_code, _, stderr = self.run_decode_file(FIXTURES_DIR / "does_not_exist.png")
        self.assertEqual(exit_code, 1)
        self.assertIn("no such file", stderr)

    def test_unreadable_image_exits_one(self):
        exit_code, _, stderr = self.run_decode_file(FIXTURES_DIR / "make_fixtures.py")
        self.assertEqual(exit_code, 1)
        self.assertIn("cannot read image", stderr)

    def test_missing_decoder_exits_one_without_traceback(self):
        with mock.patch.object(qr2clip, "decoder_available", return_value=False):
            exit_code, _, stderr = self.run_decode_file(FIXTURES_DIR / "qr_plain.png")
        self.assertEqual(exit_code, 1)
        self.assertIn("zxing-cpp is not installed", stderr)


class ScanScreenTests(unittest.TestCase):
    """The interactive flow with every macOS side effect mocked out."""

    def setUp(self):
        self.capture_paths = []
        self.notify = self.patch("notify")
        self.copy_to_clipboard = self.patch("copy_to_clipboard")
        self.open_settings = self.patch("open_screen_recording_settings")
        self.patch("decoder_available", return_value=True)

    def patch(self, function_name, **kwargs):
        patcher = mock.patch.object(qr2clip, function_name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def fake_capture(self, fixture_name):
        """Stand-in for capture_selection: fixture_name=None simulates an empty capture."""
        def capture(capture_path):
            self.capture_paths.append(capture_path)
            if fixture_name is None:
                return False
            shutil.copyfile(FIXTURES_DIR / fixture_name, capture_path)
            return True
        return capture

    def assert_temp_file_removed(self):
        self.assertEqual(len(self.capture_paths), 1)
        self.assertFalse(os.path.exists(self.capture_paths[0]))

    def test_empty_capture_with_access_reports_cancelled(self):
        self.patch("capture_selection", side_effect=self.fake_capture(None))
        self.patch("has_screen_capture_access", return_value=True)
        self.assertEqual(qr2clip.scan_screen(), 0)
        self.notify.assert_called_once_with(qr2clip.MSG_CANCELLED)
        self.open_settings.assert_not_called()
        self.copy_to_clipboard.assert_not_called()
        self.assert_temp_file_removed()

    def test_empty_capture_without_access_reports_permission(self):
        self.patch("capture_selection", side_effect=self.fake_capture(None))
        self.patch("has_screen_capture_access", return_value=False)
        self.assertEqual(qr2clip.scan_screen(), 0)
        self.notify.assert_called_once_with(qr2clip.MSG_PERMISSION)
        self.open_settings.assert_called_once_with()
        self.copy_to_clipboard.assert_not_called()
        self.assert_temp_file_removed()

    def test_capture_without_qr_reports_not_found(self):
        self.patch("capture_selection", side_effect=self.fake_capture("no_qr.png"))
        self.assertEqual(qr2clip.scan_screen(), 0)
        self.notify.assert_called_once_with(qr2clip.MSG_NOT_FOUND)
        self.copy_to_clipboard.assert_not_called()
        self.assert_temp_file_removed()

    def test_successful_scan_copies_payload(self):
        self.patch("capture_selection", side_effect=self.fake_capture("qr_center_logo.jpg"))
        self.assertEqual(qr2clip.scan_screen(), 0)
        self.copy_to_clipboard.assert_called_once_with(CENTER_LOGO_QR_TEXT)
        self.notify.assert_called_once_with(
            qr2clip.MSG_COPIED.format(preview=CENTER_LOGO_QR_TEXT)
        )
        self.assert_temp_file_removed()

    def test_missing_decoder_reports_before_capturing(self):
        self.patch("decoder_available", return_value=False)
        capture = self.patch("capture_selection")
        self.assertEqual(qr2clip.scan_screen(), 0)
        self.notify.assert_called_once_with(qr2clip.MSG_MISSING_DECODER)
        capture.assert_not_called()

    def test_capture_file_already_gone_is_not_an_error(self):
        def capture_that_unlinks(capture_path):
            self.capture_paths.append(capture_path)
            os.remove(capture_path)
            return False
        self.patch("capture_selection", side_effect=capture_that_unlinks)
        self.patch("has_screen_capture_access", return_value=True)
        self.assertEqual(qr2clip.scan_screen(), 0)
        self.notify.assert_called_once_with(qr2clip.MSG_CANCELLED)

    def test_decode_failure_is_reported_and_cleaned_up(self):
        self.patch("capture_selection", side_effect=self.fake_capture("qr_plain.png"))
        self.patch("decode_qr", side_effect=RuntimeError("decoder exploded"))
        with self.assertRaises(RuntimeError):
            qr2clip.scan_screen()
        self.notify.assert_called_once_with(qr2clip.MSG_FAILED.format(error="decoder exploded"))
        self.copy_to_clipboard.assert_not_called()
        self.assert_temp_file_removed()

    def test_clipboard_failure_is_reported_not_announced_as_success(self):
        self.patch("capture_selection", side_effect=self.fake_capture("qr_plain.png"))
        self.copy_to_clipboard.side_effect = OSError("pbcopy failed")
        with self.assertRaises(OSError):
            qr2clip.scan_screen()
        self.notify.assert_called_once_with(qr2clip.MSG_FAILED.format(error="pbcopy failed"))
        self.assert_temp_file_removed()

    def test_long_payload_preview_is_truncated(self):
        long_payload = "x" * (qr2clip.PREVIEW_LENGTH + 50)
        self.assertEqual(len(qr2clip.preview_of(long_payload)), qr2clip.PREVIEW_LENGTH + 1)
        self.assertTrue(qr2clip.preview_of(long_payload).endswith("…"))
        self.assertEqual(qr2clip.preview_of("short"), "short")


HOSTILE_PAYLOAD = 'x" & do shell script "touch /tmp/pwned" & "$(id)`id`'


class SideEffectCommandTests(unittest.TestCase):
    """The real helpers, with only subprocess.run replaced."""

    def setUp(self):
        patcher = mock.patch.object(qr2clip.subprocess, "run")
        self.addCleanup(patcher.stop)
        self.run = patcher.start()

    def test_notify_passes_untrusted_text_as_argument_never_as_script(self):
        qr2clip.notify(HOSTILE_PAYLOAD)
        command = self.run.call_args.args[0]
        self.assertEqual(command[0], qr2clip.OSASCRIPT_BIN)
        self.assertEqual(command[-2:], [HOSTILE_PAYLOAD, qr2clip.NOTIFICATION_TITLE])
        script_lines = [command[i + 1] for i, part in enumerate(command[:-2]) if part == "-e"]
        self.assertEqual(tuple(script_lines), qr2clip.NOTIFY_APPLESCRIPT)
        self.assertNotIn(HOSTILE_PAYLOAD, " ".join(script_lines))

    def test_clipboard_gets_utf8_bytes_with_an_explicit_utf8_locale(self):
        qr2clip.copy_to_clipboard("日本語 café")
        call = self.run.call_args
        self.assertEqual(call.args[0], [qr2clip.PBCOPY_BIN])
        self.assertEqual(call.kwargs["input"], "日本語 café".encode("utf-8"))
        self.assertEqual(call.kwargs["env"]["LC_CTYPE"], qr2clip.CLIPBOARD_LOCALE)
        self.assertTrue(call.kwargs["check"])

    def test_capture_selection_is_false_for_empty_or_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            empty = os.path.join(directory, "empty.png")
            open(empty, "wb").close()
            self.assertFalse(qr2clip.capture_selection(empty))
            self.assertFalse(qr2clip.capture_selection(os.path.join(directory, "missing.png")))
        self.assertEqual(self.run.call_args.args[0][:2], [qr2clip.SCREENCAPTURE_BIN, "-i"])

    def test_capture_selection_is_true_for_non_empty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            captured = os.path.join(directory, "captured.png")
            shutil.copyfile(FIXTURES_DIR / "qr_plain.png", captured)
            self.assertTrue(qr2clip.capture_selection(captured))


class CopyFromImageTests(unittest.TestCase):
    """Right-click mode: every notified outcome exits 0, and the payload is only copied."""

    def setUp(self):
        self.notify = self.patch("notify")
        self.copy_to_clipboard = self.patch("copy_to_clipboard")
        self.patch("decoder_available", return_value=True)
        self.run_process = self.patch_subprocess_run()

    def patch(self, function_name, **kwargs):
        patcher = mock.patch.object(qr2clip, function_name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def patch_subprocess_run(self):
        patcher = mock.patch.object(qr2clip.subprocess, "run")
        self.addCleanup(patcher.stop)
        return patcher.start()

    def assert_copied(self, text):
        self.copy_to_clipboard.assert_called_once_with(text)
        self.notify.assert_called_once_with(qr2clip.MSG_COPIED.format(preview=text))
        self.run_process.assert_not_called()  # never `open`s the payload

    def test_image_file_payload_is_copied(self):
        self.assertEqual(qr2clip.copy_from_image(str(FIXTURES_DIR / "qr_center_logo.jpg")), 0)
        self.assert_copied(CENTER_LOGO_QR_TEXT)

    def test_image_bytes_on_stdin_are_decoded(self):
        image_bytes = (FIXTURES_DIR / "qr_plain.png").read_bytes()
        stdin = mock.Mock(buffer=io.BytesIO(image_bytes))
        with mock.patch.object(qr2clip.sys, "stdin", stdin):
            self.assertEqual(qr2clip.copy_from_image(qr2clip.STDIN_SOURCE), 0)
        self.assert_copied(PLAIN_QR_TEXT)

    def test_image_without_qr_reports_not_found(self):
        self.assertEqual(qr2clip.copy_from_image(str(FIXTURES_DIR / "no_qr.png")), 0)
        self.notify.assert_called_once_with(qr2clip.MSG_NOT_FOUND_IN_IMAGE)
        self.copy_to_clipboard.assert_not_called()

    def test_unreadable_or_missing_image_is_reported(self):
        for path in (str(FIXTURES_DIR / "make_fixtures.py"), "/nonexistent/qr.png"):
            self.notify.reset_mock()
            self.assertEqual(qr2clip.copy_from_image(path), 0)
            self.notify.assert_called_once_with(qr2clip.MSG_UNREADABLE_IMAGE)
        self.copy_to_clipboard.assert_not_called()

    def test_missing_decoder_is_reported(self):
        self.patch("decoder_available", return_value=False)
        self.assertEqual(qr2clip.copy_from_image(str(FIXTURES_DIR / "qr_plain.png")), 0)
        self.notify.assert_called_once_with(qr2clip.MSG_MISSING_DECODER)
        self.copy_to_clipboard.assert_not_called()


class MainDispatchTests(unittest.TestCase):
    def run_main(self, *arguments):
        with mock.patch.object(sys, "argv", ["qr2clip", *arguments]), \
                mock.patch.object(qr2clip, "scan_screen", return_value=0) as scan, \
                mock.patch.object(qr2clip, "decode_file", return_value=0) as decode, \
                contextlib.redirect_stdout(io.StringIO()):
            return qr2clip.main(), scan, decode

    def test_no_arguments_scans_the_screen(self):
        _, scan, decode = self.run_main()
        scan.assert_called_once_with()
        decode.assert_not_called()

    def test_one_argument_decodes_that_file(self):
        _, scan, decode = self.run_main("poster.png")
        decode.assert_called_once_with("poster.png")
        scan.assert_not_called()

    def test_copy_flag_copies_from_that_image(self):
        with mock.patch.object(qr2clip, "copy_from_image", return_value=0) as copy_from_image:
            exit_code, scan, decode = self.run_main(qr2clip.COPY_FLAG, "poster.png")
        self.assertEqual(exit_code, 0)
        copy_from_image.assert_called_once_with("poster.png")
        scan.assert_not_called()
        decode.assert_not_called()

    def test_help_and_bad_usage(self):
        self.assertEqual(self.run_main("--help")[0], 0)
        self.assertEqual(self.run_main("a.png", "b.png")[0], 2)

if __name__ == "__main__":
    unittest.main()
