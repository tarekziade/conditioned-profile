import asyncio
import os
import unittest
import shutil
from datetime import date, timedelta
import tempfile
import tarfile
import io

from heavyprofile.tests.support import fresh_profile
from heavyprofile.archiver import update_archives
from heavyprofile.creator import build_profile


class TestArchiver(unittest.TestCase):
    def setUp(self):
        self.profile_dir = fresh_profile()
        self.archives_dir = os.path.join(tempfile.mkdtemp())

    def _diff_name(self, now=None, then=None):
        if now is None:
            now = date.today()
        if then is None:
            then = now - timedelta(days=1)
        then_str = then.strftime('%Y-%m-%d')
        now_str = now.strftime('%Y-%m-%d')
        return 'diff-%s-%s-hp.tar.gz' % (then_str, now_str)

    def tearDown(self):
        shutil.rmtree(self.profile_dir)
        shutil.rmtree(self.archives_dir)

    def test_simple_archiving(self):
        # this creates a simple archive and updates the latest sl
        update_archives(self.profile_dir, self.archives_dir)

        res = os.listdir(self.archives_dir)
        res.sort()
        today = date.today()
        archive = today.strftime('%Y-%m-%d-hp.tar.gz')
        wanted = [archive, 'latest.tar.gz']
        self.assertEqual(res, wanted)

    def test_diff_archiving(self):
        # we update the archives every day for 15 days
        # we keep the last ten days
        wanted = ['latest.tar.gz']
        _15_days_ago = date.today() - timedelta(days=15)

        for i in range(15):
            when = _15_days_ago + timedelta(days=i)
            wanted.append(when.strftime('%Y-%m-%d-hp.tar.gz'))
            if i != 0:
                wanted.append(self._diff_name(when))
            update_archives(self.profile_dir, self.archives_dir, when)

        wanted.sort()
        res = os.listdir(self.archives_dir)
        res.sort()
        self.assertEqual(res, wanted)

    def test_archiving_after_changes(self):
        # this creates a simple archive
        when = date.today() - timedelta(days=1)
        update_archives(self.profile_dir, self.archives_dir, when)

        # then we do some browsing
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(build_profile(self.profile_dir))
        finally:
            loop.close()

        # a new archive will create a diff
        update_archives(self.profile_dir, self.archives_dir)
        diffname = os.path.join(self.archives_dir, self._diff_name())
        diffinfo = io.BytesIO()

        with tarfile.open(diffname, "r:gz") as tar:
            for tarinfo in tar:
                if tarinfo.name != 'diffinfo':
                    continue
                diffinfo.write(tarinfo.tobuf())
                diffinfo.seek(0)

        #import pdb; pdb.set_trace()

