#!/usr/bin/env python3
import re
import os  # utime, getmtime
import time  # mktime, time
from sys import stderr
from html import unescape
from datetime import datetime
import unicodedata  # normalize
from string import ascii_letters, digits


class Log:
    @staticmethod
    def error(e):
        print('{} [ERROR] {}'.format(datetime.now(), e), file=stderr)

    @staticmethod
    def info(m):
        print('{} {}'.format(datetime.now(), m))


class FileTime:
    @staticmethod
    def set(fname, date):
        modTime = time.mktime(date.timetuple())
        os.utime(fname, (modTime, modTime))

    @staticmethod
    def get(fname, *, absolute=False):
        x = os.path.getmtime(fname)
        return x if absolute else time.time() - x


class StrFormat:
    re_img = re.compile(r'<img [^>]*?(?:alt="([^"]*?)"[^>]*)?'
                        r'src="([^"]*?)"(?:[^>]*?alt="([^"]*?)")?[^>]*?/>')
    re_href = re.compile(r'<a [^>]*href="([^"]*?)"[^>]*?>(.*?)</a>')
    re_br = re.compile(r'<br[^>]*>|</p>')
    re_tags = re.compile(r'<[^>]*>')
    re_crlf = re.compile(r'[\n\r]{2,}')

    @staticmethod
    def strip_html(text):
        text = StrFormat.re_img.sub(r'[IMG: \2, \1\3]', text)
        text = StrFormat.re_href.sub(r'\2 (\1)', text)
        text = StrFormat.re_br.sub('\n', text)
        text = StrFormat.re_tags.sub('', text)
        text = StrFormat.re_crlf.sub('\n\n', text)
        return unescape(text).replace(' ', ' ').strip()

    @staticmethod
    def to_date(text):
        for date_format in (
            '%a, %d %b %Y %H:%M:%S %z',  # RSS
            '%Y-%m-%dT%H:%M:%S%z',  # Atom
            '%Y-%m-%dT%H:%M:%S.%f%z',  # Atom
            '%Y-%m-%dT%H:%M:%S',  # without timezone
            '%Y-%m-%dT%H:%M:%S.%f'  # without timezone
        ):
            try:
                return datetime.strptime(text, date_format)
            except ValueError:
                pass
        raise ValueError('Could not match date format. {}'.format(text))

    fnameChars = set('-_.,() {}{}'.format(ascii_letters, digits))

    @staticmethod
    def safe_filename(text):
        text = unicodedata.normalize('NFKD', text)  # makes 2-bytes of umlauts
        text = text.replace('̈', 'e')  # replace umlauts e.g., Ä -> Ae
        text = text.encode('ASCII', 'ignore')
        return ''.join(chr(c) for c in text if chr(c) in StrFormat.fnameChars)
