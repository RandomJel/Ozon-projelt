import os
import telebot
from telebot import types
import shutil
import pandas as pd
import config

bot = telebot.TeleBot(config.API_TOKEN)

# Команды бота
def set_commands_to_start():
    bot.set_my_commands([
    telebot.types.BotCommand("/start", "Запустить бота"),
    telebot.types.BotCommand("/help", "Список команд"),
    telebot.types.BotCommand("/compare", "Сравнить данные из таблицы")
    ])

# Словарь для отслеживания состояний пользователей
user_states = {}

# /start
@bot.message_handler(commands=['start'])
def start(message):
    set_commands_to_start()

    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(row_width=2)
    item_compare = types.KeyboardButton('Сравнить данные')
    item_help = types.KeyboardButton('Помощь')
    
    # Добавляем кнопки на клавиатуру
    markup.add(item_compare, item_help)

    bot.reply_to(message, "Привет! Напиши /help, чтобы узнать, что я умею.", reply_markup=markup)

# /help
@bot.message_handler(commands=['help'])
@bot.message_handler(func=lambda message: "Помощь" in message.text)
def help(message):
    bot.reply_to(message, """*И так... я умею*: 
- _Анализирую таблицы в форматах_ `.xlsx` _и_ `.csv`
- _Сравниваю данные из таблицы_

Команды:
/start - запустить бота
/compare - сравнить данные из таблицы

P.s
Чтобы работать с ботом, для начала нужно отправить ему файл
""", parse_mode='markdown')

# Отправка файла
@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    file_id = message.document.file_id
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path

    downloaded_file = bot.download_file(file_path)
    filename = f"{user_id}/{message.document.file_name}"

    if not os.path.exists(str(user_id)):
        os.makedirs(str(user_id))

    with open(filename, 'wb') as new_file:
        new_file.write(downloaded_file)

    # Сохраняем состояние пользователя
    user_states[user_id] = {'filename': filename}

    bot.send_message(user_id, "Файл успешно загружен. Теперь вы можете выполнить команду /compare для сравнения данных.")

# /compare
@bot.message_handler(commands=['compare'])
@bot.message_handler(func=lambda message: "Сравнить данные" in message.text)
def compare_data(message):
    user_id = message.from_user.id

    # Проверяем, есть ли файл для сравнения
    if user_id not in user_states or 'filename' not in user_states[user_id]:
        bot.send_message(user_id, "Для сравнения данных, пожалуйста, сначала загрузите файл.")
        return

    filename = user_states[user_id]['filename']  # Перенесено сюда

    try:
        # Получаем данные из файла
        data = pd.read_excel(filename) if filename.endswith('.xlsx') else pd.read_csv(filename, delimiter=';')

        # Предварительная обработка столбца 'price'
        data['Цена товара'] = data['Цена товара'].replace(r'[\$,]', '', regex=True).astype(float)

        # Сравниваем данные
        if 'Название товара' not in data.columns:
            bot.send_message(user_id, "Файл не содержит столбца 'Название товара'.")
            return

        # Загружаем данные из файла
        existing_products = [(row['Название товара'], row['Категория товара'], row['Цена товара'], row['Описание товара']) for _, row in data.iterrows()]

        # Отправляем результат пользователю
        if existing_products:
            result_message = "Товары из файла:\n"
            result_message += "\n".join(f" - {', '.join(map(str, product))}" for product in existing_products)
        else:
            result_message = "Файл не содержит товаров."

        bot.send_message(user_id, result_message)

    except Exception as e:
        print(f"Ошибка при сравнении данных: {e}")
        bot.send_message(user_id, "Произошла ошибка при сравнении данных.")

    finally:
        # Удаляем пользовательскую папку
        os.remove(filename)
        shutil.rmtree(str(user_id))

        # Удаляем состояние пользователя
        del user_states[user_id]

# Запуск бота
bot.polling()
