from datetime import datetime
from logging import Handler, LogRecord
from logging.handlers import RotatingFileHandler

from pysaic.entities import IncomingEvent
from pysaic.enums import AppEventEnum
from pysaic.log.utils import escape_stand_and_end
from pysaic.use_cases.ui.utils import normalize_content


class PySAICRotatingFileHandler(RotatingFileHandler):
    def format(self, record):
        return normalize_content(escape_stand_and_end(super().format(record)))


class PySAICIRCLoggingHandler(Handler):
    def __init__(self, incoming_queue, config):
        super().__init__()
        self.incoming_queue = incoming_queue
        self.config = config

    def format(self, record: LogRecord):
        content = normalize_content(
            escape_stand_and_end(super().format(record))
        ).replace(self.config.password, "********")
        return (
            f'[{datetime.fromtimestamp(record.created).strftime("%H:%M:%S")}] '
            f'{content}\n'
        )

    def emit(self, record):
        self.incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                what=AppEventEnum.RAW_IRC_MESSAGE,
                payload=self.format(record),
            )
        )
