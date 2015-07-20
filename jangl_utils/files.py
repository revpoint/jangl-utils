import json
import os
from django.core.files.storage import default_storage
from django.utils.encoding import force_str, smart_text


def handle_uploaded_file(upload_to, uploaded_file, storage=None):
    if storage is None:
        storage = default_storage
    file_name = os.path.join(upload_to, uploaded_file.name)
    return storage.save(file_name, uploaded_file)


class FieldFile(object):

    def __init__(self, name, storage=None):
        self.name = name
        self.storage = storage or default_storage

    def __str__(self):
        return smart_text(self.name or '')

    def __repr__(self):
        return force_str("<%s: %s>" % (self.__class__.__name__, self or "None"))

    def __bool__(self):
        return bool(self.name)

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def __len__(self):
        return self.size

    def __eq__(self, other):
        # Older code may be expecting FileField values to be simple strings.
        # By overriding the == operator, it can remain backwards compatibility.
        if hasattr(other, 'name'):
            return self.name == other.name
        return self.name == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name)

    def _require_file(self):
        if not self:
            raise ValueError("This field has no file associated with it." )

    def _get_file(self):
        self._require_file()
        if not hasattr(self, '_file') or self._file is None:
            self._file = self.storage.open(self.name, 'rb')
        return self._file
    file = property(_get_file)

    def _get_path(self):
        self._require_file()
        return self.storage.path(self.name)
    path = property(_get_path)

    def _get_url(self):
        self._require_file()
        return self.storage.url(self.name)
    url = property(_get_url)

    def _get_size(self):
        self._require_file()
        return self.storage.size(self.name)
    size = property(_get_size)

    def open(self, mode='rb'):
        self._require_file()
        self.file.open(mode)
