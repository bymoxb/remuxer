import subprocess

from .command_runner import CommandRunner


class FFmpegRunner(CommandRunner):
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
