"""Logging configuration owned by preprocessing entrypoints, not library modules."""

import logging
from pathlib import Path

_HANDLER_MARKER = "_hemoflow_preprocessing"
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(
    *,
    debug: bool = False,
    log_path: Path | None = None,
) -> None:
    """Configure console and optional append-only file logging without duplicates.

    Preserve handlers installed by callers. Open the requested file before
    replacing our handlers so a file-open failure leaves console logging intact.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_path is not None:
        handlers.append(logging.FileHandler(log_path, mode="a", encoding="utf-8"))

    root = logging.getLogger()
    for handler in root.handlers[:]:
        if getattr(handler, _HANDLER_MARKER, False):
            root.removeHandler(handler)
            handler.close()

    level = logging.DEBUG if debug else logging.INFO
    root.setLevel(level)
    formatter = logging.Formatter(_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    for handler in handlers:
        setattr(handler, _HANDLER_MARKER, True)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        root.addHandler(handler)
