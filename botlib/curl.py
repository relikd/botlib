#!/usr/bin/env python3
import os
import json
from sys import stderr
from hashlib import md5
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, ParseResult
from urllib.request import urlretrieve, urlopen, Request
from typing import List, Dict, Optional, Any, TextIO
from datetime import datetime  # typing
from http.client import HTTPResponse  # typing
from .helper import FileTime
import ssl
# somehow macOS default behavior for SSL verification is broken
ssl._create_default_https_context = ssl._create_unverified_context


def _read_modified_header(fname: str) -> Dict[str, str]:
    ''' Extract Etag and Last-Modified headers, rename for sending. '''
    res = {}
    if os.path.isfile(fname):
        with open(fname) as fp:
            for line in fp.readlines():
                key, val = line.strip().split(': ', 1)
                if key == 'Etag' and val:
                    res['If-None-Match'] = val
                elif key == 'Last-Modified' and val:
                    res['If-Modified-Since'] = val.replace('-gzip', '')
    return res


class Curl:
    ''' Rename Curl.CACHE_DIR to move the cache somewhere else. '''
    CACHE_DIR = 'cache'

    @staticmethod
    def valid_url(url: str) -> Optional[ParseResult]:
        ''' If valid, return urlparse() result. '''
        url = url.strip().replace(' ', '+')
        x = urlparse(url)
        return x if x.scheme and x.netloc else None

    @staticmethod
    def url_hash(url: str) -> str:
        ''' Unique url-hash used for filename / storage. '''
        x = Curl.valid_url(url)
        return '{}-{}'.format(x.hostname if x else 'ERR',
                              md5(url.encode()).hexdigest())

    @staticmethod
    def _cached_is_recent(fname: str, *, maxAge: int) -> bool:
        fname = os.path.join(Curl.CACHE_DIR, fname)
        return os.path.isfile(fname) and FileTime.get(fname) < maxAge

    @staticmethod
    def _cached_read(
        conn: Optional[HTTPResponse], fname_data: str, fname_head: str
    ) -> Optional[TextIO]:
        fname_data = os.path.join(Curl.CACHE_DIR, fname_data)
        if conn:
            os.makedirs(Curl.CACHE_DIR, exist_ok=True)
            with open(os.path.join(Curl.CACHE_DIR, fname_head), 'w') as fp:
                fp.write(str(conn.info()).strip())
            with open(fname_data, 'wb') as fpb:
                while True:
                    data = conn.read(8192)  # 1024 Bytes
                    if not data:
                        break
                    fpb.write(data)
        return open(fname_data) if os.path.isfile(fname_data) else None

    @staticmethod
    def open(
        url: str,
        *,
        post: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[HTTPResponse]:
        ''' Open a network connection, returl urlopen() result or None. '''
        try:
            head = {'User-Agent': 'Mozilla/5.0'}
            if headers:
                head.update(headers)
            return urlopen(Request(url, data=post, headers=head))
        except Exception as e:
            if isinstance(e, HTTPError) and e.getcode() == 304:
                # print('Not-Modified: {}'.format(url), file=stderr)
                return None  # ignore not-modified
            print('ERROR: Load URL "{}" -- {}'.format(url, e), file=stderr)
            return None

    @staticmethod
    def get(
        url: str,
        *,
        cache_only: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[TextIO]:
        '''
        Returns an already open file pointer.
        You are responsible for closing the file.
        NOTE: `HTML2List.parse` and `Feed2List.parse` will close it for you.
        '''
        fname = 'curl-{}.data'.format(Curl.url_hash(url))
        # If file was created less than 45 sec ago, reuse cached value
        if cache_only or Curl._cached_is_recent(fname, maxAge=45):
            return Curl._cached_read(None, fname, '')

        fname_head = fname[:-5] + '.head'
        head = _read_modified_header(fname_head)
        if headers:
            head.update(headers)
        conn = Curl.open(url, headers=head)
        return Curl._cached_read(conn, fname, fname_head)

    @staticmethod
    def post(
        url: str,
        data: bytes,
        *,
        cache_only: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[TextIO]:
        '''
        Perform POST operation.
        Returns an already open file pointer.
        You are responsible for closing the file.
        '''
        fname = 'curl-{}.post.data'.format(Curl.url_hash(url))
        if cache_only:
            return Curl._cached_read(None, fname, '')

        conn = Curl.open(url, post=data, headers=headers)
        return Curl._cached_read(conn, fname, fname[:-5] + '.head')

    @staticmethod
    def json(url: str, fallback: Any = None, *, cache_only: bool = False) \
            -> Any:
        ''' Open network connection and download + parse json result. '''
        conn = Curl.get(url, cache_only=cache_only)
        if not conn:
            return fallback
        with conn as fp:
            return json.load(fp)

    @staticmethod
    def file(url: str, dest_file: str, *, raise_except: bool = False) -> bool:
        '''
        Download raw data to file. Creates an intermediate ".inprogress" file.
        If raise_except = False, silently ignore errors (default).
        '''
        tmp_file = dest_file + '.inprogress'
        try:
            urlretrieve(url, tmp_file)
            os.rename(tmp_file, dest_file)  # atomic download, no broken files
            return True
        except HTTPError as e:
            # print('ERROR: Load URL "{}" -- {}'.format(url, e), file=stderr)
            if raise_except:
                raise e
            return False

    @staticmethod
    def once(
        dest_dir: str,
        fname: str,
        urllist: List[str],
        date: Optional[datetime] = None,
        *, override: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
        intro: Optional[str] = None
    ) -> bool:
        '''
        Download and store a list of raw files. If local file exists, ignore.
        `fname` should be the filename without extension. Extension is added
        based on the extension in the `urllist` (per file).
        If `date` is set, change last modified date of downloaded file.
        Print `intro` before download (if any loaded or if `override`).
        '''
        did_update = False
        for url_str in urllist:
            parts = Curl.valid_url(url_str)
            if not parts:
                raise URLError('URL not valid: "{}"'.format(url_str))

            ext = parts.path.split('.')[-1] or 'unknown'
            file_path = os.path.join(dest_dir, fname + '.' + ext)
            if override or not os.path.isfile(file_path):
                url = parts.geturl()
                if verbose:
                    if not did_update and intro:
                        print(intro)
                    print('  GET', url)
                did_update = True
                if not dry_run:
                    Curl.file(url, file_path, raise_except=True)
                    if date:
                        FileTime.set(file_path, date)
        return did_update
