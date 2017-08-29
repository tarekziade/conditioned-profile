import unittest
import shutil
from heavyprofile.tests.support import fresh_profile


class TestArchiver(unittest.TestCase):
    def setUp(self):
        self.profile, self.profile_dir = fresh_profile()

    def tearDown(self):
        shutil.rmtree(self.profile_dir)

    def test_simple_archiving(self):
        pass
