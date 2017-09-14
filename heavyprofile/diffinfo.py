def _b(data):
    return bytes(data, "utf8")


class DiffInfo(object):
    def __init__(self):
        self._info = []
        self.changed = 0
        self.new = 0
        self.deleted = 0

    def __repr__(self):
        msg = "=> %d new files, %d modified, %d deleted."
        return msg % (self.new, self.changed, self.deleted)

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
        self.changed += 1
        self._info.append(b"CHANGED:%s" % name)

    def add_new(self, name):
        self.new += 1
        self._info.append(b"NEW:%s" % name)

    def add_deleted(self, name):
        self.deleted += 1
        self._info.append(b"DELETED:%s" % name)

    def update(self, current_files, previous_files):
        files = []
        for name, info in current_files.items():
            if name not in previous_files:
                self.add_new(_b(name))
                files.append(info)
            else:
                old = previous_files[name][0].get_info()['chksum']
                new = info[0].get_info()['chksum']
                if old != new:
                    self.add_changed(_b(name))
                    files.append(info)

        for name, info in previous_files.items():
            if name not in current_files:
                self.add_deleted(_b(name))

        return files
