#!/usr/bin/env python3
from botlib.curl import Curl
from botlib.html2list import HTML2List, MatchGroup
from botlib.oncedb import OnceDB
from typing import Optional, Callable, TextIO

CRAIGSLIST = 'https://newyork.craigslist.org/search/boo'


def load(url: str) -> Optional[TextIO]:
    # return open('test.html')
    return Curl.get(url)


def download() -> None:
    db = OnceDB('cache.sqlite')

    def proc(
        cohort: str,
        source: Optional[TextIO],
        select: str,
        regex: dict = {},
        fn: Callable[[MatchGroup], str] = str
    ) -> None:
        match = MatchGroup(regex)
        for elem in reversed(HTML2List(select).parse(source)):
            match.set_html(elem)
            x_uid = match['url']
            if not x_uid or db.contains(cohort, x_uid):
                continue
            txt = (fn(match) or '').strip()
            if txt:
                print(txt)
                db.put(cohort, x_uid, txt)

    proc('boat:craigslist', load(CRAIGSLIST), 'li.result-row', {
        'url': r'<a href="([^"]*)"',
        'title': r'<h3[\s\S]*?<a [^>]*>([\s\S]*?)</a>[\s\S]*?</h3>',
        'price': r'<span class="result-price">([\s\S]*?)</span>',
        'hood': r'<span class="result-hood">([\s\S]*?)</span>',
    }, lambda match: '''
<a href="{url}">{title}</a>
<strong>{price}</strong>, {hood}'''.format(**match))

    # process another source ...
    # def fn(match):
    #     print(match.to_dict())
    #     return advanced_fn(match)
    # proc(cohort, load(url), select, match, fn)


# download()
