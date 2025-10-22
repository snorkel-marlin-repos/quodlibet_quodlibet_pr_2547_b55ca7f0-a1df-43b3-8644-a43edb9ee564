# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from senf import fsnative, path2fsn

from quodlibet.compat import text_type, PY3

from ._audio import AudioFile


extensions = []


class RemoteFile(AudioFile):
    is_file = False
    fill_metadata = True

    format = "Remote File"

    def __init__(self, uri):
        if PY3:
            assert not isinstance(uri, bytes)
        self["~uri"] = text_type(uri)
        self.sanitize(fsnative(self["~uri"]))

    def __getitem__(self, key):
        # we used to save them with the wrong type
        value = super(RemoteFile, self).__getitem__(key)
        if key in ("~filename", "~mountpoint") and \
                not isinstance(value, fsnative):
            value = path2fsn(value)

        return value

    def rename(self, newname):
        pass

    def reload(self):
        pass

    def exists(self):
        return True

    def valid(self):
        return True

    def mounted(self):
        return True

    def write(self):
        pass

    def can_change(self, k=None):
        if k is None:
            return []
        else:
            return False

    @property
    def key(self):
        return self["~uri"]

loader = RemoteFile
types = [RemoteFile]
