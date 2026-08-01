from curses import version
import logging

import requests

APP_GITHUB_RELEASES = "https://api.github.com/repos/bymoxb/remuxer/releases/latest"

class UpdateService:
    def __init__(self):
        self.logger = logging.getLogger("RemuxerApp.UpdateService")

    """Encargado de verificar actualizaciones en GitHub"""

    def check_for_updates(self, current_version):
        try:
            response = requests.get(APP_GITHUB_RELEASES, timeout=2)
            response.raise_for_status()
            data = response.json()
            tag = data.get("tag_name", "").lstrip("v")

            if tag and version.parse(tag) > version.parse(current_version):
                self.logger.info(f"New version available {tag}")
                return tag
        except Exception as e:
            self.logger.error(f"Update check failed: {e}")
        return None
