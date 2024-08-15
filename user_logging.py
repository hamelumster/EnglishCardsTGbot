import json
import os
from datetime import datetime
from telebot import types


# Функция для добавления никнейма пользователя и времени в JSON файл
def add_user_to_json(username, file_name='users.json'):
    # Если файл существует, загружаем данные
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            data = json.load(file)
    else:
        data = {}

    # Текущее время
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Добавляем время для существующего пользователя или создаем новую запись
    if username in data:
        data[username].append(current_time)
    else:
        data[username] = [current_time]

    # Сохраняем обновленные данные обратно в файл
    with open(file_name, 'w') as file:
        json.dump(data, file, indent=4)

    print(f"Username {username} and time {current_time} added/updated in {file_name}")