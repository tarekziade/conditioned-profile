import random
import os
from heavyprofile import logger


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


async def simple(session, args):
    metadata = {}
    max = args.max_urls
    for current, url in enumerate(URL_LIST):
        logger.visit_url(index=current+1, total=max, url=url)
        await session.get(url)
        if max != -1 and current + 1 == max:
            break

    metadata['visited_url'] = current
    return metadata
