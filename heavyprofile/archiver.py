"""Maintains an archives directory given a profile
"""
import sys
import argparse
import tarfile
import os
import glob
from datetime import date, timedelta
import tempfile


def _log(msg):
    print(msg)


def create_diff(archives_dir, when, current, previous):
    current_files = {}
    previous_files = {}
    diff_info = []

    with tarfile.open(current, "r:gz") as tar:
        for tarinfo in tar:
            current_files[tarinfo.name] = tarinfo
        with tarfile.open(previous, "r:gz") as tar:
            for tarinfo in tar:
                previous_files[tarinfo.name] = tarinfo

        for name, info in current_files.items():
            if name not in previous_files:
                diff_info.append("NEW:%s" % name)
            else:
                # XXX need to compare them
                pass
        for name, info in previous_files.items():
            if name not in current_files:
                diff_info.append("DELETED:%s" % name)

    day_before = when - timedelta(days=1)
    diff_archive = 'diff-%s-%s-hp.tar.gz' % (day_before.strftime('%Y-%m-%d'),
                                             when.strftime('%Y-%m-%d'))
    diff_archive = os.path.join(archives_dir, diff_archive)
    handle, diff_info_file = tempfile.mkstemp()
    os.close(handle)

    with open(diff_info_file, 'w') as f:
        for line in diff_info:
            f.write(line + '\n')

    with tarfile.open(diff_archive, "w:gz") as tar:
        tar.add(diff_info_file, arcname="diffinfo")


def update_archives(profile_dir, archives_dir, when=None):
    if when is None:
        when = date.today()
    day_before = when - timedelta(days=1)
    archive = when.strftime('%Y-%m-%d-hp.tar.gz')
    _log("Creating %s..." % archive)
    archive = os.path.join(archives_dir, archive)

    with tarfile.open(archive, "w:gz") as tar:
        for filename in glob.glob(os.path.join(profile_dir, "*")):
            _log("\tAdding %s..." % filename)
            tar.add(filename, os.path.basename(filename))

    _log("Done.")
    latest = os.path.join(archives_dir, 'latest.tar.gz')
    if os.path.exists(latest):
        os.remove(latest)
    os.symlink(archive, latest)
    previous = os.path.join(archives_dir,
                            day_before.strftime('%Y-%m-%d-hp.tar.gz'))
    if os.path.exists(previous):
        _log("Creating a diff tarball with the previous day")
        create_diff(archives_dir, when, archive, previous)


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Archiver')
    parser.add_argument('profile-dir', help='Profile Dir', type=str)
    parser.add_argument('archives-dir', help='Archives Dir', type=str)
    args = parser.parse_args(args=args)
    update_archives(args.profile_dir, args.archives_dir)


if __name__ == "__main__":
    main()
