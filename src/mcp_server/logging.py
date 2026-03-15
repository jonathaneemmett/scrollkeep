import logging
import os


def setup_logging() -> logging.Logger:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger("mcp_server")
    logger.setLevel(getattr(logging, level, logging.INFO))

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
