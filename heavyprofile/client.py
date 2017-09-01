import shutil
import argparse
import os
import sys
import requests
import time
from datetime import date, timedelta

from clint.textui import progress
from heavyprofile import logger


_STATE = '/tmp/hp-state'


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


def apply_archive(server, archive, profile_dir):
    download_file(server + '/' + archive)
    raise NotImplementedError()


def apply_diff(server, diff, profile_dir):
    download_file(server + '/' + diff)
    raise NotImplementedError()


def check_exists(server, archive):
    logger.msg("Check if %r exists" % archive)
    resp = requests.head(server + '/' + archive)
    return resp.status_code == 200


def sync_profile(profile_dir, server, state=_STATE, when=None):
    server = server.rstrip('/')

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
    if last_state is not None:
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

    logger.msg("Backing up the profile")
    shutil.copytree(profile_dir, profile_dir + '.new')
    profile_dir = profile_dir + '.new'

    if full:
        # let's pick up the last full archive
        archive = when.strftime('%Y-%m-%d-hp.tar.gz')
        apply_archive(server, archive, profile_dir)
    else:
        for diff in diffs:
            apply_diff(server, diff, profile_dir)

    with open(_STATE, 'w') as f:
        f.write(when.strftime('%Y-%m-%d'))

    # moving over of everything went well
    os.rename(profile_dir, profile_dir[:-len('.new')])
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
