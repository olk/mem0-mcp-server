# Safe Logger (`mcp_server/utils/safe_logger.py`)

## Overview

SafeLogger Implementation - Separates MCP stdout from library stderr logs. Implements Output Stream Separation Pattern (DP-8) ensuring clean MCP output.

## Enums

### `LoggingLevel`

Server logging verbosity levels.

| Value | Description |
|-------|-------------|
| `DEBUG` | Debug level logging |
| `INFO` | Info level logging |
| `WARN` | Warning level logging |
| `ERROR` | Error level logging |

## Classes

### `StderrStreamHandler`

Custom StreamHandler that routes all log records to stderr.

**Inheritance:** `logging.StreamHandler`

**Methods:**
- `emit(record: logging.LogRecord) -> None`: Emit log record to stderr

### `MCPWriter`

Writes MCP messages directly to stdout without buffering.

**Static Methods:**
- `write(message: str) -> None`: Write MCP message to stdout without buffering
- `write_line(message: str) -> None`: Write MCP message with newline

**Usage:**

```python
from mcp_server.utils.safe_logger import MCPWriter

# Direct stdout write for MCP messages
MCPWriter.write('{"jsonrpc": "2.0", "method": "notification"}')
MCPWriter.write_line('{"jsonrpc": "2.0", "method": "response"}')
```

### `SafeLogger`

Ensures clean separation between MCP protocol output (stdout) and library logs (stderr).

**Class Methods:**

#### `configure_logging(level: LoggingLevel) -> None`

Configure root logger with stderr handler.

**Parameters:**
- `level` (`LoggingLevel`): The logging level to configure

**Raises:**
- `ValueError`: If level is not a valid LoggingLevel

**Usage:**

```python
from mcp_server.utils.safe_logger import SafeLogger, LoggingLevel

SafeLogger.configure_logging(LoggingLevel.INFO)
```

#### `get_logger(name: str) -> logging.Logger`

Get a logger instance for a library component. All library logs are routed to stderr.

**Parameters:**
- `name` (`str`): The name of the logger (typically module name)

**Returns:**
- `logging.Logger`: Configured logger instance

**Usage:**

```python
logger = SafeLogger.get_logger("my_library")
logger.info("This goes to stderr")
```

#### `mcp_write(message: str) -> None`

Write MCP message to stdout. MCP messages bypass logging entirely.

#### `mcp_write_line(message: str) -> None`

Write MCP message with newline to stdout.

## Convenience Functions

### `configure_logging(level: str = "info") -> None`

Convenience function to configure logging from string level.

**Parameters:**
- `level` (`str`): String representation of logging level ("debug", "info", "warn", "error")

**Raises:**
- `ValueError`: If level is not valid

### `get_logger(name: str) -> logging.Logger`

Convenience function to get a logger.

## Output Separation

```
┌─────────────────────────────────────────┐
│           Application                   │
└─────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────┐      ┌─────────────┐
│ SafeLogger  │      │  MCPWriter  │
│ (library    │      │  (MCP msgs) │
│  logs)       │      │             │
└──────┬──────┘      └──────┬──────┘
       │                    │
       ▼                    ▼
┌─────────────┐      ┌─────────────┐
│   stderr    │      │   stdout     │
│ (logs)      │      │ (MCP JSON)  │
└─────────────┘      └─────────────┘
```

## Usage Example

```python
from mcp_server.utils.safe_logger import (
    SafeLogger, MCPWriter, configure_logging, get_logger, LoggingLevel
)

# Configure logging
configure_logging("info")

# Get logger for library
logger = get_logger("mem0")
logger.info("Library log message")  # Goes to stderr

# Write MCP message directly to stdout
MCPWriter.write_line('{"jsonrpc": "2.0", "method": "tools/list"}')
```

## Design Pattern

**DP-8: Output Stream Separation Pattern**

- Intent: Separate MCP protocol output (stdout) from library logs (stderr)
- Usage: COMP-5 SafeLogger directs MCP messages to stdout, logs to stderr
- Implementation: Custom StreamHandler for stderr, direct stdout.write for MCP messages

## See Also

- [transport.py](../transport.md) - Transport module using SafeLogger