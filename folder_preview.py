import subprocess
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import ttk

from renamer import file_suffix, natural_key

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk
except ImportError:
    Image = ImageDraw = ImageFont = ImageOps = ImageTk = None

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

    def __init__(self, parent, navigate, translate):
        super().__init__(parent, padding=12, style='Panel.TFrame')
        self.navigate = navigate
        self.translate = translate
        self.folder = None
        self.folders = {}
        self.entries = {}
        self.selected_rows = {}
        self.images = {}
        self.selection_images = {}
        self.thumbnail_job = None
        self.thumbnail_count = 0
        self.folder_messages = []
        self.folder_values = {}
        self.frame_worker = ThreadPoolExecutor(max_workers=1)
        self.pending_frame = None
        self.sort_field = tk.StringVar(master=self, value='name')
        self.sort_descending = tk.BooleanVar(master=self, value=False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.heading = ttk.Label(self, style='Heading.TLabel')
        self.heading.grid(
            row=0, column=0, sticky='w', pady=(0, 10),
        )
        self.up_icon = self.make_up_icon()
        self.up_button = ttk.Button(
            self, image=self.up_icon,
            command=self.go_up, state='disabled',
        )
        self.up_button.grid(row=0, column=1, sticky='e', padx=(8, 4), pady=(0, 8))
        sort_button = self.sort_button = ttk.Menubutton(self)
        sort_button.grid(row=0, column=2, sticky='e', pady=(0, 8))
        sort_menu = self.sort_menu = tk.Menu(sort_button, tearoff=False)
        self.sort_labels = {}
        sort_button.configure(menu=sort_menu)
        for label, field in (
            ('Имя', 'name'), ('Дата изменения', 'modified'), ('Тип', 'type'), ('Размер', 'size')
        ):
            sort_menu.add_radiobutton(
                label=label, value=field, variable=self.sort_field, command=self.sort_rows,
            )
            self.sort_labels[sort_menu.index('end')] = label
        sort_menu.add_separator()
        for label, descending in (('По возрастанию', False), ('По убыванию', True)):
            sort_menu.add_radiobutton(
                label=label, value=descending, variable=self.sort_descending, command=self.sort_rows,
            )
            self.sort_labels[sort_menu.index('end')] = label
        style = ttk.Style(self)
        style.configure('FolderPreview.Treeview', rowheight=self.THUMBNAIL_SIZE + 8)
        style.layout('FolderPreview.Treeview.Item', [
            ('Treeitem.padding', {'sticky': 'nsew', 'children': [
                ('Treeitem.image', {'side': 'right', 'sticky': ''}),
                ('Treeitem.text', {'side': 'left', 'sticky': 'w'}),
            ]}),
        ])
        self.tree = ttk.Treeview(
            self, show='tree', columns=('filename',), selectmode='none', style='FolderPreview.Treeview',
        )
        self.tree.column('#0', width=self.THUMBNAIL_SIZE + 42, stretch=False)
        self.tree.column('filename', minwidth=80)
        self.tree.tag_configure('chosen', background='#322456', foreground='#ffffff')
        self.tree.grid(row=1, column=0, columnspan=3, sticky='nsew')
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        scrollbar.grid(row=1, column=3, sticky='ns')
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.context_menu = tk.Menu(self.tree, tearoff=False)
        self.context_file = None
        self.context_menu.add_command(command=self.copy_file_name)
        self.tree.bind('<Button-3>', self.open_file_menu)
        self.tree.bind('<Double-1>', self.open_clicked_folder)
        self.tree.bind('<ButtonRelease-1>', self.toggle_clicked_file)
        self.tree.bind('<Return>', self.open_selected_folder)
        self.tree.bind('<space>', lambda _event: self.toggle_file(self.tree.focus()))
        self.status = ttk.Label(self, justify='left', style='Status.TLabel')
        self.status.grid(row=2, column=0, columnspan=4, sticky='ew', pady=(8, 0))
        self.folder_icon = self.make_icon(folder=True)
        self.file_icon = self.make_icon(folder=False)
        self.update_language()

    def update_language(self):
        self.heading.configure(text=self.translate('Содержимое папки'))
        self.up_button.configure(text=self.translate('Родительская папка'))
        self.sort_button.configure(text=self.translate('Сортировка'))
        for index, label in self.sort_labels.items():
            self.sort_menu.entryconfigure(index, label=self.translate(label))
        self.context_menu.entryconfigure(0, label=self.translate('Скопировать текущее имя файла'))
        self.update_status()

    def update_status(self):
        self.status.configure(text='\n'.join(
            self.translate(message, **self.folder_values) for message in self.folder_messages
        ))

    def make_icon(self, folder):
        icon = tk.PhotoImage(master=self, width=44, height=44)
        if folder:
            icon.put('#a184fa', to=(6, 11, 20, 18))
            icon.put('#9164ef', to=(6, 15, 38, 34))
        else:
            icon.put('#8773bc', to=(11, 6, 33, 38))
            icon.put('#352b54', to=(12, 7, 32, 37))
            for y in (16, 21, 26):
                icon.put('#b7a4ee', to=(16, y, 28, y + 1))
        return icon

    def make_up_icon(self):
        icon = tk.PhotoImage(master=self, width=22, height=20)
        icon.put('#a184fa', to=(2, 4, 10, 10))
        icon.put('#9164ef', to=(2, 7, 20, 17))
        icon.put('#ffffff', to=(10, 9, 12, 15))
        for offset in range(4):
            icon.put('#ffffff', to=(10 - offset, 7 + offset, 12 + offset, 8 + offset))
        return icon

    def show_folder(self, folder):
        self.cancel_thumbnails()
        self.tree.delete(*self.tree.get_children())
        self.images.clear()
        self.selection_images.clear()
        self.thumbnail_count = 0
        self.folders.clear()
        self.entries.clear()
        self.selected_rows.clear()
        self.folder = None
        self.up_button.state(['disabled'])
        self.folder_values = {}
        if folder is None:
            self.folder_messages = ['Выберите папку или введите путь.']
            self.update_status()
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
            self.folder_messages = ['Не удалось открыть папку. Проверьте путь.']
            self.update_status()
            return

        self.folder = folder
        if folder.parent != folder:
            self.up_button.state(['!disabled'])
        thumbnails = []
        missing_decoder = False
        for entry, is_folder in entries:
            icon = self.folder_icon if is_folder else self.file_icon
            row = self.tree.insert('', 'end', values=(entry.name,), image=icon)
            self.entries[row] = entry
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
        self.folder_messages = ['Объектов: {count}' if entries else 'Папка пуста.']
        self.folder_values = {'count': len(entries)}
        if missing_decoder:
            self.folder_messages.append('В запущенном Python отсутствует декодер миниатюр.')
        self.thumbnail_count = len(thumbnails)
        if thumbnails:
            self.folder_messages.append('Загрузка миниатюр…')
        self.update_status()
        self.sort_rows()
        thumbnails.sort(key=lambda item: item[1].suffix.lower() in self.VIDEO_SUFFIXES)
        self.load_thumbnails(iter(thumbnails))

    def sort_rows(self):
        field = self.sort_field.get()
        descending = self.sort_descending.get()

        def sort_value(row):
            entry = self.entries[row]
            if field == 'type':
                return entry.suffix.casefold() if row not in self.folders else ''
            if field == 'size' and row in self.folders:
                return 0
            try:
                info = entry.stat()
            except OSError:
                return -1
            return info.st_mtime_ns if field == 'modified' else info.st_size

        rows = sorted(
            self.entries, key=lambda row: natural_key(self.entries[row].name), reverse=descending,
        )
        if field != 'name':
            rows.sort(key=sort_value, reverse=descending)
        rows.sort(key=lambda row: row not in self.folders)
        self.tree.set_children('', *rows)

    def load_thumbnails(self, thumbnails):
        for _ in range(8):
            item = next(thumbnails, None)
            if item is None:
                self.thumbnail_job = None
                if self.thumbnail_count:
                    self.folder_messages[-1] = 'Миниатюр загружено: {loaded} из {total}'
                    self.folder_values.update(loaded=len(self.images), total=self.thumbnail_count)
                    self.update_status()
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
            self.update_file_row(row)

    def update_file_row(self, row):
        thumbnail = self.images.get(row, self.file_icon)
        number = self.selected_rows.get(row)
        if number is None:
            self.tree.item(row, image=thumbnail, text='', tags=())
            self.selection_images.pop(row, None)
            return
        if ImageDraw is None:
            label = chr(0x245F + number) if number <= 20 else str(number)
            self.tree.item(row, image=thumbnail, text=label, tags=('chosen',))
            return

        diameter = 32
        badge = Image.new('RGBA', (diameter * 2, diameter * 2))
        draw = ImageDraw.Draw(badge)
        draw.ellipse((1, 1, 62, 62), fill='#8050ff', outline='#c9afff', width=3)
        label = str(number)
        font = ImageFont.load_default(size=min(30, 84 // len(label)))
        draw.text((32, 32), label, font=font, fill='white', anchor='mm', stroke_width=1)
        badge = badge.resize((diameter, diameter), Image.Resampling.LANCZOS)
        badge_image = ImageTk.PhotoImage(badge, master=self)
        size = self.THUMBNAIL_SIZE
        combined = tk.PhotoImage(master=self, width=diameter + 6 + size, height=size)
        # Both Tk and Pillow thumbnails expose a Tk image name for copying.
        combined.tk.call(str(combined), 'copy', str(badge_image), '-to', 0, (size - diameter) // 2)
        combined.tk.call(
            str(combined), 'copy', str(thumbnail), '-to',
            diameter + 6 + (size - thumbnail.width()) // 2, (size - thumbnail.height()) // 2,
        )
        self.selection_images[row] = combined
        self.tree.item(row, image=combined, text='', tags=('chosen',))

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

    def open_file_menu(self, event):
        entry = self.entries.get(self.tree.identify_row(event.y))
        if entry is None or not entry.is_file():
            return
        self.context_file = entry
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_file_name(self):
        entry = self.context_file
        if entry is None:
            return
        self.clipboard_clear()
        self.clipboard_append(entry.name.removesuffix(file_suffix(entry.name)))

    def go_up(self):
        if self.folder is not None:
            self.navigate(self.folder.parent)

    def selected_files(self):
        return tuple(self.entries[row] for row in self.selected_rows)

    def toggle_clicked_file(self, event):
        self.toggle_file(self.tree.identify_row(event.y))

    def toggle_file(self, row):
        if row not in self.entries or not self.entries[row].is_file():
            return
        self.tree.focus(row)
        if row in self.selected_rows:
            del self.selected_rows[row]
            self.update_file_row(row)
        else:
            self.selected_rows[row] = 0
        for index, selected_row in enumerate(self.selected_rows, start=1):
            if self.selected_rows[selected_row] != index:
                self.selected_rows[selected_row] = index
                self.update_file_row(selected_row)

    def open_clicked_folder(self, event):
        self.open_folder(self.tree.identify_row(event.y))

    def open_selected_folder(self, _event):
        self.open_folder(self.tree.focus())

    def open_folder(self, row):
        if row in self.folders:
            self.navigate(self.folders[row])
