# SPDX-License-Identifier: GPL-3.0-only

import json
from fractions import Fraction
from datetime import timedelta
import subprocess
import logging

from .command_runner import CommandRunner, StreamInfo


class FFmpegRunner(CommandRunner):

    def __init__(self):
        self.logger = logging.getLogger("RemuxerApp.FFmpegRunner")

    def start(self, video, audio, destination):
        cmd = [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-i", video,
            "-i", audio,
            "-map", "0",
            "-map", "1:a:0",
            "-map_metadata", "0",
            "-c", "copy",
            destination,
        ]

        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _parse_fps(self, value):
        if not value or value == "0/0":
            return 0

        try:
            return float(Fraction(value))
        except (ValueError, ZeroDivisionError):
            return 0

    def extract_tracks_info(self, path) -> list[StreamInfo]:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            self.logger.error(f"ffprobe failed: {result.stderr}")
            return []

        try:
            data = json.loads(result.stdout)

            streams = []
            for stream in data["streams"]:
                if stream["codec_type"] not in ["video", "audio"]:
                    continue

                duration = stream.get("tags", {}).get(
                    "DURATION", stream.get("duration", "0:0:0"))

                h, m, s = duration.split(":")

                total_seconds = timedelta(
                    hours=int(h),
                    minutes=int(m),
                    seconds=float(s)
                ).total_seconds()

                avg_frame_rate = stream.get("avg_frame_rate")

                streams.append(StreamInfo(
                    index=stream.get("index", 0),
                    codec_type=stream.get("codec_type", ""),
                    codec_name=stream.get("codec_name", ""),
                    avg_frame_rate=self._parse_fps(avg_frame_rate),
                    duration_in_seconds=total_seconds,
                    duration_text=duration,
                    title=stream.get("tags", {}).get("title", ""),
                    language=stream.get("tags", {}).get("language", ""),
                    is_default=stream.get("disposition", {}).get(
                        "default", 0) == 1,
                ))

            return streams
        except Exception as e:
            self.logger.error(f"Invalid JSON returned by ffprobe: {e}")
            return []
