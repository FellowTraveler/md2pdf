"""Tests for python_select.sh: install.sh's choice of interpreter for the venv."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SELECTOR = Path(__file__).resolve().parent.parent / "python_select.sh"


class FindVenvPythonTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bin_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _add_interpreter(self, name):
        exe = self.bin_dir / name
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
        return str(exe)

    def _find(self, versions=None):
        env = {"PATH": str(self.bin_dir)}
        if versions is not None:
            env["MD2PDF_PYTHON_VERSIONS"] = versions
        result = subprocess.run(
            ["/bin/bash", "-c", f'source "{SELECTOR}"; find_venv_python'],
            env=env, capture_output=True, text=True,
        )
        return result.returncode, result.stdout.strip()

    def test_prefers_known_good_version_over_newer_python(self):
        self._add_interpreter("python3.15")
        self._add_interpreter("python3.14")
        expected = self._add_interpreter("python3.13")
        self.assertEqual(self._find(), (0, expected))

    def test_falls_back_to_next_supported_version(self):
        self._add_interpreter("python3.15")
        expected = self._add_interpreter("python3.12")
        self.assertEqual(self._find(), (0, expected))

    def test_ignores_unversioned_python3(self):
        self._add_interpreter("python3")
        self._add_interpreter("python3.15")
        self.assertEqual(self._find(), (1, ""))

    def test_env_override_sets_preference(self):
        self._add_interpreter("python3.13")
        expected = self._add_interpreter("python3.12")
        self.assertEqual(self._find(versions="3.12 3.13"), (0, expected))


if __name__ == "__main__":
    unittest.main()
