# SPDX-License-Identifier: GPL-3.0-only


import logging
import os
from pathlib import Path


class FileService:
    def __init__(self, allowed_extensions={".mp4", ".mkv"}):
        self.logger = logging.getLogger("RemuxerApp.FileService")
        self.allowed_extensions=allowed_extensions

    """Encargado de interactuar con el sistema de archivos"""

    def list_videos(self, path):
        videos = []
        try:
            files = sorted(os.listdir(path))
            for i, f in enumerate(files):
                if Path(f).suffix.lower() in self.allowed_extensions:
                    videos.append({
                        "name": f,
                        "path": path,
                        "abs_path": os.path.join(path, f),
                        "order": i
                    })
            self.logger.debug(f"{len(videos)} found in {path}")
        except Exception as e:
            self.logger.error(f"Error listando archivos: {e}")
        return videos
