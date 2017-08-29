import os
import unittest
import shutil

from heavyprofile.tests.support import fresh_profile
from heavyprofile.archiver import create_archives
import tempfile


class TestArchiver(unittest.TestCase):
    def setUp(self):
        self.profile, self.profile_dir = fresh_profile()
        self.archives_dir = os.path.join(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.profile_dir)
        shutil.rmtree(self.archives_dir)

    def test_simple_archiving(self):
        create_archives(self.profile_dir, self.archives_dir)
        self.assertTrue(len(os.listdir(self.archives_dir)), 3)
