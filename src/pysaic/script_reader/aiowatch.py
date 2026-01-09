import asyncio
import logging
from pathlib import Path

import inject
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from pysaic.entities import IncomingEvent, IncomingQueue
from pysaic.script_reader.router import parse_line

logger = logging.getLogger(__name__)


class _EventHandler(FileSystemEventHandler):
    file_size = 0

    def __init__(
        self,
        loop: asyncio.BaseEventLoop,
        *args,
        **kwargs,
    ):
        self._loop = loop
        super(*args, **kwargs)

    @inject.autoparams()
    def on_modified(
        self, event: FileSystemEvent, incoming_queue: IncomingQueue
    ) -> None:
        if not event.src_path.endswith("crc_output.txt"):
            return

        with open(event.src_path, "r+") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    self._loop.create_task(parse_line(line, incoming_queue))
                except Exception:
                    logger.exception("Error parsing line: %r", line)
                    incoming_queue.put_nowait(
                        IncomingEvent.create_error_event(
                            f"Error parsing line: {line}"
                        )
                    )

            f.seek(0)
            f.truncate()


def game_files_watcher(
    path: Path,
    loop: asyncio.BaseEventLoop,
    recursive: bool = False,
) -> None:
    """Watch a directory for changes."""
    handler = _EventHandler(loop)

    observer = Observer()
    observer.schedule(handler, str(path), recursive=recursive)
    observer.start()
    logger.debug("Observer started")
