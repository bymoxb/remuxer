# SPDX-License-Identifier: GPL-3.0-only

from gi.repository import GObject

from .view_item import VideoItem

class ColumnViewRow(GObject.Object):
    video = GObject.Property(type=VideoItem)
    audio = GObject.Property(type=VideoItem)
    status = GObject.Property(type=str, default="pending")
    selected = GObject.Property(type=bool, default=True)

    def __init__(self, video, audio):
        super().__init__()
        self.video = video
        self.audio = audio

        self.status = "warning" if (
            audio and audio.has_multiple_audio_streams()) else "pending"
