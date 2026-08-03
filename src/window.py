# SPDX-License-Identifier: GPL-3.0-only

import logging
import threading

from gettext import gettext as _

from gi.repository import Adw, Gtk, Gio, Pango, GLib, GObject

from .models.column_view_row import ColumnViewRow, StatusViewRow
from .models.view_item import VideoItem, StreamItem
from .services.ffmpeg import FFmpegRunner
from .services.file_service import FileService
from .services.remux_service import RemuxService
from .services.update_service import UpdateService

from remuxer import const


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
    pg_cr_audio_tracks = Gtk.Template.Child()

    # Factories
    cv_selection_factory = Gtk.Template.Child()
    cv_video_factory = Gtk.Template.Child()
    cv_audio_factory = Gtk.Template.Child()
    cv_status_factory = Gtk.Template.Child()

    current_column_row_index = None
    current_column_row = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.logger = logging.getLogger("RemuxerApp.MainWindow")

        # Inicializar Servicios
        self.remux_service = RemuxService(FFmpegRunner())
        self.update_service = UpdateService(
            target_url=const.APP_GITHUB_RELEASES, current_version=const.VERSION)
        self.file_service = FileService()
        self.video_data_cache = {"videos": [], "audios": []}

        # Estado de la UI
        self.cv_store = Gio.ListStore(item_type=GObject.Object)
        self.cv_selection_model = Gtk.SingleSelection(model=self.cv_store)

        #
        self.cr_stream_store = Gio.ListStore.new(StreamItem)
        self.cr_audio_stream_selection_model = Gtk.SingleSelection(
            model=self.cr_stream_store)

        #
        self.setup_ui()
        self.connect_signals()
        self.setup_cv_actions()

        # Tarea de red en segundo plano
        threading.Thread(target=self._check_updates_async, daemon=True).start()

    def connect_selection_model(self):

        self.pg_cr_audio_tracks.set_model(self.cr_audio_stream_selection_model)

        self.cv_selection_model.connect(
            "notify::selected-item",
            self._on_column_row_selected
        )

        self.pg_cr_audio_tracks.connect(
            "notify::selected-item",
            self.on_combo_changed
        )

    def on_combo_changed(self, selection_model, _):

        if self._updating_combo:
            return

        stream = selection_model.get_selected_item()

        if stream is None:
            return

        self.logger.debug(f"combo_changed: {stream}")

        current_column_row = self.cv_selection_model.get_selected_item()

        if current_column_row and current_column_row.audio:
            self.logger.debug(
                f"combo_changed.change_audio_stream: source_audio_track: {current_column_row.audio.audio_stream_index_selected} -> {stream.index}\n")
            current_column_row.audio.audio_stream_index_selected = stream.index

    def _on_column_row_selected(self, selection_model, _param):
        item = selection_model.get_selected_item()  # item es ColumnViewRow
        if not item or not item.audio:
            return

        self.logger.debug(f"on_column_row_selected: {item}")

        # BLOQUEO: Evitamos que el proceso de carga dispare on_combo_selection_changed
        self._updating_combo = True

        self.cr_stream_store.remove_all()

        target_index = 0
        streams = item.audio.get_audio_streams()

        for index, stream in enumerate(streams):
            self.cr_stream_store.append(stream)
            if stream.index == item.audio.audio_stream_index_selected:
                target_index = index

        self.cr_audio_stream_selection_model.set_selected(target_index)
        self.pg_cr_audio_tracks.set_selected(target_index)

        self._updating_combo = False

    def setup_ui(self):
        self.cv_files.set_model(self.cv_selection_model)
        self._setup_selection_factory()
        self._setup_label_factory(
            self.cv_video_factory, self._on_bind_video_column)
        self._setup_label_factory(
            self.cv_audio_factory, self._on_bind_audio_column)
        self._setup_status_factory()
        self._setup_preferences()
        self.connect_selection_model()

    def _setup_preferences(self):
        factory = Gtk.SignalListItemFactory()

        factory.connect("setup", self._on_setup_pg_audio_track)
        factory.connect("bind", self._on_bind_pg_audio_track)

        self.pg_cr_audio_tracks.set_factory(factory)

    def _on_setup_pg_audio_track(self, factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)

        list_item.set_child(label)

    def _on_bind_pg_audio_track(self, factory, list_item):

        label = list_item.get_child()
        stream = list_item.get_item()

        label.set_text(stream.get_display_name())


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

            for cls in ["success", "error", "accent", "warning"]:
                icon.remove_css_class(cls)

            label.remove_css_class("dim-label")

            if status == StatusViewRow.PROCESSING.value:
                stack.set_visible_child_name("spinner")
                spinner.start()
                label.set_text(_("Processing..."))
            else:
                spinner.stop()
                stack.set_visible_child_name("icon")

                if status == StatusViewRow.COMPLETED.value:
                    icon.set_from_icon_name("object-select-symbolic")
                    icon.add_css_class("success")
                    label.set_text(_("Done"))
                elif status == StatusViewRow.ERROR.value:
                    icon.set_from_icon_name("dialog-error-symbolic")
                    icon.add_css_class("error")
                    label.set_text(_("Error"))
                elif status == StatusViewRow.WARNING.value:
                    icon.set_from_icon_name("info-outline-symbolic")
                    icon.add_css_class("warning")
                    label.set_text(_("Needs Review"))

        list_item.handler_id = row.connect("notify::status", update_ui)

        update_ui()

    def _on_unbind_status_column(self, factory, list_item):
        row = list_item.get_item()
        handler_id = getattr(list_item, "handler_id", None)
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

        bind = row.bind_property(
            "selected",
            check,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE
        )

        list_item.selection_binding = bind

    def _on_unbind_selection_column(self, factory, list_item):
        bind = getattr(list_item, "selection_binding", None)
        if bind:
            bind.unbind()
            list_item.selection_binding = None

    def _on_select_all_activated(self, action, parameter):
        for i in range(self.cv_store.get_n_items()):
            self.cv_store.get_item(i).selected = True

    def _on_unselect_all_activated(self, action, parameter):
        for i in range(self.cv_store.get_n_items()):
            self.cv_store.get_item(i).selected = False

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
        if const.IS_DEVEL:
            self.logger.debug("Development mode: skipping update check")
            return
        new_version = self.update_service.check_for_updates()
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

    def _worker_thread_analyze(self, v_list, a_list):
        self.logger.info("Analyzing files...")
        self.remux_service.cancel_event.clear()
        v_list = self.video_data_cache["videos"]
        a_list = self.video_data_cache["audios"]

        total = max(len(v_list), len(a_list))
        total_steps = total * 2

        size = 0

        for i in range(max(len(v_list), len(a_list))):

            if self.remux_service.cancel_event.is_set():
                break

            micro_step_start = (i * 2) + 1
            progress_start = micro_step_start / total_steps

            GLib.idle_add(self._update_progress, progress_start)

            v_obj = None
            if i < len(v_list):
                v_obj = VideoItem(**v_list[i])
                v_streams = [
                    StreamItem(**s.to_dict())
                    for s in self.remux_service.extract_tracks_info(v_list[i]["abs_path"])
                ]
                v_obj.set_streams(v_streams)

            a_obj = None
            if i < len(a_list):
                a_obj = VideoItem(**a_list[i])
                a_streams = [
                    StreamItem(**s.to_dict())
                    for s in self.remux_service.extract_tracks_info(a_list[i]["abs_path"])
                ]
                a_obj.set_streams(a_streams)

            GLib.idle_add(self.cv_store.append, ColumnViewRow(
                video=v_obj, audio=a_obj))
            size += 1

        self.logger.info("Analysis completed")

        GLib.idle_add(self.pro_bar.set_visible, False)
        GLib.idle_add(self.btn_analizar.set_sensitive, True)
        GLib.idle_add(self.btn_procesar.set_sensitive, size > 0)

    def on_analyze_clicked(self, btn):
        self.cv_store.remove_all()

        v_list = self.video_data_cache["videos"]
        a_list = self.video_data_cache["audios"]

        self.pro_bar.set_visible(True)
        self.pro_bar.set_fraction(0.0)

        threading.Thread(target=self._worker_thread_analyze,
                         args=(v_list, a_list),
                         daemon=True).start()

        self.btn_procesar.set_sensitive(False)
        self.btn_analizar.set_sensitive(False)

    def handle_reorder(self, type, direction):
        pos = self.cv_selection_model.get_selected()
        n = self.cv_store.get_n_items()
        target = pos - 1 if direction == "UP" else pos + 1

        if pos == Gtk.INVALID_LIST_POSITION or target < 0 or target >= n:
            return

        row_curr = self.cv_store.get_item(pos)
        row_target = self.cv_store.get_item(target)

        obj_curr = row_curr.video if type == "VIDEO" else row_curr.audio
        obj_target = row_target.video if type == "VIDEO" else row_target.audio

        if obj_curr and obj_target:
            self._swap_video_props(obj_curr, obj_target)
            self.cv_selection_model.set_selected(target)

    def _swap_video_props(self, a, b):
        a.name, b.name = b.name, a.name
        a.abs_path, b.abs_path = b.abs_path, a.abs_path

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
        for i in range(self.cv_store.get_n_items()):
            row = self.cv_store.get_item(i)
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

            GLib.idle_add(setattr, row, "status",
                          StatusViewRow.PROCESSING.value)
            GLib.idle_add(self._update_progress, progress_start)

            output_file = self.remux_service.prepare_output_path(
                row.video.abs_path, row.audio.abs_path, out_dir, mode
            )

            is_success = self.remux_service.execute(
                row.video.abs_path, row.audio.abs_path, output_file)

            final_status = StatusViewRow.COMPLETED.value if is_success == True else StatusViewRow.ERROR.value
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
