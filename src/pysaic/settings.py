import os
from pathlib import Path

from packaging.version import Version

START_OF_ACTOR_CHARACTER = "☻"
END_OF_ACTOR_CHARACTER = "☺"
VERSION = "0.3.0b6"
CURRENT_VERSION = Version(VERSION)
SUPPORTED_SCRIPT_VERSION = (12,)
APP_IDENTITY = f"PySAIC {VERSION}"

# logs
MAX_BYTES = 2 * 1024 * 1024  # 2 mb
NUMBER_OF_BACKUPS = 5

# paths
avatar_images_path = (
    Path(os.path.abspath(os.path.dirname(__file__))) / "avatar"
)
WORKDIR = Path(os.getcwd())

# If running from src/pysaic directory, this only happens during development
if WORKDIR.parts[-2:] == ("src", "pysaic"):
    WORKDIR = (WORKDIR / ".." / "..").resolve()
    GAMEDATA_PATH = (WORKDIR / "gamedata").resolve()

elif (WORKDIR / "gamedata").exists():
    GAMEDATA_PATH = (WORKDIR / "gamedata").resolve()

else:
    # this happens during exe runtime
    GAMEDATA_PATH = (WORKDIR / ".." / "gamedata").resolve()

RES_PATH = (GAMEDATA_PATH / ".." / "res").resolve()
LOCATIONS_FOR_ENUM_PATH = RES_PATH / "locations.yml"

ANOMALY_DIR_PATH = (os.environ.get("ANOMALY_DIR_PATH") or "").strip()
if ANOMALY_DIR_PATH:
    ANOMALY_DIR_PATH = Path(ANOMALY_DIR_PATH)
DEBUG = os.environ.get("PYSAIC_DEBUG", "0") == "1"


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
            "pysaic.tasks.outgoing_queue": {
                "handlers": ["default", "app", "error"],
                "level": "INFO",
                "propagate": False,
            },
            "pysaic.script_reader": {
                "handlers": ["default", "reader_log"],
                "level": "INFO",
                "propagate": False,
            },
            "pysaic.ui.options": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "pysaic.ui.hyper_links": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "pysaic.controllers.game": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "pysaic.irc_protocol": {
                "handlers": ["default", "app", "error"],
                "level": "INFO",
                "propagate": False,
            },
            "pysaic.router": {
                "handlers": ["default", "app", "error"],
                "level": "INFO",
                "propagate": False,
            },
            "pysaic.use_cases": {
                "handlers": ["default", "app", "error"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
