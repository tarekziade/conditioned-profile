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
from heavyprofile.util import DiffInfo, checksum
from clint.textui import progress


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

    diff_info = DiffInfo()

    for name, info in current_files.items():
        if name not in previous_files:
            diff_info.add_new(_b(name))
            new += 1
            tarfiles.append(info)
        else:
            old = previous_files[name][0].get_info()['chksum']
            new = info[0].get_info()['chksum']
            if old != new:
                diff_info.add_changed(_b(name))
                changed += 1
                tarfiles.append(info)

    for name, info in previous_files.items():
        if name not in current_files:
            diff_info.add_deleted(_b(name))
            deleted += 1

    day_before = when - timedelta(days=1)
    diff_archive = 'diff-%s-%s-hp.tar.gz' % (day_before.strftime('%Y-%m-%d'),
                                             when.strftime('%Y-%m-%d'))
    diff_archive = os.path.join(archives_dir, diff_archive)
    diff_data = diff_info.dump()

    with tarfile.open(diff_archive, "w:gz") as tar:
        size = len(tarfiles) + 1
        with progress.Bar(expected_size=size) as bar:
            diff_info = tarfile.TarInfo(name="diffinfo")
            diff_info.size = len(diff_data)
            tar.addfile(diff_info, fileobj=io.BytesIO(diff_data))
            bar.show(1)

            for info, data in tarfiles:
                if data is not None:
                    tar.addfile(info, fileobj=io.BytesIO(data))
                else:
                    tar.addfile(info)
                bar.show(bar.last_progress + 1)

    msg = "=> %d new files, %d modified, %d deleted."
    logger.msg(msg % (new, changed, deleted))
    return diff_archive


def update_archives(profile_dir, archives_dir, when=None):
    if when is None:
        when = date.today()
    day_before = when - timedelta(days=1)
    archive = when.strftime('%Y-%m-%d-hp.tar.gz')
    logger.msg("Creating %s..." % archive)
    archive = os.path.join(archives_dir, archive)

    with tarfile.open(archive, "w:gz") as tar:
        files = glob.glob(os.path.join(profile_dir, "*"))
        size = len(files)
        with progress.Bar(expected_size=size) as bar:
            for filename in files:
                tar.add(filename, os.path.basename(filename))
                bar.show(bar.last_progress + 1)

    checksum(archive)
    archive_hash = archive + '.sha256'
    logger.msg("Done.")

    latest = os.path.join(archives_dir, 'latest.tar.gz')
    if os.path.exists(latest):
        os.remove(latest)
    os.symlink(archive, latest)

    latest_hash = os.path.join(archives_dir, 'latest.tar.gz.sha256')
    if os.path.exists(latest_hash):
        os.remove(latest_hash)
    os.symlink(archive_hash, latest_hash)

    previous = os.path.join(archives_dir,
                            day_before.strftime('%Y-%m-%d-hp.tar.gz'))

    if os.path.exists(previous):
        logger.msg("Creating a diff tarball with the previous day")
        diff = create_diff(archives_dir, when, archive, previous)
        checksum(diff)
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
