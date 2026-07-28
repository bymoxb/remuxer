from gi.repository import Gtk, Gio, GObject, Pango, Adw, GLib
from gi.repository import Gtk, Gio, GObject, Pango
import os
import gi
from pathlib import Path
import threading
import subprocess
import time
from pathlib import Path

# Configurar versiones de GTK
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
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


@Gtk.Template(filename="ui/main.ui")
class MainWindow(Adw.ApplicationWindow):
    # Este nombre DEBE coincidir con el $MainWindow del blueprint
    __gtype_name__ = "MainWindow"

    # Definimos los hijos que queremos usar directamente (Internal children)
    # Esto reemplaza a builder.get_object()
    view_episodios = Gtk.Template.Child()

    btn_seleccionar_videos_principales = Gtk.Template.Child()
    btn_seleccionar_videos_audio = Gtk.Template.Child()
    btn_seleccionar_salida = Gtk.Template.Child()

    btn_analizar = Gtk.Template.Child()
    btn_procesar = Gtk.Template.Child()

    btn_video_subir = Gtk.Template.Child()
    btn_video_bajar = Gtk.Template.Child()
    btn_audio_subir = Gtk.Template.Child()
    btn_audio_bajar = Gtk.Template.Child()

    pro_bar = Gtk.Template.Child()

    # DEBES DECLARAR CADA WIDGET QUE USES CON self.nombre_widget
    entry_videos_principales = Gtk.Template.Child()
    entry_videos_audio = Gtk.Template.Child()
    entry_directorio_salida = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Almacenamiento de datos
        # Cambia a tu tipo de objeto
        self.store = Gio.ListStore(item_type=GObject.Object)
        self.selection_model = Gtk.SingleSelection(model=self.store)

        self.setup_column_view()
        self.connect_signals()

    def setup_column_view(self):
        # Usamos directamente la referencia self.view_episodios
        self.view_episodios.set_model(self.selection_model)

        # Columna de Video
        factory_v = Gtk.SignalListItemFactory()
        factory_v.connect("setup", self._on_factory_setup_label)
        factory_v.connect("bind", self._on_bind_video_column)
        col_v = Gtk.ColumnViewColumn(title="Source Video", factory=factory_v)
        col_v.set_expand(True)
        self.view_episodios.append_column(col_v)

        # Columna de Audio
        factory_a = Gtk.SignalListItemFactory()
        factory_a.connect("setup", self._on_factory_setup_label)
        factory_a.connect("bind", self._on_bind_audio_column)
        col_a = Gtk.ColumnViewColumn(title="Source Audio", factory=factory_a)
        col_a.set_expand(True)
        self.view_episodios.append_column(col_a)

    def _on_factory_setup_label(self, factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        list_item.set_child(label)

    def _on_bind_video_column(self, factory, list_item):
        row = list_item.get_item()
        label = list_item.get_child()

        if row and row.video:
            row.video.bind_property("name", label, "label",
                                    GObject.BindingFlags.SYNC_CREATE)
        else:
            label.set_text("---")

    def _on_bind_audio_column(self, factory, list_item):
        row = list_item.get_item()
        label = list_item.get_child()

        if row and row.audio:
            row.audio.bind_property("name", label, "label",
                                    GObject.BindingFlags.SYNC_CREATE)
        else:
            label.set_text("---")

    def connect_signals(self):
        # Ahora conectamos directamente a los atributos de la clase
        self.btn_seleccionar_videos_principales.connect(
            "clicked", self.on_select_videos)
        self.btn_seleccionar_videos_audio.connect(
            "clicked", self.on_select_audios)
        self.btn_seleccionar_salida.connect("clicked", self.on_select_output)
        self.btn_analizar.connect("clicked", self.on_analyze)
        self.btn_procesar.connect("clicked", self.on_process)

        self.btn_video_subir.connect(
            "clicked", lambda _: self.handle_selection("VIDEO", "UP"))
        self.btn_video_bajar.connect(
            "clicked", lambda _: self.handle_selection("VIDEO", "DOWN"))
        self.btn_audio_subir.connect(
            "clicked", lambda _: self.handle_selection("AUDIO", "UP"))
        self.btn_audio_bajar.connect(
            "clicked", lambda _: self.handle_selection("AUDIO", "DOWN"))

    # --- LÓGICA DE SELECCIÓN DE CARPETAS ---

    def select_folder(self, title, callback):
        dialog = Gtk.FileDialog(title=title)
        dialog.select_folder(
            self, None, self._folder_dialog_callback, callback)

    def _folder_dialog_callback(self, dialog, result, callback):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                callback(folder.get_path())
        except Exception as e:
            print(f"Selección cancelada: {e}")

    def on_select_videos(self, btn):
        def cb(path):
            self.entry_videos_principales.set_text(path)
            self.video_files_data = self.list_videos(path)
        self.select_folder("Seleccionar Videos", cb)

    def on_select_audios(self, btn):
        def cb(path):
            self.entry_videos_audio.set_text(path)
            self.audio_files_data = self.list_videos(path)
        self.select_folder("Seleccionar Audios", cb)

    def on_select_output(self, btn):
        def cb(path):
            self.entry_directorio_salida.set_text(path)
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

        self.btn_procesar.set_sensitive(True)

    def _swap_video_data(self, item1, item2):
        item1.name, item2.name = item2.name, item1.name
        item1.path, item2.path = item2.path, item1.path
        item1.abs_path, item2.abs_path = item2.abs_path, item1.abs_path
        item1.is_deleted, item2.is_deleted = item2.is_deleted, item1.is_deleted
        item1.order, item2.order = item2.order, item1.order
        # Intercambio de Nombre
        # temp_name = obj_curr.name
        # obj_curr.name = obj_target.name
        # obj_target.name = temp_name

        # # Intercambio de Rutas
        # temp_path = obj_curr.path
        # obj_curr.path = obj_target.path
        # obj_target.path = temp_path

        # temp_abs = obj_curr.abs_path
        # obj_curr.abs_path = obj_target.abs_path
        # obj_target.abs_path = temp_abs

        # # Intercambio de estado de borrado
        # temp_del = obj_curr.is_deleted
        # obj_curr.is_deleted = obj_target.is_deleted
        # obj_target.is_deleted = temp_del

        # # Intercambio de Orden (opcional, según tu lógica de negocio)
        # temp_order = obj_curr.order
        # obj_curr.order = obj_target.order
        # obj_target.order = temp_order

    def handle_selection(self, item_type, action):
        # 1. Obtener la posición seleccionada
        pos = self.selection_model.get_selected()
        if pos == Gtk.INVALID_LIST_POSITION:
            print("LOG: Intento de acción sin selección.")
            return

        n_items = self.store.get_n_items()

        # 2. Determinar el índice objetivo
        target_pos = -1
        if action == "UP" and pos > 0:
            target_pos = pos - 1
        elif action == "DOWN" and pos < n_items - 1:
            target_pos = pos + 1

        if target_pos == -1:
            print(
                f"LOG: Acción {action} en posición {pos} ignorada (límite de lista).")
            return

        # 3. Obtener las filas involucradas
        row_curr = self.store.get_item(pos)
        row_target = self.store.get_item(target_pos)

        # 4. Seleccionar los sub-objetos según el tipo (Video o Audio)
        obj_curr = row_curr.video if item_type == "VIDEO" else row_curr.audio
        obj_target = row_target.video if item_type == "VIDEO" else row_target.audio

        # Validación: Solo procedemos si ambos objetos existen en las filas
        if obj_curr is None or obj_target is None:
            print(
                f"LOG: No se puede intercambiar {item_type} porque una de las celdas está vacía.")
            return

        # Helper para los logs (limpia el nombre para visualización)
        def extract_name(item):
            if not item or not item.name:
                return "Vacio"
            # Ajustado para capturar la parte final
            return item.name.split(" - ")[-1]

        print(f"\n--- ACTION {item_type}: {action} ---")
        print(f"Propiedades ANTES:")
        print(f"  [Fila {pos}]: {extract_name(obj_curr)}")
        print(f"  [Fila {target_pos}]: {extract_name(obj_target)}")

        # 5. INTERCAMBIO DE PROPIEDADES (Property Swap)
        # Al modificar estas variables, la UI reacciona sola por el bind_property
        self._swap_video_data(obj_curr, obj_target)

        print(f"Propiedades DESPUÉS:")
        print(f"  [Fila {pos}]: {extract_name(obj_curr)}")
        print(f"  [Fila {target_pos}]: {extract_name(obj_target)}")
        print("-" * 30)

        # 6. Mover la selección para seguir al elemento
        self.selection_model.set_selected(target_pos)

    def handle_action_delete(self):
        pos = self.selection_model.get_selected()
        if pos != Gtk.INVALID_LIST_POSITION:
            item = self.store.get_item(pos)
            item.is_deleted = True
            item.name = f" [ELIMINADO] {item.name}"

    def on_process(self, btn):
        n_items = self.store.get_n_items()

        if n_items == 0:
            print("LOG: No hay elementos para procesar.")
            return

        print(
            f"\n================ COMUENZA EL PROCESO ({n_items} FILAS) ================")

        # Lista donde guardaremos la estructura final para tu proceso (FFmpeg, Remux, etc.)
        lista_para_procesar = []

        for i in range(n_items):
            # 1. Obtener la fila actual en el orden visual de la UI
            row = self.store.get_item(i)

            video = row.video
            audio = row.audio

            # 2. Filtrar o ignorar si fue marcado como eliminado
            if video and video.is_deleted:
                print(
                    f"Fila {i}: Video '{video.name}' omitido por estar marcado como ELIMINADO.")
                continue

            # 3. Estructurar la información de la fila
            # Nota: 'i' representa el nuevo orden final de procesamiento
            data_fila = {
                "orden_final": i,
                "video_name": video.name if video else None,
                "video_path": video.abs_path if video else None,
                "audio_name": audio.name if audio else None,
                "audio_path": audio.abs_path if audio else None,
            }

            lista_para_procesar.append(data_fila)

        # --- MOSTRAR RESULTADO EN CONSOLA ---
        # print("\nLista final ordenada lista para remuxing/procesar:")
        # for elem in lista_para_procesar:
        #     v_info = elem['video_name'] if elem['video_name'] else "SIN VIDEO"
        #     a_info = elem['audio_name'] if elem['audio_name'] else "SIN AUDIO"
        #     print(f"[{elem['orden_final']}] Video: {v_info} | Audio: {a_info}")

        # print("====================================================================\n")

        # Aquí ya tienes 'lista_para_procesar' disponible para pasarla a tu función de FFmpeg
        # ej: self.ejecutar_remux(lista_para_procesar)

            # 2. Desactivar el botón para evitar múltiples clics durante el proceso
        btn.set_sensitive(False)

        # 3. Obtener el widget de la barra de progreso
        self.pro_bar.set_fraction(0.0)
        self.pro_bar.set_text("Iniciando...")

        # 4. Lanzar el hilo para no congelar la UI
        # Pasamos n_items y el botón como argumentos
        thread = threading.Thread(
            target=self._run_heavy_task, args=(n_items, btn))
        thread.start()

    def _run_append_audio(self, video, audio, destination):
        print("="*50)
        print("Video: "+video)
        print("Audio: "+audio)
        print("Desti: "+destination)
        cmd = [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            ##
            "-i", video,
            "-i", audio,
            ##
            "-map", "0",
            "-map", "1:a:0",
            ##
            "-map_metadata", "0",
            ##
            "-c", "copy",
            ##
            destination,
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            print(f"ffmpeg falló:\n{result.stderr}")
            # raise RuntimeError(
            #     f"ffmpeg falló:\n{result.stderr}"
            # )

        print("="*50)

    def _run_heavy_task(self, n_items, btn):
        """Esta función corre en un hilo separado (background)"""
        destination_path = Path(self.output_dir)
        destination_path.mkdir(parents=True, exist_ok=True)

        for i in range(n_items):
            # OBTENER EL ELEMENTO DE LA LISTA
            # Aquí es donde accedes a tus datos para procesarlos
            row = self.store.get_item(i)
            print(f"Procesando: {row.video.name} con audio {row.audio.name}")

            # Simulamos el trabajo (1 segundo)

            new_file_name = Path(row.video.abs_path)

            # time.sleep(1)
            self._run_append_audio(
                row.video.abs_path,
                row.audio.abs_path,
                str(destination_path/new_file_name.name))

            # Calcular el progreso (de 0.0 a 1.0)
            fraction = (i + 1) / n_items
            text = f"Procesando {i + 1} de {n_items}..."

            # ACTUALIZAR UI: Debe hacerse mediante GLib.idle_add
            GLib.idle_add(self._update_ui_progress, fraction, text)

        # Al terminar, rehabilitamos el botón y limpiamos el texto
        GLib.idle_add(btn.set_sensitive, True)
        GLib.idle_add(self._update_ui_progress, 1.0, "¡Proceso Completado!")

    def _update_ui_progress(self, fraction, text):
        """Esta función corre en el hilo principal (UI)"""
        self.pro_bar.set_fraction(fraction)
        self.pro_bar.set_text(text)
        return False  # Importante para que GLib no repita la llamada


class AudioRemuxApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.bymoxb.audioremux",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        # Simplemente instanciamos la MainWindow
        self.window = MainWindow(application=self)
        self.window.present()


if __name__ == "__main__":
    app = AudioRemuxApp()
    app.run(None)
