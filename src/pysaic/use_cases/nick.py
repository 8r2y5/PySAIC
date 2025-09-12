import logging
import re

from pysaic.crc_strings.use_case import random_name

logger = logging.getLogger(__name__)

NICK_PATTERN = re.compile(r"^([a-zA-Z0-9_{}\[\]\\|^-]{3,26})$")


def sanitize_nick(value: str) -> str:
    match = NICK_PATTERN.match(value)
    if not match:
        logger.warning(
            "Invalid nick format: %r, using default nick",
            value,
        )
        value = sanitize_nick(random_name().replace(" ", "_"))
    logger.debug("Sanitized nick: %s", value)
    return value[:26]
