import platform
import time
import os
import tempfile
import shutil
import contextlib
import json

import requests
from requests.exceptions import ConnectionError
from bs4 import BeautifulSoup
from clint.textui import progress

from condprof import logger
from condprof.signing import Signer


_BASE_PROFILE = os.path.join(os.path.dirname(__file__), 'base_profile')
TASK_CLUSTER = 'TASKCLUSTER_WORKER_TYPE' in os.environ.keys()


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
    if server is not None:
        archive = server + '/' + archive
    try:
        resp = requests.head(archive)
    except ConnectionError:
        return False, {}

    if resp.status_code == 303:
        return check_exists(resp.headers['Location'])
    return resp.status_code == 200, resp.headers


def download_file(url, target=None, check_file=True):
    signer = Signer()
    present, headers = check_exists(url)
    if not present:
        logger.msg("Cannot find %r" % url)
        raise ArchiveNotFound(url)

    etag = headers.get('ETag')
    if target is None:
        target = url.split('/')[-1]

    if check_file:
        check = requests.get(url + '.sha256')
        check = check.text

    if os.path.exists(target):
        if not check_file:
            if etag is not None:
                if os.path.exists(target + '.etag'):
                    with open(target + '.etag') as f:
                        current_etag = f.read()
                    if etag == current_etag:
                        logger.msg("Already Downloaded")
                        # should at least check the size?
                        return target

            logger.msg("Changed!")
        else:
            existing = signer.checksum(target)
            if existing == check:
                logger.msg("Already Downloaded")
                return target

    logger.msg("Downloading %s" % url)
    req = requests.get(url, stream=True)
    total_length = int(req.headers.get('content-length'))
    target_dir = os.path.dirname(target)
    if target_dir != '' and not os.path.exists(target_dir):
        os.makedirs(target_dir)
    with open(target, 'wb') as f:
        if TASK_CLUSTER:
            for chunk in req.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    f.flush()
        else:
            iter = req.iter_content(chunk_size=1024)
            size = total_length / 1024 + 1
            for chunk in progress.bar(iter, expected_size=size):
                if chunk:
                    f.write(chunk)
                    f.flush()

    if etag is not None:
        with open(target + '.etag', 'w') as f:
            f.write(etag)

    if check_file and check != signer.checksum(target):
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
            cmd = "hdiutil attach -mountpoint /Volumes/Nightly %s"
            os.system(cmd % target)
            binary = ('/Volumes/Nightly/FirefoxNightly.app'
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
                os.system("hdiutil detach /Volumes/Nightly")
            elif platform.system() == 'Linux':
                # XXX we should keep it for next time
                shutil.rmtree('firefox')
