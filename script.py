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

# Словарь для хранения истории диалогов пользователей
# Ключ — user_id (уникальный идентификатор пользователя в Telegram)
# Значение — список сообщений с ролями user и assistant
user_conversations = {}

def get_or_create_conversation(user_id):
    """Бот находит или создает новую (пустую) строку с историей диалога для данного user_id"""
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    return user_conversations[user_id]

def add_user_message(conversation, message):
    """Бот добавляет в эту строку новый запрос пользователя («role: user»)"""
    conversation.append({
        "role": "user",
        "content": message
    })

def add_assistant_message(conversation, message):
    """Полученный от модели ответ бот добавляет в строку с историей («role: assistant»)"""
    conversation.append({
        "role": "assistant", 
        "content": message
    })

def clear_conversation_history(user_id):
    """Очищает историю диалога для пользователя"""
    if user_id in user_conversations:
        user_conversations[user_id] = []

# Команды
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я ваш Telegram бот, подключенный к LM Studio.\n"
        "Доступные команды:\n"
        "/start - вывод всех доступных команд\n"
        "/model - выводит название используемой языковой модели\n"
        "/clear - очищает историю нашего диалога\n"
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

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    clear_conversation_history(user_id)
    bot.reply_to(message, "✅ История нашего диалога очищена! Начнем заново.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_id = message.from_user.id
        user_query = message.text
        
        # Получаем историю диалога пользователя
        conversation = get_or_create_conversation(user_id)
        
        # Добавляем новый запрос пользователя
        add_user_message(conversation, user_query)
        
        # Отправляем всю историю в LM Studio
        request = {
            "messages": conversation,
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
            
            # Добавляем ответ ассистента в историю
            add_assistant_message(conversation, bot_reply)
            
            # Ограничиваем размер истории
            if len(conversation) > 20:
                user_conversations[user_id] = conversation[-20:]
            
            bot.reply_to(message, bot_reply)
        else:
            if conversation and conversation[-1]["role"] == "user":
                conversation.pop()
            bot.reply_to(message, f'Ошибка API: {response.status_code}')
            
    except requests.exceptions.ConnectionError:
        if 'conversation' in locals() and conversation and conversation[-1]["role"] == "user":
            conversation.pop()
        bot.reply_to(message, 'Ошибка: Не могу подключиться к LM Studio.')
    except Exception as e:
        if 'conversation' in locals() and conversation and conversation[-1]["role"] == "user":
            conversation.pop()
        bot.reply_to(message, f'Произошла ошибка: {str(e)}')

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)