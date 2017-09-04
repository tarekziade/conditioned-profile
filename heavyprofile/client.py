import shutil
import argparse
import os
import sys
import requests
import time
from datetime import date, timedelta
import tarfile
import functools

from clint.textui import progress
from heavyprofile import logger
from heavyprofile.util import DiffInfo


_STATE = '/tmp/hp-state'


# XXX we want a local download cache
def download_file(url, target=None):
    logger.msg("Downloading %s" % url)
    if target is None:
        target = url.split('/')[-1]
    req = requests.get(url, stream=True)
    total_length = int(req.headers.get('content-length'))

    with open(target, 'wb') as f:
        iter = req.iter_content(chunk_size=1024)
        size = total_length / 1024 + 1
        for chunk in progress.bar(iter, expected_size=size):
            if chunk:
                f.write(chunk)
                f.flush()
    return target


def apply_archive(server, archive, profile_dir):
    file = download_file(server + '/' + archive)
    logger.msg("Extracting everything in %r" % profile_dir)

    with tarfile.open(file, "r:gz") as tar:
        size = len(list(tar))
        with progress.Bar(expected_size=size) as bar:
            def _extract(self, *args, **kw):
                bar.show(bar.last_progress + 1)
                return self.old(*args, **kw)

            tar.old = tar.extract
            tar.extract = functools.partial(_extract, tar)

            # we want feedback during extraction
            tar.extractall(profile_dir)


def apply_diff(server, diff, profile_dir):
    file = download_file(server + '/' + diff)
    diffinfo = DiffInfo()

    logger.msg("Applying diff %r..." % diff)

    with tarfile.open(file, "r:gz") as tar:
        info = tar.getmember("diffinfo")
        diffinfo.load(tar.extractfile(info).read())
        size = len(diffinfo)

        for change_type, filename in progress.bar(diffinfo,
                                                  expected_size=size):
            filename = filename.decode()
            if change_type in (b'NEW', b'CHANGED'):
                info = tar.getmember(filename)
                target = os.path.join(profile_dir, filename)
                if info.isdir():
                    if not os.path.exists(target):
                        os.mkdir(target)
                else:
                    with open(target, 'wb') as f:
                        # stream?
                        data = tar.extractfile(info).read()
                        f.write(data)
            else:
                target = os.path.join(profile_dir, filename)
                if os.path.exists(target):
                    os.remove(target)


def check_exists(server, archive):
    logger.msg("Check if %r exists" % archive)
    resp = requests.head(server + '/' + archive)
    return resp.status_code == 200


def sync_profile(profile_dir, server, state=_STATE, when=None):
    server = server.rstrip('/')
    old_profile_dir = profile_dir = profile_dir.rstrip('/')
    logger.msg("Syncing profile located at %r" % profile_dir)
    if not os.path.exists(profile_dir):
        logger.msg("This is a new profile")

    # what was the last state ?
    if os.path.exists(_STATE):
        with open(_STATE) as f:
            last_state = time.strptime(f.read(), '%Y-%m-%d')
            last_state = date.fromtimestamp(time.mktime(last_state))
    else:
        last_state = None

    if when is None:
        when = date.today()

    full = True
    if last_state is not None and os.path.exists(profile_dir):
        if last_state == when:
            logger.msg("Nothing to do. Up-to-date.")
            return

        # if last state is known, we want to try to pick
        # up the diffs until we reach the target date
        delta = when - last_state
        diffs = []
        for day in range(delta.days):
            date1 = last_state + timedelta(days=day)
            date2 = last_state + timedelta(days=day+1)
            date1 = date1.strftime('%Y-%m-%d')
            date2 = date2.strftime('%Y-%m-%d')
            diffs.append('diff-%s-%s-hp.tar.gz' % (date1, date2))
        # we want to make sure each diff exists, if not, full download
        for diff in diffs:
            if not check_exists(server, diff):
                break
        full = False

    if os.path.exists(profile_dir):
        logger.msg("Backing up the profile...")
        shutil.copytree(profile_dir, profile_dir + '.new')
        profile_dir = profile_dir + '.new'

    if full:
        logger.msg("Full download...")
        # let's pick up the last full archive
        archive = when.strftime('%Y-%m-%d-hp.tar.gz')
        apply_archive(server, archive, profile_dir)
    else:
        logger.msg("Diffs download...")
        for diff in diffs:
            apply_diff(server, diff, profile_dir)

    with open(_STATE, 'w') as f:
        f.write(when.strftime('%Y-%m-%d'))

    # moving over of everything went well
    if not full:
        shutil.rmtree(old_profile_dir)
        os.rename(profile_dir, old_profile_dir)
    logger.msg("Done.")


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Client')
    parser.add_argument('profile', help='Profile Dir', type=str)
    parser.add_argument('--server', help='Archives server', type=str,
                        default='http://localhost:8000')
    args = parser.parse_args(args=args)
    sync_profile(args.profile, args.server)


if __name__ == '__main__':
    main()
