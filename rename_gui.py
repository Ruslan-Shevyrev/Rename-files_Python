import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from folder_preview import FolderPreview
from renamer import rename_files


def configure_theme(root):
    background = '#101321'
    panel = '#191d30'
    field = '#222740'
    border = '#343956'
    text = '#f4f1ff'
    accent = '#7446ee'
    root.configure(background=background)
    root.option_add('*Menu.background', panel)
    root.option_add('*Menu.foreground', text)
    root.option_add('*Menu.activeBackground', '#3c2b68')
    root.option_add('*Menu.activeForeground', text)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=panel, foreground=text, font=('Segoe UI', 10))
    style.configure('Panel.TFrame', borderwidth=1, relief='solid', bordercolor=border)
    style.configure('Heading.TLabel', font=('Segoe UI', 13, 'bold'))
    style.configure('Status.TLabel', foreground='#b8b5d0')
    style.configure('TEntry', fieldbackground=field, foreground=text, insertcolor=text,
                    bordercolor=border, lightcolor=field, darkcolor=field, padding=(9, 7))
    style.map('TEntry', bordercolor=[('focus', '#ad89ff')])
    for name in ('TButton', 'TMenubutton'):
        style.configure(name, background=field, bordercolor=border, lightcolor=field,
                        darkcolor=field, arrowcolor=text, padding=(10, 7))
        style.map(name, background=[('pressed', '#4a347a'), ('active', '#343052')],
                  foreground=[('disabled', '#85839e')])
    style.configure('Accent.TButton', background=accent, bordercolor=accent,
                    lightcolor=accent, darkcolor=accent, padding=(16, 9),
                    font=('Segoe UI', 10, 'bold'))
    style.map('Accent.TButton', background=[('pressed', '#6336d5'), ('active', '#865cff')])
    style.configure('TCheckbutton', indicatorbackground=field, indicatorforeground=text,
                    indicatorbordercolor=border, padding=(0, 4))
    style.map('TCheckbutton', indicatorbackground=[('selected', accent)],
              background=[('active', panel)])
    style.configure('Vertical.TScrollbar', background=border, troughcolor=panel,
                    bordercolor=panel, lightcolor=border, darkcolor=border, arrowcolor=text)
    style.configure('FolderPreview.Treeview', background=background, fieldbackground=background,
                    foreground=text, bordercolor=border, lightcolor=background, darkcolor=background)
    return background


def run():
    root = tk.Tk()
    background = configure_theme(root)
    root.title('Переименование файлов')
    icon_path = Path(__file__).resolve().parent / 'assets' / 'rename-icon.png'
    root.iconphoto(True, tk.PhotoImage(master=root, file=str(icon_path)))
    root.geometry('1080x560')
    root.minsize(760, 360)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    panes = tk.PanedWindow(
        root, orient='horizontal', sashwidth=10, borderwidth=0, background=background,
    )
    panes.grid(sticky='nsew', padx=12, pady=12)
    form = ttk.Frame(panes, padding=20, style='Panel.TFrame')
    form.columnconfigure(1, weight=1)
    launch_file = sys.executable if getattr(sys, 'frozen', False) else __file__
    path = tk.StringVar(value=str(Path(launch_file).resolve().parent))
    name = tk.StringVar()
    start_number = tk.StringVar(value='1')
    append_remaining = tk.BooleanVar(value=False)
    status = tk.StringVar()
    refresh_job = None

    preview = FolderPreview(panes, lambda folder: path.set(str(folder)))
    panes.add(preview, width=460, minsize=280, stretch='always')
    panes.add(form, width=615, minsize=380, stretch='always')

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
            folder = Path(folder).absolute()
            selected = preview.selected_files() if folder == preview.folder else ()
            count = rename_files(
                folder, name.get().strip(), start_number=first_number,
                selected_files=selected, append_remaining=append_remaining.get(),
            )
        except (OSError, ValueError) as error:
            messagebox.showerror('Ошибка переименования', str(error), parent=root)
            return
        status.set(f'Переименовано файлов: {count}')
        refresh_preview()

    ttk.Label(form, text='Параметры переименования', style='Heading.TLabel').grid(
        row=0, column=0, columnspan=3, sticky='w', pady=(0, 18)
    )
    ttk.Label(form, text='Папка').grid(row=1, column=0, sticky='w')
    path_entry = ttk.Entry(form, textvariable=path, width=34)
    path_entry.grid(row=1, column=1, sticky='ew', padx=8)
    path_entry.bind('<Return>', lambda _event: refresh_preview())
    ttk.Button(form, text='Обзор…', command=choose_folder).grid(row=1, column=2)
    ttk.Label(form, text='Имя').grid(row=2, column=0, sticky='w', pady=10)
    ttk.Entry(form, textvariable=name).grid(row=2, column=1, sticky='ew', padx=8, pady=10)
    ttk.Label(form, text='Начальный номер').grid(row=3, column=0, sticky='w')
    ttk.Entry(form, textvariable=start_number, width=8).grid(row=3, column=1, sticky='w', padx=8)
    ttk.Checkbutton(
        form, text='Добавлять невыбранные файлы в конец', variable=append_remaining,
    ).grid(row=4, column=1, columnspan=2, sticky='w', padx=8, pady=(12, 0))
    ttk.Button(form, text='Переименовать', style='Accent.TButton', command=submit).grid(
        row=5, column=1, columnspan=2, sticky='e', pady=(18, 8)
    )
    ttk.Label(form, textvariable=status, style='Status.TLabel').grid(
        row=6, column=0, columnspan=3, sticky='w'
    )
    path_entry.focus_set()
    root.mainloop()
