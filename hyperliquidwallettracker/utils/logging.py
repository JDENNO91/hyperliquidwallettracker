"""
Modern structured logging for HyperLiquidWalletTracker.

This module provides structured logging using structlog with JSON output,
correlation IDs, and comprehensive context tracking.
"""

import logging
import sys
from typing import Any, Dict, Optional
import structlog
from structlog.stdlib import LoggerFactory


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    include_timestamp: bool = True,
    include_level: bool = True,
    include_logger_name: bool = True
) -> None:
    """
    Setup structured logging for HyperLiquidWalletTracker.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Output format (json, console)
        include_timestamp: Include timestamps in logs
        include_level: Include log level in output
        include_logger_name: Include logger name in output
    """
    # Configure structlog
    processors = []
    
    if include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="ISO"))
    
    if include_level:
        processors.append(structlog.processors.add_log_level)
    
    if include_logger_name:
        processors.append(structlog.stdlib.add_logger_name)
    
    processors.extend([
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ])
    
    if format_type == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )
    
    # Set specific logger levels
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add structured logging to any class."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)


class ContextLogger:
    """Logger with persistent context for tracking operations."""
    
    def __init__(self, name: str, **context: Any):
        """
        Initialize context logger.
        
        Args:
            name: Logger name
            **context: Initial context to bind to all log messages
        """
        self.logger = get_logger(name)
        self.context = context
    
    def bind(self, **kwargs: Any) -> "ContextLogger":
        """
        Create new logger with additional context.
        
        Args:
            **kwargs: Additional context to bind
            
        Returns:
            New ContextLogger with combined context
        """
        new_context = {**self.context, **kwargs}
        return ContextLogger(self.logger.name, **new_context)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with context."""
        self.logger.debug(message, **{**self.context, **kwargs})
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with context."""
        self.logger.info(message, **{**self.context, **kwargs})
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with context."""
        self.logger.warning(message, **{**self.context, **kwargs})
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with context."""
        self.logger.error(message, **{**self.context, **kwargs})
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with context."""
        self.logger.critical(message, **{**self.context, **kwargs})
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, **{**self.context, **kwargs})
