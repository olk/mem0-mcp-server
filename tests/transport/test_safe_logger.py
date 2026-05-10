"""
Unit tests for SafeLogger implementation.

# UT-10: Test SafeLogger output stream separation
# Validates: FR-23
# Scenarios:
#   - SCEN-28: MCP protocol output to stdout
#   - SCEN-29: library logs go to stderr
#   - SCEN-30: clean separation verified

# Acceptance Criteria:
#   - AC-55: stdout contains only MCP protocol messages
#   - AC-56: Library logs go to stderr

# Design Pattern: DP-8 Output Stream Separation Pattern
"""

import io
import logging
import sys

import pytest

from mcp_server.utils.safe_logger import (
    LoggingLevel,
    MCPWriter,
    SafeLogger,
    StderrStreamHandler,
    configure_logging,
    get_logger,
)


class TestLoggingLevel:
    """Test LoggingLevel enum."""

    def test_logging_level_values(self):
        """# EN-2: Verify LoggingLevel enum values"""
        assert LoggingLevel.DEBUG.value == "debug"
        assert LoggingLevel.INFO.value == "info"
        assert LoggingLevel.WARN.value == "warn"
        assert LoggingLevel.ERROR.value == "error"

    def test_logging_level_from_string(self):
        """Test creating LoggingLevel from string."""
        assert LoggingLevel("debug") == LoggingLevel.DEBUG
        assert LoggingLevel("info") == LoggingLevel.INFO
        assert LoggingLevel("warn") == LoggingLevel.WARN
        assert LoggingLevel("error") == LoggingLevel.ERROR


class TestStderrStreamHandler:
    """Test StderrStreamHandler class."""

    def test_handler_uses_stderr(self):
        """# DP-8: Verify handler routes to stderr"""
        handler = StderrStreamHandler()
        assert handler.stream == sys.stderr


class TestMCPWriter:
    """Test MCPWriter class."""

    def test_write_to_stdout(self):
        """# SCEN-28: MCP protocol output to stdout"""
        captured = io.StringIO()
        original_stdout = sys.stdout

        try:
            sys.stdout = captured
            MCPWriter.write("test message")
        finally:
            sys.stdout = original_stdout

        assert captured.getvalue() == "test message"

    def test_write_flushes(self):
        """Verify write also flushes."""
        captured = io.StringIO()
        original_stdout = sys.stdout

        try:
            sys.stdout = captured
            MCPWriter.write("test")
            # If not flushed, value might be empty or partial
            # After write and flush, value should be complete
            assert captured.getvalue() == "test"
        finally:
            sys.stdout = original_stdout

    def test_write_line_newline(self):
        """Test write_line adds newline."""
        captured = io.StringIO()
        original_stdout = sys.stdout

        try:
            sys.stdout = captured
            MCPWriter.write_line("test message")
        finally:
            sys.stdout = original_stdout

        assert captured.getvalue() == "test message\n"


class TestSafeLogger:
    """Test SafeLogger class."""

    def test_configure_logging_accepts_valid_level(self):
        """# CPARA-2: LOGGING_LEVEL validation - valid levels"""
        # Should not raise
        SafeLogger.configure_logging(LoggingLevel.INFO)

    def test_configure_logging_rejects_invalid_level(self):
        """# CPARA-2: LOGGING_LEVEL validation - invalid level raises ValueError"""
        with pytest.raises(ValueError):
            SafeLogger.configure_logging("invalid"  )  # type: ignore

    def test_get_logger_returns_logger_instance(self):
        """Test get_logger returns logger instance."""
        SafeLogger.configure_logging(LoggingLevel.INFO)
        logger = SafeLogger.get_logger("test_logger")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_logs_to_stderr(self):
        """# SCEN-29: library logs go to stderr"""
        # Capture stderr
        stderr_captured = io.StringIO()
        original_stderr = sys.stderr

        try:
            sys.stderr = stderr_captured
            SafeLogger.configure_logging(LoggingLevel.DEBUG)
            logger = SafeLogger.get_logger("test_lib")
            logger.warning("test warning message")
        finally:
            sys.stderr = original_stderr

        # Verify log went to stderr
        assert "test warning message" in stderr_captured.getvalue()
        assert "test_lib" in stderr_captured.getvalue()

    def test_mcp_write_to_stdout(self):
        """# SCEN-28: MCP protocol output to stdout"""
        stdout_captured = io.StringIO()
        original_stdout = sys.stdout

        try:
            sys.stdout = stdout_captured
            SafeLogger.configure_logging(LoggingLevel.INFO)
            SafeLogger.mcp_write("mcp message")
        finally:
            sys.stdout = original_stdout

        assert stdout_captured.getvalue() == "mcp message"

    def test_mcp_write_line_to_stdout(self):
        """Test mcp_write_line outputs to stdout."""
        stdout_captured = io.StringIO()
        original_stdout = sys.stdout

        try:
            sys.stdout = stdout_captured
            SafeLogger.mcp_write_line("mcp message")
        finally:
            sys.stdout = original_stdout

        assert stdout_captured.getvalue() == "mcp message\n"


class TestConfigureLoggingFunction:
    """Test configure_logging convenience function."""

    def test_configure_logging_string_debug(self):
        """# CPARA-2: LOGGING_LEVEL - debug level"""
        # Should not raise
        configure_logging("debug")

    def test_configure_logging_string_info(self):
        """# CPARA-2: LOGGING_LEVEL - info level"""
        configure_logging("info")

    def test_configure_logging_string_warn(self):
        """# CPARA-2: LOGGING_LEVEL - warn level"""
        configure_logging("warn")

    def test_configure_logging_string_error(self):
        """# CPARA-2: LOGGING_LEVEL - error level"""
        configure_logging("error")

    def test_configure_logging_invalid_raises_valueerror(self):
        """# CPARA-2: LOGGING_LEVEL validation - invalid raises ValueError"""
        with pytest.raises(ValueError):
            configure_logging("invalid_level")


class TestGetLoggerFunction:
    """Test get_logger convenience function."""

    def test_get_logger_returns_logger(self):
        """Test convenience function returns logger."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)


class TestOutputSeparation:
    """# SCEN-30: Clean separation verified - tests that stdout and stderr are properly separated."""

    def test_mcp_message_on_stdout_not_stderr(self):
        """# AC-55: stdout contains only MCP protocol messages"""
        stdout_captured = io.StringIO()
        stderr_captured = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            sys.stdout = stdout_captured
            sys.stderr = stderr_captured

            SafeLogger.configure_logging(LoggingLevel.INFO)
            SafeLogger.mcp_write("mcp protocol message")

            # Verify stdout has MCP message
            assert stdout_captured.getvalue() == "mcp protocol message"
            # Verify stderr does NOT have MCP message
            assert stderr_captured.getvalue() == ""
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def test_library_log_on_stderr_not_stdout(self):
        """# AC-56: Library logs go to stderr"""
        stdout_captured = io.StringIO()
        stderr_captured = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            sys.stdout = stdout_captured
            sys.stderr = stderr_captured

            SafeLogger.configure_logging(LoggingLevel.INFO)
            logger = SafeLogger.get_logger("test_lib")
            logger.info("library log message")

            # Verify stderr has log message
            assert "library log message" in stderr_captured.getvalue()
            # Verify stdout does NOT have log message
            assert stdout_captured.getvalue() == ""
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def test_clean_separation_mcp_and_logs(self):
        """# SCEN-30: clean separation verified - both streams used correctly"""
        stdout_captured = io.StringIO()
        stderr_captured = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            sys.stdout = stdout_captured
            sys.stderr = stderr_captured

            SafeLogger.configure_logging(LoggingLevel.DEBUG)
            logger = SafeLogger.get_logger("test_lib")

            # Write MCP message
            SafeLogger.mcp_write('{"jsonrpc": "2.0", "method": "notify"}')

            # Write log message
            logger.debug("debug message")

            # Verify stdout has ONLY MCP message
            stdout_value = stdout_captured.getvalue()
            assert '{"jsonrpc": "2.0", "method": "notify"}' in stdout_value
            assert "debug message" not in stdout_value

            # Verify stderr has ONLY log message
            stderr_value = stderr_captured.getvalue()
            assert "debug message" in stderr_value
            assert '{"jsonrpc"' not in stderr_value
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def test_multiple_mcp_messages_all_on_stdout(self):
        """Verify multiple MCP messages all go to stdout."""
        stdout_captured = io.StringIO()
        original_stdout = sys.stdout

        try:
            sys.stdout = stdout_captured
            SafeLogger.configure_logging(LoggingLevel.INFO)

            SafeLogger.mcp_write('{"id": 1}')
            SafeLogger.mcp_write('{"id": 2}')
            SafeLogger.mcp_write('{"id": 3}')

            stdout_value = stdout_captured.getvalue()
            assert stdout_value == '{"id": 1}{"id": 2}{"id": 3}'
        finally:
            sys.stdout = original_stdout

    def test_multiple_log_messages_all_on_stderr(self):
        """Verify multiple log messages all go to stderr."""
        stderr_captured = io.StringIO()
        original_stderr = sys.stderr

        try:
            sys.stderr = stderr_captured
            SafeLogger.configure_logging(LoggingLevel.DEBUG)
            logger = SafeLogger.get_logger("test_lib")

            logger.debug("debug 1")
            logger.info("info 1")
            logger.warning("warn 1")

            stderr_value = stderr_captured.getvalue()
            assert "debug 1" in stderr_value
            assert "info 1" in stderr_value
            assert "warn 1" in stderr_value
        finally:
            sys.stderr = original_stderr
