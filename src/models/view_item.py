# SPDX-License-Identifier: GPL-3.0-only

from gi.repository import GObject

class VideoItem(GObject.Object):
    name = GObject.Property(type=str)
    abs_path = GObject.Property(type=str)

    def __init__(self, name, path, abs_path, order):
        super().__init__()
        self.name = name
        self.path = path
        self.abs_path = abs_path
        self.order = order
