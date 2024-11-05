import asyncio
import logging
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from pysaic.script_reader.parser import parse_line

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

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.src_path.endswith("crc_output.txt"):
            return

        with open(event.src_path, "r+") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                self._loop.create_task(parse_line(line))

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
