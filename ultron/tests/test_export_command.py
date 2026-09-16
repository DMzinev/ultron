"""
ultron.tests.test_export_command
Automated test suite for Task P5-A1: Executive Architecture Report and Briefing Export.
"""

import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from ultron.interfaces.cli.commands.export import run_export_command
from ultron.interfaces.server import UltronAPIHandler


class TestExportCommand(unittest.TestCase):
    """Hermetic unit tests for the 'ultron export' CLI command and export-brief endpoint."""

    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def test_export_markdown_stdout(self):
        """Verify export command outputs markdown architecture brief to stdout."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_export_command(repo_path=self.repo_root, fmt="markdown")

        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Context Brief", output)
        self.assertIn("Directory Structure", output)

    def test_export_json_stdout(self):
        """Verify export command outputs valid JSON brief with schema_version 1.0.0."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_export_command(repo_path=self.repo_root, fmt="json")

        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("format"), "json")
        self.assertEqual(data.get("schema_version"), "1.0.0")
        self.assertIn("brief", data)

    def test_export_html_stdout(self):
        """Verify export command outputs valid HTML document."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_export_command(repo_path=self.repo_root, fmt="html")

        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("<!DOCTYPE html>", output)
        self.assertIn("<pre>", output)
        self.assertIn("Ultron Architecture Report", output)

    def test_export_text_stdout(self):
        """Verify export command outputs text brief to stdout."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_export_command(repo_path=self.repo_root, fmt="text")

        self.assertEqual(code, 0)
        self.assertGreater(len(buf.getvalue().strip()), 0)

    def test_export_to_file(self):
        """Verify export command writes report to destination file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "reports", "architecture-brief.md")
            code = run_export_command(repo_path=self.repo_root, fmt="markdown", output_path=out_file)

            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Context Brief", content)

    def test_export_unsupported_format(self):
        """Verify export command rejects unsupported formats with exit code 1."""
        err_buf = io.StringIO()
        with patch("sys.stderr", err_buf):
            code = run_export_command(repo_path=self.repo_root, fmt="unsupported_format")

        self.assertEqual(code, 1)
        self.assertIn("Unsupported format", err_buf.getvalue())

    def test_export_nonexistent_repo(self):
        """Verify export command exits 1 when repository directory does not exist."""
        err_buf = io.StringIO()
        with patch("sys.stderr", err_buf):
            code = run_export_command(repo_path="nonexistent/directory/path/here")

        self.assertEqual(code, 1)
        self.assertIn("Error: Repository directory", err_buf.getvalue())

    def test_cli_export_command_dispatch(self):
        """Verify CLI entrypoint parser properly delegates to run_export_command."""
        from ultron.interfaces.ultron import main

        with patch("ultron.interfaces.cli.commands.export.run_export_command", return_value=0) as mock_export:
            with patch("sys.argv", ["ultron", "export", "--repo", ".", "--format", "json", "--output", "out.json"]):
                try:
                    main()
                except SystemExit as e:
                    self.assertEqual(e.code, 0)

            mock_export.assert_called_once_with(
                repo_path=".",
                fmt="json",
                output_path="out.json",
            )

    def test_api_v1_export_brief_formats(self):
        """Verify REST API /api/v1/export-brief handles markdown and html formats."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/export-brief"
        handler.headers = {}
        handler.get_repo_root_path = lambda: self.repo_root

        # Test Markdown format
        handler.wfile = io.BytesIO()
        handler.get_post_data = lambda: {"repo": self.repo_root, "format": "markdown"}
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.send_json_response = lambda code, body: handler.wfile.write(json.dumps(body).encode("utf-8"))

        handler.handle_v1_export_brief()
        res_md = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res_md.get("status"), "ok")
        self.assertEqual(res_md.get("schema_version"), "1.0.0")
        self.assertEqual(res_md.get("format"), "markdown")
        self.assertIn("content", res_md)
        self.assertIn("Context Brief", res_md["content"])

        # Test HTML format
        handler.wfile = io.BytesIO()
        handler.get_post_data = lambda: {"repo": self.repo_root, "format": "html"}
        handler.handle_v1_export_brief()
        res_html = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res_html.get("status"), "ok")
        self.assertEqual(res_html.get("format"), "html")
        self.assertIn("<!DOCTYPE html>", res_html["content"])

        # Test Unsupported format rejection
        handler.wfile = io.BytesIO()
        handler.get_post_data = lambda: {"repo": self.repo_root, "format": "unsupported_xyz"}
        handler.handle_v1_export_brief()
        res_err = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res_err.get("status"), "error")


if __name__ == "__main__":
    unittest.main()