
import logging
from pathlib import Path
import threading
import time

from .command_runner import CommandRunner


class RemuxService:
    """Encargado de la lógica pesada de FFmpeg y procesos"""

    def __init__(self, runner: CommandRunner):
        self.runner = runner
        self.current_process = None
        self.cancel_event = threading.Event()
        self.logger = logging.getLogger("RemuxerApp.RemuxService")

    def cancel(self):
        self.cancel_event.set()
        if self.current_process:
            self.current_process.terminate()

    def prepare_output_path(self, video_path, audio_path, output_dir, naming_mode):
        dest_path = Path(output_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        file_ref = Path(
            video_path) if naming_mode == "source" else Path(audio_path)
        return str(dest_path / file_ref.name)

    def execute(self, video, audio, destination):
        try:
            new_file = Path(destination)
            self.logger.debug(f"Running process for: {new_file.name}")
            self.current_process = self.runner.start(
                video,
                audio,
                destination,
            )
            while self.current_process.poll() is None:
                if self.cancel_event.is_set():
                    self.logger.warning(
                        f"Process canelled on: {new_file.name}")
                    self.current_process.terminate()
                    return False
                time.sleep(1)
            return self.current_process.returncode == 0
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            return False
        finally:
            self.current_process = None
