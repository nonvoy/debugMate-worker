import logging
from functools import lru_cache

from src.config.basic_config import get_config


@lru_cache()
def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger instance."""
    config = get_config()

    logger = logging.getLogger(name)
    logger.setLevel(config.log_level)
    logger.propagate = False  # Prevent log messages from being propagated to the root logger

    handler = logging.StreamHandler()
    handler.setLevel(config.log_level)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

    return logger
