import asyncio
import sys
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config.config import TELEGRAM_TOKEN, ADMIN_IDS
from handlers.admin_handlers import AdminHandler
from handlers.user_handlers import UserHandler
from services.google_ai import GoogleAIService
from services.scraper import Scraper
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Настройка расширенного логирования
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Файловый логер с ротацией
    file_handler = RotatingFileHandler(
        'bot.log', 
        maxBytes=10*1024*1024,  # 10 МБ
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)

    # Логирование ошибок
    def log_exceptions(exc_type, exc_value, exc_traceback):
        logger.error(
            "Uncaught exception", 
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = log_exceptions

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.application = None
        self.should_stop = False
        # Initialize services that will be passed to handlers
        self.ai_service = GoogleAIService()
        self.scraper = Scraper()

    async def setup(self):
        """Initialize bot and handlers"""
        # Create application
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Initialize handlers with required services
        admin_handler = AdminHandler(
            ai_service=self.ai_service,
            scraper=self.scraper
        )
        user_handler = UserHandler()

        # Register command handlers
        self.application.add_handler(CommandHandler("generate", admin_handler.generate_post))
        
        # Register callback query handlers
        self.application.add_handler(CallbackQueryHandler(admin_handler.edit_post, pattern="^edit_"))
        self.application.add_handler(CallbackQueryHandler(admin_handler.publish_post, pattern="^publish_"))
        
        # Register message handlers
        self.application.add_handler(MessageHandler(
            filters.TEXT & filters.User(user_id=ADMIN_IDS) & ~filters.COMMAND,
            admin_handler.handle_edited_post
        ))
        
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            user_handler.handle_question
        ))

        # Store admin IDs in bot data
        self.application.bot_data['admin_ids'] = ADMIN_IDS

    # Остальной код остается без изменений
    async def start(self):
        """Start the bot"""
        logger.info('Starting bot...')
        await self.setup()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        
        try:
            # Keep the bot running until stop signal
            while not self.should_stop:
                await asyncio.sleep(1)
        finally:
            logger.info('Stopping bot...')
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

def run_bot():
    """Run the bot with proper async handling"""
    if sys.platform == 'win32':
        # Set the event loop policy for Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    bot = TelegramBot()
    
    try:
        # Create and run event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.should_stop = True
        # Give the bot a chance to shutdown cleanly
        if loop.is_running():
            loop.run_until_complete(asyncio.sleep(1))
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Clean up
        loop.close()

if __name__ == '__main__':
    run_bot()