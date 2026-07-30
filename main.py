import os
import gettext
import locale
import gi
import threading
import subprocess
import time
from pathlib import Path
import requests
from packaging import version
import logging
from abc import ABC, abstractmethod

# Configuración profesional del logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("RemuxerApp")

# --- CONSTANTES Y CONFIGURACIÓN ---
APP_NAME = "remuxer"
APP_ID = "com.github.bymoxb.remuxer"
APP_VERSION = "0.1.0-dev"
APP_GITHUB = "https://github.com/bymoxb/remuxer"
APP_GITHUB_RELEASES = "https://api.github.com/repos/bymoxb/remuxer/releases/latest"
VIDEO_EXTENSIONS = {".mp4", ".mkv"}
LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale')

# Localización
try:
    locale.setlocale(locale.LC_ALL, '')
    locale.bindtextdomain(APP_NAME, LOCALE_DIR)
    locale.textdomain(APP_NAME)
except:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

gettext.bindtextdomain(APP_NAME, LOCALE_DIR)
gettext.textdomain(APP_NAME)


_ = gettext.gettext

# Configuración de GTK
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gio, GObject, Pango, Adw, GLib

logger.info(f"Current version: {APP_VERSION}")
logger.info(f"Current language: {os.environ.get('LANGUAGE')}")
logger.info(f"Translation search path: {LOCALE_DIR}")


# --- 1. MODELOS DE DATOS ---
class CommandRunner(ABC):

    @abstractmethod
    def start(
        self,
        video: str,
        audio: str,
        destination: str
    ) -> subprocess.Popen:
        ...


class VideoItem(GObject.Object):
    name = GObject.Property(type=str)
    path = GObject.Property(type=str)
    abs_path = GObject.Property(type=str)
    order = GObject.Property(type=int)
    is_deleted = GObject.Property(type=bool, default=False)

    def __init__(self, name, path, abs_path, order):
        super().__init__()
        self.name = name
        self.path = path
        self.abs_path = abs_path
        self.order = order


class ColumnViewRow(GObject.Object):
    video = GObject.Property(type=VideoItem)
    audio = GObject.Property(type=VideoItem)

    def __init__(self, video, audio):
        super().__init__()
        self.video = video
        self.audio = audio

# --- 2. SERVICIOS (LÓGICA DE NEGOCIO Y DATOS) ---


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


class FileService:
    def __init__(self):
        self.logger = logging.getLogger("RemuxerApp.FileService")

    """Encargado de interactuar con el sistema de archivos"""

    def list_videos(self, path):
        videos = []
        try:
            files = sorted(os.listdir(path))
            for i, f in enumerate(files):
                if Path(f).suffix.lower() in VIDEO_EXTENSIONS:
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

# --- 3. VISTA (INTERFAZ DE USUARIO) ---


@Gtk.Template(filename="ui/main.ui")
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    # Widgets de la plantilla
    view_episodios = Gtk.Template.Child()
    btn_seleccionar_videos_principales = Gtk.Template.Child()
    btn_seleccionar_videos_audio = Gtk.Template.Child()
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
        self.setup_actions()

        # Tarea de red en segundo plano
        threading.Thread(target=self._check_updates_async, daemon=True).start()

    def setup_ui(self):
        self.view_episodios.set_model(self.selection_model)
        self._add_column(_("Source Video"), self._on_bind_video_column)
        self._add_column(_("Source Audio"), self._on_bind_audio_column)

    def _add_column(self, title, bind_callback):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup_label)
        factory.connect("bind", bind_callback)
        col = Gtk.ColumnViewColumn(title=title, factory=factory)
        col.set_expand(True)
        self.view_episodios.append_column(col)

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
                self.video_data_cache["videos"] = self.file_service.list_videos(
                    path)
            elif target == "audios":
                self.entry_videos_audio.set_text(path)
                self.video_data_cache["audios"] = self.file_service.list_videos(
                    path)
            else:
                self.entry_directorio_salida.set_text(path)
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

    def on_process_clicked(self, btn):
        out_dir = self.entry_directorio_salida.get_text()
        if not out_dir:
            self.logger.error("output path is not set")
            self.entry_directorio_salida.add_css_class("error")
            return

        self.entry_directorio_salida.remove_css_class("error")
        btn.set_sensitive(False)
        self.action_stack.set_visible_child_name("cancel")

        threading.Thread(target=self._worker_thread,
                         args=(out_dir,), daemon=True).start()

    def _worker_thread(self, out_dir):
        self.logger.info("Processing started")
        self.remux_service.cancel_event.clear()
        n = self.store.get_n_items()
        mode = "source" if self.radio_keep_source_name.get_active() else "dest"

        for i in range(n):
            if self.remux_service.cancel_event.is_set():
                break

            row = self.store.get_item(i)
            if not row.video or not row.audio:
                continue

            GLib.idle_add(self._update_progress, i/n, f"{i+1}/{n}")

            output_file = self.remux_service.prepare_output_path(
                row.video.abs_path, row.audio.abs_path, out_dir, mode
            )

            self.remux_service.execute(
                row.video.abs_path, row.audio.abs_path, output_file)

        self.logger.info("Processing finished")
        GLib.idle_add(self._on_process_finished)

    def _update_progress(self, fraction, text):
        self.pro_bar.set_fraction(fraction)
        self.pro_bar.set_text(text)

    def _on_process_finished(self):
        self.btn_procesar.set_sensitive(True)
        self.action_stack.set_visible_child_name("process")
        status = _("Cancelled") if self.remux_service.cancel_event.is_set() else _(
            "Completed!")
        self._update_progress(1.0 if "Comp" in status else 0.0, status)

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
            self.pro_bar.set_text(_(""))

    def setup_actions(self):
        # Acciones de menú (About, etc)
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about_clicked)
        self.add_action(action)

        menu = Gio.Menu.new()
        menu.append(_("About Remuxer"), "win.about")
        self.btn_menu.set_menu_model(menu)

    def on_about_clicked(self, *args):
        Adw.AboutWindow(
            transient_for=self, version=APP_VERSION, application_name=APP_NAME,
            application_icon=APP_ID, website=APP_GITHUB, developer_name="bymoxb"
        ).present()

# --- 4. APLICACIÓN ---


class AudioRemuxApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = MainWindow(application=self)
        win.present()


if __name__ == "__main__":
    app = AudioRemuxApp()
    app.run(None)
