import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


def setup_logger() -> logging.Logger:
    """
    Sets up a centralized, production-ready logging configuration.
    
    Features:
    - Console logging for development and containerized environments.
    - File logging with rotation to prevent logs from growing indefinitely.
    - Standardized formatting.
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Logger initialization
    logger = logging.getLogger("crimelens")
    
    # Prevent duplicate logs if the logger is retrieved multiple times
    if logger.hasHandlers():
        return logger
        
    if settings.ENVIRONMENT == "development":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 1. Console Handler (Useful for Docker / standard output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # 2. File Handler (Rotating file handler to manage log size)
    # Max size: 5 MB, Backup count: 5 files
    file_handler = RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    mlops_handler = RotatingFileHandler(
        filename=log_dir / "mlops.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
    )
    mlops_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(mlops_handler)

    logging.getLogger("crimelens.mlops").addHandler(mlops_handler)
    logging.getLogger("crimelens.mlops").setLevel(logger.level)
    
    # Set levels for third party loggers to prevent noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.ENVIRONMENT == "development" else logging.WARNING
    )
    
    return logger

# Export a configured logger instance
logger = setup_logger()
