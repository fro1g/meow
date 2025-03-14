import re
from typing import List

def clean_text(text: str) -> str:
    # Удаляем разметочные символы и лишние пробелы
    text = re.sub(r'[\*_`<>]', '', text)  # Убрал [] из списка удаляемых символов
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_keywords(text: str, min_length: int = 4) -> List[str]:
    """Извлекает ключевые слова из текста для формирования тегов"""
    # Простой алгоритм извлечения слов длиннее min_length
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set([w for w in words if len(w) >= min_length]))

def format_message(text: str, max_length: int = 4096) -> str:
    # Если текст помещается в лимит, возвращаем как есть
    if len(text) <= max_length:
        return text
    
    # Пытаемся разделить текст на логические части
    parts = text.split('\n\n')
    current_part = ""
    
    for paragraph in parts:
        # Если добавление параграфа не превышает лимит, добавляем
        if len(current_part) + len(paragraph) + 2 <= max_length:
            current_part += paragraph + '\n\n'
        else:
            break  # Прекращаем добавление, когда превышаем лимит
    
    # Обрезаем последний перевод строки
    current_part = current_part.strip()
    
    # Если текст всё ещё слишком длинный, обрезаем до максимальной длины
    if len(current_part) > max_length:
        current_part = current_part[:max_length-50]  # Оставляем место для многоточия
    
    # Убираем многоточие
    result = current_part
    
    return result