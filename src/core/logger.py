import logging
import sys

from core.config import LOG_LEVEL


class ColoredFormatter(logging.Formatter):
    RESET = "\033[0m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD_RED = "\033[1;31m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    def format(self, record):
        colors = {
            logging.DEBUG: self.CYAN,
            logging.INFO: self.GREEN,
            logging.WARNING: self.YELLOW,
            logging.ERROR: self.RED,
            logging.CRITICAL: self.BOLD_RED,
        }
        color = colors.get(record.levelno, self.WHITE)
        log_fmt = (
            f"{self.GRAY}%(asctime)s{self.RESET} │ "
            f"{color}%(levelname)-8s{self.RESET} │ "
            f"{self.CYAN}%(name)-12s{self.RESET} │ "
            f"{color}%(message)s{self.RESET}"
        )
        return logging.Formatter(log_fmt, datefmt="%H:%M:%S").format(record)


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredFormatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        logger.propagate = False
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return logger
