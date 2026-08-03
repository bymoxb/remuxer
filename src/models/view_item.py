# SPDX-License-Identifier: GPL-3.0-only

from gi.repository import GObject


class StreamItem(GObject.Object):
    index = GObject.Property(type=int)
    codec_type = GObject.Property(type=str)
    codec_name = GObject.Property(type=str)
    avg_frame_rate = GObject.Property(type=str)
    duration_in_seconds = GObject.Property(type=float)
    duration_text = GObject.Property(type=str)

    def __init__(self, index, codec_type, codec_name, avg_frame_rate, duration_in_seconds, duration_text):
        super().__init__()
        self.index = index
        self.codec_type = codec_type
        self.codec_name = codec_name
        self.avg_frame_rate = avg_frame_rate
        self.duration_in_seconds = duration_in_seconds
        self.duration_text = duration_text

class VideoItem(GObject.Object):
    name = GObject.Property(type=str)
    abs_path = GObject.Property(type=str)
    streams = GObject.Property(type=object)

    def __init__(self, name, path, abs_path, order):
        super().__init__()
        self.name = name
        self.path = path
        self.abs_path = abs_path
        self.order = order

    def set_streams(self, streams: list[StreamItem]):
        self.streams = streams

    def has_multiple_audio_streams(self):
        if not self.streams:
            return False
        audio_streams = [s for s in self.streams if s.codec_type == "audio"]
        return len(audio_streams) > 1
