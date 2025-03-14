from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config.config import DATABASE_URL
import sqlite3
import re
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Вывод в stdout
        logging.FileHandler('db_debug.log', encoding='utf-8')  # Запись в файл
    ]
)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    source_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50))

class QA(Base):
    __tablename__ = 'qa'
    
    id = Column(Integer, primary_key=True)
    question = Column(Text)
    answer = Column(Text)

class DBManager:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def normalize_text(self, text):
        """
        Нормализация текста для более точного сравнения
        """
        if not text:
            return ""
        
        # Удаление знаков препинания в начале и конце, приведение к нижнему регистру
        text = text.strip('?.,()[] ')
        text = text.lower()
        
        # Удаление знаков препинания внутри текста
        text = re.sub(r'[^\w\s]', '', text)
        
        # Замена похожих букв
        text = text.replace('ё', 'е')
        
        # Удаление лишних пробелов
        text = ' '.join(text.split())
        
        return text
    def print_all_qa_questions(self):
        """
        Вывод всех вопросов в базе данных для отладки
        """
        all_qa_pairs = self.session.query(QA).all()
        logger.debug("=== СПИСОК ВСЕХ ВОПРОСОВ В БД ===")
        for qa in all_qa_pairs:
            logger.debug(f"ID: {qa.id}")
            logger.debug(f"Question: {qa.question}")
            logger.debug("---")

    def calculate_similarity(self, text1, text2):
        """
        Расчет процента совпадения слов между двумя текстами
        с более мягким подходом к сравнению
        """
        if not text1 or not text2:
            return 0
        
        # Нормализация текстов
        norm_text1 = self.normalize_text(text1)
        norm_text2 = self.normalize_text(text2)
        
        logger.debug(f"Normalized input text: {norm_text1}")
        logger.debug(f"Normalized db text:    {norm_text2}")
        
        # Разбиваем на слова
        words1 = norm_text1.split()
        words2 = norm_text2.split()
        
        if not words1 or not words2:
            return 0
        
        # Подсчет общих слов с учетом частичных совпадений
        common_words = 0
        for word1 in words1:
            for word2 in words2:
                # Проверяем, содержит ли одно слово другое (более мягкое сравнение)
                if word1 in word2 or word2 in word1:
                    common_words += 1
                    break
        
        # Процент совпадения
        max_words_length = max(len(words1), len(words2))
        similarity = (common_words / max_words_length) * 100
        
        logger.debug(f"Common words: {common_words}")
        logger.debug(f"Total words: {max_words_length}")
        logger.debug(f"Similarity: {similarity}%")
        
        return similarity
    
    def get_qa(self, question, similarity_threshold=70):
        """
        Поиск вопроса с высокой степенью совпадения
        
        :param question: Входящий вопрос
        :param similarity_threshold: Порог схожести (по умолчанию 75%)
        """
        logger.debug(f"Searching QA for question: {question}")
        
        # Получаем все существующие вопросы
        all_qa_pairs = self.session.query(QA).all()
        
        logger.debug(f"Total QA pairs in database: {len(all_qa_pairs)}")
        
        best_match = None
        best_similarity = 0
        
        # Подробный лог проверки каждой пары
        for qa_pair in all_qa_pairs:
            norm_input = self.normalize_text(question)
            norm_db = self.normalize_text(qa_pair.question)
            
            similarity = self.calculate_similarity(question, qa_pair.question)
            
            logger.debug(f"Checking pair:")
            logger.debug(f"  Input (normalized): {norm_input}")
            logger.debug(f"  DB Question (normalized): {norm_db}")
            logger.debug(f"  Similarity: {similarity}%")
            
            # Более подробное сравнение
            logger.debug(f"  Full input question: {question}")
            logger.debug(f"  Full DB question: {qa_pair.question}")
            
            if similarity > best_similarity and similarity >= similarity_threshold:
                best_match = qa_pair
                best_similarity = similarity
        
        if best_match:
            logger.info(f"Best match found: {best_match.question}")
            logger.info(f"Answer: {best_match.answer}")
            logger.info(f"Similarity: {best_similarity}%")
            return best_match
        
        logger.warning("No matching QA pair found")
        return None
    def manual_similarity_check(self, question):
        """
        Ручная проверка совпадения вопросов
        """
        all_qa_pairs = self.session.query(QA).all()
        
        print("\n=== MANUAL SIMILARITY CHECK ===")
        print(f"Input question: {question}")
        
        for qa_pair in all_qa_pairs:
            similarity = self.calculate_similarity(question, qa_pair.question)
            print(f"\nDB Question: {qa_pair.question}")
            print(f"Similarity: {similarity}%")
            print(f"Normalized Input:  {self.normalize_text(question)}")
            print(f"Normalized DB Q:   {self.normalize_text(qa_pair.question)}")

    def add_qa(self, question, answer):
        """
        Добавление новой пары вопрос-ответ в базу данных
        """
        try:
            # Проверяем, существует ли уже такой вопрос
            existing_qa = self.session.query(QA).filter(QA.question == question).first()
            
            if existing_qa:
                logger.info(f"QA pair already exists. Updating the existing record.")
                existing_qa.answer = answer
            else:
                # Создаем новую запись, если вопрос не существует
                new_qa = QA(question=question, answer=answer)
                self.session.add(new_qa)
            
            # Фиксируем изменения в базе данных
            self.session.commit()
            logger.info(f"Successfully added/updated QA pair: {question}")
            return True
        
        except Exception as e:
            # Откатываем транзакцию в случае ошибки
            self.session.rollback()
            logger.error(f"Error adding QA pair: {e}")
            return False

    def close_connection(self):
        """
        Закрытие соединения с базой данных
        """
        if self.session:
            self.session.close()
            logger.info("Database connection closed.")

    def get_all_qa(self):
        """
        Получение всех вопросов из базы данных для отладки
        """
        all_qa_pairs = self.session.query(QA).all()
        logger.debug("=== ALL QA PAIRS ===")
        for qa in all_qa_pairs:
            logger.debug(f"ID: {qa.id}")
            logger.debug(f"Question: {qa.question}")
            logger.debug(f"Answer: {qa.answer}")
            logger.debug("---")