# SPDX-License-Identifier: GPL-3.0-only

import sys
import gi

from gettext import gettext as _

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from .window import RemuxerWindow


class RemuxerApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='dev.illapa.Remuxer',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/dev/illapa/Remuxer')

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
                                application_icon='dev.illapa.Remuxer',
                                # developer_name='Luis Fernando',
                                version='0.1.0',
                                # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
                                # translator_credits = _('translator-credits'),
                                # developers=['Luis Fernando'],
                                # copyright='© 2026 Luis Fernando'
                                )
        about.present(self.props.active_window)


    def _setup_actions(self):
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)



def main(version):
    """The application's entry point."""
    app = RemuxerApplication()
    return app.run(sys.argv)
