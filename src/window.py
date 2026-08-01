# SPDX-License-Identifier: GPL-3.0-only

import logging
import threading

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import Pango
from gi.repository import GLib
from gi.repository import GObject

from .models.column_view_row import ColumnViewRow
from .models.view_item import VideoItem
from .services.ffmpeg import FFmpegRunner
from .services.file_service import FileService
from .services.remux_service import RemuxService
from .services.update_service import UpdateService

APP_VERSION = "0.1.0-dev"

@Gtk.Template(resource_path='/dev/illapa/Remuxer/window.ui')
class RemuxerWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'RemuxerWindow'

    # Widgets de la plantilla
    cv_files = Gtk.Template.Child()
    btn_seleccionar_videos_principales = Gtk.Template.Child()
    btn_seleccionar_videos_audio = Gtk.Template.Child()
    row_video_folder = Gtk.Template.Child()
    row_audio_folder = Gtk.Template.Child()
    row_output_folder = Gtk.Template.Child()
    btn_seleccionar_salida = Gtk.Template.Child()
    action_stack = Gtk.Template.Child()
    btn_analizar = Gtk.Template.Child()
    btn_procesar = Gtk.Template.Child()
    btn_cancelar = Gtk.Template.Child()
    btn_video_subir = Gtk.Template.Child()
    btn_video_bajar = Gtk.Template.Child()
    btn_audio_subir = Gtk.Template.Child()
    btn_audio_bajar = Gtk.Template.Child()
    pro_bar = Gtk.Template.Child()
    entry_videos_principales = Gtk.Template.Child()
    entry_videos_audio = Gtk.Template.Child()
    entry_directorio_salida = Gtk.Template.Child()
    radio_keep_source_name = Gtk.Template.Child()
    btn_menu = Gtk.Template.Child()
    updates_banner = Gtk.Template.Child()
    dialog_confirmar_cancelacion = Gtk.Template.Child()

    # Factories
    cv_selection_factory = Gtk.Template.Child()
    cv_video_factory = Gtk.Template.Child()
    cv_audio_factory = Gtk.Template.Child()
    cv_status_factory = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.logger = logging.getLogger("RemuxerApp.MainWindow")

        # Inicializar Servicios
        self.remux_service = RemuxService(FFmpegRunner())
        self.update_service = UpdateService()
        self.file_service = FileService()
        self.video_data_cache = {"videos": [], "audios": []}

        # Estado de la UI
        self.store = Gio.ListStore(item_type=GObject.Object)
        self.selection_model = Gtk.SingleSelection(model=self.store)

        self.setup_ui()
        self.connect_signals()
        self.setup_cv_actions()

        # Tarea de red en segundo plano
        threading.Thread(target=self._check_updates_async, daemon=True).start()

    def setup_ui(self):
        self.cv_files.set_model(self.selection_model)
        self._setup_selection_factory()
        self._setup_label_factory(
            self.cv_video_factory, self._on_bind_video_column)
        self._setup_label_factory(
            self.cv_audio_factory, self._on_bind_audio_column)
        self._setup_status_factory()

    def _setup_selection_factory(self):
        self.cv_selection_factory.connect(
            "setup", self._on_setup_selection_column)
        self.cv_selection_factory.connect(
            "bind", self._on_bind_selection_column)
        self.cv_selection_factory.connect(
            "unbind", self._on_unbind_selection_column)

    def setup_cv_actions(self):
        action_select_all = Gio.SimpleAction.new("select_all", None)
        action_select_all.connect("activate", self._on_select_all_activated)
        self.add_action(action_select_all)

        action_unselect_all = Gio.SimpleAction.new("unselect_all", None)
        action_unselect_all.connect(
            "activate", self._on_unselect_all_activated)
        self.add_action(action_unselect_all)

    def _setup_status_factory(self):
        self.cv_status_factory.connect("setup", self._on_setup_status_column)
        self.cv_status_factory.connect("bind", self._on_bind_status_column)
        self.cv_status_factory.connect("unbind", self._on_unbind_status_column)

    def _setup_label_factory(self, factory, bind_callback):
        factory.connect("setup", self._on_factory_setup_label)
        factory.connect("bind", bind_callback)

    def _on_setup_status_column(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        stack.set_transition_duration(250)

        icon = Gtk.Image()
        spinner = Gtk.Spinner()

        stack.add_named(icon, "icon")
        stack.add_named(spinner, "spinner")

        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)

        box.append(stack)
        box.append(label)

        list_item.set_child(box)

    def _on_bind_status_column(self, factory, list_item):
        row = list_item.get_item()
        box = list_item.get_child()
        stack = box.get_first_child()
        icon = stack.get_child_by_name("icon")
        spinner = stack.get_child_by_name("spinner")
        label = stack.get_next_sibling()

        def update_ui(*args):
            status = row.status

            for cls in ["success", "error", "accent"]:
                icon.remove_css_class(cls)

            label.remove_css_class("dim-label")

            if status == "processing":
                stack.set_visible_child_name("spinner")
                spinner.start()
                label.set_text(_("Processing..."))
            else:
                spinner.stop()
                stack.set_visible_child_name("icon")

                if status == "completed":
                    icon.set_from_icon_name("object-select-symbolic")
                    icon.add_css_class("success")
                    label.set_text(_("Done"))
                elif status == "error":
                    icon.set_from_icon_name("dialog-error-symbolic")
                    icon.add_css_class("error")
                    label.set_text(_("Error"))

        list_item.handler_id = row.connect("notify::status", update_ui)

        update_ui()

    def _on_unbind_status_column(self, factory, list_item):
        row = list_item.get_item()
        handler_id = list_item.get_data("handler-id")
        if row and handler_id:
            row.disconnect(handler_id)
            list_item.handler_id = None

    def _on_setup_selection_column(self, factory, list_item):
        check = Gtk.CheckButton()
        check.set_halign(Gtk.Align.CENTER)
        check.set_valign(Gtk.Align.CENTER)
        list_item.set_child(check)

    def _on_bind_selection_column(self, factory, list_item):
        row = list_item.get_item()
        check = list_item.get_child()

        # Creamos un binding bidireccional entre la propiedad 'selected' del objeto
        # y la propiedad 'active' del CheckButton
        # GObject.BindingFlags.BIDIRECTIONAL: si uno cambia, el otro también
        # GObject.BindingFlags.SYNC_CREATE: sincroniza el valor inmediatamente al crear el vínculo
        bind = row.bind_property(
            "selected",
            check,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE
        )

        # Guardamos la referencia del binding para poder desvincularlo luego
        list_item.selection_binding = bind

    def _on_unbind_selection_column(self, factory, list_item):
        # Limpiar el binding al reciclar el widget
        # bind = getattr(list_item, "selection_binding", None)
        bind = list_item.get_data("selection-binding")
        if bind:
            bind.unbind()

        list_item.set_data("selection-binding", None)

    def _on_select_all_activated(self, action, parameter):
        for i in range(self.store.get_n_items()):
            self.store.get_item(i).selected = True

    def _on_unselect_all_activated(self, action, parameter):
        for i in range(self.store.get_n_items()):
            self.store.get_item(i).selected = False

    # --- Handlers de UI ---

    def _on_factory_setup_label(self, factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        list_item.set_child(label)

    def _on_bind_video_column(self, factory, list_item):
        row = list_item.get_item()
        if row and row.video:
            row.video.bind_property("name", list_item.get_child(
            ), "label", GObject.BindingFlags.SYNC_CREATE)

    def _on_bind_audio_column(self, factory, list_item):
        row = list_item.get_item()
        if row and row.audio:
            row.audio.bind_property("name", list_item.get_child(
            ), "label", GObject.BindingFlags.SYNC_CREATE)

    def connect_signals(self):
        self.btn_seleccionar_videos_principales.connect(
            "clicked", self.on_select_folder_clicked, "videos")
        self.btn_seleccionar_videos_audio.connect(
            "clicked", self.on_select_folder_clicked, "audios")
        self.btn_seleccionar_salida.connect(
            "clicked", self.on_select_folder_clicked, "output")
        self.btn_analizar.connect("clicked", self.on_analyze_clicked)
        self.btn_procesar.connect("clicked", self.on_process_clicked)
        self.btn_cancelar.connect("clicked", self.on_cancel_clicked)
        self.updates_banner.connect(
            "button-clicked", self._on_close_updates_banner)

        # Movimientos
        self.btn_video_subir.connect(
            "clicked", lambda _: self.handle_reorder("VIDEO", "UP"))
        self.btn_video_bajar.connect(
            "clicked", lambda _: self.handle_reorder("VIDEO", "DOWN"))
        self.btn_audio_subir.connect(
            "clicked", lambda _: self.handle_reorder("AUDIO", "UP"))
        self.btn_audio_bajar.connect(
            "clicked", lambda _: self.handle_reorder("AUDIO", "DOWN"))

    # --- Lógica de Interfaz ---

    def _check_updates_async(self):
        new_version = self.update_service.check_for_updates(APP_VERSION)
        if new_version:
            GLib.idle_add(self._show_update_banner, new_version)

    def _on_close_updates_banner(self, btn):
        self.updates_banner.set_revealed(False)

    def _show_update_banner(self, ver):
        self.updates_banner.set_title(
            self.updates_banner.get_title().format(ver))
        self.updates_banner.set_revealed(True)

    def on_select_folder_clicked(self, btn, target):
        dialog = Gtk.FileDialog(title=_("Select Folder"))
        dialog.select_folder(self, None, self._on_folder_selected, target)

    def _on_folder_selected(self, dialog, result, target):
        try:
            folder = dialog.select_folder_finish(result)
            if not folder:
                return
            path = folder.get_path()

            if target == "videos":
                self.entry_videos_principales.set_text(path)
                self.row_video_folder.set_tooltip_text(path)
                self.video_data_cache["videos"] = self.file_service.list_videos(
                    path)
            elif target == "audios":
                self.entry_videos_audio.set_text(path)
                self.row_audio_folder.set_tooltip_text(path)
                self.video_data_cache["audios"] = self.file_service.list_videos(
                    path)
            else:
                self.entry_directorio_salida.set_text(path)
                self.row_output_folder.set_tooltip_text(path)
        except Exception:
            pass

    def on_analyze_clicked(self, btn):
        self.store.remove_all()
        v_list = self.video_data_cache["videos"]
        a_list = self.video_data_cache["audios"]

        for i in range(max(len(v_list), len(a_list))):
            v_obj = VideoItem(**v_list[i]) if i < len(v_list) else None
            a_obj = VideoItem(**a_list[i]) if i < len(a_list) else None
            self.store.append(ColumnViewRow(video=v_obj, audio=a_obj))

        self.btn_procesar.set_sensitive(self.store.get_n_items() > 0)

    def handle_reorder(self, type, direction):
        pos = self.selection_model.get_selected()
        n = self.store.get_n_items()
        target = pos - 1 if direction == "UP" else pos + 1

        if pos == Gtk.INVALID_LIST_POSITION or target < 0 or target >= n:
            return

        row_curr = self.store.get_item(pos)
        row_target = self.store.get_item(target)

        obj_curr = row_curr.video if type == "VIDEO" else row_curr.audio
        obj_target = row_target.video if type == "VIDEO" else row_target.audio

        if obj_curr and obj_target:
            # Intercambio de datos (Property Swap)
            self._swap_video_props(obj_curr, obj_target)
            self.selection_model.set_selected(target)

    def _swap_video_props(self, a, b):
        a.name, b.name = b.name, a.name
        a.abs_path, b.abs_path = b.abs_path, a.abs_path
        # ... puedes swappear más si es necesario

    def _change_button_status(self, disabled: bool = True):
        self.btn_analizar.set_sensitive(disabled is not True)

        self.btn_video_subir.set_sensitive(disabled is not True)
        self.btn_video_bajar.set_sensitive(disabled is not True)
        self.btn_audio_subir.set_sensitive(disabled is not True)
        self.btn_audio_bajar.set_sensitive(disabled is not True)
        self.btn_procesar.set_sensitive(disabled is not True)

    def on_process_clicked(self, btn):
        out_dir = self.entry_directorio_salida.get_text()
        if not out_dir:
            self.logger.error("output path is not set")
            self.row_output_folder.add_css_class("error")
            return

        items_to_process = []
        for i in range(self.store.get_n_items()):
            row = self.store.get_item(i)
            if row.video and row.audio and row.selected:
                items_to_process.append(row)

        if not items_to_process:
            self.logger.warning("No items selected for processing")
            return

        mode = "source" if self.radio_keep_source_name.get_active() else "dest"

        self.row_output_folder.remove_css_class("error")
        self.action_stack.set_visible_child_name("cancel")
        self.pro_bar.set_visible(True)
        self.pro_bar.set_fraction(0.0)
        self._change_button_status(disabled=True)

        threading.Thread(target=self._worker_thread,
                         args=(items_to_process, out_dir, mode),
                         daemon=True).start()

    def _worker_thread(self, items_to_process, out_dir, mode):
        self.logger.info("Processing started")
        self.remux_service.cancel_event.clear()
        total = len(items_to_process)

        total_steps = total * 2

        for index, row in enumerate(items_to_process):

            if self.remux_service.cancel_event.is_set():
                break

            micro_step_start = (index * 2) + 1
            progress_start = micro_step_start / total_steps

            GLib.idle_add(setattr, row, "status", "processing")
            GLib.idle_add(self._update_progress, progress_start)

            output_file = self.remux_service.prepare_output_path(
                row.video.abs_path, row.audio.abs_path, out_dir, mode
            )

            is_success = self.remux_service.execute(
                row.video.abs_path, row.audio.abs_path, output_file)

            final_status = "completed" if is_success == True else "error"
            GLib.idle_add(setattr, row, "status", final_status)

        self.logger.info("Processing finished")
        GLib.idle_add(self._on_process_finished)

    def _update_progress(self, fraction):
        self.pro_bar.set_fraction(fraction)
        return False

    def _on_process_finished(self):
        self.pro_bar.set_visible(False)
        self._change_button_status(disabled=False)
        self.action_stack.set_visible_child_name("process")

    def on_cancel_clicked(self, btn):
        self.dialog_confirmar_cancelacion.choose(
            self,
            None,
            self.on_cancel_approved)

    def on_cancel_approved(self, dialog, result):
        response = dialog.choose_finish(result)

        if response == "confirm":
            self.remux_service.cancel()
            self.logger.info("Cancelling...")

