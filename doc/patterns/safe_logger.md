# SafeLogger Output Separation Pattern

## Overview

The SafeLogger Output Separation Pattern separates MCP protocol output (stdout) from library logs (stderr), ensuring clean stdout for JSON-RPC messages.

## Problem

MCP protocol requires clean stdout for JSON-RPC messages. If library logs contaminate stdout:
- MCP client receives corrupted messages
- JSON parsing fails
- Protocol broken

## Solution

Two-output strategy:
1. MCP messages → stdout (via MCPWriter)
2. Library logs → stderr (via StderrStreamHandler)

```python
class StderrStreamHandler(logging.StreamHandler):
    """Custom handler that routes all logs to stderr."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

class MCPWriter:
    """Writes MCP messages directly to stdout without buffering."""
    @staticmethod
    def write(message: str) -> None:
        sys.stdout.write(message)
        sys.stdout.flush()
```

## Output Architecture

```
┌─────────────────────────────────────────┐
│           Application Code              │
└─────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│  SafeLogger     │  │   MCPWriter     │
│  (library logs) │  │  (MCP messages) │
└────────┬────────┘  └────────┬────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│     stderr      │  │     stdout      │
│   (logs)        │  │   (JSON-RPC)    │
└─────────────────┘  └─────────────────┘
```

## Configuration

```python
class SafeLogger:
    _configured: bool = False
    _logging_level: LoggingLevel = LoggingLevel.INFO

    @classmethod
    def configure_logging(cls, level: LoggingLevel) -> None:
        """Configure root logger with stderr handler."""
        root_logger = logging.getLogger()
        root_logger.setLevel(cls._get_logging_level(level))

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add stderr handler
        stderr_handler = StderrStreamHandler()
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        stderr_handler.setFormatter(formatter)
        root_logger.addHandler(stderr_handler)
```

## Usage

```python
from mcp_server.utils.safe_logger import (
    SafeLogger, MCPWriter, configure_logging, LoggingLevel
)

# Configure logging
configure_logging("info")

# Library logs go to stderr
logger = SafeLogger.get_logger("mem0")
logger.info("This is a library log message")  # → stderr

# MCP messages go to stdout
MCPWriter.write('{"jsonrpc": "2.0", "method": "response"}')  # → stdout
```

## Constraints

- **FR-23**: SafeLogger Implementation
- **AC-55**: stdout contains only MCP protocol messages
- **AC-56**: Library logs go to stderr
- **CPARA-2**: LOGGING_LEVEL controls verbosity
- **IC-1**: No global state for MCP messages

## Benefits

| Benefit | Description |
|---------|-------------|
| **Protocol compliance** | Clean stdout for MCP |
| **Debuggability** | Library logs visible on stderr |
| **No buffering** | MCPWriter flushes immediately |
| **Configurable** | LOGGING_LEVEL controls verbosity |

## Maintenance Considerations

- MCPWriter must not buffer output (prevents latency)
- Logs should not block MCP messages
- Use direct stdout.write() not print()

## Related Patterns

- [Transport Strategy Pattern](./transport_strategy.md) - Transport selection

## ADR Reference

- ADR-8: SafeLogger Output Separation

## Implementation Files

- `src/mcp_server/utils/safe_logger.py`
