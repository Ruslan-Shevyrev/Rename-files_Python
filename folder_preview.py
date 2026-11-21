import subprocess
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import ttk

from renamer import natural_key

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:
    Image = ImageOps = ImageTk = None

try:
    from imageio_ffmpeg import get_ffmpeg_exe
except ImportError:
    get_ffmpeg_exe = None


def read_media_frame(entry, size):
    try:
        return subprocess.run(
            [get_ffmpeg_exe(), '-nostdin', '-loglevel', 'error', '-i', str(entry),
             '-map', '0:V:0', '-frames:v', '1', '-vf',
             f'scale={size}:{size}:force_original_aspect_ratio=decrease',
             '-c:v', 'png', '-f', 'image2pipe', 'pipe:1'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            timeout=8, check=True,
        ).stdout
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return None


class FolderPreview(ttk.Frame):
    THUMBNAIL_SIZE = 72
    IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tif', '.tiff'}
    JPEG_SUFFIXES = {'.jpg', '.jpeg', '.jpe', '.jfif'}
    VIDEO_SUFFIXES = {
        '.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.wmv', '.mpeg', '.mpg',
        '.3gp', '.flv', '.mts', '.m2ts', '.ts',
    }

    def __init__(self, parent, navigate):
        super().__init__(parent, padding=12)
        self.navigate = navigate
        self.folder = None
        self.folders = {}
        self.images = {}
        self.thumbnail_job = None
        self.thumbnail_count = 0
        self.folder_status = ''
        self.frame_worker = ThreadPoolExecutor(max_workers=1)
        self.pending_frame = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text='Содержимое папки').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.up_button = ttk.Button(self, text='Вверх', command=self.go_up, state='disabled')
        self.up_button.grid(row=0, column=1, sticky='e', pady=(0, 8))
        ttk.Style(self).configure('FolderPreview.Treeview', rowheight=self.THUMBNAIL_SIZE + 8)
        self.tree = ttk.Treeview(self, show='tree', style='FolderPreview.Treeview')
        self.tree.grid(row=1, column=0, columnspan=2, sticky='nsew')
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        scrollbar.grid(row=1, column=2, sticky='ns')
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind('<Double-1>', self.open_clicked_folder)
        self.tree.bind('<Return>', self.open_selected_folder)
        self.status = ttk.Label(self, justify='left')
        self.status.grid(row=2, column=0, columnspan=3, sticky='ew', pady=(8, 0))
        self.folder_icon = self.make_icon(folder=True)
        self.file_icon = self.make_icon(folder=False)

    def make_icon(self, folder):
        icon = tk.PhotoImage(master=self, width=44, height=44)
        if folder:
            icon.put('#d6a64a', to=(6, 11, 20, 18))
            icon.put('#e9bc62', to=(6, 15, 38, 34))
        else:
            icon.put('#a0aaba', to=(11, 6, 33, 38))
            icon.put('#eef2f7', to=(12, 7, 32, 37))
            for y in (16, 21, 26):
                icon.put('#a0aaba', to=(16, y, 28, y + 1))
        return icon

    def show_folder(self, folder):
        self.cancel_thumbnails()
        self.tree.delete(*self.tree.get_children())
        self.images.clear()
        self.thumbnail_count = 0
        self.folders.clear()
        self.folder = None
        self.up_button.state(['disabled'])
        if folder is None:
            self.status.configure(text='Выберите папку или введите путь.')
            return
        self.list_folder(folder)

    def cancel_thumbnails(self):
        if self.thumbnail_job is not None:
            self.after_cancel(self.thumbnail_job)
            self.thumbnail_job = None
        if self.pending_frame is not None:
            self.pending_frame.cancel()
            self.pending_frame = None

    def destroy(self):
        self.cancel_thumbnails()
        self.frame_worker.shutdown(wait=False, cancel_futures=True)
        super().destroy()

    def list_folder(self, folder):
        try:
            entries = [(entry, entry.is_dir()) for entry in folder.iterdir()]
        except (OSError, ValueError):
            self.status.configure(text='Не удалось открыть папку. Проверьте путь.')
            return

        self.folder = folder
        if folder.parent != folder:
            self.up_button.state(['!disabled'])
        entries.sort(key=lambda item: (not item[1], natural_key(item[0].name)))
        thumbnails = []
        missing_decoder = False
        for entry, is_folder in entries:
            icon = self.folder_icon if is_folder else self.file_icon
            row = self.tree.insert('', 'end', text=entry.name, image=icon)
            if is_folder:
                self.folders[row] = entry
                continue
            suffix = entry.suffix.lower()
            if suffix in self.VIDEO_SUFFIXES:
                if get_ffmpeg_exe is None:
                    missing_decoder = True
                else:
                    thumbnails.append((row, entry))
            elif suffix in self.IMAGE_SUFFIXES or suffix in self.JPEG_SUFFIXES:
                if (Image is not None or suffix in {'.png', '.gif'}
                        or (suffix in self.JPEG_SUFFIXES and get_ffmpeg_exe is not None)):
                    thumbnails.append((row, entry))
                else:
                    missing_decoder = True
        self.folder_status = f'Объектов: {len(entries)}' if entries else 'Папка пуста.'
        if missing_decoder:
            self.folder_status += '\nВ запущенном Python отсутствует декодер миниатюр.'
        self.thumbnail_count = len(thumbnails)
        if thumbnails:
            self.status.configure(text=f'{self.folder_status}\nЗагрузка миниатюр…')
        else:
            self.status.configure(text=self.folder_status)
        thumbnails.sort(key=lambda item: item[1].suffix.lower() in self.VIDEO_SUFFIXES)
        self.load_thumbnails(iter(thumbnails))

    def load_thumbnails(self, thumbnails):
        for _ in range(8):
            item = next(thumbnails, None)
            if item is None:
                self.thumbnail_job = None
                if self.thumbnail_count:
                    self.status.configure(
                        text=f'{self.folder_status}\nМиниатюр загружено: '
                             f'{len(self.images)} из {self.thumbnail_count}'
                    )
                return
            row, entry = item
            suffix = entry.suffix.lower()
            thumbnail = None if suffix in self.VIDEO_SUFFIXES else self.read_thumbnail(entry)
            if thumbnail is None and get_ffmpeg_exe is not None and (
                suffix in self.VIDEO_SUFFIXES or suffix in self.JPEG_SUFFIXES
            ):
                self.pending_frame = self.frame_worker.submit(read_media_frame, entry, self.THUMBNAIL_SIZE)
                self.thumbnail_job = self.after(25, self.show_media_frame, row, thumbnails)
                return
            self.set_thumbnail(row, thumbnail)
        self.thumbnail_job = self.after(10, self.load_thumbnails, thumbnails)

    def show_media_frame(self, row, thumbnails):
        if not self.pending_frame.done():
            self.thumbnail_job = self.after(25, self.show_media_frame, row, thumbnails)
            return
        frame = self.pending_frame.result()
        self.pending_frame = None
        if frame:
            try:
                self.set_thumbnail(row, tk.PhotoImage(master=self, data=frame, format='png'))
            except tk.TclError:
                pass
        self.load_thumbnails(thumbnails)

    def set_thumbnail(self, row, thumbnail):
        if thumbnail is not None:
            self.images[row] = thumbnail
            self.tree.item(row, image=thumbnail)

    def read_thumbnail(self, entry):
        try:
            if Image is not None:
                try:
                    with Image.open(entry) as source:
                        thumbnail = ImageOps.exif_transpose(source)
                        thumbnail.thumbnail((self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE))
                        return ImageTk.PhotoImage(thumbnail, master=self)
                except Image.DecompressionBombError:
                    return None

            if entry.suffix.lower() in {'.png', '.gif'}:
                source = tk.PhotoImage(master=self, file=str(entry))
                largest_side = max(source.width(), source.height())
                factor = (largest_side + self.THUMBNAIL_SIZE - 1) // self.THUMBNAIL_SIZE
                return source.subsample(factor)
        except (OSError, ValueError, tk.TclError):
            return None

    def go_up(self):
        if self.folder is not None:
            self.navigate(self.folder.parent)

    def open_clicked_folder(self, event):
        self.open_folder(self.tree.identify_row(event.y))

    def open_selected_folder(self, _event):
        self.open_folder(self.tree.focus())

    def open_folder(self, row):
        if row in self.folders:
            self.navigate(self.folders[row])
