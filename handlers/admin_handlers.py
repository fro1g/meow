from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.google_ai import GoogleAIService
from services.scraper import Scraper
from database.db_manager import DBManager
from services.post_generator import PostGenerator
import asyncio
import logging

logger = logging.getLogger(__name__)

class AdminHandler:
    def __init__(self, ai_service: GoogleAIService, scraper: Scraper):
        self.ai_service = ai_service
        self.scraper = scraper
        self.post_generator = PostGenerator(self.ai_service, self.scraper)
        self.CHANNEL_ID = "@neurolife_clinic"  # ID канала для публикации

    async def generate_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Генерация поста с помощью AI
        """
        if update.effective_user.id not in context.bot_data.get('admin_ids', []):
            return

        status_message = await update.message.reply_text("🔄 Генерирую пост...")

        try:
            post = await self.post_generator.generate_ai_post(
                category="parenting",
                post_type="advice"
            )

            if post:
                keyboard = [[
                    InlineKeyboardButton("Опубликовать", callback_data="publish_ai"),
                    InlineKeyboardButton("Редактировать", callback_data="edit_ai")
                ]]
                
                context.user_data['current_post'] = post  # Сохраняем текущий пост

                await update.message.reply_text(
                    f"🤖 Новый пост:\n\n{post}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                await status_message.delete()
            else:
                await status_message.edit_text("❌ Не удалось сгенерировать пост")

        except Exception as e:
            logger.error(f"Ошибка генерации: {str(e)}", exc_info=True)
            await status_message.edit_text("❌ Произошла ошибка при генерации поста")
            
    async def edit_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработка редактирования поста
        """
        query = update.callback_query
        await query.answer()

        # Получаем текущий пост из user_data
        current_post = context.user_data.get('current_post')
        
        if current_post:
            # Устанавливаем режим редактирования
            context.user_data['editing_post'] = True
            
            # Отправляем текущий пост как сообщение, которое можно редактировать
            await query.message.reply_text(
                f"✏️ Отредактируйте пост ниже, просто отправив новое сообщение:\n\n{current_post}"
            )
        else:
            await query.message.reply_text("❌ Нет поста для редактирования")
            
    async def handle_edited_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработка отредактированного поста
        """
        if context.user_data.get('editing_post'):
            edited_post = update.message.text

            # Создаем новую клавиатуру
            keyboard = [[
                InlineKeyboardButton("Опубликовать", callback_data="publish_edited"),
                InlineKeyboardButton("Редактировать", callback_data="edit_again")
            ]]

            await update.message.reply_text(
                f"🖊️ Отредактированный пост:\n\n{edited_post}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            context.user_data['current_post'] = edited_post
            context.user_data['editing_post'] = False
        
    async def publish_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Публикация поста в канал
        """
        query = update.callback_query
        await query.answer()

        current_post = context.user_data.get('current_post')
        
        if current_post:
            try:
                # Публикация поста в канал
                await context.bot.send_message(
                    chat_id=self.CHANNEL_ID, 
                    text=current_post
                )
                await query.message.reply_text("✅ Пост опубликован в канале")
                
                # Очищаем текущий пост
                context.user_data['current_post'] = None
            except Exception as e:
                logger.error(f"Ошибка публикации: {str(e)}")
                await query.message.reply_text("❌ Не удалось опубликовать пост")
        else:
            await query.message.reply_text("❌ Нет поста для публикации")