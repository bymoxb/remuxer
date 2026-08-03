# SPDX-License-Identifier: GPL-3.0-only

from enum import Enum
from gi.repository import GObject

from .view_item import VideoItem


class StatusViewRow(Enum):
    PENDING = "pending"
    WARNING = "warning"
    SUCCESS = "success"
    ERROR = "error"
    COMPLETED = "completed"
    PROCESSING = "processing"

class ColumnViewRow(GObject.Object):
    video = GObject.Property(type=VideoItem)
    audio = GObject.Property(type=VideoItem)
    status = GObject.Property(type=str, default=StatusViewRow.PENDING.value)
    selected = GObject.Property(type=bool, default=True)

    def __init__(self, video, audio):
        super().__init__()
        self.video = video
        self.audio = audio

        self.status = StatusViewRow.WARNING.value if (
            audio and audio.has_multiple_audio_streams()) else StatusViewRow.PENDING.value

    def __str__(self):
        return f"ColumnViewRow{{ source_video_name: {self.video.name}; source_audio_name: {self.audio.name}; status: {self.status}; selected: {self.selected} }}"
