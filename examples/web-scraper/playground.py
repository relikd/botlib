#!/usr/bin/env python3
from botlib.curl import Curl
from botlib.html2list import HTML2List, MatchGroup

URL = 'https://www.vice.com/en/topic/motherboard'
SOURCE = Curl.get(URL, cache_only=True)

SELECT = '.vice-card__content'
match = MatchGroup({
    'url': r'<a href="([^"]*)"',
    'title': r'<h3[^>]*><a [^>]*>([\s\S]*?)</a>[\s\S]*?</h3>',
    'desc': r'<p[^>]*>([\s\S]*?)</p>',
    'wrong-regex': r'<a xref="([\s\S]*?)"',
})
for elem in reversed(HTML2List(SELECT).parse(SOURCE)):
    match.set_html(elem)
    for k, v in match.to_dict().items():
        print(k, '=', v)
    print()
    break
