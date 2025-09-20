from logging import Handler
from logging.handlers import RotatingFileHandler

from pysaic.entities import IncomingEvent
from pysaic.enums import AppEventEnum
from pysaic.log.utils import escape_stand_and_end
from pysaic.use_cases.ui.utils import normalize_content


class PySAICRotatingFileHandler(RotatingFileHandler):
    def format(self, record):
        return normalize_content(escape_stand_and_end(super().format(record)))


class PySAICIRCLoggingHandler(Handler):
    def __init__(self, incoming_queue):
        super().__init__()
        self.incoming_queue = incoming_queue

    def emit(self, record):
        self.incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                what=AppEventEnum.RAW_IRC_MESSAGE,
                payload=record,
            )
        )
