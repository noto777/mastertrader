import logging
import logging.handlers
from pathlib import Path
import os
import config.config as cfg

def setup_logging():
    """Configure logging for the application."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File Handler with rotation
    fh = logging.handlers.RotatingFileHandler("logs/application.log", maxBytes=5*1024*1024, backupCount=2)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def get_logger(name):
    """Get a named logger."""
    return logging.getLogger(name)

def setup_logging_old():
    """Set up logging configuration."""
    # Ensure the log directory exists
    log_dir = os.path.dirname(cfg.LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging
    logging.basicConfig(
        level=cfg.LOG_LEVEL,
        format=cfg.LOG_FORMAT,
        handlers=[
            logging.FileHandler(cfg.LOG_FILE_PATH),
            logging.StreamHandler()
        ]
    )

def get_logger_old(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)

def setup_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, cfg.LOG_LEVEL.upper(), logging.INFO))

        # Console Handler
        c_handler = logging.StreamHandler()
        c_handler.setLevel(getattr(logging, cfg.LOG_LEVEL.upper(), logging.INFO))
        c_formatter = logging.Formatter(cfg.LOG_FORMAT)
        c_handler.setFormatter(c_formatter)

        # File Handler
        f_handler = logging.FileHandler(cfg.LOG_FILE_PATH)
        f_handler.setLevel(getattr(logging, cfg.LOG_LEVEL.upper(), logging.INFO))
        f_formatter = logging.Formatter(cfg.LOG_FORMAT)
        f_handler.setFormatter(f_formatter)

        # Add Handlers
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)

        # Prevent log messages from being propagated to the root logger multiple times
        logger.propagate = False

    return logger 