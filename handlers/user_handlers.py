from telegram import Update
from telegram.ext import ContextTypes
from services.google_ai import GoogleAIService
from database.db_manager import DBManager
from config.config import ADMIN_IDS
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_requests=10, time_window=60):
        self.request_counts = defaultdict(list)
        self.max_requests = max_requests
        self.time_window = time_window

    def is_allowed(self, user_id):
        current_time = time.time()
        user_requests = self.request_counts[user_id]
        # Удаляем устаревшие запросы
        user_requests[:] = [t for t in user_requests if current_time - t < self.time_window]
        
        if len(user_requests) >= self.max_requests:
            return False
        
        user_requests.append(current_time)
        return True

class UserHandler:
    def __init__(self):
        self.ai_service = GoogleAIService()
        self.db = DBManager()
        self.rate_limiter = RateLimiter()

    async def handle_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Проверка rate limit для всех пользователей
        if not self.rate_limiter.is_allowed(user_id):
            await update.message.reply_text("Слишком много запросов. Пожалуйста, подождите.")
            return

        question = update.message.text
        
        # Проверка длины вопроса
        if len(question) > 500:  # Ограничение на длину
            await update.message.reply_text("Вопрос слишком длинный.")
            return
        
        # Фильтрация небезопасного контента
        if self.contains_dangerous_content(question):
            await update.message.reply_text("Содержание вопроса не соответствует правилам.")
            return

        # Проверяем, есть ли ответ в базе данных
        qa = self.db.get_qa(question)
        if qa:
            await update.message.reply_text(qa.answer)
            return

        # Если ответа нет в базе, генерируем новый с помощью AI
        answer = self.ai_service.answer_question(question, None)
        
        # Сохраняем новый вопрос и ответ
        self.db.add_qa(question, answer)
        
        await update.message.reply_text(answer)

    def contains_dangerous_content(self, text):
        # Расширенный список запрещенных слов
        forbidden_words = [
            'hack', 'exploit', 'injection', 'malware', 
            'вирус', 'атака', 'взлом', 'шпионаж', 
            'паролей', 'данные', 'кража', 'trojans'
        ]
        
        # Проверка на наличие запрещенных слов с учетом регистра
        return any(word.lower() in text.lower() for word in forbidden_words)