import asyncio
import os
import unittest
import shutil
from datetime import date, timedelta
import tempfile
import tarfile
from collections import namedtuple

from condprof.util import fresh_profile
from condprof.archiver import Archiver
from condprof.creator import build_profile


class TestArchiver(unittest.TestCase):
    def setUp(self):
        self.profile_dir = fresh_profile()
        self.archives_dir = os.path.join(tempfile.mkdtemp())
        self.args = args = namedtuple(
            "args", ["scenarii", "profile", "firefox", "max_urls"]
        )
        args.scenarii = "heavy"
        args.profile = self.profile_dir
        args.firefox = None
        args.max_urls = 2
        args.profile_dir = self.profile_dir
        args.archives_server = None
        args.force_new = True
        args.archives_dir = self.archives_dir
        self.archiver = Archiver(args.profile_dir, args.archives_dir)

    def _diff_name(self, now=None, then=None):
        if now is None:
            now = date.today()
        if then is None:
            then = now - timedelta(days=1)
        then_str = then.strftime("%Y-%m-%d")
        now_str = now.strftime("%Y-%m-%d")
        return "heavy-diff-%s-%s-hp.tar.gz" % (then_str, now_str)

    def tearDown(self):
        shutil.rmtree(self.profile_dir)
        shutil.rmtree(self.archives_dir)

    def test_heavy_archiving(self):
        # this creates a heavy archive and updates the latest sl
        self.archiver.update()

        res = os.listdir(self.archives_dir)
        res.sort()
        today = date.today()
        archive = today.strftime("heavy-%Y-%m-%d-hp.tar.gz")
        wanted = [archive, "heavy-latest.tar.gz"]
        wanted.sort()
        self.assertEqual(res, wanted)

    def test_diff_archiving(self):
        # we update the archives every day for 15 days
        # we keep the last ten days
        wanted = ["heavy-latest.tar.gz"]

        _15_days_ago = date.today() - timedelta(days=15)

        for i in range(15):
            when = _15_days_ago + timedelta(days=i)
            wanted.append(when.strftime("heavy-%Y-%m-%d-hp.tar.gz"))

            if i != 0:
                wanted.append(self._diff_name(when))

            self.archiver.update(when)

        wanted.sort()
        res = os.listdir(self.archives_dir)
        res.sort()
        self.assertEqual(res, wanted)

    def test_archiving_after_changes(self):
        # this creates a heavy archive
        today = date.today()
        yesterday = today - timedelta(days=1)
        _2_days_ago = today - timedelta(days=2)

        self.archiver.update(_2_days_ago)
        # then we do some browsing
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(build_profile(self.args))
        finally:
            loop.close()

        # a new archive will create a diff
        self.archiver.update(yesterday)
        diffname = self._diff_name(yesterday, _2_days_ago)
        diffname = os.path.join(self.archives_dir, diffname)

        # let's check the diff file
        with tarfile.open(diffname, "r:gz") as tar:
            for tarinfo in tar:
                if tarinfo.name != "diffinfo":
                    continue
                diff = tar.extractfile(tarinfo)
                diff = diff.read()
                diff = [line for line in diff.split(b"\n") if line.strip() != b""]
                break

        # we have over 100 new files
        self.assertTrue(len(diff) > 100, diff)

        # let's do it again with today/yesterday
        self.archiver.update(today)
        diffname = self._diff_name(today, yesterday)
        diffname = os.path.join(self.archives_dir, diffname)

        # let's check the diff file
        with tarfile.open(diffname, "r:gz") as tar:
            for tarinfo in tar:
                if tarinfo.name != "diffinfo":
                    continue
                diff = tar.extractfile(tarinfo)
                diff = diff.read()
                diff = diff.split(b"\n")
                diff = [line for line in diff if line.strip() != b""]
                break

        # we have no difference
        self.assertTrue(len(diff) == 0)
