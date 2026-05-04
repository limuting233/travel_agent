import logging
import sys

from loguru import logger

from app.core.config import settings


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    # Intercept everything that goes to standard logging
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.LOG_LEVEL)

    # Remove all existing loggers and add our own
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # Configure Loguru
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
    )

    # Optional: Add file logging
    # log_path = Path("logs")
    # log_path.mkdir(exist_ok=True)
    #
    # logger.add(
    #     str(log_path / "app.log"),
    #     rotation="500 MB",
    #     retention="10 days",
    #     compression="zip",
    #     level=settings.LOG_LEVEL,
    #     enqueue=True,
    #     format=settings.LOG_FORMAT,
    # )