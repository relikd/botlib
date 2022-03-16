#!/usr/bin/env python3
import os
import json
from sys import stderr
from hashlib import md5
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlretrieve, urlopen, Request
from .helper import FileTime
import ssl
# somehow macOS default behavior for SSL verification is broken
ssl._create_default_https_context = ssl._create_unverified_context


def _read_modified_header(fname: str):  # dict or None
    if not os.path.isfile(fname):
        return None
    res = {}
    with open(fname) as fp:
        head = dict(x.strip().split(': ', 1) for x in fp.readlines())
        etag = head.get('Etag')
        if etag:
            res['If-None-Match'] = etag
        lastmod = head.get('Last-Modified')
        if lastmod:
            res['If-Modified-Since'] = lastmod.replace('-gzip', '')
    return res or None


class Curl:
    CACHE_DIR = 'cache'

    @staticmethod
    def valid_url(url):
        url = url.strip().replace(' ', '+')
        x = urlparse(url)
        return x if x.scheme and x.netloc else None

    @staticmethod
    def url_hash(url) -> str:
        x = Curl.valid_url(url)
        return '{}-{}'.format(x.hostname if x else 'ERR',
                              md5(url.encode()).hexdigest())

    @staticmethod
    def open(url: str, *, headers={}):  # url-open-pointer or None
        try:
            head = {'User-Agent': 'Mozilla/5.0'}
            if headers:
                head.update(headers)
            return urlopen(Request(url, headers=head))
        except Exception as e:
            if isinstance(e, HTTPError) and e.getcode() == 304:
                # print('Not-Modified: {}'.format(url), file=stderr)
                return None  # ignore not-modified
            print('ERROR: Load URL "{}" -- {}'.format(url, e), file=stderr)
            return None

    @staticmethod
    def get(url: str, *, cache_only=False):  # file-pointer
        '''
        Returns an already open file pointer.
        You are responsible for closing the file.
        NOTE: `HTML2List.parse` and `Feed2List.parse` will close it for you.
        '''
        fname = '{}/curl-{}.data'.format(Curl.CACHE_DIR, Curl.url_hash(url))
        fname_head = fname[:-5] + '.head'
        # If file was created less than 45 sec ago, reuse cached value
        if cache_only or (os.path.isfile(fname) and FileTime.get(fname) < 45):
            return open(fname)

        os.makedirs(Curl.CACHE_DIR, exist_ok=True)
        conn = Curl.open(url, headers=_read_modified_header(fname_head))
        if conn:
            with open(fname_head, 'w') as fp:
                fp.write(str(conn.info()).strip())
            with open(fname, 'wb') as fp:
                while True:
                    data = conn.read(8192)  # 1024 Bytes
                    if not data:
                        break
                    fp.write(data)
        if os.path.isfile(fname):
            return open(fname)

    @staticmethod
    def json(url: str, fallback=None, *, cache_only=False) -> object:
        conn = Curl.get(url, cache_only=cache_only)
        if not conn:
            return fallback
        with conn as fp:
            return json.load(fp)

    @staticmethod
    def file(url: str, dest_path: str, *, raise_except=False) -> bool:
        tmp_file = dest_path + '.inprogress'
        try:
            urlretrieve(url, tmp_file)
            os.rename(tmp_file, dest_path)  # atomic download, no broken files
            return True
        except HTTPError as e:
            # print('ERROR: Load URL "{}" -- {}'.format(url, e), file=stderr)
            if raise_except:
                raise e
            return False

    @staticmethod
    def once(dest_dir, fname, urllist, date, desc=None, *,
             override=False, dry_run=False, verbose=False, intro=''):
        did_update = False
        for url_str in urllist:
            parts = Curl.valid_url(url_str)
            if not parts:
                raise URLError('URL not valid: "{}"'.format(url_str))

            ext = parts.path.split('.')[-1] or 'unknown'
            file_path = os.path.join(dest_dir, fname + '.' + ext)
            if override or not os.path.isfile(file_path):
                if not did_update and verbose and intro:
                    print(intro)
                did_update = True
                if verbose:
                    print('  GET', parts.geturl())
                if not dry_run:
                    Curl.file(parts.geturl(), file_path, raise_except=True)
                    FileTime.set(file_path, date)
        if desc:
            desc_path = os.path.join(dest_dir, fname + '.txt')
            if override or not os.path.isfile(desc_path):
                did_update = True
                if verbose:
                    print('  –>', desc_path)
                if not dry_run:
                    with open(desc_path, 'w') as f:
                        f.write(desc)
                    FileTime.set(desc_path, date)
        return did_update
