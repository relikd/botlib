#!/usr/bin/env python3
import re
import json
from sys import stderr
from argparse import ArgumentParser, FileType
from typing import List, Tuple, Dict, Optional, Union, Callable
from typing import TextIO, BinaryIO, Iterator, KeysView
from html.parser import HTMLParser

XMLAttrs = List[Tuple[str, Optional[str]]]


class CSSSelector:
    ''' Limited support, match single tag with classes: div.class.other '''

    def __init__(self, selector: str) -> None:
        if any(x in ' >+' for x in selector):
            raise NotImplementedError(
                'No support for nested tags. "{}"'.format(selector))
        self.tag, *self.cls = selector.split('.')

    def matches(self, tag: str, attrs: XMLAttrs) -> bool:
        ''' Test if tag and attrs match the target selector. '''
        if self.tag and tag != self.tag:
            return False
        if self.cls:
            for k, val in attrs:
                if k == 'class' and val:
                    classes = val.split()
                    return all(x in classes for x in self.cls)
            return False
        return True


class HTML2List(HTMLParser):
    '''
    :select:    CSS-selector should match a list of articles.
    :callback:  If set, callback is called for each found match.
                If not set, return a list of strings instead.
    '''

    def __init__(
        self,
        select: str,
        callback: Optional[Callable[[str], str]] = None
    ) -> None:
        super().__init__()
        self._filter = CSSSelector(select)
        self._data = ''  # temporary data built-up
        self._elem = []  # type: List[str] # tag stack
        self._tgt = 0  # remember matching level for filter
        self._result = []  # type: List[str] # empty if callback
        self._callback = callback or self._result.append

    def parse(self, source: Optional[Union[TextIO, BinaryIO]]) -> List[str]:
        '''
        :source: A file-pointer or web-source with read() attribute.
        Warning: return value empty if callback is set!
        '''
        def rb2str(data: bytes, fp: BinaryIO, limit: int = 256) -> str:
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                extra = fp.read(limit)
                if not extra:
                    return data  # type: ignore[return-value]
                return rb2str(data + extra, fp, limit)

        if not source:
            return []

        while True:
            try:
                data = source.read(65536)  # 64k
                if not data:
                    break
            except Exception as e:
                print('ERROR: {}'.format(e), file=stderr)
                break
            if isinstance(data, bytes):
                data = rb2str(data, source)  # type: ignore[arg-type]
            self.feed(data)
        source.close()
        self.close()
        return self._result

    def handle_starttag(self, tag: str, attrs: XMLAttrs) -> None:
        ''' [internal] HTMLParser callback '''
        self._elem.append(tag)
        if self._filter.matches(tag, attrs):
            if self._tgt > 0:
                raise RuntimeError('No nested tags! Adjust your filter.')
            self._tgt = len(self._elem) - 1
        if self._tgt > 0:
            self._data += self.get_starttag_text() or ''

    def handle_startendtag(self, tag: str, attrs: XMLAttrs) -> None:
        ''' [internal] HTMLParser callback '''
        self._elem.append(tag)
        if self._tgt > 0:
            self._data += self.get_starttag_text() or ''

    def handle_data(self, data: str) -> None:
        ''' [internal] HTMLParser callback '''
        if self._tgt > 0:
            self._data += data

    def handle_endtag(self, tag: str) -> None:
        ''' [internal] HTMLParser callback '''
        if self._tgt > 0:
            self._data += '</{}>'.format(tag)
        # drop any non-closed tags
        while self._elem[-1] != tag:
            self._elem.pop(-1)  # e.g., <img> which is not start-end-type
        self._elem.pop(-1)  # remove actual closing tag
        # if level matches search-level, yield whole element
        if len(self._elem) == self._tgt:
            self._tgt = 0
            if self._data:
                # print('DEBUG:', self._data)
                self._callback(self._data)
                self._data = ''


class Grep:
    '''
    Use `[\\s\\S]*?` to match multi-line content.
    Will replace all continuous whitespace (incl. newline) with a single space.
    If you whish to keep whitespace, set cleanup to False.
    '''
    re_whitespace = re.compile(r'\s+')  # will also replace newline with space

    def __init__(self, regex: str, *, cleanup: bool = True) -> None:
        self.cleanup = cleanup
        self._rgx = re.compile(regex)

    def find(self, text: str) -> Optional[str]:
        ''' Perform regex search to find desired snippet. '''
        grp = self._rgx.search(text)
        if not grp:
            return None
        res = grp.groups()[0]
        if self.cleanup:
            return self.re_whitespace.sub(' ', res.strip())
        return res


class MatchGroup(dict):
    ''' Use {#tagname#} to replace values with regex value. '''
    re_tag = re.compile(r'{#(.*?)#}')

    def __init__(
        self,
        grepDict: Optional[Dict[str, Union[str, Grep]]] = None
    ) -> None:
        self._regex = {}  # type: Dict[str, Grep]
        for k, v in (grepDict or {}).items():
            self.add(k, v)
        self.set_html('')

    def add(
        self,
        tagname: str,
        regex: Union[str, Grep],
        *, cleanup: bool = True
    ) -> None:
        ''' Add a single search pattern to the internal table. '''
        self._regex[tagname] = \
            regex if isinstance(regex, Grep) else Grep(regex, cleanup=cleanup)

    def set_html(self, html: str) -> 'MatchGroup':
        ''' Reuse existing MatchGroup but set new search html. '''
        self._html = html
        self._res = {}  # type: Dict[str, Optional[str]]
        return self

    def keys(self) -> KeysView[str]:
        ''' Get all search keys. '''
        return self._regex.keys()

    def __iter__(self) -> Iterator[str]:
        ''' Iter is required for a dict subclass to support **unwrap. '''
        return iter(self.keys())

    def __getitem__(self, key: str) -> Optional[str]:
        '''
        Conditional getter. Regex search is only perfromed on access.
        Once the search was performed, result is cached until `set_html()`.
        '''
        try:
            return self._res[key]
        except KeyError:
            val = self._regex[key].find(self._html)
            self._res[key] = val
            return val

    def __str__(self) -> str:
        return '\n'.join('{}: {}'.format(k, self._res.get(k, '<?>'))
                         for k in self._regex)

    def to_dict(self) -> Dict[str, Optional[str]]:
        ''' Force unwrap all keys and perform regex. '''
        return {k: self[k] for k in self._regex}

    def use_template(self, template: str) -> str:
        ''' Use {#tagname#} to replace values with regex value. '''
        return self.re_tag.sub(lambda x: self[x.groups()[0]] or '', template)


def _cli() -> None:
    ''' CLI entry point. '''
    parser = ArgumentParser()
    parser.add_argument('FILE', type=FileType('r'), help='Input html file')
    parser.add_argument('selector', help='CSS selector. E.g., article.entry')
    parser.add_argument('-t', '--template',
                        help='E.g., <a href="{#url#}">{#title#}</a>')
    parser.add_argument('regex', nargs='+',
                        help='''"tagname:regex" E.g., 'url:<a href="(.*?)">'
                        'title:<a [^>]*>([\\s\\S]*?)</a>'
                        ''')
    args = parser.parse_args()
    # create grep/regex mapping
    grp = MatchGroup()
    for x in args.regex:
        try:
            tag, regex = x.split(':', 1)
            grp.add(tag, regex)
        except ValueError:
            print('Did you forget to prefix a tagname? `{}`'.format(x),
                  file=stderr)
            exit(1)
    # parse
    if args.template:
        try:
            for x in HTML2List(args.selector).parse(args.FILE):
                print(grp.set_html(x).use_template(args.template))
        except KeyError as e:
            print('Did you forget a tagname? ' + str(e), file=stderr)
    else:
        print(json.dumps([
            grp.set_html(x).to_dict()
            for x in
            HTML2List(args.selector).parse(args.FILE)
        ]))


if __name__ == '__main__':
    _cli()
