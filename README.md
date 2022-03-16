# botlib

A collection of scripts to parse and process input files (html, RSS, Atom) – without dependencies<sup>1</sup>.

<sup>1</sup>: Well, except for `pytelegrambotapi`, but feel free to replace it with another module.

Includes tools for extracting “news” articles, detection of duplicates, content downloader, cron-like repeated events, and Telegram bot client.
Basically everything you need for quick and dirty format processing (html->RSS, notification->telegram, rss/podcast->download, webscraper, ...) without writing the same code over and over again.
The architecture is modular and pipeline processing oriented.
Use whatever suits the task at hand.


### In progress

Documentation, examples, tests and `setup.py` will be added soon.

Meanwhile, take a look at the [Usage](botlib/README.md) documentation.
