import re
from pathlib import Path
from tempfile import mkdtemp


def natural_key(s):
    return [int(text) if text.isdecimal() else text.lower()
            for text in re.split(r'(\d+)', s)]


def rename_files(folder, name, start_number=1):
    if type(start_number) is not int or start_number < 0:
        raise ValueError('Начальный номер должен быть целым числом от 0.')
    if not name or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith('.'):
        raise ValueError('Введите имя без запрещённых символов и точки в конце.')

    files = sorted(
        (file for file in folder.iterdir() if file.is_file()),
        key=lambda file: natural_key(file.name),
    )
    original_paths = set(files)
    changes = []
    for index, source in enumerate(files, start=start_number):
        # The dot after the sequence number is not an extension separator.
        unnumbered_name = re.sub(r'^\d+\. ', '', source.name)
        suffix = Path(unnumbered_name).suffix
        target = folder / f'{index}. {name}{suffix}'
        if source.name == target.name:
            continue
        if target not in original_paths and (target.exists() or target.is_symlink()):
            raise ValueError(f'Имя уже занято: {target.name}')
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
                raise FileExistsError(f'Имя уже занято: {target.name}')
            temporary.rename(target)
            completed.append((target, temporary))
    except OSError:
        try:
            for target, temporary in reversed(completed):
                target.rename(temporary)
            for source, temporary in reversed(staged):
                if source.exists() or source.is_symlink():
                    raise FileExistsError(f'Имя уже занято: {source.name}')
                temporary.rename(source)
        except OSError as error:
            raise OSError(
                f'Не удалось полностью восстановить исходные имена. '
                f'Проверьте папки {folder} и {staging}.\n{error}'
            ) from error
        staging.rmdir()
        raise
    staging.rmdir()
    return len(changes)
