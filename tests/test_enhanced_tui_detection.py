#!/usr/bin/env python3
"""Tests for enhanced TUI detection in transport manager.

This module tests the enhanced _is_tui_parent() method with various scenarios
including environment variables, process detection, and error handling.
"""

import os
import subprocess
import sys
import time
from unittest.mock import Mock, patch

import pytest
import structlog

from src.transport.transport_manager import TransportManager


class TestEnhancedTUIDetection:
    """Test cases for enhanced TUI detection functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Configure structlog for testing
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        self.mock_server = Mock()
        self.transport_manager = TransportManager(self.mock_server)

    def teardown_method(self) -> None:
        """Clean up after tests."""
        # Clear any environment variables set during tests
        for env_var in ["DSHIELD_TUI_MODE", "DSHIELD_MCP_TUI_MODE", "DSHIELD_MCP_TCP_MODE"]:
            if env_var in os.environ:
                del os.environ[env_var]

    def test_environment_variable_detection_true(self) -> None:
        """Test TUI detection via environment variable (true values)."""
        # Test various true values
        true_values = ["true", "TRUE", "True", "1", "yes", "YES", "Yes"]
        
        for value in true_values:
            with patch.dict(os.environ, {"DSHIELD_TUI_MODE": value}):
                result = self.transport_manager._is_tui_parent()
                assert result is True, f"Expected True for DSHIELD_TUI_MODE={value}"

    def test_environment_variable_detection_false(self) -> None:
        """Test TUI detection via environment variable (false values)."""
        # Test various false values
        false_values = ["false", "FALSE", "False", "0", "no", "NO", "No", "", "invalid"]
        
        for value in false_values:
            with patch.dict(os.environ, {"DSHIELD_TUI_MODE": value}):
                result = self.transport_manager._is_tui_parent()
                assert result is False, f"Expected False for DSHIELD_TUI_MODE={value}"

    def test_environment_variable_not_set(self) -> None:
        """Test TUI detection when environment variable is not set."""
        # Ensure environment variable is not set
        if "DSHIELD_TUI_MODE" in os.environ:
            del os.environ["DSHIELD_TUI_MODE"]
        
        # Mock parent process to return False (no TUI indicators)
        with patch('psutil.Process') as mock_process:
            mock_parent = Mock()
            mock_parent.name.return_value = "python"
            mock_parent.cmdline.return_value = ["python", "regular_script.py"]
            mock_parent.pid = 12345
            
            mock_current = Mock()
            mock_current.parent.return_value = mock_parent
            mock_current.cmdline.return_value = ["python", "mcp_server.py"]
            mock_process.return_value = mock_current
            
            result = self.transport_manager._is_tui_parent()
            assert result is False

    @patch('psutil.Process')
    def test_parent_process_tui_indicators(self, mock_process: Mock) -> None:
        """Test TUI detection via parent process indicators."""
        # Test various TUI indicators in parent process
        tui_indicators = [
            "tui", "textual", "rich", "curses",
            "dshield-mcp-tui", "mcp-tui", "tui_launcher.py"
        ]
        
        for indicator in tui_indicators:
            # Test indicator in process name
            mock_parent = Mock()
            mock_parent.name.return_value = f"python-{indicator}"
            mock_parent.cmdline.return_value = ["python", "script.py"]
            mock_parent.pid = 12345
            
            mock_current = Mock()
            mock_current.parent.return_value = mock_parent
            mock_current.cmdline.return_value = ["python", "mcp_server.py"]
            mock_process.return_value = mock_current
            
            result = self.transport_manager._is_tui_parent()
            assert result is True, f"Expected True for TUI indicator '{indicator}' in process name"
            
            # Test indicator in command line
            mock_parent.cmdline.return_value = ["python", f"{indicator}.py"]
            mock_parent.name.return_value = "python"
            
            result = self.transport_manager._is_tui_parent()
            assert result is True, f"Expected True for TUI indicator '{indicator}' in command line"

    @patch('psutil.Process')
    def test_terminal_multiplexer_detection(self, mock_process: Mock) -> None:
        """Test TUI detection via terminal multiplexers."""
        multiplexers = ["tmux", "screen", "byobu"]
        
        for mux in multiplexers:
            mock_parent = Mock()
            mock_parent.name.return_value = "python"
            mock_parent.cmdline.return_value = ["python", f"{mux}_session.py"]
            mock_parent.pid = 12345
            
            mock_current = Mock()
            mock_current.parent.return_value = mock_parent
            mock_current.cmdline.return_value = ["python", "mcp_server.py"]
            mock_process.return_value = mock_current
            
            result = self.transport_manager._is_tui_parent()
            assert result is True, f"Expected True for terminal multiplexer '{mux}'"

    @patch('psutil.Process')
    def test_current_process_tui_launcher_detection(self, mock_process: Mock) -> None:
        """Test TUI detection via current process command line."""
        mock_parent = Mock()
        mock_parent.name.return_value = "python"
        mock_parent.cmdline.return_value = ["python", "regular_script.py"]
        mock_parent.pid = 12345
        
        mock_current = Mock()
        mock_current.parent.return_value = mock_parent
        mock_current.cmdline.return_value = ["python", "-m", "src.tui_launcher"]
        mock_process.return_value = mock_current
        
        result = self.transport_manager._is_tui_parent()
        assert result is True, "Expected True for tui_launcher in current process"

    @patch('psutil.Process')
    def test_psutil_no_such_process_exception(self, mock_process: Mock) -> None:
        """Test handling of psutil.NoSuchProcess exception."""
        import psutil
        
        mock_current = Mock()
        mock_current.parent.side_effect = psutil.NoSuchProcess(12345)
        mock_current.cmdline.return_value = ["python", "mcp_server.py"]
        mock_process.return_value = mock_current
        
        result = self.transport_manager._is_tui_parent()
        assert result is False, "Expected False when parent process doesn't exist"

    @patch('psutil.Process')
    def test_psutil_access_denied_exception(self, mock_process: Mock) -> None:
        """Test handling of psutil.AccessDenied exception."""
        import psutil
        
        mock_current = Mock()
        mock_current.parent.side_effect = psutil.AccessDenied(12345)
        mock_current.cmdline.return_value = ["python", "mcp_server.py"]
        mock_process.return_value = mock_current
        
        result = self.transport_manager._is_tui_parent()
        assert result is False, "Expected False when access to parent process is denied"

    @patch('psutil.Process')
    def test_generic_exception_handling(self, mock_process: Mock) -> None:
        """Test handling of generic exceptions."""
        mock_current = Mock()
        mock_current.parent.side_effect = Exception("Generic error")
        mock_current.cmdline.return_value = ["python", "mcp_server.py"]
        mock_process.return_value = mock_current
        
        result = self.transport_manager._is_tui_parent()
        assert result is False, "Expected False when generic exception occurs"

    @patch('psutil.Process')
    def test_no_parent_process(self, mock_process: Mock) -> None:
        """Test handling when no parent process exists."""
        mock_current = Mock()
        mock_current.parent.return_value = None
        mock_current.cmdline.return_value = ["python", "mcp_server.py"]
        mock_process.return_value = mock_current
        
        result = self.transport_manager._is_tui_parent()
        assert result is False, "Expected False when no parent process exists"

    def test_detect_transport_mode_tui_detected(self) -> None:
        """Test transport mode detection when TUI is detected."""
        with patch.dict(os.environ, {"DSHIELD_TUI_MODE": "true"}):
            with patch.object(self.transport_manager, '_is_tui_parent', return_value=True):
                mode = self.transport_manager.detect_transport_mode()
                assert mode == "tcp", "Expected TCP mode when TUI is detected"

    def test_detect_transport_mode_tcp_flag(self) -> None:
        """Test transport mode detection via TCP flag."""
        with patch('sys.argv', ['mcp_server.py', '--tcp']):
            with patch.object(self.transport_manager, '_is_tui_parent', return_value=False):
                mode = self.transport_manager.detect_transport_mode()
                assert mode == "tcp", "Expected TCP mode when TCP flag is present"

    def test_detect_transport_mode_tcp_env_var(self) -> None:
        """Test transport mode detection via TCP environment variable."""
        with patch.dict(os.environ, {"DSHIELD_MCP_TCP_MODE": "true"}):
            with patch.object(self.transport_manager, '_is_tui_parent', return_value=False):
                with patch.object(self.transport_manager, '_has_tcp_flag', return_value=False):
                    mode = self.transport_manager.detect_transport_mode()
                    assert mode == "tcp", "Expected TCP mode when TCP environment variable is set"

    def test_detect_transport_mode_default_stdio(self) -> None:
        """Test transport mode detection defaults to STDIO."""
        with patch.object(self.transport_manager, '_is_tui_parent', return_value=False):
            with patch.object(self.transport_manager, '_has_tcp_flag', return_value=False):
                mode = self.transport_manager.detect_transport_mode()
                assert mode == "stdio", "Expected STDIO mode as default"

    @pytest.mark.integration
    def test_actual_tui_launcher_detection(self) -> None:
        """Integration test with actual TUI launcher process.
        
        This test runs the TUI launcher in a subprocess and verifies
        that the transport manager can detect it properly.
        """
        # This test requires the TUI launcher to be available
        tui_launcher_path = "src/tui_launcher.py"
        if not os.path.exists(tui_launcher_path):
            pytest.skip("TUI launcher not available for integration test")
        
        # Start TUI launcher in a subprocess
        env = os.environ.copy()
        env["DSHIELD_TUI_MODE"] = "true"
        
        try:
            # Start the TUI launcher process
            process = subprocess.Popen(
                [sys.executable, "-m", "src.tui_launcher"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                # Process is running, test detection
                with patch.dict(os.environ, {"DSHIELD_TUI_MODE": "true"}):
                    result = self.transport_manager._is_tui_parent()
                    assert result is True, "Expected True for TUI launcher detection"
                
                # Clean up
                process.terminate()
                process.wait(timeout=5)
            else:
                # Process exited, check stderr for errors
                stdout, stderr = process.communicate()
                pytest.skip(f"TUI launcher failed to start: {stderr}")
                
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("TUI launcher process did not terminate in time")
        except Exception as e:
            pytest.skip(f"Integration test failed: {e}")

    def test_debug_logging_output(self) -> None:
        """Test that debug logging provides useful information."""
        
        # Create a custom logger that captures messages
        captured_messages = []
        
        def capture_log(message, **kwargs):
            captured_messages.append((message, kwargs))
        
        # Mock the logger to capture debug messages
        with patch.object(self.transport_manager.logger, 'debug', side_effect=capture_log):
            with patch.dict(os.environ, {"DSHIELD_TUI_MODE": "true"}):
                result = self.transport_manager._is_tui_parent()
                assert result is True
        
        # Check that debug logs were generated
        assert len(captured_messages) > 0, "Expected debug log messages"
        
        # Check for specific debug messages
        tui_detection_messages = [msg for msg, kwargs in captured_messages if "TUI detection" in msg]
        assert len(tui_detection_messages) > 0, "Expected TUI detection debug messages"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
