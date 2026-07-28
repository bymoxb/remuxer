package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/diamondburned/gotk4/pkg/core/glib"
	"github.com/diamondburned/gotk4/pkg/gio/v2"
	"github.com/diamondburned/gotk4/pkg/gtk/v4"
	"github.com/diamondburned/gotk4/pkg/pango"
)

var videoExtensions = map[string]struct{}{
	".mp4": {},
	".mkv": {},
}

type VideoSource struct {
	Name          string
	Path          string
	AbsPath       string
	Order         int
	AudioDuration int
	IsDeleted     bool
}

type FormVideos struct {
	VideoFiles []VideoSource
	AudioFiles []VideoSource
	OutputDir  string
}

type App struct {
	app        *gtk.Application
	window     *gtk.ApplicationWindow
	cv         *gtk.ColumnView
	ls         *gio.ListStore
	btnProcess *gtk.Button
	sm         *gtk.SingleSelection

	form *FormVideos
}

func main() {

	app := gtk.NewApplication(
		"com.github.bymoxb.audioremux",
		gio.ApplicationFlagsNone,
	)

	app.ConnectActivate(func() {
		activate(app)
	})

	if code := app.Run(os.Args); code > 0 {
		os.Exit(code)
	}
}

func activate(application *gtk.Application) {

	app := &App{
		app:  application,
		form: &FormVideos{},
	}

	app.buildUI()
}

func (a *App) buildUI() {

	builder := gtk.NewBuilderFromFile("ui/main.ui")

	a.window = builder.GetObject("MainWindow").Cast().(*gtk.ApplicationWindow)

	if a.window == nil {
		panic("No se encontró MainWindow")
	}

	a.connectSignals(builder)

	a.window.SetApplication(a.app)
	a.window.Present()
}

func (a *App) connectSignals(builder *gtk.Builder) {

	btnVUp := builder.GetObject("btn_video_subir").Cast().(*gtk.Button)
	btnVDown := builder.GetObject("btn_video_bajar").Cast().(*gtk.Button)
	btnVDelete := builder.GetObject("btn_video_eliminar").Cast().(*gtk.Button)

	entryVideos := builder.GetObject("entry_videos_principales").Cast().(*gtk.Entry)
	btnVideos := builder.GetObject("btn_seleccionar_videos_principales").Cast().(*gtk.Button)

	entryAudio := builder.GetObject("entry_videos_audio").Cast().(*gtk.Entry)
	btnAudio := builder.GetObject("btn_seleccionar_videos_audio").Cast().(*gtk.Button)

	entryOutput := builder.GetObject("entry_directorio_salida").Cast().(*gtk.Entry)
	btnOutput := builder.GetObject("btn_seleccionar_salida").Cast().(*gtk.Button)

	btnProcess := builder.GetObject("btn_procesar").Cast().(*gtk.Button)
	a.btnProcess = btnProcess

	btnAnalize := builder.GetObject("btn_analizar").Cast().(*gtk.Button)

	btnVideos.ConnectClicked(func() {
		a.selectVideoFolder(entryVideos, &a.form.VideoFiles)
	})

	btnAudio.ConnectClicked(func() {
		a.selectVideoFolder(entryAudio, &a.form.AudioFiles)
	})

	btnOutput.ConnectClicked(func() {
		a.selectOutputFolder(entryOutput)
	})

	btnAnalize.ConnectClicked(func() {
		a.analyze()
	})

	btnVUp.ConnectClicked(func() {
		a.handleSelection("Video", "UP")
	})

	btnVDown.ConnectClicked(func() {
		a.handleSelection("Video", "DOWN")
	})

	btnVDelete.ConnectClicked(func() {
		a.handleSelection("Video", "DELETE")
	})

	btnProcess.ConnectClicked(func() {
		a.process()
	})

	cv := builder.GetObject("view_episodios").Cast().(*gtk.ColumnView)

	//
	f0 := gtk.NewSignalListItemFactory()

	f0.ConnectSetup(func(object *glib.Object) {
		cell := object.Cast().(*gtk.ColumnViewCell)
		label := gtk.NewLabel("")
		label.SetXAlign(0) // Alinear a la izquierda
		label.SetEllipsize(pango.EllipsizeEnd)
		cell.SetChild(label)
	})

	f0.ConnectBind(func(object *glib.Object) {
		cell := object.Cast().(*gtk.ColumnViewCell)
		item := cell.Item().Cast().(*gtk.StringObject)
		label := cell.Child().(*gtk.Label)
		label.SetText(item.String())
		// cell := object.Cast().(*gtk.ColumnViewCell)
		// pos := int(cell.Position())
		// if pos < len(a.form.VideoFiles) {
		// 	data := a.form.VideoFiles[pos]
		// 	if label, ok := cell.Child().(*gtk.Label); ok {
		// 		label.SetText(data.Name)
		// 	}
		// }
	})

	c0 := gtk.NewColumnViewColumn("Source Video", &f0.ListItemFactory)
	c0.SetExpand(true)
	cv.AppendColumn(c0)

	// f1 := gtk.NewSignalListItemFactory()

	// f1.ConnectSetup(func(object *glib.Object) {
	// 	cell := object.Cast().(*gtk.ColumnViewCell)
	// 	label := gtk.NewLabel("")
	// 	label.SetXAlign(0)
	// 	label.SetEllipsize(pango.EllipsizeEnd)
	// 	cell.SetChild(label)
	// })

	// f1.ConnectBind(func(object *glib.Object) {
	// 	cell := object.Cast().(*gtk.ColumnViewCell)
	// 	pos := int(cell.Position())
	// 	if pos < len(a.form.AudioFiles) {
	// 		data := a.form.AudioFiles[pos]
	// 		if label, ok := cell.Child().(*gtk.Label); ok {
	// 			label.SetText(data.Name)
	// 		}
	// 	}

	// })

	// c1 := gtk.NewColumnViewColumn("Source Audio", &f1.ListItemFactory)
	// c1.SetExpand(true)
	// cv.AppendColumn(c1)

	a.cv = cv
}

type VideoItem struct {
	Object *gtk.StringObject

	Data VideoSource
}

func (a *App) analyze() {

	fmt.Println("========== FORM ==========")
	fmt.Printf("Videos      : %d\n", len(a.form.VideoFiles))
	fmt.Printf("Audios      : %d\n", len(a.form.AudioFiles))
	fmt.Printf("Destino     : %s\n", a.form.OutputDir)

	fmt.Println("\nVideos encontrados:")

	for _, file := range a.form.VideoFiles {
		fmt.Println(" -", file)
	}

	fmt.Println("\nAudios encontrados:")

	for _, file := range a.form.AudioFiles {
		fmt.Println(" -", file)
	}

	store := gio.NewListStore(glib.TypeObject)

	items := make([]*VideoItem, 0)

	for _, v := range a.form.VideoFiles {

		obj := gtk.NewStringObject(v.Name)

		item := &VideoItem{
			Object: obj,
			Data:   v,
		}

		items = append(items, item)

		store.Append(obj.Object)
	}

	selectionModel := gtk.NewSingleSelection(store)
	a.cv.SetModel(selectionModel)
	a.ls = store

	a.sm = selectionModel
	a.btnProcess.SetSensitive(true)
}

func (a *App) selectVideoFolder(entry *gtk.Entry, destination *[]VideoSource) {

	a.selectFolder(
		"Seleccionar carpeta",
		func(path string) {

			files, err := listVideos(path)

			if err != nil {
				fmt.Println(err)
				return
			}

			entry.SetText(path)
			*destination = files
		},
	)
}

func (a *App) selectOutputFolder(entry *gtk.Entry) {

	a.selectFolder(
		"Seleccionar carpeta de salida",
		func(path string) {

			entry.SetText(path)
			a.form.OutputDir = path
		},
	)
}

func (a *App) selectFolder(title string, callback func(path string)) {

	dialog := gtk.NewFileDialog()

	dialog.SetTitle(title)

	dialog.SelectFolder(
		context.Background(),
		&a.window.Window,
		func(result gio.AsyncResulter) {

			folder, err := dialog.SelectFolderFinish(result)

			if err != nil {
				return
			}

			callback(folder.Path())
		},
	)
}

func listVideos(path string) ([]VideoSource, error) {

	entries, err := os.ReadDir(path)

	if err != nil {
		return nil, err
	}

	files := make([]VideoSource, 0)

	for i, entry := range entries {

		if entry.IsDir() {
			continue
		}

		if !isVideo(entry.Name()) {
			continue
		}

		files = append(
			files,
			VideoSource{
				Name:          entry.Name(),
				Path:          path,
				Order:         i,
				AudioDuration: 0,
				AbsPath:       filepath.Join(path, entry.Name()),
				IsDeleted:     false,
			},
		)
	}

	fmt.Printf(
		"Se detectaron %d videos en %s\n",
		len(files),
		path,
	)

	return files, nil
}

func isVideo(filename string) bool {

	ext := strings.ToLower(filepath.Ext(filename))

	_, ok := videoExtensions[ext]

	return ok
}

func check(err error) {

	if err != nil {
		log.Fatal(err)
	}
}

func (a *App) process() {
	a.ls.Remove(0)
}

func (a *App) handleSelection(group string, action string) {}
