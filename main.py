from gi.repository import Gtk, Gio, GObject, Pango
import os
import gi
from pathlib import Path

# Configurar versiones de GTK
gi.require_version('Gtk', '4.0')
gi.require_version('Pango', '1.0')

VIDEO_EXTENSIONS = {".mp4", ".mkv"}

# --- MODELO DE DATOS ---
# Al heredar de GObject, este objeto puede ser "escuchado" por la interfaz


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
    # Definimos que esta clase contiene dos objetos de tipo VideoItem
    video = GObject.Property(type=VideoItem)
    audio = GObject.Property(type=VideoItem)

    def __init__(self, video, audio):
        super().__init__()
        self.video = video
        self.audio = audio


class AudioRemuxApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.github.bymoxb.audioremux")
        self.builder = None
        self.window = None

        # Almacenamiento de datos (Equivalente a FormVideos en tu Go)
        self.video_files_data = []  # Lista de diccionarios crudos
        self.audio_files_data = []
        self.output_dir = ""

        # El "Store" que alimenta al ColumnView
        self.store = Gio.ListStore(item_type=VideoItem)
        self.selection_model = Gtk.SingleSelection(model=self.store)

    def do_activate(self):
        # Cargar el XML del .ui
        self.builder = Gtk.Builder()
        try:
            self.builder.add_from_file("ui/main.ui")
        except Exception as e:
            print(f"Error cargando UI: {e}")
            return

        self.window = self.builder.get_object("MainWindow")
        self.window.set_application(self)

        self.setup_column_view()
        self.connect_signals()

        self.window.present()

    def setup_column_view(self):
        cv = self.builder.get_object("view_episodios")

        # El Store ahora guarda objetos ColumnViewRow
        self.store = Gio.ListStore(item_type=ColumnViewRow)
        self.selection_model = Gtk.SingleSelection(model=self.store)
        cv.set_model(self.selection_model)

        # Columna de Video
        factory_v = Gtk.SignalListItemFactory()
        factory_v.connect("setup", self._on_factory_setup_label)
        factory_v.connect("bind", self._on_bind_video_column)

        col_v = Gtk.ColumnViewColumn(title="Source Video", factory=factory_v)
        col_v.set_expand(True)
        cv.append_column(col_v)

        # Columna de Audio
        factory_a = Gtk.SignalListItemFactory()
        factory_a.connect("setup", self._on_factory_setup_label)
        factory_a.connect("bind", self._on_bind_audio_column)

        col_a = Gtk.ColumnViewColumn(title="Source Audio", factory=factory_a)
        col_a.set_expand(True)
        cv.append_column(col_a)

    # El setup es genérico para cualquier columna que use un Label
    def _on_factory_setup_label(self, factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        list_item.set_child(label)

    def _on_bind_video_column(self, factory, list_item):
        row = list_item.get_item()  # Esto es un ColumnViewRow
        label = list_item.get_child()

        # Accedemos al objeto video dentro de la fila y bindeamos su nombre
        if row.video:
            row.video.bind_property(
                "name", label, "label", GObject.BindingFlags.SYNC_CREATE)
        else:
            label.set_text("---")

    def _on_bind_audio_column(self, factory, list_item):
        row = list_item.get_item()  # Esto es un ColumnViewRow
        label = list_item.get_child()

        # Accedemos al objeto audio dentro de la fila y bindeamos su nombre
        if row.audio:
            row.audio.bind_property(
                "name", label, "label", GObject.BindingFlags.SYNC_CREATE)
        else:
            label.set_text("---")

    def connect_signals(self):
        # Obtener objetos del builder y conectar clicks
        b = self.builder

        b.get_object("btn_seleccionar_videos_principales").connect(
            "clicked", self.on_select_videos)
        b.get_object("btn_seleccionar_videos_audio").connect(
            "clicked", self.on_select_audios)
        b.get_object("btn_seleccionar_salida").connect(
            "clicked", self.on_select_output)

        b.get_object("btn_analizar").connect("clicked", self.on_analyze)
        b.get_object("btn_procesar").connect("clicked", self.on_process)

        # Botones de edición
        b.get_object("btn_video_subir").connect(
            "clicked", lambda _: self.handle_selection("VIDEO", "UP"))
        b.get_object("btn_video_bajar").connect(
            "clicked", lambda _: self.handle_selection("VIDEO", "DOWN"))
        b.get_object("btn_video_eliminar").connect(
            "clicked", lambda _: self.handle_action_delete())

    # --- LÓGICA DE SELECCIÓN DE CARPETAS ---

    def select_folder(self, title, callback):
        dialog = Gtk.FileDialog(title=title)
        dialog.select_folder(
            self.window, None, self._folder_dialog_callback, callback)

    def _folder_dialog_callback(self, dialog, result, callback):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                callback(folder.get_path())
        except Exception as e:
            print(f"Selección cancelada: {e}")

    def on_select_videos(self, btn):
        def cb(path):
            self.builder.get_object("entry_videos_principales").set_text(path)
            self.video_files_data = self.list_videos(path)
        self.select_folder("Seleccionar Videos", cb)

    def on_select_audios(self, btn):
        def cb(path):
            self.builder.get_object("entry_videos_audio").set_text(path)
            self.audio_files_data = self.list_videos(path)
        self.select_folder("Seleccionar Audios", cb)

    def on_select_output(self, btn):
        def cb(path):
            self.builder.get_object("entry_directorio_salida").set_text(path)
            self.output_dir = path
        self.select_folder("Seleccionar Salida", cb)

    def list_videos(self, path):
        videos = []
        try:
            # Listar y filtrar archivos
            files = sorted(os.listdir(path))
            for i, f in enumerate(files):
                if Path(f).suffix.lower() in VIDEO_EXTENSIONS:
                    videos.append({
                        "name": f,
                        "path": path,
                        "abs_path": os.path.join(path, f),
                        "order": i
                    })
        except Exception as e:
            print(f"Error listando: {e}")
        return videos

    # --- LÓGICA DE PROCESAMIENTO ---

    def on_analyze(self, btn):
        print(f"Analizando: {len(self.video_files_data)} videos")
        self.store.remove_all()  # Limpiar lista actual

        # Buscamos el máximo para no dejar filas fuera
        limit = max(len(self.video_files_data), len(self.audio_files_data))

        for i in range(limit):
            v_obj = None
            if i < len(self.video_files_data):
                d = self.video_files_data[i]
                v_obj = VideoItem(d['name'], d['path'], d['abs_path'], i)

            a_obj = None
            if i < len(self.audio_files_data):
                d = self.audio_files_data[i]
                a_obj = VideoItem(d['name'], d['path'], d['abs_path'], i)

            # Creamos la fila contenedora
            row = ColumnViewRow(video=v_obj, audio=a_obj)
            self.store.append(row)

        self.builder.get_object("btn_procesar").set_sensitive(True)

    def handle_selection(self, item_type, action):
        if item_type == "VIDEO":
            pos = self.selection_model.get_selected()
            if pos == Gtk.INVALID_LIST_POSITION:
                return

            # n_items = self.store.get_n_items()

            if action == "UP" and pos > 0:
                # Obtenemos las filas completas (que contienen video y audio)
                current_row = self.store.get_item(pos)
                prev_row = self.store.get_item(pos - 1)

                print("current_row.audio"+current_row.audio.name)
                print("prev_row.audio"+prev_row.audio.name)

                temp_curr_audio = (current_row.audio)
                temp_prev_audio = (prev_row.audio)

                current_row.audio = temp_prev_audio
                prev_row.audio = temp_curr_audio

                print("="*20)
                print("current_row.audio"+current_row.audio.name)
                print("prev_row.audio"+prev_row.audio.name)

                # Intercambiamos las filas completas
                self.store.splice(pos - 1, 2, [current_row, prev_row])
                self.selection_model.set_selected(pos - 1)

            elif action == "DOWN" and pos < self.store.get_n_items() - 1:
                current_row = self.store.get_item(pos)
                next_row = self.store.get_item(pos + 1)

                temp_curr_audio = current_row.audio
                temp_next_audio = next_row.audio

                current_row.audio = temp_next_audio
                next_row.audio = temp_curr_audio

                self.store.splice(pos, 2, [next_row, current_row])
                self.selection_model.set_selected(pos + 1)

            return

        raise Exception(f"not implemented: {item_type} - {action}")

    def handle_action_delete(self):
        pos = self.selection_model.get_selected()
        if pos != Gtk.INVALID_LIST_POSITION:
            item = self.store.get_item(pos)
            item.is_deleted = True
            item.name = f" [ELIMINADO] {item.name}"

    def on_process(self, btn):
        # Ejemplo: Quitar el primer elemento
        if self.store.get_n_items() > 0:
            self.store.remove(0)


if __name__ == "__main__":
    app = AudioRemuxApp()
    app.run(None)
