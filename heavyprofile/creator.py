import os
import sys
import argparse
import asyncio

from arsenic import get_session
from arsenic.browsers import Firefox
from arsenic.services import Geckodriver, free_port


class CustomGeckodriver(Geckodriver)
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


def next_url():
    for url in URLS:
        url = url.strip()
        if url.startswith('#'):
            continue
        for word in WORDS:
            word = word.strip()
            if word.startswith('#'):
                continue
            yield url % word


firefox = '/Applications/FirefoxNightly.app/Contents/MacOS/firefox'

async def build_profile(profile_dir, max_urls=10):
    caps = {"moz:firefoxOptions": {"binary": firefox,
                                   "args": ["-profile", profile_dir],
                                   }}
    visited = 0

    async with get_session(CustomGeckodriver(), Firefox(**caps)) as session:
        for url in next_url():
            await session.get(url)
            visited += 1
            if visited == max_urls:
                break


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Creator')
    parser.add_argument('profile', help='Profile Dir', type=str)
    args = parser.parse_args(args=args)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(build_profile(args.profile_dir))
    loop.close()


if __name__ == '__main__':
    main()
