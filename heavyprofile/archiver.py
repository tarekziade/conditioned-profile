"""Maintains an archives directory given a profile
"""
import io
import sys
import argparse
import tarfile
import os
import glob
from datetime import date, timedelta
import copy

from heavyprofile import logger


def _b(data):
    return bytes(data, "utf8")


def _tarinfo2mem(tar, tarinfo):
    metadata = copy.copy(tarinfo)
    data = tar.extractfile(tarinfo)
    if data is not None:
        data = data.read()
    return metadata, data


def create_diff(archives_dir, when, current, previous):
    current_files = {}
    previous_files = {}
    diff_info = []
    tarfiles = []
    changed = 0
    new = 0
    deleted = 0

    # reading all files and dirs
    with tarfile.open(current, "r:gz") as tar:
        for tarinfo in tar:
            current_files[tarinfo.name] = _tarinfo2mem(tar, tarinfo)

    with tarfile.open(previous, "r:gz") as tar:
        for tarinfo in tar:
            previous_files[tarinfo.name] = _tarinfo2mem(tar, tarinfo)

    for name, info in current_files.items():
        if name not in previous_files:
            diff_info.append(b"NEW:%s" % _b(name))
            new += 1
            tarfiles.append(info)
        else:
            old = previous_files[name][0].get_info()['chksum']
            new = info[0].get_info()['chksum']
            if old != new:
                diff_info.append(b"CHANGED:%s" % _b(name))
                changed += 1
                tarfiles.append(info)

    for name, info in previous_files.items():
        if name not in current_files:
            diff_info.append(b"DELETED:%s" % _b(name))
            deleted += 1

    day_before = when - timedelta(days=1)
    diff_archive = 'diff-%s-%s-hp.tar.gz' % (day_before.strftime('%Y-%m-%d'),
                                             when.strftime('%Y-%m-%d'))
    diff_archive = os.path.join(archives_dir, diff_archive)
    diff_data = b'\n'.join(diff_info)

    with tarfile.open(diff_archive, "w:gz") as tar:
        diff_info = tarfile.TarInfo(name="diffinfo")
        diff_info.size = len(diff_data)
        tar.addfile(diff_info, fileobj=io.BytesIO(diff_data))

        for info, data in tarfiles:
            if data is not None:
                tar.addfile(info, fileobj=io.BytesIO(data))
            else:
                tar.addfile(info)
    logger.msg("=> %d new files, %d modified, %d deleted." % (new,
                    changed, deleted))


def update_archives(profile_dir, archives_dir, when=None):
    if when is None:
        when = date.today()
    day_before = when - timedelta(days=1)
    archive = when.strftime('%Y-%m-%d-hp.tar.gz')
    logger.msg("Creating %s..." % archive)
    archive = os.path.join(archives_dir, archive)

    with tarfile.open(archive, "w:gz") as tar:
        for filename in glob.glob(os.path.join(profile_dir, "*")):
            logger.msg("=> Adding %s..." % filename)
            tar.add(filename, os.path.basename(filename))

    logger.msg("Done.")
    latest = os.path.join(archives_dir, 'latest.tar.gz')
    if os.path.exists(latest):
        os.remove(latest)
    os.symlink(archive, latest)
    previous = os.path.join(archives_dir,
                            day_before.strftime('%Y-%m-%d-hp.tar.gz'))

    if os.path.exists(previous):
        logger.msg("Creating a diff tarball with the previous day")
        create_diff(archives_dir, when, archive, previous)
        logger.msg("Done.")

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Archiver')
    parser.add_argument('profile_dir', help='Profile Dir', type=str)
    parser.add_argument('archives_dir', help='Archives Dir', type=str)
    parser.add_argument('--prior', help='Prior', type=int, default=0)
    args = parser.parse_args(args=args)

    when = date.today()
    if args.prior > 0:
        when = when - timedelta(days=args.prior)

    if not os.path.exists(args.archives_dir):
        logger.msg("%r does not exists." % args.archives_dir)
        sys.exit(1)
    update_archives(args.profile_dir, args.archives_dir, when)


if __name__ == "__main__":
    main()
