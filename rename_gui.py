import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from folder_preview import FolderPreview
from renamer import rename_files


def run():
    root = tk.Tk()
    root.title('Переименование файлов')
    root.geometry('920x560')
    root.minsize(680, 360)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    panes = ttk.Panedwindow(root, orient='horizontal')
    panes.grid(sticky='nsew')
    form = ttk.Frame(panes, padding=16)
    form.columnconfigure(1, weight=1)
    path = tk.StringVar()
    name = tk.StringVar()
    start_number = tk.StringVar(value='1')
    status = tk.StringVar()
    refresh_job = None

    preview = FolderPreview(panes, lambda folder: path.set(str(folder)))
    panes.add(preview, weight=3)
    panes.add(form, weight=2)

    def refresh_preview():
        nonlocal refresh_job
        if refresh_job is not None:
            root.after_cancel(refresh_job)
            refresh_job = None
        folder = path.get().strip()
        preview.show_folder(Path(folder).absolute() if folder else None)

    def schedule_refresh(*_args):
        nonlocal refresh_job
        if refresh_job is not None:
            root.after_cancel(refresh_job)
        refresh_job = root.after(300, refresh_preview)

    path.trace_add('write', schedule_refresh)
    refresh_preview()

    def choose_folder():
        selected = filedialog.askdirectory(parent=root)
        if selected:
            path.set(selected)
            refresh_preview()

    def submit():
        status.set('')
        try:
            folder = path.get().strip()
            if not folder:
                raise ValueError('Укажите папку с файлами.')
            try:
                first_number = int(start_number.get())
            except ValueError:
                raise ValueError('Начальный номер должен быть целым числом от 0.') from None
            count = rename_files(Path(folder), name.get().strip(), start_number=first_number)
        except (OSError, ValueError) as error:
            messagebox.showerror('Ошибка переименования', str(error), parent=root)
            return
        status.set(f'Переименовано файлов: {count}')
        refresh_preview()

    ttk.Label(form, text='Папка').grid(row=0, column=0, sticky='w')
    path_entry = ttk.Entry(form, textvariable=path, width=24)
    path_entry.grid(row=0, column=1, sticky='ew', padx=8)
    path_entry.bind('<Return>', lambda _event: refresh_preview())
    ttk.Button(form, text='Обзор…', command=choose_folder).grid(row=0, column=2)
    ttk.Label(form, text='Имя').grid(row=1, column=0, sticky='w', pady=8)
    ttk.Entry(form, textvariable=name).grid(row=1, column=1, sticky='ew', padx=8)
    ttk.Label(form, text='Начальный номер').grid(row=2, column=0, sticky='w')
    ttk.Entry(form, textvariable=start_number, width=8).grid(row=2, column=1, sticky='w', padx=8)
    ttk.Button(form, text='Переименовать', command=submit).grid(
        row=3, column=1, columnspan=2, sticky='e', pady=(4, 8)
    )
    ttk.Label(form, textvariable=status).grid(row=4, column=0, columnspan=3, sticky='w')
    path_entry.focus_set()
    root.mainloop()
