import time
import os
import sys
import argparse
import asyncio
import random

from arsenic import get_session
from arsenic.browsers import Firefox
from arsenic.services import Geckodriver, free_port, subprocess_based_service

from heavyprofile.util import (fresh_profile, get_firefox_download_link,
                               download_file)
from heavyprofile import logger


class CustomGeckodriver(Geckodriver):
    async def start(self):
        port = free_port()
        await self._check_version()
        return await subprocess_based_service(
            [self.binary, '--port', str(port), '--marionette-port', '50499'],
            f'http://localhost:{port}',
            self.log_file
        )


WORDS = os.path.join(os.path.dirname(__file__), 'words.txt')
with open(WORDS) as f:
    WORDS = f.readlines()


URLS = os.path.join(os.path.dirname(__file__), 'urls.txt')
with open(URLS) as f:
    URLS = f.readlines()


URL_LIST = []


def _build_url_list():
    for url in URLS:
        url = url.strip()
        if url.startswith('#'):
            continue
        for word in WORDS:
            word = word.strip()
            if word.startswith('#'):
                continue
            URL_LIST.append(url.format(word))
    random.shuffle(URL_LIST)


_build_url_list()


async def build_profile(profile_dir, max_urls=2, firefox=None):
    logger.msg("Updating profile located at %r" % profile_dir)
    caps = {"moz:firefoxOptions": {"args": ["-headless", "-profile",
                                            profile_dir]}}
    if firefox is not None:
        caps['moz:firefoxOptions']['binary'] = firefox

    logger.msg("Starting the Fox...")
    with open('gecko.log', 'a+') as glog:
        async with get_session(CustomGeckodriver(log_file=glog),
                               Firefox(**caps)) as session:
            for current, url in enumerate(URL_LIST):
                logger.visit_url(index=current+1, total=max_urls, url=url)
                await session.get(url)
                if max_urls != -1 and current + 1 == max_urls:
                    break

    logger.msg("Done.")


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Creator')
    parser.add_argument('profile', help='Profile Dir', type=str)
    parser.add_argument('--max-urls', help='How many URLS to visit',
                        type=int, default=-1)
    parser.add_argument('--firefox', help='Firefox Binary',
                        type=str, default=None)

    args = parser.parse_args(args=args)
    if not os.path.exists(args.profile):
        fresh_profile(args.profile)

    if args.firefox is None:
        # we want to use the latest nightly
        # mac os specific for now
        nightly_archive = get_firefox_download_link()
        logger.msg("Downloading %s" % nightly_archive)
        target = download_file(nightly_archive, check_file=False)
        cmd = "hdiutil attach -mountpoint /Volumes/Firefox %s"
        os.system(cmd % target)
        # now that the dmg is mounted, we can use it
        args.firefox = ('/Volumes/Firefox/FirefoxNightly.app'
                        '/Contents/MacOS/firefox')
        unmount = True
    else:
        unmount = False

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(build_profile(args.profile,
                                              max_urls=args.max_urls,
                                              firefox=args.firefox))
    finally:
        loop.close()

    if unmount:
        logger.msg("Unmounting Firefox")
        time.sleep(10)
        os.system("hdiutil detach /Volumes/Firefox")


if __name__ == '__main__':
    main()
