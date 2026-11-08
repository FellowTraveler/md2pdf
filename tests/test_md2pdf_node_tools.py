"""md2pdf uses md-to-pdf/mermaid-cli from ~/.md2pdf-node (installed fresh by install.sh)
instead of `npx --yes`, which reused a stale, vulnerable first download forever."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

MD2PDF = Path(__file__).resolve().parent.parent / "md2pdf"


class Md2pdfNodeToolsTest(unittest.TestCase):
    def test_missing_node_tools_tells_user_to_reinstall(self):
        with tempfile.TemporaryDirectory() as home:
            themes = Path(home) / ".md2pdf-themes"
            themes.mkdir()
            (themes / "executive.css").write_text("")
            doc = Path(home) / "doc.md"
            doc.write_text("# Hello\n")

            result = subprocess.run(
                ["/bin/bash", str(MD2PDF), str(doc)],
                env={**os.environ, "HOME": home}, capture_output=True, text=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("re-run md2pdf's install.sh", result.stdout)

    def test_does_not_use_npx(self):
        self.assertNotIn("npx", MD2PDF.read_text())


if __name__ == "__main__":
    unittest.main()
