import logging
from tkinter import END

from pysaic.controllers.game import add_channel_message_to_game
from pysaic.entities import IncomingEvent, OutgoingMessage
from pysaic.enums import FactionsEnum, HistoryMessageEnum
from pysaic.use_cases.irc_mode_to_user_type import parsed_mode_to_name
from pysaic.use_cases.text import make_content_malformed
from pysaic.use_cases.ui.utils import (
    add_content_of_message_to_messages_list,
    enable_disable,
    get_faction_actor,
)

logger = logging.getLogger(__name__)


class TkinterMessageListController:
    @staticmethod
    def add_message(messages_list, hyperlinks, chat_user, content, created_at):
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
            add_content_of_message_to_messages_list(
                messages_list, hyperlinks, f": {content}", ["Text"]
            )


class OurMessageUseCase:
    @property
    def chat_users(self):
        return self.state.chat_users

    @property
    def messages_list(self):
        return self.ui.messages_list

    @property
    def hyperlinks(self):
        return self.ui.hyperlinks

    def __init__(self, state, config, ui, outgoing_queue, incoming_queue):
        self.state = state
        self.config = config
        self.ui = ui
        self.outgoing_queue = outgoing_queue
        self.incoming_queue = incoming_queue

    def _add_our_message(self, user, outgoing_message):
        logger.debug("Adding our message: %r", outgoing_message)

        TkinterMessageListController.add_message(
            self.messages_list,
            self.hyperlinks,
            user,
            outgoing_message.content,
            outgoing_message.created_at,
        )

    def execute(self, content):
        logger.debug("Outgoing message: %r", content)
        for word in self.config.blocked_words:
            if word in content:
                self.incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        "Blocked word found in message. %s", word
                    )
                )
                return

        if self.state.should_malform_messages:
            logger.debug(
                "Fake disconnect is enabled, making content malformed %r",
                content,
            )
            content = make_content_malformed(content)
        outgoing_message = OutgoingMessage(
            self.config.server.previous_channel, content
        )
        self.outgoing_queue.put_nowait(outgoing_message)
        try:
            user = self.chat_users[self.state.nick]
        except KeyError:
            logger.exception("User not found when adding our message")
            user = self.state.player.create_chat_user()
            self.chat_users.add_user(user.name, user)

        with enable_disable(self.messages_list):
            self._add_our_message(user, outgoing_message)

        self.state.add_message(HistoryMessageEnum.channel, user, content)
        add_channel_message_to_game(
            faction_actor=get_faction_actor(user),
            author=user.name,
            icon_id=user.avatar,
            reputation_author=user.reputation,
            rank_author=user.rank,
            highlight="False",
            user_type=parsed_mode_to_name(user.irc_mode),
            content=content,
        )
