# SPDX-License-Identifier: GPL-3.0-only

from abc import ABC, abstractmethod
import subprocess


class CommandRunner(ABC):

    @abstractmethod
    def start(
        self,
        video: str,
        audio: str,
        destination: str
    ) -> subprocess.Popen:
        ...
