import contextvars
import json
import logging
import os
import sys

from core.config import LOG_LEVEL

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)


def set_correlation_id(cid: str | None):
    """Set the correlation ID for the current async execution context."""
    return _correlation_id.set(cid)


def get_correlation_id() -> str | None:
    """Retrieve the correlation ID of the current async execution context."""
    return _correlation_id.get()


class ColoredFormatter(logging.Formatter):
    RESET = "\033[0m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD_RED = "\033[1;31m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"
    PURPLE = "\033[35m"

    def format(self, record):
        cid = get_correlation_id()
        cid_str = f" {self.PURPLE}[{cid}]{self.RESET}" if cid else ""

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
            f"{self.CYAN}%(name)-12s{self.RESET}{cid_str} │ "
            f"{color}%(message)s{self.RESET}"
        )
        return logging.Formatter(log_fmt, datefmt="%H:%M:%S").format(record)


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record):
        cid = get_correlation_id()
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if cid:
            payload["correlation_id"] = cid
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        use_json = os.getenv("LOG_FORMAT", "").lower() == "json"
        if use_json:
            handler.setFormatter(StructuredJsonFormatter())
        else:
            handler.setFormatter(ColoredFormatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        logger.propagate = False
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return logger
