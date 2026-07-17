import logging

from app.core.config import settings


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format=(
            "%(asctime)s %(levelname)s %(name)s "
            "%(message)s"
        ),
    )
    return logging.getLogger("polaris")
