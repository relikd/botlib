#!/usr/bin/env python3
import telebot  # pip3 install pytelegrambotapi
from threading import Thread
from time import sleep
from typing import List, Optional, Any, Union, Iterable, Callable
from telebot.types import Message, Chat  # typing
from .helper import Log


class Kill(Exception):
    ''' Used to intentionally kill the bot. '''
    pass


class TGClient(telebot.TeleBot):
    '''
    Telegram client. Wrapper around telebot.TeleBot.
    If `polling` if False, you can run the bot for a single send_message.
    If `allowedUsers` is None, all users are allowed.
    '''

    def __init__(
        self,
        apiKey: str,
        *, polling: bool,
        allowedUsers: Optional[List[str]] = None,
        **kwargs: Any
    ) -> None:
        ''' If '''
        super().__init__(apiKey, **kwargs)
        self.users = allowedUsers
        self.onKillCallback = None  # type: Optional[Callable[[], None]]

        if polling:
            def _fn() -> None:
                try:
                    Log.info('Ready')
                    self.polling(skip_pending=True)  # none_stop=True
                except Kill:
                    Log.info('Quit by /kill command.')
                    if self.onKillCallback:
                        self.onKillCallback()
                    return
                except Exception as e:
                    Log.error(e)
                    Log.info('Auto-restart in 15 sec ...')
                    sleep(15)
                    _fn()

            Thread(target=_fn, name='Polling').start()

            @self.message_handler(commands=['?'])
            def _healthcheck(message: Message) -> None:
                if self.allowed(message):
                    self.reply_to(message, 'yes')

            @self.message_handler(commands=['kill'])
            def _kill(message: Message) -> None:
                if self.allowed(message):
                    self.reply_to(message, 'bye bye')
                    raise Kill()

    def set_on_kill(self, callback: Optional[Callable[[], None]]) -> None:
        ''' Callback is executed when a Kill exception is raised. '''
        self.onKillCallback = callback

    @staticmethod
    def listen_chat_info(api_key: str, user: str) -> 'TGClient':
        ''' Wait for a single /start command, print chat-id, then quit. '''
        bot = TGClient(api_key, polling=True, allowedUsers=[user])

        @bot.message_handler(commands=['start'])
        def handle_start(message: Message) -> None:
            bot.log_chat_info(message.chat)
            raise Kill()
        return bot

    # Helper methods

    def log_chat_info(self, chat: Chat) -> None:
        ''' Print current chat details (chat-id, title, etc.) to console. '''
        Log.info('[INFO] chat-id: {} ({}, title: "{}")'.format(
            chat.id, chat.type, chat.title or ''))

    def allowed(self, src_msg: Message) -> bool:
        ''' Return true if message is sent to an previously allowed user. '''
        return not self.users or src_msg.from_user.username in self.users

    def send(self, chat_id: int, msg: str, **kwargs: Any) -> Optional[Message]:
        ''' Send a message to chat. '''
        try:
            return self.send_message(chat_id, msg, **kwargs)
        except Exception as e:
            Log.error(e)
            sleep(45)
            return None

    def send_buttons(
        self,
        chat_id: int,
        msg: str,
        options: Iterable[Union[str, int, float]]
    ) -> Message:
        ''' Send tiling keyboard with predefined options to user. '''
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(*(telebot.types.KeyboardButton(str(x)) for x in options))
        return self.send_message(chat_id, msg, reply_markup=markup)

    def send_abort_keyboard(self, src_msg: Message, reply_msg: str) -> Message:
        ''' Cancel previously sent keyboards. '''
        return self.reply_to(src_msg, reply_msg,
                             reply_markup=telebot.types.ReplyKeyboardRemove())

    def send_force_reply(self, chat_id: int, msg: str) -> Message:
        ''' Send a message which is automatically set to reply_to. '''
        return self.send_message(chat_id, msg,
                                 reply_markup=telebot.types.ForceReply())
