# Usage

Just import the parts you need:

```py
from botlib.cli import Cli, DirType
from botlib.cron import Cron
from botlib.curl import Curl
from botlib.feed2list import Feed2List
from botlib.helper import Log, FileTime, StrFormat, FileWrite
from botlib.html2list import HTML2List, MatchGroup
from botlib.oncedb import OnceDB
from botlib.tgclient import TGClient
```



## Cli, DirType

A wrapper around `argparse`. Shorter calls for common parameters.
If `.arg_dir()` is not enough, use `DirType` for existing directory params.

```py
cli = Cli()
cli.arg_dir('dest_dir', help='...')
cli.arg_file('FILE', help='...')
cli.arg_bool('--dry-run', help='...')
cli.arg('source', help='...')
args = cli.parse()
```



## Cron

Simple recurring tasks. Either manually or via csv-jobs-file.

```py
# If you just have one job to do:
Cron.simple(5, callback).fire()
# OR, customize:
cron = Cron(sleep=range(1, 8))
# Load from CSV
cron.load_csv('jobs.csv', str, cols=[int, str, str])
cron.save_csv('jobs.csv', cols=['chat-id', 'url', 'regex'])
# Or add jobs manually
cron.add_job(10, callback, ['42', 'custom', obj])  # every 10 min
cron.add_job(1440, clean_db)  # daily
cron.start()  # always call start() to begin updates
cron.fire()  # optionally: fire callbacks immediatelly
```

Note: when working with `OnceDB`, make sure you open the DB inside the callback method.
Otherwise SQLite will complain about not using the same thread on which it was created.



## Curl

Used to download web content. Ignores all network errors (just logs them).
Implements a quick cache: If you request the same URL within 45 seconds twice, reuse previously downloaded content.
Includes an etag / last-modified check to reduce network load.

```py
# for these 3 calls, create a download connection just once.
# the result is stored in cache/curl-example.org-1234..ABC.data
Curl.get('https://example.org', cache_only=False)
Curl.get('https://example.org')
Curl.get('https://example.org')
# if the URL path is different, the content is downloaded into another file
Curl.get('https://example.org?1')
# download files
Curl.file('https://example.org/image.png', './example-image.png')
# ... or json
Curl.json('https://example.org/data.json', fallback={})
# ... or just open a connection
with Curl.open('https://example.org') as wp:
    wp.read()
```

There is also an easy-getter to download multiple files if they were not already.

```py
Curl.once('./dest/dir/', 'filename', [
    'https://example.org/audio.mp3',
    'https://example.org/image.jpg'
], date)
```

This will check whether `./dest/dir/filename.mp3` and `./dest/dir/filename.jpg` exists – and if not, download them.
All file modification dates will be set to `date` (if set).



## Feed2List

Parse RSS or Atom xml and return list. Similar to `HTML2list`.

```py
for entry in reversed(Feed2List(fp, keys=[
    'link', 'title', 'description', 'enclosure',  # audio
    'pubDate', 'media:content',  # image
    # 'itunes:image', 'itunes:duration', 'itunes:summary'
])):
    date = entry.get('pubDate')
    process_entry(entry, date)
```



## Log, FileTime, StrFormat, FileWrite

A few tools that may be helpful.

- `Log.error` and `Log.info` will just print a message (including the current timestamp) to the console.
- `FileTime.get` and `FileTime.set` reads and writes file times, e.g., set the date to the same time when a podcast episode was released.
- `StrFormat` has:
  - `.strip_html()` make plain text from html
  - `.to_date()`: convert string to date
  - `.safe_filename()`: strips all filesystem-unsafe characters

`FileWrite.once` works exactly the same way as `Curl.once` does.
The only difference is that `FileWrite` accepts just one filename and requires a callback method:

```py
@FileWrite.once(dest_dir, 'description.txt', date, overwrite=False)
def _fn():
    desc = title + '\n' + '=' * len(title)
    desc += '\n\n' + StrFormat.strip_html(entry.get('description', ''))
    return desc + '\n\n\n' + entry.get('link', '') + '\n'
```

The callback `_fn` is only called if the file does not exist yet.
This avoids unnecessary processing in repeated calls.



## HTML2List, MatchGroup

Used to parse html content into a feed-like list.
Selector is a CSS-selector matching a single tag (with optional classes).

```py
match = MatchGroup({
    'url': r'<a href="([^"]*)">',
    'title': r'<a [^>]*>([\s\S]*?)</a>'
})
source = open('path/to/src.html')  # auto-closed in parse()
selector = 'article.main'
for elem in reversed(HTML2List(selector).parse(source)):
    match.set_html(elem)
    if match['url']:
        print('<a href="{url}">{title}</a>'.format(**match))
```

You may also call this script directly (CLI):

```sh
html2list.py \
  'path/to/src.html' \
  'article.main' \
  -t '<a href="{#url#}">{#title#}</a>' \
  'url:<a href="([^"]*)">' \
  'title:<a [^>]*>([\s\S]*?)</a>'
```

If you omit the template (`-t`), the output will be in JSON format.



## OnceDB

Used as cache. DB ensures that each unique-id entry is evaluated once.
Adding existing entries is silently ignored.
You can iterate over existing entries that haven't been processed yet.

```py
db = OnceDB('cache.sqlite')
# Either do a pre-evaluation to break execution early:
if db.contains(cohort, uid):
    continue
# Or, just put a new object into the store.
# If it exists, the object is not added a second time
db.put(cohort, uid, 'my-object')
# Entries are unique regarding cohort + uid
# If you cleanup() the DB, entries are grouped by cohort and then cleaned
db.cleanup(limit=20)  # keep last 20 entries, delete earlier entries
# The DB also acts as a queue, you can enumerate outstanding entries
def _send(cohort, uid, obj):
    # Do stuff
    return True if success else False  # if False, cancel enumeration
if not db.foreach(_send):
    # something went wrong, you returned False in _send()
    pass
```



## TGClient

Communcation with Telegram Bot API. (`pip3 install pytelegrambotapi`)

```py
# Make it simple to just retrieve a chat-id
TGClient.listen_chat_info(API_KEY, 'username')
exit(0)
# Else: create a one-time bot
bot = TGClient(API_KEY, polling=False, allowedUsers=['username'])
bot.send(chat_id, 'message', parse_mode='HTML', disable_web_page_preview=True)
# Or: create a polling bot
bot = TGClient(API_KEY, polling=True, allowedUsers=['username'])
bot.set_on_kill(cron.stop)

@bot.message_handler(commands=['info'])
def current_job_info(message):
    if bot.allowed(message):  # checks if user is permitted
        try:
            bot.reply_to(message, cron.get(message.chat.id).object,
                         disable_web_page_preview=True)
        except KeyError:
            bot.reply_to(message, 'Not found.')
```
