import random
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
from config.config import POST_TEMPLATES
from services.google_ai import GoogleAIService
from services.scraper import Scraper
from utils.text_processor import clean_text, format_message
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('post_generator.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class PostGenerator:
    # Оставляем только нужные эмодзи и теги
    EMOJI_MAP = {
        'advice': ['💡', '🌈', '🤔', '📝', '🌱'],
        'default': ['📌']
    }

    TAGS_MAP = {
        'advice': ['#совет', '#полезнаяинформация', '#развитие'],
        'default': ['#здоровье']
    }

    def __init__(self, ai_service: GoogleAIService, scraper: Scraper):
        self.ai_service = ai_service
        self.scraper = Scraper()

    def extract_key_points(self, text: str, max_points: int = 4, max_length: int = 150) -> str:
        """
        Извлекает ключевые моменты из текста
        """
        # Предварительная очистка текста
        text = re.sub(r'[\*_`\(\)\{\}]', '', text)
        text = re.sub(r'\*\*', '', text)
        
        # Стратегии извлечения с приоритетом информативности
        strategies = [
            # Прямые списки
            lambda t: re.findall(r'^[-•*]\s*(.{20,'+str(max_length)+'}[.!?])$', t, re.MULTILINE),
            
            # Содержательные предложения
            lambda t: [
                sent.strip() for sent in re.split(r'[.!?]', t) 
                if 40 < len(sent.strip()) < max_length 
                and not sent.strip().startswith(('В', 'А', 'И', 'Но'))
            ]
        ]
        
        # Обработка ключевых моментов
        key_points = []
        for strategy in strategies:
            points = strategy(text)
            points = [
                point.capitalize().strip('.') + '.'
                for point in points 
                if point.strip() and 20 < len(point) < max_length
            ]
            
            if points:
                key_points = points[:max_points]
                break
        
        return '\n• ' + '\n• '.join(key_points) if key_points else 'Ключевые моменты не определены'

    async def generate_ai_post(self, category: str, post_type: str = 'advice') -> Optional[str]:
        """
        Генерирует пост с абсолютно уникальной структурой 
        в двух сценариях: с использованием сайтов и полностью через ИИ
        """
        try:
            # Случайный выбор стратегии генерации
            use_articles = random.choice([True, False])
            
            if use_articles:
                # Попытка найти статьи
                articles = await self.scraper.scrape_by_category(category or random.choice(['здоровье', 'психология', 'питание']))
                
                if articles:
                    source_article = random.choice(articles)
                    logger.info(f"Выбрана статья: {source_article['title']} из {len(articles)} доступных")
                    
                    # Промпт для создания уникальной структуры на основе статьи
                    structure_prompt = f"""
                    Создай абсолютно уникальную структуру поста, основанную на статье:
                    Название: "{source_article['title']}"
                    Источник: {source_article['source_name']}

                    Создай пост для Telegram-канала «Медицинские клиники»,/n
                    специализирующийся на заболевании детей с ДЦП и аутизмом./n
                    Используй информацию из базовых знаний. /n
                    Напиши текст в дружелюбном, открытом и мотивирующем стиле, включая практические советы /n
                    или вдохновляющие факты. В конце обязательно укажите ссылку на источник.

                    Краткое содержание статьи для контекста:
                    {source_article['content'][:500]}
                    """

                    # Генерация уникальной структуры
                    unique_structure = await self.ai_service.generate_post(structure_prompt)

                    # Промпт для наполнения уникальной структуры контентом
                    content_prompt = f"""
                    Наполни следующую уникальную структуру контентом из статьи:

                    Структура: {unique_structure}
                    Исходная статья: "{source_article['title']}"
                    Содержание статьи: {source_article['content'][:700]}

                    Требования:
                    - Полностью соответствовать сгенерированной структуре
                    - Сохранять суть исходной статьи
                    - Максимально креативно интерпретировать информацию
                    """

                    # Генерация контента в уникальной структуре
                    raw_content = await self.ai_service.generate_post(content_prompt)
                    
                    # Метаданные поста
                    post_content = {
                        'source': source_article['source_name'],
                        'source_url': source_article.get('source_url', ''),
                    }
                    
                    disclaimer = "\n\n⚠️ Материал основан на информации из источника. Требует профессиональной консультации."
                else:
                    # Переход к полной AI-генерации, если статьи не найдены
                    use_articles = False
            
            if not use_articles:
                # Полная AI-генерация
                category = category or random.choice(['здоровье', 'психология', 'питание', 'саморазвитие'])
                
                # Промпт для создания полностью уникальной структуры
                structure_prompt = f"""
                Создай абсолютно уникальную структуру поста на тему "{category}".
                Создай пост для Telegram-канала «Медицинские клиники»,/n
                специализирующийся на заболевании детей с ДЦП и аутизмом. /n
                Найди в Интернете актуальную информацию или статьи на тему [заданная тема]./n
                Избегайте демотивирующих или вводящих в заблуждение тем, чтобы не сохранять сомнений в окружающем./n
                Напиши текст в дружелюбном, мотивирующем стиле. Обязательно прикрепите ссылку к статье или источнику.

                Специальные ограничения:
                - Объем: 500-700 символов
                - Целевая аудитория: Родители детей с особенностями развития
                """

                # Генерация уникальной структуры
                unique_structure = await self.ai_service.generate_post(structure_prompt)

                # Промпт для наполнения уникальной структуры контентом
                content_prompt = f"""
                Наполни следующую уникальную структуру содержанием:

                Структура: {unique_structure}
                Тема: {category}

                Требования:
                - Полностью соответствовать сгенерированной структуре
                - Сохранять эмоциональность и креативность
                - Избегать прямых инструкций
                """

                # Генерация контента в уникальной структуре
                raw_content = await self.ai_service.generate_post(content_prompt)
                
                # Метаданные поста
                post_content = {
                    'source': 'Генерация ИИ',
                    'source_url': '',
                }
                
                disclaimer = "\n\n⚠️ Материал сгенерирован ИИ. Требует индивидуального подхода."
            
            # Динамическая генерация эмодзи и тегов
            all_emoji = ['🌈', '💡', '❤️', '🤝', '🌟', '🔍', '📣', '💖', '🌱']
            all_tags = ['#особыедети', '#поддержка', '#развитие', '#любовь', '#забота', '#вместе']
            
            # Финальная сборка поста
            final_post = (
                f"{random.choice(all_emoji)} {raw_content}\n\n"
                f"🌐 Источник: {post_content['source']}\n"
                f"{' '.join(random.sample(all_tags, k=random.randint(1, 3)))}"
                f"{disclaimer}"
            )
            
            return format_message(final_post)
                
        except Exception as e:
            logger.error(f"Ошибка при генерации поста с уникальной структурой: {str(e)}", exc_info=True)
            return None



