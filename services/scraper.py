import aiohttp
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict, Optional, Union
from datetime import datetime
import logging
from config.config import MedicalSource, MEDICAL_SOURCES
import socket
from urllib.parse import urlparse
from functools import lru_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Scraper:
    def __init__(self, timeout: int = 60, max_retries: int = 3):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries

    @lru_cache(maxsize=100)
    async def check_host_availability(self, url: str) -> bool:
        """Кэшированная проверка доступности хоста"""
        try:
            parsed_url = urlparse(url)
            host = parsed_url.netloc
            socket.gethostbyname(host)
            return True
        except socket.gaierror:
            logger.error(f"Хост {host} недоступен")
            return False

    async def scrape_by_category(self, category: str, language: str = 'ru') -> List[Dict]:
        """
        Скрапит контент из источников, соответствующих указанной категории и языку
        
        Args:
            category (str): Категория для фильтрации источников
            language (str): Язык контента (по умолчанию 'ru')
            
        Returns:
            List[Dict]: Список словарей с контентом из подходящих источников
        """
        try:
            logger.info(f"Начало скрапинга для категории '{category}' на языке '{language}'")
            
            # Фильтруем источники по категории и языку
            filtered_sources = [
                source for source in MEDICAL_SOURCES
                if (category in source.category or any(cat in category for cat in source.category))
                and source.language == language
            ]
            
            if not filtered_sources:
                logger.warning(f"Не найдены источники для категории '{category}' на языке '{language}'")
                return []
            
            logger.info(f"Найдено {len(filtered_sources)} подходящих источников")
            
            # Создаём задачи для асинхронного скрапинга
            tasks = [self.scrape_with_retry(source) for source in filtered_sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Фильтруем успешные результаты
            valid_results = [
                result for result in results
                if isinstance(result, dict) and result is not None
            ]
            
            logger.info(f"Успешно получено {len(valid_results)} результатов из {len(filtered_sources)} источников")
            
            return valid_results
            
        except Exception as e:
            logger.error(f"Ошибка при скрапинге категории {category}: {str(e)}", exc_info=True)
            return []


    def _extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """Улучшенное извлечение ключевых слов"""
        try:
            words = content.lower().split()
            # Фильтрация стоп-слов и коротких слов
            stop_words = {'это', 'что', 'как', 'для', 'или', 'но', 'и'}
            keywords = set(word for word in words if len(word) > 3 and word not in stop_words)
            return list(keywords)[:max_keywords]
        except Exception as e:
            logger.warning(f"Ошибка при извлечении ключевых слов: {e}")
            return []

    async def find_content(self, soup: BeautifulSoup, selectors: Dict[str, Union[str, List[str]]]) -> Dict[str, Optional[str]]:
        result = {'title': None, 'content': None, 'article': None}
        
        for field, field_selectors in selectors.items():
            if isinstance(field_selectors, str):
                field_selectors = [field_selectors]
            
            for selector in field_selectors:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text and len(text) > 50:
                            result[field] = text
                            logger.info(f"Найден контент для поля {field} длиной {len(text)} символов")
                            break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске {field} с селектором {selector}: {str(e)}")
        
        # Логируем результаты поиска
        for field, value in result.items():
            if value is None:
                logger.warning(f"Не найден контент для поля {field}")
            else:
                logger.info(f"Успешно найден контент для поля {field}")
        
        return result

    async def scrape_with_retry(self, source: MedicalSource, max_retries: int = 3) -> Optional[Dict]:
        """Скрапит медицинский контент с механизмом повторных попыток"""
        logger.info(f"Начало скрапинга источника {source.name} ({source.url})")
        
        # Проверяем доступность хоста перед скрапингом
        if not await self.check_host_availability(source.url):
            logger.error(f"Хост недоступен для {source.url}")
            return None

        for attempt in range(max_retries):
            try:
                result = await self.scrape_medical_source(source)
                
                if result:
                    logger.info(f"Успешный скрапинг для {source.name}: {result.get('title', 'Без заголовка')}")
                    return result
                else:
                    logger.warning(f"Скрапинг не удался для {source.name} (попытка {attempt + 1})")
                
                if attempt < max_retries - 1:
                    delay = min(2 ** attempt, 10)
                    logger.warning(f"Попытка {attempt + 1} не удалась для {source.url}. Ожидание {delay} секунд.")
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Попытка {attempt + 1} не удалась для {source.url}: {str(e)}", exc_info=True)
                if attempt < max_retries - 1:
                    delay = min(2 ** attempt, 10)
                    await asyncio.sleep(delay)
        
        logger.error(f"Все попытки скрапинга для {source.url} завершились неудачно")
        return None

    async def scrape_medical_source(self, source: MedicalSource) -> Optional[Dict]:
        """Безопаснее и информативнее скрапит источник"""
        try:
            if not await self.check_host_availability(source.url):
                return None

            ssl_context = source.ssl_context or (False if not source.verify_ssl else None)
            connector = aiohttp.TCPConnector(
                ssl=ssl_context, 
                force_close=True, 
                enable_cleanup_closed=True, 
                limit_per_host=1
            )

            async with aiohttp.ClientSession(
                headers={**self.headers, **(source.headers or {})},
                timeout=self.timeout,
                connector=connector
            ) as session:
                async with session.get(source.url, allow_redirects=True) as response:
                    if response.status not in {200, 302}:
                        logger.error(f"Статус {response.status} для {source.url}")
                        return None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    content_data = await self.find_content(soup, source.selectors)
                    
                    if not all([content_data['title'], content_data['content']]):
                        logger.warning(f"Неполные данные для {source.url}")
                        return None
                    
                    return {
                        'title': content_data['title'],
                        'content': content_data['content'],
                        'keywords': self._extract_keywords(content_data['content']),
                        'source_name': source.name,
                        'source_url': source.url,
                        'category': source.category,
                        'language': source.language,
                        'timestamp': datetime.now().isoformat()
                    }
                        
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при скрапинге {source.url}: {e}")
            return None


    # Добавляем метод scrape_page_articles
    async def scrape_page_articles(self, url: str, max_articles: int = 10) -> List[Dict]:
        """Скрапит Multiple статей с указанной страницы"""
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Не удалось получить страницу {url}. Статус: {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    articles = []
                    
                    # Расширенный список селекторов для поиска статей
                    article_selectors = [
                        '.post', 'article', '.news-item', '.article-item', 
                        '.blog-post', '.content-block', '.entry', 
                        '.article', '.post-item', '.card'
                    ]
                    
                    for selector in article_selectors:
                        items = soup.select(selector)
                        if items:
                            for item in items[:max_articles]:
                                try:
                                    # Более гибкий поиск заголовка и контента
                                    title = (
                                        item.select_one('h1, h2, h3, .title, .headline, a.title') or
                                        item.select_one('.post-title, .entry-title')
                                    )
                                    
                                    content = (
                                        item.select_one('p, .content, .text, .excerpt, .summary') or
                                        item.select_one('.post-content, .entry-content')
                                    )
                                    
                                    # Поиск ссылки на полную статью
                                    link = (
                                        item.select_one('a.read-more, a.more-link, a.post-link') or
                                        (title.find('a') if title and title.find('a') else None)
                                    )
                                    
                                    if title and content:
                                        article_data = {
                                            'title': title.get_text(strip=True),
                                            'content': content.get_text(strip=True)[:500],  # Ограничиваем длину контента
                                            'url': link['href'] if link and link.has_attr('href') else url
                                        }
                                        
                                        # Добавляем дополнительные метаданные, если возможно
                                        date = item.select_one('time, .date, .post-date')
                                        if date:
                                            article_data['date'] = date.get_text(strip=True)
                                        
                                        articles.append(article_data)
                                        
                                        if len(articles) >= max_articles:
                                            break
                                except Exception as e:
                                    logger.error(f"Ошибка при парсинге статьи: {str(e)}")
                                    continue
                            
                            break  # Если нашли статьи по одному из селекторов, прекращаем поиск
                    
                    logger.info(f"Найдено {len(articles)} статей на странице {url}")
                    return articles
                    
        except Exception as e:
            logger.error(f"Ошибка при скрапинге страницы {url}: {str(e)}")
            return []