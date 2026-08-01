# SPDX-License-Identifier: GPL-3.0-only

from packaging import version
import logging

import requests


class UpdateService:
    def __init__(self, target_url: str, current_version: str, timeout: int = 2):
        self.logger = logging.getLogger("RemuxerApp.UpdateService")

        self.target_url = target_url
        self.current_version = current_version
        self.timeout = timeout

    """Encargado de verificar actualizaciones en GitHub"""

    def check_for_updates(self):
        try:
            response = requests.get(self.target_url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            tag = data.get("tag_name", "").lstrip("v")

            if tag and version.parse(tag) > version.parse(self.current_version):
                self.logger.info(f"New version available {tag}")
                return tag
        except Exception as e:
            self.logger.error(f"Update check failed: {e}")
        return None
