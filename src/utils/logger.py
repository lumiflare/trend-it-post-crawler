"""
Logging utilities using loguru.
"""
import sys
from loguru import logger
from pathlib import Path


def setup_logger(log_level: str = "INFO", log_file: str = "logs/app.log"):
    """
    Configure loguru logger with console and file outputs.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    """
    # Remove default handler
    logger.remove()

    # Add console handler with color
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Add file handler with rotation
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="1 day",
        retention="7 days",
        compression="zip",
    )

    return logger


# Export configured logger
log = setup_logger()
