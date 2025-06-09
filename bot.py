import telebot
import requests
import yadisk
import logging
import os
from datetime import datetime
import time
from dotenv import load_dotenv

yadisktoken = os.getenv("YADISK_TOKEN")
tgbottoken = os.getenv("TELEBOT_TOKEN")
yacloudtoken = os.getenv("YACLOUD_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot_errors.log'
)
logger = logging.getLogger(__name__)

try:
    disk = yadisk.YaDisk(token=yadisktoken)
    if not disk.check_token():
        logger.error("Недействительный токен Яндекс.Диска")
        disk = None  
except Exception as e:
    logger.error(f"Ошибка при подключении к Яндекс.Диску: {e}")
    disk = None

class Message:    
    def __init__(self, userText):
        self.userText = userText    
    def GetMessage(self):
        return self.userText
    def SetMessage(self, text):
        self.userText = text   

bot = telebot.TeleBot(tgbottoken)
question = Message("")
answer = Message("")
localReviewsName = "reviews.txt"

statringText = '''
Добро пожаловать в HR-переводчик Инфо Мотя  🇷🇺✨  

❌«Планируем демо для стейкхолдеров» — знакомо? 
Наш бот превращает такие фразы в:  
✅«Покажем проект заинтересованным сторонам» — коротко и ясно.  

Как это поможет вам?
💫 Упрощение коммуникации— меньше недопонимания в чатах,  
💫 Снижение стресса— особенно для новичков и возрастных сотрудников
💫 Увеличение откликов и просмотров на вакансиях от соискателей
💫 Чистота языка — без слепого копирования англицизмов.  

Примеры работы 🔍:  
• «Заапрувьте бюджет»→ «Подтвердите бюджет» 
• «Кандидат на рекрутере» → «Кандидат в поиске»

Давайте говорить на одном языке — без барьеров! 🚀  

✨Попробуйте прямо сейчас — напишите любой термин и получите «перевод» с комментарием!✨
'''
helpingText = '''
/help - Помощь с функционалом и командами
/translate - Обяснить значение слова
/start - Начать диалог
/about - Узнать историю создания бота
/review - Оставить отзыв
'''
aboutText = '''
Как появилась идея?

Мы спросили HR-специалистов, что чаще всего мешает пониманию. Ответ оказался простым: англицизмы и непонятные слова 🤔
Это мешало новичкам адаптироваться и даже отпугивало кандидатов. Идея создать «переводчика» сразу нашла поддержку — больше 30% опрошенных поддержали её с энтузиазмом 🙌
Так родилась Инфо Мотя — простой и дружелюбный помощник для лёгких HR-коммуникаций ✨
'''

systemPromt = "Ты - бот для объяснения сложных слов, англицизмов и подросткового/молодежного сленга, в особенности в HR сфере. Объясни значение слова или фразы-англицизма так, чтобы было понятно человеку старшего возраста. Используй простые аналогии из советского/русского быта, если возможно. Приведи 1-2 примера употребления. Если слово имеет несколько значений, укажи основные. Ответ должен быть доброжелательным, без сложных терминов, максимум на 5-7 предложений. Не переходи на ты, ипользуй вежливое общение."

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
headers = {
    "Content-Type" : "application/json",
    "Authorization" : f"Api-Key {yacloudtoken}"
}

def Response():
    promt = {
    "modelUri" : "gpt://b1g2ni26cv1m5sa1fkvv/yandexgpt-lite",
    "completionOptions" : {
        "stream" : False,
        "temperature" : 0.6,
        "maxTokens" : "2000"
    },

    "messages" : [
        {
            "role" : "system",
            "text" : f"{systemPromt}"
        },
        {
            "role" : "user",
            "text" : f"{question.GetMessage()}"
        }        
    ]
    }
    try:
        response = requests.post(url, headers=headers, json=promt)
        if response and response.status_code == 200:
            return response.json()['result']['alternatives'][0]['message']['text']
        else:
            logger.error(f"Ошибка API: {response.status_code if response else 'No response'}")
            return "Извините, сервис временно недоступен. Попробуйте позже."
    except Exception as e:
        logger.error(f"Ошибка в Response: {e}")
        return "Произошла ошибка при обработке запроса."

@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        bot.send_message(message.chat.id, statringText)
    except Exception as e:
        logger.error(f"Ошибка в handle_start: {e}")

@bot.message_handler(commands=['help'])
def handle_help(message):
    try:
        bot.send_message(message.chat.id, helpingText)
    except Exception as e:
        logger.error(f"Ошибка в handle_help: {e}")

@bot.message_handler(commands=['about'])
def handle_about(message):
    try:
        bot.send_message(message.chat.id, aboutText)
    except Exception as e:
        logger.error(f"Ошибка в handle_about: {e}")

def WriteReview(review):    
    try:
        if not review or len(review.strip()) < 3:  # Проверка на пустой отзыв
            return False        
        with open(localReviewsName, "a", encoding="utf-8") as reviewsDoc:
            reviewsDoc.write(review[8:] + '\n' if review.startswith('/review ') else review + '\n')     
        if disk:
            try:                
                disk.upload(localReviewsName, "/tgBotMotya/reviews.txt", overwrite=True)
            except Exception as e:
                logger.warning(f"Не удалось загрузить на Яндекс.Диск: {e}")        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка в WriteReview: {e}")
        return False

@bot.message_handler(commands=['review'])
def handle_review(message):
    try:
        text = message.text
        if text != "/review":
            success = WriteReview(text)
            reply = "Ваш отзыв принят! Большое спасибо что помогаете нашему сервису" if success else "Не удалось сохранить отзыв"
            bot.send_message(message.chat.id, reply)
        else:
            msg = bot.send_message(message.chat.id, "Введите сообщение для отзыва")
            bot.register_next_step_handler(msg, process_review_step)
    except Exception as e:
        logger.error(f"Ошибка в handle_review: {e}")

def process_review_step(message):
    try:
        success = WriteReview(" " * 8 + message.text)
        reply = "Ваш отзыв принят! Большое спасибо что помогаете нашему сервису" if success else "Не удалось сохранить отзыв"
        bot.send_message(message.chat.id, reply)
    except Exception as e:
        logger.error(f"Ошибка в process_review_step: {e}")

@bot.message_handler(commands=['translate'])
def handle_translate(message):
    try:
        text = message.text
        if text != "/translate":
            question.SetMessage(text[10:] if text.startswith('/translate') else text)
            response = Response()
            bot.send_message(message.chat.id, response)
        else:
            msg = bot.send_message(message.chat.id, "Введите слово/фразу для пояснения")
            bot.register_next_step_handler(msg, process_translate_step)
    except Exception as e:
        logger.error(f"Ошибка в handle_translate: {e}")

def process_translate_step(message):
    try:
        question.SetMessage("Переведи " + message.text)
        response = Response()
        bot.send_message(message.chat.id, response)
    except Exception as e:
        logger.error(f"Ошибка в process_translate_step: {e}")

@bot.message_handler()
def handle_all_messages(message):
    try:
        question.SetMessage(message.text)
        response = Response()
        bot.send_message(message.chat.id, response)
    except Exception as e:
        logger.error(f"Ошибка в handle_all_messages: {e}")

def main():
    while True:
        try:
            logger.info("Запуск бота...")
            bot.delete_webhook()
            bot.polling(non_stop=True, skip_pending=True)
        except Exception as e:
            logger.critical(f"Критическая ошибка: {e}")
            time.sleep(3)

if __name__ == "__main__":    
    if not os.path.exists(localReviewsName):
        try:
            with open(localReviewsName, 'w', encoding='utf-8') as f:
                f.write('')
        except Exception as e:
            logger.error(f"Не удалось создать файл отзывов: {e}")
    
    main()
