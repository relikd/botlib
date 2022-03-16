#!/usr/bin/env python3
import telebot  # pip3 install pytelegrambotapi
from threading import Thread
from time import sleep
from .helper import Log


class Kill(Exception):
    pass


class TGClient(telebot.TeleBot):
    @staticmethod
    def listen_chat_info(api_key, user):
        bot = TGClient(api_key, polling=True, allowedUsers=[user])

        @bot.message_handler(commands=['start'])
        def handle_start(message):
            bot.log_chat_info(message.chat)
            raise Kill()
        return bot

    def __init__(self, apiKey, *, polling, allowedUsers=[], **kwargs):
        super().__init__(apiKey, **kwargs)
        self.users = allowedUsers
        self.onKillCallback = None

        if polling:
            def _fn():
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
            def _healthcheck(message):
                if self.allowed(message):
                    self.reply_to(message, 'yes')

            @self.message_handler(commands=['kill'])
            def _kill(message):
                if self.allowed(message):
                    self.reply_to(message, 'bye bye')
                    raise Kill()

    def set_on_kill(self, callback):
        self.onKillCallback = callback

    # Helper methods

    def log_chat_info(self, chat):
        Log.info('[INFO] chat-id: {} ({}, title: "{}")'.format(
            chat.id, chat.type, chat.title or ''))

    def allowed(self, src_msg):
        return not self.users or src_msg.from_user.username in self.users

    def send(self, chat_id, msg, **kwargs):
        try:
            return self.send_message(chat_id, msg, **kwargs)
        except Exception as e:
            Log.error(e)
            sleep(45)
            return None

    def send_buttons(self, chat_id, msg, options):
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(*(telebot.types.KeyboardButton(x) for x in options))
        return self.send_message(chat_id, msg, reply_markup=markup)

    def send_abort_keyboard(self, src_msg, reply_msg):
        return self.reply_to(src_msg, reply_msg,
                             reply_markup=telebot.types.ReplyKeyboardRemove())

    def send_force_reply(self, chat_id, msg):
        return self.send_message(chat_id, msg,
                                 reply_markup=telebot.types.ForceReply())
