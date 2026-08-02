# Remuxer

**Remuxer** is a high-performance batch media muxing tool for Linux. It allows you to effortlessly copy audio tracks from one source to another set of high-quality video files. Built with **GTK4** and **Libadwaita**, it provides a modern interface to manage mass media processing using the power of **FFmpeg** without quality loss (no recoding).

<p align="center">
  <img src="screenshots/screenshot-side-by-side.png" alt="Remuxer Screenshot" width="800">
</p>

## 🎯 Who is this for?

**Remuxer** is designed for users who need to swap or attach audio streams across multiple files in bulk, eliminating the tedious process of doing it file-by-file in complex editors or via manual terminal commands

### 🔄 The Workflow

Instead of spending hours processing files individually, Remuxer reduces the entire job to three simple steps:

1. **Select Video Source:** Pick the folder containing your high-quality target video files.
2. **Select Audio Source:** Pick the folder containing the replacement or supplementary audio tracks.
3. **Align & Process:** Use the intuitive table to verify that each video matches its corresponding audio file, hit **Start Processing**, and let FFmpeg stream-copy the entire batch in seconds with **zero quality loss**.

## 🚀 Key Features (SEO)

- **Batch Media Muxing:** Process entire directories of video and audio simultaneously.
- **Zero Quality Loss:** Uses FFmpeg stream copying (no re-encoding) for lightning-fast results.
- **Intuitive Mapping:** Align source and destination files easily using a modern GTK4 ColumnView.
- **Linux Native:** Beautifully integrated with the GNOME ecosystem using Libadwaita.

## Build it yourself

### Prerequisites

```
git clone https://github.com/bymoxb/remuxer.git
cd remuxer
flatpak --user install org.gnome.{Platform,Sdk}//50
flatpak-builder --user --force-clean --install build dev.illapa.Remuxer.Devel.json
flatpak --user run --branch=master dev.illapa.Remuxer.Devel
```

Or just use [Builder](https://flathub.org/apps/details/org.gnome.Builder)
