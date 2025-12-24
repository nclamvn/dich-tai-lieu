#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Structured Logging Configuration for AI Translator Pro

Enterprise-grade logging with rotation, formatting, and error tracking.
"""

import logging
import logging.handlers
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


# ============================================================================
# Log Levels & Configuration
# ============================================================================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


# ============================================================================
# Structured Log Record
# ============================================================================

@dataclass
class StructuredLogRecord:
    """Structured log record for JSON logging."""
    timestamp: str
    level: str
    logger: str
    message: str
    module: str
    function: str
    line_no: int

    # Optional context
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None

    # Error details
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None

    # Performance metrics
    duration_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None

    # Additional metadata
    extra: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


# ============================================================================
# Custom JSON Formatter
# ============================================================================

class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON string."""
        # Extract exception info if present
        exception_type = None
        exception_message = None
        stack_trace = None

        if record.exc_info:
            exception_type = record.exc_info[0].__name__ if record.exc_info[0] else None
            exception_message = str(record.exc_info[1]) if record.exc_info[1] else None
            stack_trace = ''.join(traceback.format_exception(*record.exc_info))

        # Build structured record
        structured = StructuredLogRecord(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            module=record.module,
            function=record.funcName,
            line_no=record.lineno,
            exception_type=exception_type,
            exception_message=exception_message,
            stack_trace=stack_trace,
            extra=getattr(record, 'extra', None),
        )

        # Add context from record attributes
        if hasattr(record, 'job_id'):
            structured.job_id = record.job_id
        if hasattr(record, 'user_id'):
            structured.user_id = record.user_id
        if hasattr(record, 'request_id'):
            structured.request_id = record.request_id
        if hasattr(record, 'duration_ms'):
            structured.duration_ms = record.duration_ms
        if hasattr(record, 'tokens_used'):
            structured.tokens_used = record.tokens_used
        if hasattr(record, 'cost_usd'):
            structured.cost_usd = record.cost_usd

        return json.dumps(structured.to_dict(), ensure_ascii=False)


# ============================================================================
# Human-Readable Formatter
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Colorized formatter for console output."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format with colors for console."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        # Build message
        msg = f"{color}[{record.levelname}]{reset} {timestamp} - {record.name} - {record.getMessage()}"

        # Add context if present
        context_parts = []
        if hasattr(record, 'job_id'):
            context_parts.append(f"job_id={record.job_id}")
        if hasattr(record, 'duration_ms'):
            context_parts.append(f"duration={record.duration_ms:.2f}ms")
        if hasattr(record, 'tokens_used'):
            context_parts.append(f"tokens={record.tokens_used}")

        if context_parts:
            msg += f" [{', '.join(context_parts)}]"

        # Add exception if present
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"

        return msg


# ============================================================================
# Logger Setup Function
# ============================================================================

def setup_logger(
    name: str = "ai_translator",
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    json_format: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Setup a logger with file rotation and optional JSON formatting.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Enable file logging
        log_to_console: Enable console logging
        json_format: Use JSON format (for file logs)
        max_bytes: Max file size before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVELS.get(level, logging.INFO))
    logger.propagate = False

    # Clear existing handlers
    logger.handlers.clear()

    # File handler with rotation
    if log_to_file:
        if json_format:
            log_file = LOG_DIR / f"{name}.json.log"
            formatter = JSONFormatter()
        else:
            log_file = LOG_DIR / f"{name}.log"
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(LOG_LEVELS.get(level, logging.INFO))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(LOG_LEVELS.get(level, logging.INFO))
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)

    return logger


# ============================================================================
# Context Logger (with extra fields)
# ============================================================================

class ContextLogger:
    """Logger wrapper that adds context to all log calls."""

    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize context logger.

        Args:
            logger: Base logger
            **context: Context fields (job_id, user_id, etc.)
        """
        self.logger = logger
        self.context = context

    def _log(self, level: int, msg: str, *args, **kwargs):
        """Log with context."""
        extra = kwargs.pop('extra', {})
        extra.update(self.context)
        self.logger.log(level, msg, *args, extra=extra, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with context."""
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Log info message with context."""
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with context."""
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log error message with context."""
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Log critical message with context."""
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """Log exception with context."""
        kwargs['exc_info'] = True
        self._log(logging.ERROR, msg, *args, **kwargs)


# ============================================================================
# Pre-configured Loggers
# ============================================================================

# Main application logger
app_logger = setup_logger(
    name="ai_translator",
    level="INFO",
    log_to_file=True,
    log_to_console=True,
    json_format=False
)

# API logger (JSON format)
api_logger = setup_logger(
    name="api",
    level="INFO",
    log_to_file=True,
    log_to_console=False,
    json_format=True
)

# Error logger (all errors)
error_logger = setup_logger(
    name="errors",
    level="ERROR",
    log_to_file=True,
    log_to_console=True,
    json_format=True
)

# Performance logger
perf_logger = setup_logger(
    name="performance",
    level="INFO",
    log_to_file=True,
    log_to_console=False,
    json_format=True
)


# ============================================================================
# Convenience Functions
# ============================================================================

def log_api_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    request_id: Optional[str] = None,
):
    """Log API request with structured data."""
    api_logger.info(
        f"{method} {endpoint} - {status_code}",
        extra={
            'request_id': request_id,
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'duration_ms': duration_ms,
        }
    )


def log_translation_job(
    job_id: str,
    status: str,
    duration_ms: Optional[float] = None,
    tokens_used: Optional[int] = None,
    cost_usd: Optional[float] = None,
):
    """Log translation job with metrics."""
    perf_logger.info(
        f"Job {job_id}: {status}",
        extra={
            'job_id': job_id,
            'status': status,
            'duration_ms': duration_ms,
            'tokens_used': tokens_used,
            'cost_usd': cost_usd,
        }
    )


def log_error_with_context(
    error: Exception,
    context: Dict[str, Any],
    logger: Optional[logging.Logger] = None,
):
    """Log error with full context and stack trace."""
    log = logger or error_logger
    log.error(
        f"Error: {str(error)}",
        exc_info=True,
        extra={'error_context': context}
    )


# ============================================================================
# Usage Example (for documentation)
# ============================================================================

if __name__ == "__main__":
    # Example usage
    app_logger.info("Application started")

    # With context
    ctx_logger = ContextLogger(app_logger, job_id="job_123", user_id="user_456")
    ctx_logger.info("Processing translation job")

    # API request logging
    log_api_request("POST", "/api/jobs", 201, 45.5, request_id="req_789")

    # Performance logging
    log_translation_job("job_123", "completed", duration_ms=1234.5, tokens_used=500, cost_usd=0.01)

    # Error logging
    try:
        raise ValueError("Test error")
    except Exception as e:
        log_error_with_context(e, {"job_id": "job_123", "step": "translation"})

    print("✅ Logging system configured successfully!")
    print(f"📁 Log files location: {LOG_DIR.absolute()}")
