import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from folder_preview import FolderPreview
from localization import translate
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
    style.map('TCombobox', fieldbackground=[('readonly', field)],
              foreground=[('readonly', text)], selectbackground=[('readonly', field)],
              selectforeground=[('readonly', text)])
    style.configure('TCombobox', background=field, bordercolor=border, arrowcolor=text,
                    lightcolor=field, darkcolor=field, padding=4)
    root.option_add('*TCombobox*Listbox.background', field)
    root.option_add('*TCombobox*Listbox.foreground', text)
    style.configure('TCheckbutton', indicatorbackground=field, indicatorforeground=text,
                    indicatorbordercolor=border, padding=(0, 4))
    style.map('TCheckbutton', indicatorbackground=[('selected', accent)],
              background=[('active', panel)])
    style.configure('Vertical.TScrollbar', background=border, troughcolor=panel,
                    bordercolor=panel, lightcolor=border, darkcolor=border, arrowcolor=text)
    style.configure('FolderPreview.Treeview', background=background, fieldbackground=background,
                    foreground=text, bordercolor=border, lightcolor=background, darkcolor=background)
    return background


def handle_clipboard_shortcut(event):
    # Windows virtual key codes stay the same when the keyboard layout changes.
    shortcuts = {0x43: '<<Copy>>', 0x58: '<<Cut>>', 0x56: '<<Paste>>'}
    # Leave Ctrl+Alt (including AltGr) available for text input.
    if event.state & 0x20008:
        return
    action = shortcuts.get(event.keycode)
    if action is not None:
        event.widget.event_generate(action)
        return 'break'


def run():
    root = tk.Tk()
    background = configure_theme(root)
    root.title('Rename in Order')
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
    language = tk.StringVar(value='Русский')
    last_count = None
    labels = []

    def current_language():
        return 'en' if language.get() == 'English' else 'ru'

    def tr(message, **values):
        return translate(current_language(), message, **values)

    def localized(widget, message):
        labels.append((widget, message))
        widget.configure(text=tr(message))
        return widget

    def update_language(_event):
        for widget, message in labels:
            widget.configure(text=tr(message))
        preview.update_language()
        update_status()

    def update_status():
        status.set('' if last_count is None else tr('Переименовано файлов: {count}', count=last_count))
    refresh_job = None

    preview = FolderPreview(panes, lambda folder: path.set(str(folder)), tr)
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
        selected = filedialog.askdirectory(parent=root, title=tr('Выберите папку'))
        if selected:
            path.set(selected)
            refresh_preview()

    def submit():
        nonlocal last_count
        last_count = None
        update_status()
        try:
            folder = path.get().strip()
            if not folder:
                raise ValueError(tr('Укажите папку с файлами.'))
            try:
                first_number = int(start_number.get())
            except ValueError:
                raise ValueError(tr('Начальный номер должен быть целым числом от 0.')) from None
            folder = Path(folder).absolute()
            selected = preview.selected_files() if folder == preview.folder else ()
            last_count = rename_files(
                folder, name.get().strip(), start_number=first_number,
                selected_files=selected, append_remaining=append_remaining.get(),
                language=current_language(),
            )
        except (OSError, ValueError) as error:
            messagebox.showerror(tr('Ошибка переименования'), str(error), parent=root)
            return
        update_status()
        refresh_preview()

    header = ttk.Frame(form)
    header.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 18))
    localized(ttk.Label(header, style='Heading.TLabel'), 'Параметры переименования').pack(side='left')
    language_picker = ttk.Combobox(
        header, textvariable=language, values=('Русский', 'English'), state='readonly', width=8,
    )
    language_picker.pack(side='right', padx=(8, 0))
    language_picker.bind('<<ComboboxSelected>>', update_language)
    localized(ttk.Label(form), 'Папка').grid(row=1, column=0, sticky='w')
    path_entry = ttk.Entry(form, textvariable=path, width=34)
    path_entry.grid(row=1, column=1, sticky='ew', padx=8)
    path_entry.bind('<Return>', lambda _event: refresh_preview())
    localized(ttk.Button(form, command=choose_folder), 'Обзор…').grid(row=1, column=2)
    localized(ttk.Label(form), 'Имя').grid(row=2, column=0, sticky='w', pady=10)
    name_entry = ttk.Entry(form, textvariable=name)
    name_entry.grid(row=2, column=1, sticky='ew', padx=8, pady=10)
    localized(ttk.Label(form), 'Начальный номер').grid(row=3, column=0, sticky='w')
    start_number_entry = ttk.Entry(form, textvariable=start_number, width=8)
    start_number_entry.grid(row=3, column=1, sticky='w', padx=8)
    localized(
        ttk.Checkbutton(form, variable=append_remaining), 'Добавлять невыбранные файлы в конец',
    ).grid(row=4, column=1, columnspan=2, sticky='w', padx=8, pady=(12, 0))
    localized(ttk.Button(form, style='Accent.TButton', command=submit), 'Переименовать').grid(
        row=5, column=1, columnspan=2, sticky='e', pady=(18, 8)
    )
    ttk.Label(form, textvariable=status, style='Status.TLabel').grid(
        row=6, column=0, columnspan=3, sticky='w'
    )
    if root.tk.call('tk', 'windowingsystem') == 'win32':
        for entry in (path_entry, name_entry, start_number_entry):
            entry.bind('<Control-KeyPress>', handle_clipboard_shortcut)
    path_entry.focus_set()
    root.mainloop()
