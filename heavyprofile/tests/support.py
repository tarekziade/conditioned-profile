import os
import tempfile
import shutil


_BASE_PROFILE = os.path.join(os.path.dirname(__file__), 'base_profile')


def fresh_profile(target_dir=None):
    if target_dir is None:
        target_dir = os.path.join(tempfile.mkdtemp(), 'profile')
    shutil.copytree(_BASE_PROFILE, target_dir)
    return target_dir
