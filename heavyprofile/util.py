import os
import tempfile
import shutil


_BASE_PROFILE = os.path.join(os.path.dirname(__file__), 'base_profile')


def fresh_profile(target_dir=None):
    if target_dir is None:
        target_dir = os.path.join(tempfile.mkdtemp(), 'profile')
    shutil.copytree(_BASE_PROFILE, target_dir)
    return target_dir


class DiffInfo(object):
    def __init__(self):
        self._info = []

    def __iter__(self):
        for change in self._info:
            yield change.split(b':')

    def __len__(self):
        return len(self._info)

    def load(self, data):
        self._info[:] = []
        for line in data.split(b'\n'):
            line = line.strip()
            if line == b'':
                continue
            self._info.append(line)

    def dump(self):
        return b'\n'.join(self._info)

    def add_changed(self, name):
        self._info.append(b"CHANGED:%s" % name)

    def add_new(self, name):
        self._info.append(b"NEW:%s" % name)

    def add_deleted(self, name):
        self._info.append(b"DELETED:%s" % name)
