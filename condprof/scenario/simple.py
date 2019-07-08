import random
import os
from condprof import logger
import asyncio


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
_TAB_OPEN = "window.open();"


class TabSwitcher(object):
    def __init__(self, session):
        self.handles = None
        self.current = 0
        self.session = session

    async def switch(self):
        session = self.session
        if self.handles is None:
            self.handles = await session.get_window_handles()
            self.current = 0

        handle = self.handles[self.current]
        if self.current == len(self.handles) - 1:
            self.current = 0
        else:
            self.current += 1
        await session.switch_to_window(handle)


async def simple(session, args):
    metadata = {}
    max = args.max_urls
    # open 20 tabs
    for i in range(20):
        await session.execute_script(_TAB_OPEN)

    tabs = TabSwitcher(session)
    visited = 0

    for current, url in enumerate(URL_LIST):
        logger.visit_url(index=current+1, total=max, url=url)
        retries = 0
        while retries < 3:
            try:
                await asyncio.wait_for(session.get(url), 5)
                visited += 1
                break
            except asyncio.TimeoutError:
                retries += 1

        if max != -1 and current + 1 == max:
            break

        await tabs.switch()

    metadata['visited_url'] = visited
    return metadata
