# SPDX-License-Identifier: GPL-3.0-only

from abc import ABC, abstractmethod
import subprocess


class StreamInfo:
    def __init__(self, index, codec_type, codec_name, avg_frame_rate, duration_in_seconds, duration_text):
        self.index = index
        self.codec_type = codec_type
        self.codec_name = codec_name
        self.avg_frame_rate = avg_frame_rate
        self.duration_in_seconds = duration_in_seconds
        self.duration_text = duration_text

    def to_dict(self):
        return {
            "index": self.index,
            "codec_type": self.codec_type,
            "codec_name": self.codec_name,
            "avg_frame_rate": self.avg_frame_rate,
            "duration_in_seconds": self.duration_in_seconds,
            "duration_text": self.duration_text
        }


class CommandRunner(ABC):

    @abstractmethod
    def start(
        self,
        video: str,
        audio: str,
        destination: str
    ) -> subprocess.Popen:
        ...

    @abstractmethod
    def extract_tracks_info(self, path: str) -> list[StreamInfo]:
        ...
