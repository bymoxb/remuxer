# SPDX-License-Identifier: GPL-3.0-only

import sys
import logging
from gettext import gettext as _


from gi.repository import Gio, Adw
from .window import RemuxerWindow

from remuxer import const


class RemuxerApplication(Adw.Application):
    """The main application singleton class."""

    development_mode = const.IS_DEVEL
    application_id = const.APP_ID
    version = const.VERSION
    settings = Gio.Settings.new(application_id)

    def __init__(self):
        super().__init__(application_id=self.application_id,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/dev/illapa/Remuxer')

        loglevel = logging.DEBUG if self.development_mode else logging.INFO

        logging.basicConfig(
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt="%d-%m-%y %H:%M:%S",
            level=loglevel,
        )

        logger = logging.getLogger("RemuxerApp")

        self._setup_actions()

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = RemuxerWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(application_name='Remuxer',
                                application_icon=self.application_id,
                                version=self.version)
        about.present(self.props.active_window)

    def _setup_actions(self):
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)


def main(version):
    """The application's entry point."""
    app = RemuxerApplication()
    return app.run(sys.argv)
