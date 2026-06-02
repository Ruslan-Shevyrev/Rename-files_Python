import os
import re

PATH = r''
NAME = ''

def natural_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]

files = sorted(
    [f for f in os.scandir(PATH) if os.path.isfile(f)],
    key=lambda f: natural_key(f.name)
)


i = 1

for file in files:
    os.rename(file.path, PATH + '\\' + str(i) + '. ' + NAME + '.' + file.path.split('.')[-1])
    i += 1