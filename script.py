import os
from dotenv import load_dotenv
import telebot
import requests
import json

# Загружаем переменные из .env файла
load_dotenv()

# Получаем токен из переменных окружения
API_TOKEN = os.getenv('BOT_TOKEN')
LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1/chat/completions')

# Проверяем что токен загружен
if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env файле!")

bot = telebot.TeleBot(API_TOKEN)
bot = telebot.TeleBot(API_TOKEN)

# Команды
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я ваш Telegram бот, подключенный к LM Studio.\n"
        "Доступные команды:\n"
        "/start - вывод всех доступных команд\n"
        "/model - выводит название используемой языковой модели\n"
        "Отправьте любое сообщение, и я отвечу с помощью LLM модели."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['model'])
def send_model_name(message):
    try:
        # Отправляем запрос к LM Studio для получения информации о модели
        response = requests.get('http://localhost:1234/v1/models')
        
        if response.status_code == 200:
            model_info = response.json()
            model_name = model_info['data'][0]['id']
            bot.reply_to(message, f"Используемая модель: {model_name}")
        else:
            bot.reply_to(message, 'Не удалось получить информацию о модели.')
    except Exception as e:
        bot.reply_to(message, f'Ошибка подключения к LM Studio: {e}')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_query = message.text
        
        # Формируем запрос к LM Studio API
        request = {
            "messages": [
                {
                    "role": "user",
                    "content": user_query
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # Отправляем запрос к LM Studio
        response = requests.post(
            'http://localhost:1234/v1/chat/completions',
            headers={"Content-Type": "application/json"},
            json=request,
            timeout=30
        )

        if response.status_code == 200:
            response_data = response.json()
            bot_reply = response_data['choices'][0]['message']['content']
            bot.reply_to(message, bot_reply)
        else:
            bot.reply_to(message, f'Ошибка API: {response.status_code}')
            
    except requests.exceptions.ConnectionError:
        bot.reply_to(message, 'Ошибка: Не могу подключиться к LM Studio. Убедитесь, что сервер запущен на localhost:1234')
    except Exception as e:
        bot.reply_to(message, f'Произошла ошибка: {str(e)}')

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)