# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import re

from gi.repository import Gtk, GObject

from quodlibet import _
from quodlibet.plugins.editing import RenameFilesPlugin, TagsFromPathPlugin
from quodlibet.util import connect_obj, gdecode
from quodlibet.qltk import Icons


class RegExpSub(Gtk.HBox, RenameFilesPlugin, TagsFromPathPlugin):
    PLUGIN_ID = "Regex Substitution"
    PLUGIN_NAME = _("Regex Substitution")
    PLUGIN_DESC = _("Allows arbitrary regex substitutions (s///) when "
                    "tagging or renaming files.")
    PLUGIN_ICON = Icons.EDIT_FIND_REPLACE

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ())
        }
    active = True

    def __init__(self):
        super(RegExpSub, self).__init__()
        self._from = Gtk.Entry()
        self._to = Gtk.Entry()
        self.pack_start(Gtk.Label("s/"), True, True, 0)
        self.pack_start(self._from, True, True, 0)
        self.pack_start(Gtk.Label("/"), True, True, 0)
        self.pack_start(self._to, True, True, 0)
        self.pack_start(Gtk.Label("/"), True, True, 0)

        connect_obj(self._from, 'changed', self.emit, 'changed')
        connect_obj(self._to, 'changed', self.emit, 'changed')

    def filter(self, orig_or_tag, value):
        fr = gdecode(self._from.get_text())
        to = gdecode(self._to.get_text())
        try:
            return re.sub(fr, to, value)
        except:
            return value
