"""
Модуль парсеров для обработки ответов LLM.

v3.0.0: Поддержка флагового формата для решения проблем с JSON-escaping
"""

import json
import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def parse_flagged_response(response: str) -> Dict:
    """
    Парсинг ответа LLM в новом флаговом формате v3.0.0.
    
    Формат:
        <THOUGHT>
        рассуждение агента
        <TOOL>
        имя_инструмента
        <PARAMS>
        {"param": "value"}
        <CONTENT>
        сырой контент (RAW, любые escapes!)
        <END>
    
    Args:
        response: Сырой ответ от LLM
        
    Returns:
        {
            'thought': str,
            'tool_name': str,
            'parameters': dict,
            'content': str  # может быть пустым, если нет блока <CONTENT>
        }
        
    Raises:
        ValueError: Если формат невалиден или отсутствуют обязательные поля
    """
    
    # Паттерны для извлечения блоков
    thought_match = re.search(
        r'<THOUGHT>\s*(.+?)\s*<TOOL>', 
        response, 
        re.DOTALL | re.IGNORECASE
    )
    
    tool_match = re.search(
        r'<TOOL>\s*([^<]+?)\s*<', 
        response, 
        re.DOTALL | re.IGNORECASE
    )
    
    params_match = re.search(
        r'<PARAMS>\s*(\{.*?\})\s*(?:</PARAMS>|</END>|<END>|<CONTENT>)', 
        response, 
        re.DOTALL | re.IGNORECASE
    )
    
    content_match = re.search(
        r'<CONTENT>\s*(.+?)\s*<END>', 
        response, 
        re.DOTALL | re.IGNORECASE
    )
    
    # Валидация: tool обязателен
    if not tool_match:
        raise ValueError(
            "Неполная структура: отсутствует обязательный флаг <TOOL>"
        )
    
    # Извлечение tool_name
    tool_name = tool_match.group(1).strip()
    
    # ВОССТАНОВЛЕНИЕ: Если <THOUGHT> отсутствует, пытаемся извлечь из текста до <TOOL>
    if not thought_match:
        tool_pos = response.find('<TOOL>')
        if tool_pos > 0:
            pre_tool_text = response[:tool_pos].strip()
            if pre_tool_text:
                logger.warning(f"⚠️ <THOUGHT> тег отсутствует, восстанавливаем из текста перед <TOOL>: '{pre_tool_text[:50]}...'")
                thought = pre_tool_text
            else:
                logger.warning(f"⚠️ <THOUGHT> тег отсутствует и нет текста перед <TOOL>, используем заглушку")
                thought = f"[Рассуждение отсутствует, используется инструмент {tool_name}]"
        else:
            thought = f"[Рассуждение отсутствует, используется инструмент {tool_name}]"
    else:
        thought = thought_match.group(1).strip()
    
    # Параметры (опционально, по умолчанию {})
    parameters = {}
    if params_match:
        try:
            parameters = json.loads(params_match.group(1))
        except json.JSONDecodeError as e:
            raise ValueError(f"Невалидный JSON в <PARAMS>: {e}")
    else:
        logger.warning(f"<PARAMS> блок не найден для инструмента '{tool_name}', параметры будут пустыми")
    
    # Контент (опционально)
    content = ""
    if content_match:
        content = content_match.group(1).strip()
    
    # Если есть content, добавляем его в parameters
    if content:
        # Если в parameters уже есть 'content', это ошибка
        if 'content' in parameters:
            logger.warning("Content указан и в <PARAMS>, и в <CONTENT>. Используем <CONTENT>.")
        parameters['content'] = content
    
    logger.debug(f"✅ Флаговый формат распознан: tool={tool_name}, parameters={parameters}")
    
    return {
        'thought': thought,
        'tool_name': tool_name,
        'parameters': parameters
    }


def parse_json_response(raw_response: str) -> Dict:
    """
    Парсинг ответа в старом JSON-формате v2.1.2 (с двухшаговой очисткой).
    
    LEGACY: Оставлен для обратной совместимости.
    
    Args:
        raw_response: Сырой ответ от LLM
        
    Returns:
        {
            'thought': str,
            'tool_name': str,
            'parameters': dict
        }
        
    Raises:
        json.JSONDecodeError, ValueError: При ошибках парсинга
    """
    
    logger.debug("Парсинг в JSON-формате (legacy v2.1.2)")
    
    # ЭТАП 1: Очистка невалидных escape-последовательностей
    def fix_content_escaping(match):
        content = match.group(1)
        # Удаляем невалидные escapes, оставляя только валидные
        content = re.sub(r'\\(?!["\\/bfnrtu])', '', content)
        return f'"content": "{content}"'
    
    # Захватываем содержимое поля content до первой неэкранированной кавычки
    pattern = r'"content":\s*"((?:[^"\\]|\\.)*)"'
    cleaned_response = re.sub(
        pattern,
        fix_content_escaping,
        raw_response,
        flags=re.DOTALL
    )
    
    # ЭТАП 2: Попытки найти JSON
    response_json = None
    
    # Способ 1: Проверяем наличие markdown-блока с json
    json_markdown_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned_response, re.DOTALL)
    if json_markdown_match:
        try:
            response_json = json.loads(json_markdown_match.group(1))
            logger.debug("JSON найден в markdown-блоке")
        except json.JSONDecodeError as e:
            logger.debug(f"Ошибка парсинга JSON из markdown: {e}")
    
    # Способ 2: Ищем первый валидный JSON-объект в тексте с балансом скобок
    if not response_json:
        start_idx = cleaned_response.find('{')
        if start_idx != -1:
            brace_count = 0
            for i, char in enumerate(cleaned_response[start_idx:], start=start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = cleaned_response[start_idx:i+1]
                        try:
                            response_json = json.loads(json_str)
                            logger.debug("JSON найден через баланс скобок")
                            break
                        except json.JSONDecodeError as e:
                            logger.debug(f"Ошибка парсинга JSON через баланс: {e}")
                            break
    
    # Способ 3: Попытка распарсить весь ответ как JSON
    if not response_json:
        try:
            response_json = json.loads(cleaned_response)
            logger.debug("Весь ответ является валидным JSON")
        except json.JSONDecodeError as e:
            logger.debug(f"Ошибка парсинга всего ответа: {e}")
    
    # Если ничего не найдено - ошибка
    if not response_json:
        logger.error(f"Не удалось найти валидный JSON. Сырой ответ: {raw_response[:500]}")
        raise json.JSONDecodeError("No valid JSON found in response", raw_response, 0)
    
    # Извлекаем данные
    thought = response_json.get("thought", "")
    action = response_json.get("action", {})
    tool_name = action.get("tool_name")
    parameters = action.get("parameters", {})
    
    # Валидация структуры
    if not thought or not action or not tool_name:
        logger.warning(f"Неполная структура JSON: thought={bool(thought)}, action={bool(action)}, tool_name={bool(tool_name)}")
        raise ValueError(f"Неполная структура JSON: thought={bool(thought)}, action={bool(action)}, tool_name={bool(tool_name)}")
    
    logger.debug(f"✅ JSON формат распознан: tool={tool_name}")
    
    return {
        'thought': thought,
        'tool_name': tool_name,
        'parameters': parameters
    }


def parse_response_with_fallback(response: str) -> Dict:
    """
    Парсер ответов LLM в флаговом формате v3.0.0+.
    
    v3.1.0: JSON fallback УДАЛЁН для устранения путаницы модели.
    Модель ОБЯЗАНА использовать только флаговый формат.
    
    Args:
        response: Сырой ответ от LLM
        
    Returns:
        {
            'thought': str,
            'tool_name': str,
            'parameters': dict
        }
        
    Raises:
        ValueError: Если формат ответа не соответствует флаговому
    """
    
    try:
        result = parse_flagged_response(response)
        logger.info("✅ Использован флаговый формат v3.0.0")
        return result
    except (ValueError, AttributeError) as e:
        logger.error(f"❌ Ответ не в флаговом формате: {e}")
        logger.error(f"Сырой ответ (первые 300 символов): {response[:300]}")
        # v3.1.0: Не пытаемся парсить JSON - требуем строгого соблюдения формата
        raise ValueError(
            "ФОРМАТ НЕВЕРНЫЙ! Используй СТРОГО: <THOUGHT>...<TOOL>...<PARAMS>{...}<END>"
        ) from e
