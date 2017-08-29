import os
import unittest
import shutil
from datetime import date

from heavyprofile.tests.support import fresh_profile
from heavyprofile.archiver import update_archives
import tempfile


class TestArchiver(unittest.TestCase):
    def setUp(self):
        self.profile, self.profile_dir = fresh_profile()
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
