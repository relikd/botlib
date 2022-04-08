#!/usr/bin/env python3
from botlib.tgclient import TGClient

print('open a new telegram chat window with your bot and send /start')

TGClient.listen_chat_info(__API_KEY__, 'my-username')
