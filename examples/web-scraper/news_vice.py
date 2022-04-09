#!/usr/bin/env python3
from botlib.curl import Curl
from botlib.html2list import HTML2List, MatchGroup
from botlib.oncedb import OnceDB


def download(*, topic: str = 'motherboard', cohort: str = 'vice:mb') -> None:
    db = OnceDB('cache.sqlite')
    url = 'https://www.vice.com/en/topic/{}'.format(topic)

    select = '.vice-card__content'
    match = MatchGroup({
        'url': r'<a href="([^"]*)"',
        'title': r'<h3[^>]*><a [^>]*>([\s\S]*?)</a>[\s\S]*?</h3>',
        'desc': r'<p[^>]*>([\s\S]*?)</p>',
    })
    for elem in reversed(HTML2List(select).parse(Curl.get(url))):
        match.set_html(elem)
        x_uid = match['url']
        if not x_uid or db.contains(cohort, x_uid):
            continue
        txt = '<a href="https://www.vice.com{url}">{title}</a>'.format(**match)
        txt += '\n' + str(match['desc'])
        if txt:
            db.put(cohort, x_uid, txt)


# download()
