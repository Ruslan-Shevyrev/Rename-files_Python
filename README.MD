# Rename Files in Order

[Читать на русском](README.ru.md)

A desktop utility for batch renaming files. Number files in the order you click their thumbnails, or use filename order.

## Download and run

Download `RenameFilesInOrder-<version>-windows-x64.zip` from [Releases](https://github.com/Ruslan-Shevyrev/rename-files-in-order/releases), extract the entire archive, and open `RenameFilesInOrder.exe`. The packaged app runs without a separate Python installation.

## How to use

Select **English** from the language menu at the top of the right panel.

1. Click **Browse…** or enter a folder path. The left panel shows the files and displays thumbnails for photos and videos.
2. Enter a new name without an extension and set the starting number. For example, `Photo` and `10` produce `10. Photo.jpg`, `11. Photo.jpg`, and so on. The app preserves file extensions.
3. To set a custom order, click files in sequence. The numbered circles show the selection order. Click a selected file again to remove it and renumber the remaining selection.
4. Click **Rename**.

With an empty selection, the app renames every file in the open folder in filename order. With a selection, it renames only the selected files by default. Enable **Append unselected files** to number the rest in filename order after the selection. The Sort menu changes the display order. Double-click a subfolder to open it. Renaming applies to files in the open folder.

## Run from source

With Python 3.13, run these commands in PowerShell from the project root.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe rename_files.py
```

The interface uses Tkinter. Pillow generates image thumbnails, and FFmpeg from `imageio-ffmpeg` extracts video frames.

## Build for Windows x64

The build requires 64-bit Python. The script installs dependencies in `.venv` and uses PyInstaller to build a portable folder.

```powershell
.\build.ps1
.\dist\RenameFilesInOrder\RenameFilesInOrder.exe
```

To also create a ZIP for distribution, run the following command.

```powershell
.\build.ps1 -Zip -Version v1.0.0
```

The archive is saved as `dist\RenameFilesInOrder-v1.0.0-windows-x64.zip`. When you push a new version tag such as `v1.0.0`, GitHub Actions runs the same build and attaches the ZIP to the release.
