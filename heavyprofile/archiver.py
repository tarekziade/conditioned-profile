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
import json

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


class Archiver(object):
    def __init__(self, profile_dir, archives_dir, pem_file=None,
                 pem_password=None):
        self.profile_dir = profile_dir
        self.archives_dir = archives_dir
        # reading metadata
        with open(os.path.join(profile_dir, '.hp.json')) as f:
            self.metadata = json.loads(f.read())
        self.profile_name = self.metadata['name']
        self.pem_file = pem_file
        self.pem_password = pem_password

    def _checksum(self, archive, sign=True):
        checksum(archive, sign=True, pem_file=self.pem_file,
                 pem_password=self.pem_password)

    def _strftime(self, date, template='-%Y-%m-%d-hp.tar.gz'):
        return date.strftime(self.profile_name + template)

    def _get_archive_path(self, when):
        archive = self._strftime(when)
        return os.path.join(self.archives_dir, archive)

    def _get_diff_path(self, date1, date2):
        date1 = date1.strftime('%Y-%m-%d')
        date2 = date2.strftime('%Y-%m-%d')
        arcname = self.profile_name + '-diff-%s-%s-hp.tar.gz' % (date1, date2)
        return os.path.join(self.archives_dir, arcname)

    def _create_archive(self, when, files=None):
        if files is None:
            files = glob.glob(os.path.join(self.profile_dir, "*"))
        archive = self._get_archive_path(when)
        with tarfile.open(archive, "w:gz") as tar:
            size = len(files)
            with progress.Bar(expected_size=size) as bar:
                for filename in files:
                    tar.add(filename, os.path.basename(filename))
                    bar.show(bar.last_progress + 1)
        self._checksum(archive)
        return archive

    def _update_symlinks(self, archive):
        for suffix in ('.tar.gz', '.tar.gz.sha256', '.tar.gz.asc'):
            path = os.path.join(self.archives_dir,
                                self.profile_name + '-latest' + suffix)
            if os.path.exists(path):
                os.remove(path)
            os.symlink(archive, path)

    def update(self, when=None):
        if when is None:
            when = date.today()
        archive = self._create_archive(when)
        logger.msg("Creating %s..." % archive)
        self._update_symlinks(archive)
        logger.msg("Done.")
        day_before = when - timedelta(days=1)
        previous = self._get_archive_path(day_before)
        if os.path.exists(previous):
            logger.msg("Creating a diff tarball with the previous day")
            self.create_diff(when, archive, previous)
            logger.msg("Done.")

    def create_diff(self, when, current, previous):
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
        diff_archive = self._get_diff_path(day_before, when)
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
        self._checksum(diff_archive)
        return diff_archive


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Archiver')
    parser.add_argument('profile_dir', help='Profile Dir', type=str)
    parser.add_argument('archives_dir', help='Archives Dir', type=str)
    parser.add_argument('--prior', help='Prior', type=int, default=0)
    parser.add_argument('--pem-file', help='pem file', type=str,
                        default='heavyprofile/tests/key.pem')
    parser.add_argument('--pem-password', help='pem password', type=str,
                        default='password')
    args = parser.parse_args(args=args)

    when = date.today()
    if args.prior > 0:
        when = when - timedelta(days=args.prior)

    if not os.path.exists(args.archives_dir):
        logger.msg("%r does not exists." % args.archives_dir)
        sys.exit(1)

    archiver = Archiver(args.profile_dir, args.archives_dir,
                        args.pem_file, args.pem_password)
    archiver.update(when)


if __name__ == "__main__":
    main()
