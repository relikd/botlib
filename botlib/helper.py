#!/usr/bin/env python3
import re
import os  # utime, getmtime
import time  # mktime, time
import traceback  # format_exc
from sys import stderr
from html import unescape
from datetime import datetime
import unicodedata  # normalize
from string import ascii_letters, digits
from typing import Optional, Callable, Union


class Log:
    FILE = 'error.log'
    LEVEL = 0  # -1: disabled, 0: error, 1: warn, 2: info, 4: debug

    @staticmethod
    def _log_if(level: int, msg: str) -> None:
        ''' Log to file if LOG_LEVEL >= level. '''
        if Log.LEVEL >= level:
            with open(Log.FILE, 'a') as fp:
                fp.write(msg + '\n')

    @staticmethod
    def error(e: Union[str, Exception]) -> None:
        ''' Log error message (incl. current timestamp) '''
        msg = '{} [ERROR] {}'.format(
            datetime.now(), e if isinstance(e, str) else repr(e))
        print(msg, file=stderr)
        Log._log_if(0, msg)
        if isinstance(e, Exception):
            Log._log_if(0, traceback.format_exc())

    @staticmethod
    def info(m: str) -> None:
        ''' Log info message (incl. current timestamp) '''
        msg = '{} {}'.format(datetime.now(), m)
        print(msg)
        Log._log_if(2, msg)


class FileTime:
    @staticmethod
    def set(fname: str, date: datetime) -> None:
        ''' Set file modification time. '''
        modTime = time.mktime(date.timetuple())
        os.utime(fname, (modTime, modTime))

    @staticmethod
    def get(fname: str, *, absolute: bool = False) -> float:
        ''' Get file modification time. '''
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
    def strip_html(text: str) -> str:
        '''
        Remove all html tags and replace with readble alternative.
        Also, strips unnecessary newlines, nbsp, br, etc.
        '''
        text = StrFormat.re_img.sub(r'[IMG: \2, \1\3]', text)
        text = StrFormat.re_href.sub(r'\2 (\1)', text)
        text = StrFormat.re_br.sub('\n', text)
        text = StrFormat.re_tags.sub('', text)
        text = StrFormat.re_crlf.sub('\n\n', text)
        return unescape(text).replace(' ', ' ').strip()

    @staticmethod
    def to_date(text: str) -> datetime:
        ''' Try parse string as date, currently RSS + Atom format. '''
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
    def safe_filename(text: str) -> str:
        ''' Replace umlauts and unsafe characters (filesystem safe). '''
        text = unicodedata.normalize('NFKD', text)  # makes 2-bytes of umlauts
        text = text.replace('̈', 'e')  # replace umlauts e.g., Ä -> Ae
        data = text.encode('ASCII', 'ignore')
        return ''.join(chr(c) for c in data if chr(c) in StrFormat.fnameChars)


class FileWrite:
    @staticmethod
    def once(
        dest_dir: str,
        fname: str,
        date: Optional[datetime] = None,
        *, override: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
        intro: Union[str, bool, None] = None
    ) -> Callable[[Callable[[], Optional[str]]], None]:
        '''
        Write file to disk – but only if it does not exist already.
        The callback method is only called if the file does not exist yet.
        Use as decorator to a function: @FileWrite.once(...)
        '''
        def _decorator(func: Callable[[], Optional[str]]) -> None:
            path = os.path.join(dest_dir, fname)
            if os.path.isfile(path) and not override:
                return
            content = func()
            if not content:
                return
            if verbose:
                if intro and intro is not True:
                    print(intro)
                print('  –>', path)
            if dry_run:
                return
            # write file
            with open(path, 'w') as f:
                f.write(content)
            if date:
                FileTime.set(path, date)
        return _decorator
