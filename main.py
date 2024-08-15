import random
from sqlalchemy import func
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from models import session, initialize_database, User, Word, UserWord
from user_logging import add_user_to_json

print('Starting telegram bot / Запуск телеграм бота...')

state_storage = StateMemoryStorage()
token_bot = ''
bot = TeleBot(token_bot, state_storage=state_storage)


def show_hint(*lines):
    return '\n'.join(lines)

def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"

# Обработчик команды /help
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/cards - Получить карточки для тренировки\n"
        f"{Command.ADD_WORD} - Добавить новое слово\n"
        f"{Command.DELETE_WORD} - Удалить существующее слово\n"
        "/help - Показать это сообщение"
    )
    bot.send_message(message.chat.id, help_text)


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


# Функция для получения или создания пользователя
def get_or_create_user(chat_id):
    user = session.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        user = User(chat_id=chat_id)
        session.add(user)
        session.commit()

        # Связываем пользователя с существующими словами
        for word in session.query(Word).all():
            user_word = UserWord(user_id=user.user_id, word_id=word.word_id)
            session.add(user_word)
        session.commit()

    return user.user_id


# Функция для извлечения слов пользователя из базы данных (извлекает сразу 4 слова)
def get_user_words(user_id):
    words = (
        session.query(Word.target_word, Word.translate_word)
        .join(UserWord, isouter=True)
        .filter(UserWord.user_id.in_([user_id, None]))
        .order_by(func.random())
        .limit(4)
        .all()
    )
    return words


# Функция для добавления слова в базу данных
def add_word_to_db(user_id, target_word, translate_word):
    # Проверяем, существует ли уже это слово в таблице Word
    word = session.query(Word).filter_by(target_word=target_word, translate_word=translate_word).first()
    if not word:
        # Если слова нет, добавляем его в таблицу Word
        word = Word(target_word=target_word, translate_word=translate_word)
        session.add(word)
        session.commit()

    # Проверяем, существует ли уже связь между пользователем и этим словом
    user_word_link = session.query(UserWord).filter_by(user_id=user_id, word_id=word.word_id).first()
    if not user_word_link:
        # Если связи нет, добавляем её в таблицу UserWord
        user_word_link = UserWord(user_id=user_id, word_id=word.word_id)
        session.add(user_word_link)
        session.commit()


# Приветственное сообщение
@bot.message_handler(commands=['start'])
def send_welcome(message):
    cid = message.chat.id
    user_id = get_or_create_user(cid)
    username = message.from_user.username

    # Добавляем никнейм пользователя и время захода в JSON файл
    add_user_to_json(username)

    welcome_text = (
        "Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе.\n\n"
        "У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения. Для этого воспрользуйся инструментами:\n\n"
        "Добавить слово ➕\n"
        "Удалить слово🔙\n\n"
        "Ну что, начнём ⬇️\n"
        "Нажми сюда: /cards или введи сообщение: /cards\n\n"
        "Для просмотра всех доступных команд, нажми /help"
    )
    bot.send_message(cid, welcome_text)


# Основная функция предложения слов и взаимодействия с ботом (перевод, добавление, удаление слова и дальнейшие шаги)
@bot.message_handler(commands=['cards'])
def create_cards(message):
    cid = message.chat.id
    user_id = get_or_create_user(cid)
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []

    # Получаем 4 слова из базы данных
    words = get_user_words(user_id)

    if not words:
        bot.send_message(cid, "Нет доступных слов. Пожалуйста, добавьте новые слова.")
        return

        # Выбираем одно слово как правильное
    target_word = random.choice(words)
    translate = target_word.translate_word

    # Получаем 3 других слова, исключая правильное слово
    filtered_words = [word for word in words if word.target_word != target_word.target_word]
    other_words = random.sample(filtered_words, 3)

    # Объединяем правильное слово с неправильными вариантами
    options = [target_word.target_word] + [word.target_word for word in other_words]
    random.shuffle(options)

    # Создаем кнопки для всех опций
    buttons = [types.KeyboardButton(option) for option in options]
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([delete_word_btn, add_word_btn, next_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word.target_word
        data['translate_word'] = translate
        data['other_words'] = other_words


# Сообщение для перехода на следующую карточку (слово)
@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


# Функция для удаления слова из базы данных
def delete_word_from_db(user_id, target_word):
    # Находим слово в таблице Word
    word = session.query(Word).filter_by(target_word=target_word).first()
    if word:
        # Удаляем связь в таблице UserWord для конкретного пользователя и слова
        user_word_link = session.query(UserWord).filter_by(user_id=user_id, word_id=word.word_id).first()
        if user_word_link:
            session.delete(user_word_link)
            session.commit()
            return True
    return False


# Сообщение для удаления слова
@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    cid = message.chat.id
    bot.send_message(cid, "Выбери слово из предложенных ниже, которое нужно удалить:")
    bot.register_next_step_handler(message, remove_word)


# Функция для удаления слова
def remove_word(message):
    cid = message.chat.id
    user_id = get_or_create_user(cid)
    try:
        target_word = message.text.strip()
        words = get_user_words(user_id)
        if len(words) <= 1:
            bot.send_message(message.chat.id, "Это последнее слово, его нельзя удалить. У тебя не останется слов для тренировок.")
        else:
            # Удаляем связь между пользователем и словом
            if delete_word_from_db(user_id, target_word):
                bot.send_message(message.chat.id, f"Слово '{target_word}' удалено\nДля продолжения нажимай сюда - /cards")
            else:
                bot.send_message(message.chat.id, f"Слово '{target_word}' не найдено среди твоих слов.")
    except Exception as e:
        bot.send_message(message.chat.id, "Ошибка при удалении слова. Пожалуйста, попробуйте ещё раз.")
        print(e)


# Сообщение для добавления нового слова
@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    bot.send_message(cid,
                     "Введи слово на английском и его перевод через запятую. Слова должны быть с заглавной буквы (например, Peace, Мир):")
    bot.register_next_step_handler(message, save_new_word)


# Функция для добавления нового слова
def save_new_word(message):
    cid = message.chat.id
    user_id = get_or_create_user(cid)
    try:
        target_word, translate_word = message.text.split(',')
        target_word = target_word.strip()
        translate_word = translate_word.strip()
        add_word_to_db(user_id, target_word, translate_word)
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
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))


if __name__ == '__main__':
    # Инициализация базы данных
    initialize_database()
    print('The bot is running / Бот запущен!')
    bot.infinity_polling(skip_pending=True)
