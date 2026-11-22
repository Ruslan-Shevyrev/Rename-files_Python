"""User-facing text for the Russian and English interfaces."""


ENGLISH = {
    "Параметры переименования": "Rename settings",
    "Папка": "Folder",
    "Обзор…": "Browse…",
    "Имя": "Name",
    "Начальный номер": "Starting number",
    "Добавлять невыбранные файлы в конец": "Append unselected files",
    "Переименовать": "Rename",
    "Содержимое папки": "Folder contents",
    "Родительская папка": "Parent folder",
    "Скопировать текущее имя файла": "Copy current file name",
    "Сортировка": "Sort",
    "Дата изменения": "Date modified",
    "Тип": "Type",
    "Размер": "Size",
    "По возрастанию": "Ascending",
    "По убыванию": "Descending",
    "Выберите папку": "Select a folder",
    "Выберите папку или введите путь.": "Select a folder or enter its path.",
    "Не удалось открыть папку. Проверьте путь.": "Could not open the folder. Check the path.",
    "Объектов: {count}": "Items: {count}",
    "Папка пуста.": "The folder is empty.",
    "В запущенном Python отсутствует декодер миниатюр.": "A thumbnail decoder is unavailable in this Python environment.",
    "Загрузка миниатюр…": "Loading thumbnails…",
    "Миниатюр загружено: {loaded} из {total}": "Thumbnails loaded: {loaded} of {total}",
    "Укажите папку с файлами.": "Select a folder containing files.",
    "Начальный номер должен быть целым числом от 0.": "The starting number must be a whole number, 0 or higher.",
    "Введите имя без запрещённых символов и точки в конце.": "Enter a name without prohibited characters or a trailing period.",
    "Выбранные файлы изменились. Обновите список и повторите выбор.": "The selected files have changed. Refresh the folder and select them again.",
    "Имя уже занято: {name}": "The name is already in use: {name}",
    "Не удалось полностью восстановить исходные имена. Проверьте папки {folder} и {staging}.\n{error}": "Could not restore all original names. Check {folder} and {staging}.\n{error}",
    "Ошибка переименования": "Rename error",
    "Переименовано файлов: {count}": "Files renamed: {count}",
}


def translate(language, message, **values):
    template = ENGLISH.get(message, message) if language == 'en' else message
    return template.format(**values)
