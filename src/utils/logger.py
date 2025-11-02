"""Logging configuration for the automation system."""
import sys
from pathlib import Path
from loguru import logger
import os

# Get log level from environment or default to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_RETENTION = os.getenv("LOG_RETENTION_DAYS", "30")

# Remove default logger
logger.remove()

# Add console logger
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True
)

# Add file logger
log_path = Path("/app/logs/automation.log")
logger.add(
    log_path,
    rotation="500 MB",
    retention=f"{LOG_RETENTION} days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}",
    level=LOG_LEVEL
)

# Add error file logger
error_log_path = Path("/app/logs/errors.log")
logger.add(
    error_log_path,
    rotation="100 MB",
    retention=f"{LOG_RETENTION} days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}",
    level="ERROR"
)

__all__ = ["logger"]
