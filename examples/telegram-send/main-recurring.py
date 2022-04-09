#!/usr/bin/env python3
from botlib.cron import Cron
from botlib.helper import Log
from botlib.oncedb import OnceDB
from botlib.tgclient import TGClient
# the pipeline process logic is split up:
# - you can have one file for generating the entries and writing to db (import)
#   e.g., import an example from web-scraper and call download()
# - and another file to read db and send its entries to telegram (this file)
#   of course, you can put your download logic inside this file as well
import sub_job_a as jobA
import sub_job_b as jobB

cron = Cron()
bot = TGClient(__API_KEY__, polling=True, allowedUsers=['my-username'])
bot.set_on_kill(cron.stop)


def main():
    def clean_db(_) -> None:
        Log.info('[clean up]')
        OnceDB('cache.sqlite').cleanup(limit=150)

    def notify_jobA(_) -> None:
        jobA.download(topic='development', cohort='dev:py')
        send2telegram(__A_CHAT_ID__)

    def notify_jobB(_) -> None:
        jobB.download()
        send2telegram(__ANOTHER_CHAT_ID__)

    # Log.info('Ready')
    cron.add_job(10, notify_jobA)  # every 10 min
    cron.add_job(30, notify_jobB)  # every 30 min
    cron.add_job(1440, clean_db)  # daily
    cron.start()
    # cron.fire()


def send2telegram(chat_id: int) -> None:
    db = OnceDB('cache.sqlite')
    # db.mark_all_done()

    def _send(cohort: str, uid: str, obj: str) -> bool:
        Log.info('[push] {} {}'.format(cohort, uid))
        msg = bot.send(chat_id, obj, parse_mode='HTML',
                       disable_web_page_preview=True)
        return msg is not None

    if not db.foreach(_send):
        # send() sleeps 45 sec (on error), safe to call immediatelly
        send2telegram(chat_id)


main()
