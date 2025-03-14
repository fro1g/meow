import asyncio
import google.generativeai as genai
from config.config import GOOGLE_AI_API_KEY

class GoogleAIService:
    def __init__(self):
        genai.configure(api_key=GOOGLE_AI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    async def generate_post(self, scraped_data):
        prompt = f"""
        На основе следующей информации создайте интересный пост для Telegram:
        {scraped_data}
        
        Пост должен быть информативным, легко читаемым и привлекательным для аудитории.
        """
        # Запускаем синхронный метод в отдельном потоке
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content(prompt)
        )
        return result.text

    def _is_toxic_content(self, text):
        """
        Check if the content contains toxic or inappropriate words.
        
        Args:
            text (str): The text to check for toxicity.
        
        Returns:
            bool: True if content is toxic, False otherwise.
        """
        toxic_keywords = [
            'hack', 'exploit', 'injection', 'malware', 
            'вирус', 'атака', 'взлом', 'шпионаж', 
            'паролей', 'данные', 'кража', 'trojans',
            'насилие', 'оскорбление', 'дискриминация'
        ]
        
        return any(keyword.lower() in text.lower() for keyword in toxic_keywords)

    def _count_tokens(self, text):
        """
        Count the number of tokens in the given text.
        
        Args:
            text (str): The text to count tokens for.
        
        Returns:
            int: Number of tokens in the text.
        """
        # This is a simple token estimation method
        # In a real-world scenario, you might want to use the actual tokenizer from the AI library
        return len(text.split())

    def _generate_answer(self, question):
        """
        Generate an AI-powered answer for the given question.
        
        Args:
            question (str): The question to answer.
        
        Returns:
            str: The generated answer.
        """
        try:
            result = self.model.generate_content(question)
            return result.text
        except Exception as e:
            return f"Извините, произошла ошибка при генерации ответа: {str(e)}"

    def answer_question(self, question, context):
        """
        Main method to answer questions with safety checks.
        
        Args:
            question (str): The question to answer.
            context (str, optional): Additional context for the question.
        
        Returns:
            str: The generated answer or an error message.
        """
        # Проверка токсичности контента перед генерацией
        if self._is_toxic_content(question):
            return "Извините, я не могу обработать этот запрос."
        
        MAX_TOKENS = 500
        # Ограничение количества токенов
        if self._count_tokens(question) > MAX_TOKENS:
            return "Слишком длинный запрос."
        
        # Основная логика генерации ответа
        return self._generate_answer(question)