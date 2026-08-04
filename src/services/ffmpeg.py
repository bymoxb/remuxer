# SPDX-License-Identifier: GPL-3.0-only

import json
from fractions import Fraction
from datetime import timedelta
import subprocess
import logging
import fnmatch
from decimal import Decimal

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

    def _get_value_by_pattern(self, data: dict, pattern: str, default=None):
        pattern = pattern.lower()

        for key, value in data.items():
            if fnmatch.fnmatch(key.lower(), pattern):
                return value

        return default

    def _format_duration(self, duration: str) -> str:
        hms, fraction = duration.split(".")
        seconds = Decimal(f"0.{fraction}")
        return f"{hms}{seconds:.2f}"[0:8] + f"{seconds:.2f}"[1:]

    def _parse_fps(self, value):
        if not value or value == "0/0":
            return 0

        try:
            return float(Fraction(value))
        except (ValueError, ZeroDivisionError):
            return 0

    def _parse_duration_in_seconds(self, stream):
        duration = self._get_value_by_pattern(
            (stream.get("tags", {})), "DURATION*")

        if not duration:
            duration = stream.get("duration", "0")

        if not duration:
            return 0.0

        try:
            if ":" in duration:
                parts = duration.split(":")
                if len(parts) != 3:
                    self.logger.error(f"Invalid duration format: {duration}")
                    return 0.0

                h, m, s = parts

                return timedelta(
                    hours=int(h),
                    minutes=int(m),
                    seconds=float(s)
                ).total_seconds()

            return float(duration)

        except (ValueError, TypeError) as e:
            self.logger.error(f"Invalid duration value '{duration}': {e}")
            return 0.0

    def _parse_duration_str(self, stream):
        duration = self._get_value_by_pattern(
            (stream.get("tags", {})), "DURATION*")

        if duration and ":" in duration:
            return self._format_duration(duration)

        try:
            total_seconds = float(stream.get("duration", 0))
            return self._format_duration(str(timedelta(seconds=total_seconds)))

        except (ValueError, TypeError) as e:
            self.logger.error(f"Invalid duration value in stream: {e}")
            return "0:00:00"


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
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON returned by ffprobe: {e}")
            return []

        streams = []
        for stream in data.get("streams", []):
            try:
                if stream["codec_type"] not in ["video", "audio"]:
                    # skipping subtitle and other streams
                    continue

                if stream.get("disposition", {}).get("attached_pic", 0) == 1:
                    # skipping attached pictures
                    continue

                duration_str = self._parse_duration_str(stream)
                total_seconds = self._parse_duration_in_seconds(stream)

                avg_frame_rate = stream.get("avg_frame_rate")

                streams.append(StreamInfo(
                    index=stream.get("index", 0),
                    codec_type=stream.get("codec_type", ""),
                    codec_name=stream.get("codec_name", ""),
                    avg_frame_rate=self._parse_fps(avg_frame_rate),
                    duration_in_seconds=total_seconds,
                    duration_text=duration_str,
                    title=stream.get("tags", {}).get("title", ""),
                    language=stream.get("tags", {}).get("language", ""),
                    is_default=stream.get("disposition", {}).get(
                        "default", 0) == 1,
                ))
            except Exception as e:
                self.logger.error(f"Error parsing stream info: {e}")
                self.logger.error(f"Failed Stream data: {stream}")
                continue

        return streams
