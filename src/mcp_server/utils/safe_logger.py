"""
SafeLogger Implementation - Separates MCP stdout from library stderr logs.

# FR-23: SafeLogger Implementation - Redirect library logs to stderr, preserve clean stdout for MCP.
# stdout contains only MCP protocol messages per AC-55.
# Library logs go to stderr per AC-56.
# Output Stream Separation Pattern (DP-8) ensures clean MCP output.
# IC-1: Implementation constraint applies.
# CPARA-2: LOGGING_LEVEL controls verbosity.

# ADR-8: Logging Strategy - SafeLogger with Output Separation
# Context: MCP protocol requires clean stdout for JSON-RPC messages, logs must not contaminate
# Decision: SafeLogger component that routes MCP messages to stdout, library logs to stderr

# Design Pattern DP-8: Output Stream Separation Pattern
# Intent: Separate MCP protocol output (stdout) from library logs (stderr)
# Usage: COMP-5 SafeLogger directs MCP messages to stdout, logs to stderr
# Implementation: Custom StreamHandler for stderr, direct stdout.write for MCP messages
"""

import logging
import sys
from enum import Enum


class LoggingLevel(Enum):
    """
    # EN-2 LoggingLevel - Server logging verbosity levels
    # Values: DEBUG (debug), INFO (info), WARN (warn), ERROR (error)
    """
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class StderrStreamHandler(logging.StreamHandler):
    """
    Custom StreamHandler that routes all log records to stderr.
    
    # Design Pattern DP-8: Custom logging handler for stderr
    # Ensures library logs go to stderr, not stdout
    """

    def __init__(self):
        """Initialize handler with stderr stream."""
        super().__init__(stream=sys.stderr)

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to stderr.
        
        Args:
            record: The log record to emit
        """
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class MCPWriter:
    """
    Writes MCP messages directly to stdout without buffering.
    
    # Design Pattern DP-8: MCPWriter for stdout - bypasses logging entirely
    # Must not buffer MCP output (DP-8 maintenance consideration)
    # Logs should not block MCP messages (DP-8 maintenance consideration)
    """

    @staticmethod
    def write(message: str) -> None:
        """
        Write MCP message directly to stdout.
        
        # AC-55: stdout contains only MCP protocol messages
        # Uses direct stdout.write() to avoid buffering
        
        Args:
            message: The MCP JSON-RPC message to write
        """
        sys.stdout.write(message)
        sys.stdout.flush()

    @staticmethod
    def write_line(message: str) -> None:
        """
        Write MCP message with newline to stdout.
        
        Args:
            message: The MCP message to write
        """
        sys.stdout.write(message + "\n")
        sys.stdout.flush()


class SafeLogger:
    """
    SafeLogger ensures clean separation between MCP protocol output (stdout)
    and library logs (stderr).
    
    # FR-23: SafeLogger Implementation
    # ADR-8: Logging Strategy with Output Separation
    # Component: COMP-5 SafeLogger
    
    Usage:
        # Configure logging
        SafeLogger.configure_logging(LoggingLevel.INFO)
        
        # Get logger for library components
        logger = SafeLogger.get_logger("my_library")
        logger.info("This goes to stderr")
        
        # Write MCP messages to stdout
        MCPWriter.write('{"jsonrpc": "2.0", "method": "notification"}')
    """

    _configured: bool = False
    _logging_level: LoggingLevel = LoggingLevel.INFO

    @classmethod
    def configure_logging(cls, level: LoggingLevel) -> None:
        """
        Configure root logger with stderr handler.
        
        # CPARA-2: LOGGING_LEVEL controls verbosity
        # Validation: MUST be one of debug, info, warn, error
        
        Args:
            level: The logging level to configure
            
        Raises:
            ValueError: If level is not a valid LoggingLevel
        """
        if not isinstance(level, LoggingLevel):
            raise ValueError(
                f"Invalid logging level: {level}. "
                f"Must be one of: {[e.value for e in LoggingLevel]}"
            )

        cls._logging_level = level
        cls._configured = True

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(cls._get_logging_level(level))

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add stderr handler
        stderr_handler = StderrStreamHandler()
        formatter = logging.Formatter(
            '%(name)s - %(levelname)s - %(message)s'
        )
        stderr_handler.setFormatter(formatter)
        root_logger.addHandler(stderr_handler)

    @classmethod
    def _get_logging_level(cls, level: LoggingLevel) -> int:
        """
        Convert LoggingLevel enum to logging module level.
        
        Args:
            level: The LoggingLevel enum value
            
        Returns:
            Corresponding logging module level
        """
        level_map = {
            LoggingLevel.DEBUG: logging.DEBUG,
            LoggingLevel.INFO: logging.INFO,
            LoggingLevel.WARN: logging.WARNING,
            LoggingLevel.ERROR: logging.ERROR,
        }
        return level_map.get(level, logging.INFO)

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance for a library component.
        
        # AC-56: Library logs go to stderr
        # All library logs are routed to stderr via StderrStreamHandler
        
        Args:
            name: The name of the logger (typically module name)
            
        Returns:
            Configured logger instance
        """
        if not cls._configured:
            cls.configure_logging(cls._logging_level)

        return logging.getLogger(name)

    @classmethod
    def mcp_write(cls, message: str) -> None:
        """
        Write MCP message to stdout.
        
        # AC-55: stdout contains only MCP protocol messages
        # MCP messages bypass logging entirely
        
        Args:
            message: The MCP JSON-RPC message
        """
        MCPWriter.write(message)

    @classmethod
    def mcp_write_line(cls, message: str) -> None:
        """
        Write MCP message with newline to stdout.
        
        Args:
            message: The MCP message
        """
        MCPWriter.write_line(message)


def configure_logging(level: str = "info") -> None:
    """
    Convenience function to configure logging from string level.
    
    # CPARA-2: LOGGING_LEVEL - validation that level is one of debug, info, warn, error
    
    Args:
        level: String representation of logging level
        
    Raises:
        ValueError: If level is not valid
    """
    try:
        logging_level = LoggingLevel(level)
        SafeLogger.configure_logging(logging_level)
    except ValueError as e:
        raise ValueError(
            f"Invalid LOGGING_LEVEL: {level}. "
            f"Must be one of: debug, info, warn, error"
        ) from e


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.
    
    Args:
        name: The logger name
        
    Returns:
        Logger instance
    """
    return SafeLogger.get_logger(name)
