import re
from pathlib import Path
from tempfile import mkdtemp

from localization import translate


def natural_key(s):
    return [int(text) if text.isdecimal() else text.lower()
            for text in re.split(r'(\d+)', s)]


def file_suffix(filename):
    # The dot after the sequence number is not an extension separator.
    return Path(re.sub(r'^\d+\. ', '', filename)).suffix


def rename_files(folder, name, start_number=1, *, selected_files=(), append_remaining=False, language='ru'):
    if type(start_number) is not int or start_number < 0:
        raise ValueError(translate(language, 'Начальный номер должен быть целым числом от 0.'))
    if not name or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith('.'):
        raise ValueError(translate(language, 'Введите имя без запрещённых символов и точки в конце.'))

    files = sorted(
        (file for file in folder.iterdir() if file.is_file()),
        key=lambda file: natural_key(file.name),
    )
    if selected_files:
        selected = list(selected_files)
        selected_paths = set(selected)
        if len(selected_paths) != len(selected) or not selected_paths <= set(files):
            raise ValueError(translate(language, 'Выбранные файлы изменились. Обновите список и повторите выбор.'))
        remaining = [file for file in files if file not in selected_paths] if append_remaining else []
        files = selected + remaining
    rename_paths = set(files)
    changes = []
    for index, source in enumerate(files, start=start_number):
        suffix = file_suffix(source.name)
        target = folder / f'{index}. {name}{suffix}'
        if source.name == target.name:
            continue
        if target not in rename_paths and (target.exists() or target.is_symlink()):
            raise ValueError(translate(language, 'Имя уже занято: {name}', name=target.name))
        changes.append((source, target))
    if not changes:
        return 0

    # Free the original names before assigning any final names.
    staging = Path(mkdtemp(prefix='.rename-', dir=folder))
    staged = []
    completed = []
    try:
        for index, (source, target) in enumerate(changes):
            temporary = staging / str(index)
            source.rename(temporary)
            staged.append((source, temporary))
        for (_, temporary), (_, target) in zip(staged, changes):
            if target.exists() or target.is_symlink():
                raise FileExistsError(translate(language, 'Имя уже занято: {name}', name=target.name))
            temporary.rename(target)
            completed.append((target, temporary))
    except OSError:
        try:
            for target, temporary in reversed(completed):
                target.rename(temporary)
            for source, temporary in reversed(staged):
                if source.exists() or source.is_symlink():
                    raise FileExistsError(translate(language, 'Имя уже занято: {name}', name=source.name))
                temporary.rename(source)
        except OSError as error:
            raise OSError(
                translate(language, 'Не удалось полностью восстановить исходные имена. '
                          'Проверьте папки {folder} и {staging}.\n{error}',
                          folder=folder, staging=staging, error=error)
            ) from error
        staging.rmdir()
        raise
    staging.rmdir()
    return len(changes)
