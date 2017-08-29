import os
from mozprofile.profile import Profile


_BASE_PROFILE = os.path.join(os.path.dirname(__here__), 'base_profile')


def clone_profile(target_dir):
    p = Profile.clone(_BASE_PROFILE, target_dir, restore=False)
    return p
