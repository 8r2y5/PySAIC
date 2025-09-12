import logging
from random import randint

from pysaic.settings import END_OF_ACTOR_CHARACTER, START_OF_ACTOR_CHARACTER

logger = logging.getLogger(__name__)


def make_content_malformed(original_content: str) -> str:
    if START_OF_ACTOR_CHARACTER in original_content:
        logger.debug("It is a death message, making it malformed")
        prefix, content = original_content.split(END_OF_ACTOR_CHARACTER, 1)
        content = list(content)
    else:
        logger.debug("It is a regular message, making it malformed")
        prefix = ""
        content = list(original_content)

    for index, character in enumerate(content):
        if randint(0, 5) == 0:  # 1 in 6 chance to change a character
            content[index] = (
                chr(randint(32, 126)) if randint(0, 1) else character.upper()
            )

    logger.debug(
        'Malformed content due to fake disconnect: "%s" -> "%s"',
        original_content,
        content,
    )
    return f"{prefix}{''.join(content)}"
