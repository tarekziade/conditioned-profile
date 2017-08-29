import os
import tempfile
from mozprofile.profile import Profile


_BASE_PROFILE = os.path.join(os.path.dirname(__file__), 'base_profile')


def fresh_profile(target_dir=None):
    if target_dir is None:
        target_dir = os.path.join(tempfile.mkdtemp(), 'profile')
    p = Profile.clone(_BASE_PROFILE, target_dir, restore=False)
    return p, target_dir
