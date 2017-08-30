import os
import unittest
import shutil
from datetime import date, timedelta

from heavyprofile.tests.support import fresh_profile
from heavyprofile.archiver import update_archives
import tempfile


class TestArchiver(unittest.TestCase):
    def setUp(self):
        self.profile_dir = fresh_profile()
        self.archives_dir = os.path.join(tempfile.mkdtemp())

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
                then = when - timedelta(days=1)
                then_str = then.strftime('%Y-%m-%d')
                when_str = when.strftime('%Y-%m-%d')
                name = 'diff-%s-%s-hp.tar.gz' % (then_str, when_str)
                wanted.append(name)

            update_archives(self.profile_dir, self.archives_dir, when)

        wanted.sort()
        res = os.listdir(self.archives_dir)
        res.sort()
        self.assertEqual(res, wanted)
