# SPDX-License-Identifier: GPL-3.0-only

from decimal import Decimal, ROUND_HALF_UP


from gi.repository import GObject


class StreamItem(GObject.Object):
    index = GObject.Property(type=int)
    codec_type = GObject.Property(type=str)
    codec_name = GObject.Property(type=str)
    avg_frame_rate = GObject.Property(type=str)
    duration_in_seconds = GObject.Property(type=float)
    duration_text = GObject.Property(type=str)
    is_default = GObject.Property(type=bool, default=False)
    title = GObject.Property(type=str)
    language = GObject.Property(type=str)

    def __init__(self, index, codec_type, codec_name, avg_frame_rate, duration_in_seconds, duration_text, language, title, is_default=False):
        super().__init__()
        self.index = index
        self.codec_type = codec_type
        self.codec_name = codec_name
        self.avg_frame_rate = avg_frame_rate
        self.duration_in_seconds = duration_in_seconds
        self.duration_text = duration_text
        self.is_default = is_default
        self.language = language
        self.title = title

    def get_display_name(self):
        return f"index: {self.index}, lang: {self.language}, is_default: {self.is_default}, title: {self.title}"

    def get_display_time(self):
        return f"{Formatter.format_time(self.duration_text)} | {Formatter.format_time(self.duration_in_seconds)} s"

    def get_display_frame_rate(self):
        return f"{Formatter.format_time(self.avg_frame_rate)}"

    def is_audio(self):
        return self.codec_type == "audio"

    def is_video(self):
        return self.codec_type == "video"

    def __str__(self):
        return f"StreamItem{{ index: {self.index}; lang: {self.language}; is_default: {self.is_default}; title: {self.title}; duration_text={self.duration_text}; duration_in_seconds={self.duration_in_seconds} }}"

class VideoItem(GObject.Object):
    name = GObject.Property(type=str)
    abs_path = GObject.Property(type=str)
    streams = GObject.Property(type=object)
    audio_stream_index_selected = GObject.Property(type=int, default=1)

    def __init__(self, name, path, abs_path, order):
        super().__init__()
        self.name = name
        self.path = path
        self.abs_path = abs_path
        self.order = order

    def set_streams(self, streams: list[StreamItem]):
        self.streams = streams

        audio_streams = [s for s in streams if s.is_audio()]

        self.audio_stream_index_selected = next(
            (s.index for s in audio_streams if s.is_default),
            audio_streams[0].index if len(audio_streams) > 0 else 1,
        )

    def has_multiple_audio_streams(self):
        if not self.streams:
            return False
        return len([s for s in self.streams if s.is_audio()]) > 1

    def get_video_stream(self):
        return next((s for s in self.streams if s.is_video()), None)

    def get_audio_streams(self):
        return [s for s in self.streams if s.is_audio()]

    def __str__(self):
        return f"VideoItem{{ name: {self.name}; audio_index_selected: {self.audio_stream_index_selected} }}"


class Formatter:

    @staticmethod
    def format_number(number) -> str:
        """
        Formatea un número a 2 decimales.
        """
        value = Decimal(str(number))
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def format_duration(duration: str) -> str:
        """
        Formatea una duración HH:MM:SS.xxxxx a HH:MM:SS.xx
        """
        hms, fraction = duration.split(".")
        decimals = Formatter.format_number(f"0.{fraction}").split(".")[1]

        return f"{hms}.{decimals}"

    @staticmethod
    def format_time(value) -> str:
        """
        Detecta automáticamente si es una duración o un número.
        """
        value = str(value)

        if ":" in value:
            return Formatter.format_duration(value)

        return Formatter.format_number(value)
