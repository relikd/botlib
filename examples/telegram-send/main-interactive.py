#!/usr/bin/env python3
from botlib.tgclient import TGClient, Message

bot = TGClient(__API_KEY__, polling=True, allowedUsers=['my-username'])


@bot.message_handler(commands=['hi'])
def bot_reply(message: Message) -> None:
    if bot.allowed(message):  # only reply to a single user (my-username)
        bot.reply_to(message, 'Good evening my dear.')


@bot.message_handler(commands=['set'])
def update_config(message: Message) -> None:
    if bot.allowed(message):
        try:
            config = DATA_STORE.get(message.chat.id)
        except KeyError:
            bot.reply_to(message, 'Not found.')
            return

        if message.text == '/set day':
            config.param = 'day'
        elif message.text == '/set night':
            config.param = 'night'
        else:
            bot.reply_to(message, 'Usage: /set [day|night]')


@bot.message_handler(commands=['start'])
def new_chat_info(message: Message) -> None:
    bot.log_chat_info(message.chat)
    if bot.allowed(message):
        if DATA_STORE.get(message.chat.id):
            bot.reply_to(message, 'Already exists')
        else:
            CreateNew(message)


class CreateNew:
    def __init__(self, message: Message) -> None:
        self.ask_name(message)

    def ask_name(self, message: Message) -> None:
        msg = bot.send_force_reply(message.chat.id, 'Enter Name:')
        bot.register_next_step_handler(msg, self.ask_interval)

    def ask_interval(self, message: Message) -> None:
        self.name = message.text
        msg = bot.send_buttons(message.chat.id, 'Update interval (minutes):',
                               options=[3, 5, 10, 15, 30, 60])
        bot.register_next_step_handler(msg, self.finish)

    def finish(self, message: Message) -> None:
        try:
            interval = int(message.text or 'error')
        except ValueError:
            bot.send_abort_keyboard(message, 'Not a number. Aborting.')
            return
        print('Name:', self.name, 'interval:', interval)
        bot.send_message(message.chat.id, 'done.')
