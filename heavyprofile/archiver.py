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
from heavyprofile.diffinfo import DiffInfo
from heavyprofile.signing import Signer
from heavyprofile.util import check_exists, download_file, TASK_CLUSTER

from clint.textui import progress


def _b(data):
    return bytes(data, "utf8")


def _tarinfo2mem(tar, tarinfo):
    metadata = copy.copy(tarinfo)
    try:
        data = tar.extractfile(tarinfo)
        if data is not None:
            data = data.read()
    except Exception:
        data = None

    return metadata, data


class Archiver(object):
    def __init__(self, profile_dir, archives_dir, pem_file=None,
                 pem_password=None, archives_server=None):
        self.archives_server = archives_server
        self.profile_dir = profile_dir
        self.archives_dir = archives_dir
        # reading metadata
        with open(os.path.join(profile_dir, '.hp.json')) as f:
            self.metadata = json.loads(f.read())
        self.profile_name = self.metadata['name']
        self.pem_file = pem_file
        self.pem_password = pem_password
        self.signer = Signer(pem_file, pem_password)

    def _checksum(self, archive, sign=True):
        return self.signer.checksum(archive, write=True, sign=True)

    def _strftime(self, date, template='-%Y-%m-%d-hp.tar.gz'):
        return date.strftime(self.profile_name + template)

    def _get_archive_path(self, when):
        archive = self._strftime(when)
        return os.path.join(self.archives_dir, archive), archive

    def _get_diff_path(self, date1, date2):
        date1 = date1.strftime('%Y-%m-%d')
        date2 = date2.strftime('%Y-%m-%d')
        arcname = self.profile_name + '-diff-%s-%s-hp.tar.gz' % (date1, date2)
        return os.path.join(self.archives_dir, arcname)

    def _create_archive(self, when, iterator=None):
        if iterator is None:
            def _files(tar):
                files = glob.glob(os.path.join(self.profile_dir, "*"))
                yield len(files)
                for filename in files:
                    try:
                        tar.add(filename, os.path.basename(filename))
                        yield filename
                    except FileNotFoundError:
                        # locks and such
                        pass
            iterator = _files

        if isinstance(when, str):
            archive = when
        else:
            archive, __ = self._get_archive_path(when)

        with tarfile.open(archive, "w:gz", dereference=True) as tar:
            it = iterator(tar)
            size = next(it)
            with progress.Bar(expected_size=size) as bar:
                for filename in it:
                    if not TASK_CLUSTER:
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
            logger.msg("%r symlinked at %r" % (archive, path))

    def _check_server(self, archive, target):
        if self.archives_server is None:
            return
        url = self.archives_server + '/' + archive
        exists, __ = check_exists(url)
        if exists:
            download_file(url, target, check_file=True)

    def update(self, when=None):
        if when is None:
            when = date.today()
        archive = self._create_archive(when)

        # for now in task cluster we just generate the latest profile
        if TASK_CLUSTER:
            return

        logger.msg("Creating symlinks for %s..." % archive)
        self._update_symlinks(archive)

        logger.msg("Done.")
        day_before = when - timedelta(days=1)
        previous, previous_fn = self._get_archive_path(day_before)
        if not os.path.exists(previous_fn):
            self._check_server(previous_fn, previous)

        if os.path.exists(previous):
            logger.msg("Creating a diff tarball with the previous day")
            self.create_diff(when, archive, previous)
            logger.msg("Done.")

    def _read_tar(self, filename):
        files = {}
        with tarfile.open(filename, "r:gz") as tar:
            for tarinfo in tar:
                files[tarinfo.name] = _tarinfo2mem(tar, tarinfo)
        return files

    def create_diff(self, when, current, previous):
        current_files = self._read_tar(current)
        previous_files = self._read_tar(previous)
        # build the diff info
        diff_info = DiffInfo()
        tarfiles = diff_info.update(current_files, previous_files)
        day_before = when - timedelta(days=1)
        diff_archive = self._get_diff_path(day_before, when)
        diff_data = diff_info.dump()

        def _arc(tar):
            yield len(tarfiles) + 1

            diff_info = tarfile.TarInfo(name="diffinfo")
            diff_info.size = len(diff_data)
            tar.addfile(diff_info, fileobj=io.BytesIO(diff_data))
            yield diff_info

            for info, data in tarfiles:
                if data is not None:
                    tar.addfile(info, fileobj=io.BytesIO(data))
                else:
                    tar.addfile(info)
                yield info

        self._create_archive(diff_archive, _arc)
        logger.msg(str(diff_info))
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
    parser.add_argument('--archives-server', help="Archives server",
                        type=str,
                        default='http://heavyprofile.dev.mozaws.net')
    args = parser.parse_args(args=args)
    args.pem_password = bytes(args.pem_password, 'utf8')

    if not os.path.exists(args.archives_dir):
        logger.msg("%r does not exists." % args.archives_dir)
        sys.exit(1)

    archiver = Archiver(args.profile_dir, args.archives_dir,
                        args.pem_file, args.pem_password,
                        args.archives_server)

    if TASK_CLUSTER:
        name = 'today-%s.tgz' % archiver.profile_name
        when = os.path.join(args.archives_dir, name)
    else:
        when = date.today()
        if args.prior > 0:
            when = when - timedelta(days=args.prior)

    archiver.update(when)


if __name__ == "__main__":
    main()
