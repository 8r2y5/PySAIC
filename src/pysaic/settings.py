import os

START_OF_ACTOR_CHARACTER = "☻"
END_OF_ACTOR_CHARACTER = "☺"
VERSION = "0.2.0"
SUPPORTED_SCRIPT_VERSION = 9
APP_IDENTITY = f"PySAIC {VERSION}"

# logs
MAX_BYTES = 2 * 1024 * 1024  # 2 mb
NUMBER_OF_BACKUPS = 5


def get_log_config():
    PROJECT_PATH = "."
    LOG_DIR = os.path.join(PROJECT_PATH, "logs")
    LOG_FILE_PATH = os.path.join(LOG_DIR, "pysaic.log")
    ERROR_LOG_FILE_PATH = os.path.join(LOG_DIR, "pysaic_error.log")
    READER_LOG_FILE_PATH = os.path.join(LOG_DIR, "pysaic_reader.log")

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(levelname)-9s - %(name)-30s - %(message)s"
            }
        },
        "handlers": {
            "default": {
                "level": "DEBUG",
                "formatter": "standard",
                "class": "logging.StreamHandler",
            },
            "app": {
                "level": "DEBUG",
                "formatter": "standard",
                "class": "pysaic.log.handlers.PySAICRotatingFileHandler",
                "filename": LOG_FILE_PATH,
                "maxBytes": MAX_BYTES,
                "backupCount": NUMBER_OF_BACKUPS,
            },
            "error": {
                "level": "ERROR",
                "formatter": "standard",
                "class": "pysaic.log.handlers.PySAICRotatingFileHandler",
                "filename": ERROR_LOG_FILE_PATH,
                "maxBytes": MAX_BYTES,
                "backupCount": NUMBER_OF_BACKUPS,
            },
            "reader_log": {
                "level": "INFO",
                "formatter": "standard",
                "class": "pysaic.log.handlers.PySAICRotatingFileHandler",
                "filename": READER_LOG_FILE_PATH,
                "maxBytes": MAX_BYTES,
                "backupCount": NUMBER_OF_BACKUPS,
            },
        },
        "loggers": {
            "pysaic": {
                "handlers": ["default", "app", "error"],
                "level": "INFO",
                "propagate": True,
            },
            "pysaic.script_reader": {
                "handlers": ["default", "reader_log"],
                "level": "DEBUG",
                "propagate": False,
            },
            "pysaic.ui.options": {
                "handlers": ["default"],
                "level": "DEBUG",
                "propagate": False,
            },
            "pysaic.controllers.game": {
                "handlers": ["default"],
                "level": "DEBUG",
                "propagate": False,
            },
            "pysaicr.irc_protocol": {
                "handlers": ["default", "app", "error"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
