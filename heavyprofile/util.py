import platform
import time
import os
import tempfile
import shutil
import hashlib
import requests
from bs4 import BeautifulSoup
from clint.textui import progress
import contextlib
import json

from heavyprofile import logger


_BASE_PROFILE = os.path.join(os.path.dirname(__file__), 'base_profile')


class ArchiveNotFound(Exception):
    pass


class ArchiveError(Exception):
    pass


def fresh_profile(target_dir=None, name='simple'):
    if target_dir is None:
        target_dir = os.path.join(tempfile.mkdtemp(), 'profile')
    shutil.copytree(_BASE_PROFILE, target_dir)
    with open(os.path.join(target_dir, '.hp.json'), 'w') as f:
        f.write(json.dumps({'name': name}))

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
    if platform.system() == 'Darwin':
        extension = '.dmg'
    elif platform.system() == 'Linux':
        arch = platform.machine()
        extension = '.linux-%s.tar.bz2' % arch
    else:
        raise NotImplementedError(platform.system())

    page = requests.get(link).text
    soup = BeautifulSoup(page, "html.parser")
    for node in soup.find_all('a', href=True):
        href = node['href']
        if href.endswith(extension):
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
        nightly_archive = get_firefox_download_link()
        logger.msg("Downloading %s" % nightly_archive)
        target = download_file(nightly_archive, check_file=False)

        # on macOs we just mount the DMG
        if platform.system() == 'Darwin':
            cmd = "hdiutil attach -mountpoint /Volumes/Firefox %s"
            os.system(cmd % target)
            binary = ('/Volumes/Firefox/FirefoxNightly.app'
                      '/Contents/MacOS/firefox')
        # on linux we unpack it
        elif platform.system() == 'Linux':
            cmd = 'bunzip2 %s' % target
            os.system(cmd)
            cmd = 'tar -xvf %s' % target[:-len('.bz2')]
            os.system(cmd)
            binary = 'firefox/firefox'

        mounted = True
    else:
        mounted = False
    try:
        yield binary
    finally:
        if mounted:
            if platform.system() == 'Darwin':
                logger.msg("Unmounting Firefox")
                time.sleep(10)
                os.system("hdiutil detach /Volumes/Firefox")
            elif platform.system() == 'Linux':
                # XXX we should keep it for next time
                shutil.rmtree('firefox')
