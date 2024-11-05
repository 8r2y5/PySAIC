import logging
from tkinter import END


from pysaic.controllers.game import (
    add_to_crc_input_file,
)
from pysaic.entities import OutgoingMessage, ChatUser
from pysaic.enums import FactionsEnum
from pysaic.use_cases.ui.utils import enable_disable, get_faction_actor

logger = logging.getLogger(__name__)


class TkinterMessageListController:
    @staticmethod
    def add_message(messages_list, chat_user, content, created_at):
        with enable_disable(messages_list):
            messages_list.insert(
                END, f"[{created_at.strftime('%H:%M:%S')}] ", "Time"
            )
            messages_list.insert(
                END,
                f"{chat_user.name}",
                (
                    chat_user.faction.name
                    if chat_user.faction
                    else FactionsEnum.Anonymous.name
                ),
            )
            content = content + ("" if content.endswith("\n") else "\n")
            messages_list.insert(
                END,
                f": {content}",
                "Text",
            )


class OurMessageUseCase:
    @property
    def chat_users(self):
        return self.state.chat_users

    @property
    def messages_list(self):
        return self.ui.messages_list

    def __init__(self, state, config, ui, outgoing_queue):
        self.state = state
        self.config = config
        self.ui = ui
        self.outgoing_queue = outgoing_queue

    def _add_our_message(self, user, outgoing_message):
        logger.debug("Adding our message: %r", outgoing_message)

        TkinterMessageListController.add_message(
            self.messages_list,
            user,
            outgoing_message.content,
            outgoing_message.created_at,
        )

    def execute(self, content):
        logger.debug("Outgoing message: %r", content)
        outgoing_message = OutgoingMessage(
            self.config.server.previous_channel, content
        )
        self.outgoing_queue.put_nowait(outgoing_message)
        try:
            user = self.chat_users[self.config.nick]
        except KeyError:
            logger.exception("User not found when adding our message")
            user = ChatUser(
                name=self.config.nick,
                faction=self.config.current_faction,
                in_game=self.state.is_game_running,
            )
            self.chat_users.add_user(user.name, user)

        with enable_disable(self.messages_list):
            self._add_our_message(user, outgoing_message)

        if self.state.game_location:
            add_to_crc_input_file(
                "Message/{faction}/{author}/{highlight}/{content}".format(
                    faction=get_faction_actor(user),
                    author=user.name,
                    highlight=False,
                    content=content,
                )
            )
