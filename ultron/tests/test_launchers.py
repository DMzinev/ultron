import io
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import json
import subprocess

import start

try:
    from launcher import tray_launcher
    HAS_TRAY_DEPS = getattr(tray_launcher, "HAS_TRAY_DEPS", False)
except Exception:
    tray_launcher = None
    HAS_TRAY_DEPS = False


class TestStartScript(unittest.TestCase):
    """Test start.py functionality and resilience."""

    def test_safe_reconfigure_console(self):
        # Stream with reconfigure method
        mock_stream = MagicMock()
        with patch.object(sys, "stdout", mock_stream):
            start._safe_reconfigure_console()
            mock_stream.reconfigure.assert_called_with(encoding="utf-8", errors="replace")

    def test_safe_reconfigure_console_handles_exception(self):
        mock_stream = MagicMock()
        mock_stream.reconfigure.side_effect = RuntimeError("TTY error")
        with patch.object(sys, "stdout", mock_stream):
            # Should not raise
            start._safe_reconfigure_console()

    def test_init_rkm_success(self):
        mock_bundle = MagicMock()
        mock_bundle.repo_uuid = "test-uuid-123"
        with patch("ultron.core.pipeline.orchestrator.analyze_repository", return_value=mock_bundle):
            res = start._init_rkm(start.ROOT)
            self.assertEqual(res, mock_bundle)

    def test_init_rkm_failure(self):
        with patch("ultron.core.pipeline.orchestrator.analyze_repository", side_effect=Exception("DB locked")):
            res = start._init_rkm(start.ROOT)
            self.assertIsNone(res)

    def test_extract_summary_data_with_bundle(self):
        mock_bundle = MagicMock()
        mock_bundle.files = ["a.py", "b.py"]
        mock_bundle.risks = [MagicMock(impact_score=5.0, level="LOW")]
        files, risks = start._extract_summary_data(mock_bundle, start.ROOT)
        self.assertEqual(files, ["a.py", "b.py"])
        self.assertEqual(len(risks), 1)

    def test_extract_summary_data_without_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_file = os.path.join(temp_dir, "sample.py")
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write("def sample_fn(): pass\n")
            files, risks = start._extract_summary_data(None, temp_dir)
            self.assertIn("sample.py", files)
            self.assertIsInstance(risks, list)

    def test_format_top_risk(self):
        self.assertEqual(start._format_top_risk([]), "None detected")
        r1 = MagicMock(file_path="foo.py", complexity=12, impact_score=10.0)
        r2 = MagicMock(file_path="bar.py", complexity=4, impact_score=20.0)
        formatted = start._format_top_risk([r1, r2])
        self.assertEqual(formatted, "bar.py (Complexity: 4)")

    def test_print_executive_summary_resilience(self):
        # Should execute cleanly without raising
        mock_bundle = MagicMock()
        mock_bundle.files = ["a.py"]
        mock_bundle.risks = [MagicMock(file_path="a.py", complexity=3, impact_score=5.0, level="HIGH")]
        start._print_executive_summary(start.ROOT, mock_bundle)

    def test_is_port_in_use_error(self):
        e1 = OSError("Address already in use")
        self.assertTrue(start._is_port_in_use_error(e1))

        e2 = OSError(10048, "WSAEADDRINUSE")
        e2.winerror = 10048
        self.assertTrue(start._is_port_in_use_error(e2))

        e3 = OSError("Permission denied")
        self.assertFalse(start._is_port_in_use_error(e3))

    def test_open_browser_delayed(self):
        with patch("threading.Thread") as mock_thread:
            start._open_browser_delayed(8000, delay=0.01)
            mock_thread.assert_called_once()

    def test_serve_port_cases(self):
        with patch("sys.stdout", new_callable=io.StringIO):
            # 1. Normal exit
            with patch("ultron.interfaces.server.serve", return_value=None), patch("start._open_browser_delayed"):
                status = start._serve_port(8000)
                self.assertEqual(status, "STOPPED")

            # 2. Port in use
            in_use_err = OSError("Address already in use")
            with patch("ultron.interfaces.server.serve", side_effect=in_use_err), patch("start._open_browser_delayed"):
                status = start._serve_port(8000)
                self.assertEqual(status, "IN_USE")

            # 3. KeyboardInterrupt
            with patch("ultron.interfaces.server.serve", side_effect=KeyboardInterrupt), patch("start._open_browser_delayed"):
                status = start._serve_port(8000)
                self.assertEqual(status, "STOPPED")

            # 4. Other exception
            with patch("ultron.interfaces.server.serve", side_effect=ValueError("Bad arg")), patch("start._open_browser_delayed"):
                status = start._serve_port(8000)
                self.assertEqual(status, "FAILED")

    def test_run_server_loop(self):
        with patch("sys.stdout", new_callable=io.StringIO):
            with patch("start._serve_port", side_effect=["IN_USE", "STOPPED"]):
                success = start._run_server_loop([8000, 8001])
                self.assertTrue(success)

            with patch("start._serve_port", return_value="IN_USE"):
                success = start._run_server_loop([8000, 8001])
                self.assertFalse(success)

    def test_launch_ultron(self):
        with patch("sys.stdout", new_callable=io.StringIO), \
             patch("start._safe_reconfigure_console") as m_rec, \
             patch("start._init_rkm", return_value=None) as m_rkm, \
             patch("start._print_executive_summary") as m_sum, \
             patch("start._run_server_loop", return_value=True) as m_loop:
            start.launch_ultron()
            m_rec.assert_called_once()
            m_rkm.assert_called_once()
            m_sum.assert_called_once()
            m_loop.assert_called_once()


class TestTrayLauncher(unittest.TestCase):
    """Test launcher/tray_launcher.py capabilities."""

    def test_find_available_port(self):
        port = tray_launcher._find_available_port([8000, 8001, 8002])
        self.assertIn(port, [8000, 8001, 8002])

    def test_read_repo_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cfg_path = os.path.join(temp_dir, "config.json")
            with patch("launcher.tray_launcher.CONFIG_FILE", cfg_path):
                # Missing file
                self.assertIsNone(tray_launcher._read_repo_root())

                # Valid config
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump({"repo_root": temp_dir}, f)
                self.assertEqual(tray_launcher._read_repo_root(), temp_dir)

                # Invalid dir config
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump({"repo_root": os.path.join(temp_dir, "nonexistent")}, f)
                self.assertIsNone(tray_launcher._read_repo_root())

    def test_open_url(self):
        with patch("webbrowser.open") as mock_open:
            tray_launcher._open_url("http://localhost:8000")
            mock_open.assert_called_with("http://localhost:8000")

    def test_make_tray_icon(self):
        img = tray_launcher._make_tray_icon()
        self.assertEqual(img.size, (64, 64))
        self.assertEqual(img.mode, "RGBA")

    def test_build_server_cmd(self):
        with patch("os.path.isfile", return_value=False):
            cmd = tray_launcher._build_server_cmd(8000)
            self.assertEqual(cmd, [sys.executable, "-m", "ultron.interfaces.server", "--port", "8000"])

        with patch("os.path.isfile", return_value=True):
            cmd = tray_launcher._build_server_cmd(8000)
            self.assertEqual(cmd, [tray_launcher.SERVER_EXE, "--port", "8000"])

    def test_terminate_process(self):
        # None process
        tray_launcher._terminate_process(None)

        # Finished process
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        tray_launcher._terminate_process(mock_proc)
        mock_proc.terminate.assert_not_called()

        # Running process exits cleanly
        mock_proc.poll.return_value = None
        mock_proc.wait.return_value = 0
        tray_launcher._terminate_process(mock_proc)
        mock_proc.terminate.assert_called_once()

        # Running process times out -> kill
        mock_proc.reset_mock()
        mock_proc.poll.return_value = None
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired(cmd="test", timeout=5), 0]
        tray_launcher._terminate_process(mock_proc)
        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()

    def test_close_log_file(self):
        mock_handle = MagicMock()
        tray_launcher._log_file_handle = mock_handle
        tray_launcher._close_log_file()
        mock_handle.close.assert_called_once()
        self.assertIsNone(tray_launcher._log_file_handle)

    def test_build_tray_menu(self):
        menu = tray_launcher._build_tray_menu()
        self.assertIsNotNone(menu)

    def test_tray_menu_callbacks(self):
        with patch("launcher.tray_launcher._open_url") as mock_open_url, \
             patch("launcher.tray_launcher._stop_server") as mock_stop:
            mock_icon = MagicMock()
            tray_launcher._on_open_dashboard(mock_icon, None)
            mock_open_url.assert_called_with(tray_launcher._active_base_url)

            tray_launcher._on_settings(mock_icon, None)
            mock_open_url.assert_called_with(f"{tray_launcher._active_base_url}/folder_picker.html")

            tray_launcher._on_quit(mock_icon, None)
            mock_stop.assert_called_once()
            mock_icon.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
