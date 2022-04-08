# botlib

A collection of scripts to parse and process input files (html, RSS, Atom) – without dependencies<sup>1</sup>.

<sup>1</sup>: Well, except for `pytelegrambotapi`, but feel free to replace it with another module.

Includes tools for extracting “news” articles, detection of duplicates, content downloader, cron-like repeated events, and Telegram bot client.
Basically everything you need for quick and dirty format processing (`html->RSS`, `notification->telegram`, `rss/podcast->download`, `web scraper`, ...) without writing the same code over and over again.
The architecture is modular and pipeline oriented.
Use whatever suits the task at hand.


## Usage

There is a short [usage](./botlib/README.md) documentation on the individual componentes of this lib.
And there are some [examples](./examples/) on how to combine them.
Lastly, for web scraping, open the [playground.py](./examples/web-scraper/playground.py) to test your regex.
