#!/usr/bin/env python3
import os
from sys import stderr
from typing import Dict, Any, Optional, TextIO
from datetime import datetime  # typing

from botlib.cli import Cli
from botlib.curl import Curl
from botlib.feed2list import Feed2List
from botlib.helper import StrFormat, FileWrite


def main() -> None:
    ''' CLI entry. '''
    cli = Cli()
    cli.arg_dir('dest_dir', help='Download all entries here')
    cli.arg('source', help='RSS file or web-url')
    cli.arg_bool('--dry-run', help='Do not download, just parse')
    cli.arg_bool('--by-year', help='Place episodes in dest_dir/year/')
    args = cli.parse()

    try:
        print('Processing:', args.dest_dir)
        process(args.source, args.dest_dir,
                by_year=args.by_year, dry_run=args.dry_run)
        print('Done.')
    except Exception as e:
        print('ERROR: ' + str(e), file=stderr)


def process(
    source: str,  # local file path or remote url
    dest_dir: str,
    *, by_year: bool = False,
    dry_run: bool = False
) -> bool:
    ''' Parse a full podcast file / source. '''
    # open source
    if os.path.isfile(source):
        fp = open(source)  # type: Optional[TextIO] # closed in Feed2List
    elif Curl.valid_url(source):
        fp = Curl.get(source)  # closed in Feed2List
    else:
        raise AttributeError('Not a valid file or URL: "{}"'.format(source))

    # process
    dest = dest_dir
    for entry in reversed(Feed2List(fp, keys=[
        'link', 'title', 'description', 'enclosure',  # audio
        'pubDate', 'media:content',  # image
        # 'itunes:image', 'itunes:duration', 'itunes:summary'
    ])):
        date = entry['pubDate']  # try RSS only # type: datetime
        if by_year:
            dest = os.path.join(dest_dir, str(date.year))
            if not dry_run and not os.path.exists(dest):
                os.mkdir(dest)
        process_entry(entry, date, dest, dry_run=dry_run)
    return True


def process_entry(
    entry: Dict[str, Any],
    date: datetime,
    dest_dir: str,
    *, dry_run: bool = False
) -> None:
    ''' Parse a single podcast media entry. '''
    title = entry['title']
    # <enclosure url="*.mp3" length="47216000" type="audio/mpeg"/>
    audio_url = entry.get('enclosure', {}).get('url')
    if not audio_url:
        print('  ERROR: URL not found for "{}"'.format(title), file=stderr)
        return
    # <media:content url="*.jpg" width="300" rel="full_image" height="300" />
    images = entry.get('media:content', [])
    if not isinstance(images, list):
        images = [images]
    maxRes = 0
    image_url = None
    for img in images:
        res = int(img.get('width', 0)) * int(img.get('height', 0))
        if res > maxRes:
            maxRes = res
            image_url = img.get('url')
    # make request
    fname = '{} - {}'.format(date.strftime('%Y-%m-%d'),
                             StrFormat.safe_filename(title))
    intro = '\ndownloading: ' + fname
    urllist = [audio_url, image_url] if image_url else [audio_url]
    flag = Curl.once(dest_dir, fname, urllist, date, override=False,
                     dry_run=dry_run, verbose=True, intro=intro)

    @FileWrite.once(dest_dir, fname + '.txt', date, override=False,
                    dry_run=dry_run, verbose=True, intro=flag or intro)
    def _description() -> str:
        return '{}\n{}\n\n{}\n\n\n{}\n'.format(
            title, '=' * len(title),
            StrFormat.strip_html(entry.get('description', '')),
            entry.get('link', ''))


if __name__ == '__main__':
    main()
