import shutil
import argparse
import os
import sys
import requests
import time

from datetime import date, timedelta
from heavyprofile import logger

_STATE = '/tmp/hp-state'



def apply_archive(archive, profile_dir):
    logger.msg("Downloading %s" % archive)


def apply_diff(diff, profile_dir):
    logger.msg("Downloading %s" % diff)


def check_exists(archive):
    logger.msg("Check if %r exists" % archive)


def sync_profile(profile_dir, archives_url, state=_STATE, when=None):
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
            if not check_exists(diff):
                break
        full = False

    logger.msg("Backing up the profile")
    shutil.copytree(profile_dir, profile_dir + '.new')
    profile_dir = profile_dir + '.new'

    if full:
        # let's pick up the last full archive
        archive = when.strftime('%Y-%m-%d-hp.tar.gz')
        apply_archive(archive, profile_dir)
    else:
        for diff in diffs:
            apply_diff(diff, profile_dir)

    with open(_STATE, 'w') as f:
        f.write(when.strftime('%Y-%m-%d'))

    # moving over of everything went well
    os.rename(profile_dir, profile_dir[:-len('.new')])
    logger.msg("Done.")


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Client')
    parser.add_argument('profile', help='Profile Dir', type=str)
    parser.add_argument('archives', help='Archives URL', type=str)
    args = parser.parse_args(args=args)
    sync_profile(args.profile, args.archives)


if __name__ == '__main__':
    main()
