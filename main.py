import random
import psycopg2
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

print('Starting telegram bot / Запуск телеграм бота...')

state_storage = StateMemoryStorage()
token_bot = 'TOKEN_BOT'
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = {}

def show_hint(*lines):
    return '\n'.join(lines)

def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'

class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()

def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0

# Установка соединения с базой данных
conn = psycopg2.connect(
    dbname='dbname',
    user='user',
    password='password'
)

# Создание базы данных с общим набором из 10 слов
def initialize_database(conn):
    with conn.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Words (
            word_id SERIAL PRIMARY KEY,
            target_word VARCHAR(255) NOT NULL,
            translate_word VARCHAR(255) NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserWords (
            user_word_id SERIAL PRIMARY KEY,
            user_id INT REFERENCES Users(user_id),
            word_id INT REFERENCES Words(word_id),
            status VARCHAR(255) DEFAULT 'added',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        words = [
            ('Green', 'Зеленый'),
            ('Every', 'Каждый'),
            ('He', 'Он'),
            ('Country', 'Страна'),
            ('Question', 'Вопрос'),
            ('Tree', 'Дерево'),
            ('They', 'Они'),
            ('Week', 'Неделя'),
            ('Head', 'Голова'),
            ('Fire', 'Огонь')
        ]
        for target_word, translate_word in words:
            cursor.execute("""
            INSERT INTO Words (target_word, translate_word) VALUES (%s, %s);
            """, (target_word, translate_word))
    conn.commit()

#Инициализация базы данных
initialize_database(conn)

# Функция для извлечения всех слов из базы данных
def get_words_from_db():
    with conn.cursor() as cursor:
        cursor.execute("SELECT target_word, translate_word FROM Words;")
        words = cursor.fetchall()
    return words


# Функция для добавления слова в базу данных
def add_word_to_db(target_word, translate_word):
    with conn.cursor() as cursor:
        cursor.execute("""
        INSERT INTO Words (target_word, translate_word) VALUES (%s, %s)
        RETURNING word_id;
        """, (target_word, translate_word))
        word_id = cursor.fetchone()[0]
    conn.commit()
    return word_id


# Функция для удаления слова из базы данных
def delete_word_from_db(target_word):
    with conn.cursor() as cursor:
        cursor.execute("""
        DELETE FROM Words WHERE target_word = %s RETURNING word_id;
        """, (target_word,))
        word_id = cursor.fetchone()[0]
    conn.commit()
    return word_id


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0

#Приветственное сообщение
@bot.message_handler(commands=['start'])
def send_welcome(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        userStep[cid] = 0
    welcome_text = (
        "Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе.\n\n"
        "У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения. Для этого воспрользуйся инструментами:\n\n"
        f"{Command.ADD_WORD}\n"
        f"{Command.DELETE_WORD}\n\n"
        "Ну что, начнём ⬇️\n"
        "Нажми сюда: /cards или введи сообщение: /cards"
    )
    bot.send_message(cid, welcome_text)

#Основная функция предложения слов и взаимодействия с ботом (перевод, добавление, удаление слова и дальнейшие шаги)
@bot.message_handler(commands=['cards'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        userStep[cid] = 0

    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []

    words = get_words_from_db()
    if words:
        selected_words = random.sample(words, 4)
        target_word, translate = random.choice(selected_words)
        other_words = [word[0] for word in selected_words if word[0] != target_word]
    else:
        target_word, translate = 'Peace', 'Мир'
        other_words = ['Green', 'White', 'Hello', 'Car']

    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    other_words_btns = [types.KeyboardButton(word) for word in other_words]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = other_words

#Сообщение для перехода на следующую карточку (слово)
@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


#Сообщение для удаления слова
@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    cid = message.chat.id
    bot.send_message(cid, "Введите слово на английском, которое нужно удалить:")
    bot.register_next_step_handler(message, remove_word)


#Функция для удаления слова
def remove_word(message):
    try:
        target_word = message.text.strip()
        delete_word_from_db(target_word)
        bot.send_message(message.chat.id, f"Слово '{target_word}' удалено\n"
                                            "Для продолжения нажимай сюда - /cards")
    except Exception as e:
        bot.send_message(message.chat.id, "Ошибка при удалении слова. Пожалуйста, попробуйте ещё раз.")
        print(e)


#Сообщение для добавления нового слова
@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    bot.send_message(cid, "Введи слово на английском и его перевод через запятую. Слова должны быть с заглавной буквы (например, Peace, Мир):")
    bot.register_next_step_handler(message, save_new_word)


#Функция для добавления нового слова
def save_new_word(message):
    try:
        target_word, translate_word = message.text.split(',')
        target_word = target_word.strip()
        translate_word = translate_word.strip()
        add_word_to_db(target_word, translate_word)
        bot.send_message(message.chat.id, f"Слово '{target_word}' добавлено с переводом '{translate_word}'\n"
                                            "Для продолжения нажимай сюда - /cards")
    except Exception as e:
        bot.send_message(message.chat.id, "Ошибка при добавлении слова. Пожалуйста, попробуй ещё раз.")
        print(e)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить перевод слова 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)

bot.add_custom_filter(custom_filters.StateFilter(bot))

if __name__ == '__main__':
    print('The bot is running / Бот запущен!')
    bot.infinity_polling(skip_pending=True)