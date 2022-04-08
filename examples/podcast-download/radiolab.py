#!/usr/bin/env python3
import os
from sys import stderr

from botlib.cli import Cli
from botlib.curl import Curl, URLError
from botlib.helper import StrFormat, FileWrite
from botlib.oncedb import OnceDB

API = 'http://api.wnyc.org/api/v3'
COHORT = 'radiolab'
db_ids = OnceDB('radiolab_ids.sqlite')
db_slugs = OnceDB('radiolab_slugs.sqlite')
# published-at does not contain timezone info, but is assumed to be EST
os.environ['TZ'] = 'America/New_York'


def main():
    cli = Cli()
    cli.arg_dir('dest_dir', help='Download all episodes to dest_dir/year/')
    cli.arg_bool('--dry-run', help='Do not download, just parse')
    args = cli.parse()

    try:
        for title, query in (
            ('Podcasts', 'radiolab/podcasts'),
            ('Radio Shows', 'radiolab/radio-shows'),
            # ('Broadcasts', 'radiolabmoreperfect/radio-broadcasts'),
        ):
            processEpisodeList(args.dest_dir, title, query,
                               dry_run=args.dry_run)
    except Exception as e:
        print('  ERROR: ' + str(e), file=stderr)
        exit(1)

    print('\nDone.\n\nNow check MP3 tags (consistency).')


def processEpisodeList(basedir, title, query, index=1, *, dry_run=False):
    print('\nProcessing: {}'.format(title), end='')
    dat = Curl.json('{}/channel/shows/{}/{}?limit=9'.format(API, query, index))
    total = dat['data']['attributes']['total-pages']
    print(' ({}/{})'.format(index, total))
    anything_new = False
    for inc in dat['included']:
        anything_new |= processEpisode(inc['attributes'], basedir,
                                       dry_run=dry_run)
    if anything_new and index < total:
        processEpisodeList(basedir, title, query, index + 1, dry_run=dry_run)


def processEpisode(obj, basedir, *, dry_run=False):
    uid = obj['cms-pk']
    if db_ids.contains(COHORT, uid):
        return False  # Already exists

    title = obj['title'].strip()
    slug = obj['slug'].strip()
    # [newsdate] 2009-11-03T00:35:34-05:00 [publish-at] 2009-11-03T00:35:34
    date_a = StrFormat.to_date(obj['newsdate'].strip())
    date_b = StrFormat.to_date(obj['publish-at'].strip())
    date = date_a if date_a.timestamp() <= date_b.timestamp() else date_b

    # create by-year subdir
    dest_dir = os.path.join(basedir, str(date.year))
    if not dry_run and not os.path.exists(dest_dir):
        os.mkdir(dest_dir)

    # make filename and download list
    fname = '{} - {}'.format(date.strftime('%Y-%m-%d'),
                             StrFormat.safe_filename(title))
    urllist = [obj['audio'], obj['video']]
    urllist = [x for x in urllist if isinstance(x, str) and Curl.valid_url(x)]
    if not urllist:
        print('\ndownloading: {} ({}, {})'.format(fname, uid, slug))
        print('  No downloadable media found.')
        return False
    # get image
    img_url, img_desc = get_img_desc(obj['image-main'])
    if img_url:
        urllist.append(img_url)
    # download files
    intro = '\ndownloading: {} ({})'.format(fname, uid)
    flag = Curl.once(dest_dir, fname, urllist, date, override=False,
                     dry_run=dry_run, verbose=True, intro=intro)

    @FileWrite.once(dest_dir, fname + '.txt', date, override=False,
                    dry_run=dry_run, verbose=True, intro=flag or intro)
    def write_description():
        nonlocal flag
        flag = True
        desc = title + '\n' + '=' * len(title)
        desc += '\n\n' + StrFormat.strip_html(obj['body'])
        if img_desc:
            desc += '\n\n' + img_desc
        return desc + '\n\n\n' + obj['url'].strip() + '\n'  # link to article

    @FileWrite.once(dest_dir, fname + '.transcript.txt', date, override=False,
                    dry_run=dry_run, verbose=True, intro=flag or intro)
    def write_transcript():
        nonlocal flag
        flag = True
        data = StrFormat.strip_html(obj['transcript'])
        return data + '\n' if data else None

    # success! now save state
    if flag and not dry_run:
        db_ids.put(COHORT, uid, fname)
        db_slugs.put(COHORT, uid, slug)
        print('  SLUG: {}'.format(slug))
    return flag  # potentially need to query the next page too


def get_img_desc(obj):
    if not obj:
        return (None, None)
    url = (obj['url'] or '').strip()
    if not url:
        return (None, None)
    txt = None
    cred_name = obj['credits-name'].strip()
    cred_url = obj['credits-url'].strip()
    if cred_name:
        txt = 'Image by ' + cred_name
    if cred_url:
        if txt:
            txt += ' @ ' + cred_url
        else:
            txt = 'Image source: ' + cred_url
    return (url, txt)


# Individuals taken from Google search
# -> inurl:radiolab/segments site:wnycstudios.org
# -> inurl:radiolab/episodes site:wnycstudios.org
# Then regex:  /episodes/([^;]*?)" onmousedown

def processSingle(slug, basedir):
    # cms-pk = 91947 , slug = '91947-do-i-know-you'
    all_slugs = [slug for _, _, _, slug in db_slugs]
    if slug not in all_slugs:
        print(slug)
        data = Curl.json('{}/story/{}'.format(API, slug))
        try:
            processEpisode(data['data']['attributes'], basedir, dry_run=True)
        except URLError as e:
            print('  ERROR: ' + str(e), file=stderr)


main()
