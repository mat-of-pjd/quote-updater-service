import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    Path("logs").mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # File
    file_handler = RotatingFileHandler(
        "logs/order_watcher.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)