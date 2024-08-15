import os

PATH = r''
NAME = ''

files = [f for f in os.scandir(PATH) if os.path.isfile(f)]

i = 1

for file in files:
    os.rename(file.path, PATH + '\\' + str(i) + '. ' + NAME + '.' + file.path.split('.')[-1])
    i += 1

