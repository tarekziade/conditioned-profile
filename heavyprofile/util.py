import time
import os
import tempfile
import shutil
import hashlib
import requests
from bs4 import BeautifulSoup
from clint.textui import progress
import contextlib

from heavyprofile import logger


_BASE_PROFILE = os.path.join(os.path.dirname(__file__), 'base_profile')


class ArchiveNotFound(Exception):
    pass


class ArchiveError(Exception):
    pass


def fresh_profile(target_dir=None):
    if target_dir is None:
        target_dir = os.path.join(tempfile.mkdtemp(), 'profile')
    shutil.copytree(_BASE_PROFILE, target_dir)
    return target_dir


class DiffInfo(object):
    def __init__(self):
        self._info = []

    def __iter__(self):
        for change in self._info:
            yield change.split(b':')

    def __len__(self):
        return len(self._info)

    def load(self, data):
        self._info[:] = []
        for line in data.split(b'\n'):
            line = line.strip()
            if line == b'':
                continue
            self._info.append(line)

    def dump(self):
        return b'\n'.join(self._info)

    def add_changed(self, name):
        self._info.append(b"CHANGED:%s" % name)

    def add_new(self, name):
        self._info.append(b"NEW:%s" % name)

    def add_deleted(self, name):
        self._info.append(b"DELETED:%s" % name)


def checksum(filename, write=True):
    hash = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)

    if write:
        check = filename + ".sha256"
        with open(check, "w") as f:
            f.write(hash.hexdigest())

    return hash.hexdigest()


link = 'https://ftp.mozilla.org/pub/firefox/nightly/latest-mozilla-central/'


def get_firefox_download_link():
    page = requests.get(link).text
    soup = BeautifulSoup(page, "html.parser")
    for node in soup.find_all('a', href=True):
        href = node['href']
        if href.endswith('.dmg'):
            return 'https://ftp.mozilla.org' + href
    raise Exception()


def check_exists(archive, server=None):
    logger.msg("Check if %r exists" % archive)
    if server is not None:
        archive = server + '/' + archive
    resp = requests.head(archive)
    return resp.status_code == 200, resp.headers


def download_file(url, target=None, check_file=True):
    present, headers = check_exists(url)
    if not present:
        logger.msg("Cannot find %r" % url)
        raise ArchiveNotFound(url)

    logger.msg("Downloading %s" % url)
    if target is None:
        target = url.split('/')[-1]

    if check_file:
        check = requests.get(url + '.sha256')
        check = check.text

    if os.path.exists(target):
        if not check_file:
            # should at least check the size?
            return target

        existing = checksum(target)
        if existing == check:
            logger.msg("Already Downloaded")
            return target

    req = requests.get(url, stream=True)
    total_length = int(req.headers.get('content-length'))

    with open(target, 'wb') as f:
        iter = req.iter_content(chunk_size=1024)
        size = total_length / 1024 + 1
        for chunk in progress.bar(iter, expected_size=size):
            if chunk:
                f.write(chunk)
                f.flush()

    if check_file and check != checksum(target):
        logger.msg("Bad checksum!")
        raise ArchiveError(target)

    return target


@contextlib.contextmanager
def latest_nightly(binary=None):
    if binary is None:
        # we want to use the latest nightly
        # mac os specific for now
        nightly_archive = get_firefox_download_link()
        logger.msg("Downloading %s" % nightly_archive)
        target = download_file(nightly_archive, check_file=False)
        cmd = "hdiutil attach -mountpoint /Volumes/Firefox %s"
        os.system(cmd % target)
        # now that the dmg is mounted, we can use it
        binary = ('/Volumes/Firefox/FirefoxNightly.app'
                  '/Contents/MacOS/firefox')
        mounted = True
    else:
        mounted = False
    try:
        yield binary
    finally:
        if mounted:
            logger.msg("Unmounting Firefox")
            time.sleep(10)
            os.system("hdiutil detach /Volumes/Firefox")
