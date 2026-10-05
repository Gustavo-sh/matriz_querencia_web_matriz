import os
import sys
from datetime import datetime

def resource_path(relative_path):

    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def write_log(message):
    dir = './logs/'
    os.makedirs(dir, exist_ok=True)
    file_path = os.path.join(dir, f'log_{datetime.now().strftime("%Y-%m-%d")}.txt')
    with open(file_path, 'a') as log_file:
        log_file.write(str(datetime.now()) + ' - ' + str(message) + '\n')

def notify(message):
    print(message)
    write_log(message)