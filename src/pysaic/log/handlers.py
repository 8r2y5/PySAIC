from logging.handlers import RotatingFileHandler

from pysaic.log.utils import escape_stand_and_end
from pysaic.use_cases.ui.utils import normalize_content


class PySAICRotatingFileHandler(RotatingFileHandler):
    def format(self, record):
        return normalize_content(escape_stand_and_end(super().format(record)))
