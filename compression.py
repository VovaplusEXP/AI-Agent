# compression.py
"""
Модуль интеллектуального сжатия контекста для ReAct-агента.

Основные функции:
- compress_history_smart(): Главная функция сжатия истории
- compress_block_on_overflow(): Сжатие конкретного блока при переполнении
- _summarize_observation(): Сжатие длинных Observation через LLM
- _extract_key_facts(): Извлечение ключевых фактов (URL, файлы, версии)
- _compress_images(): Сжатие изображений в сообщениях
"""

import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def compress_block_on_overflow(
    block_content: str,
    llm,
    max_tokens: int = 2048,
    preserve_images: bool = True
) -> str:
    """
    Сжимает конкретный блок контента при переполнении лимита токенов.
    Вместо дропа всей сессии сжимает только переполняющий блок.
    
    Стратегия:
    1. Если есть изображения - оптимизируем/удаляем избыточные
    2. Если есть длинный текст - сжимаем через LLM
    3. Извлекаем только ключевые факты
    
    Args:
        block_content: Содержимое блока для сжатия
        llm: Экземпляр LLM для суммаризации
        max_tokens: Максимальное количество токенов для блока
        preserve_images: Сохранять ли изображения (если False - удаляются)
        
    Returns:
        Сжатое содержимое блока
    """
    logger.info(f"🗜️ Сжатие переполняющего блока (limit={max_tokens} токенов)...")
    
    original_length = len(block_content)
    
    # === ШАГ 1: Обработка изображений ===
    image_pattern = r'\[(?:PAGE_\d+_)?IMAGE_DATA:[^\]]+\]'
    images = re.findall(image_pattern, block_content)
    
    if images:
        logger.debug(f"Найдено изображений в блоке: {len(images)}")
        
        if preserve_images and len(images) <= 3:
            # Сохраняем до 3 изображений
            text_without_images = re.sub(image_pattern, '', block_content)
            compressed_images = images[:3]
        else:
            # Удаляем все изображения или оставляем 1 если preserve_images
            text_without_images = re.sub(image_pattern, '', block_content)
            compressed_images = images[:1] if preserve_images else []
        
        # Добавляем описание удаленных изображений
        if len(images) > len(compressed_images):
            removed_count = len(images) - len(compressed_images)
            text_without_images += f"\n[Удалено изображений для экономии токенов: {removed_count}]"
    else:
        text_without_images = block_content
        compressed_images = []
    
    # === ШАГ 2: Сжатие текста если он все еще слишком длинный ===
    if len(text_without_images) > max_tokens * 4:  # Приблизительно 4 символа = 1 токен
        logger.debug(f"Сжимаем текст через LLM...")
        
        # Сжимаем через LLM
        compressed_text = _summarize_observation(text_without_images, llm)
    else:
        # Текст уже подходит по размеру
        compressed_text = text_without_images
    
    # === ШАГ 3: Собираем результат ===
    result_parts = [compressed_text]
    
    # Добавляем обратно изображения (если сохраняем)
    if compressed_images:
        result_parts.extend(compressed_images)
    
    result = "\n".join(result_parts)
    
    compression_ratio = (1 - len(result) / original_length) * 100 if original_length > 0 else 0
    logger.info(f"✅ Блок сжат: {original_length} → {len(result)} символов ({compression_ratio:.1f}% сокращение)")
    
    return result


def _compress_images_in_message(content: str, max_images: int = 2) -> str:
    """
    Сжимает количество изображений в сообщении.
    
    Args:
        content: Содержимое сообщения
        max_images: Максимальное количество изображений
        
    Returns:
        Сообщение с ограниченным количеством изображений
    """
    image_pattern = r'\[(?:PAGE_\d+_)?IMAGE_DATA:[^\]]+\]'
    images = re.findall(image_pattern, content)
    
    if len(images) <= max_images:
        return content
    
    # Удаляем все изображения
    text_without_images = re.sub(image_pattern, '', content)
    
    # Добавляем обратно только первые max_images
    kept_images = images[:max_images]
    removed_count = len(images) - max_images
    
    result = text_without_images
    if kept_images:
        result += "\n" + "\n".join(kept_images)
    
    result += f"\n[Удалено изображений для экономии контекста: {removed_count}]"
    
    logger.debug(f"Сжато изображений: {len(images)} → {max_images}")
    
    return result


def compress_history_smart(
    history: List[Dict],
    scratchpad: Dict,
    llm,
    memory_manager,
    current_chat: str
) -> List[Dict]:
    """
    Интеллектуальное сжатие истории без засирания векторной памяти.
    
    Стратегия:
    1. Сжимаем ТОЛЬКО длинные Observation (>1500 символов) через LLM
    2. Сохраняем в L3 память ТОЛЬКО ключевые факты (URL, файлы, версии)
    3. Удаляем повторы и ошибки формата
    
    Args:
        history: История диалога
        scratchpad: Рабочая память (план, цель)
        llm: Экземпляр LLM для суммаризации
        memory_manager: Менеджер памяти
        current_chat: Название текущего чата
        
    Returns:
        Сжатая история
    """
    logger.info("🗜️ Начало интеллектуального сжатия истории...")
    
    # Статистика
    original_count = len(history)
    observations_compressed = 0
    facts_saved = 0
    duplicates_removed = 0
    
    # === ШАГ 1: Сжатие длинных Observation через LLM ===
    compressed_history = []
    
    # Первое сообщение всегда сохраняем (системный промпт)
    if history:
        compressed_history.append(history[0])
    
    for i, msg in enumerate(history[1:], 1):
        content = msg.get('content', '')
        
        # Сжимаем изображения в сообщении если их больше 2
        image_pattern = r'\[(?:PAGE_\d+_)?IMAGE_DATA:[^\]]+\]'
        images = re.findall(image_pattern, content)
        
        if len(images) > 2:
            content = _compress_images_in_message(content, max_images=2)
            logger.debug(f"Сжаты изображения в сообщении #{i}")
        
        # Проверяем длинные Observation
        if content.startswith('Observation:') and len(content) > 1500:
            logger.debug(f"Сжимаем Observation #{i} (длина: {len(content)})")
            
            # Сжимаем через LLM
            summary = _summarize_observation(content, llm)
            
            compressed_history.append({
                "role": msg['role'],
                "content": f"Observation (сжато): {summary}"
            })
            observations_compressed += 1
            
        else:
            # Короткие сообщения оставляем без изменений (но с уже сжатыми изображениями)
            compressed_history.append({
                "role": msg['role'],
                "content": content
            })
    
    logger.info(f"🗜️ Сжато длинных Observation: {observations_compressed}")
    
    # === ШАГ 2: УДАЛЕНО дублирующее сохранение в память ===
    # Факты уже сохраняются в основном цикле выполнения (agent.py lines 458-476)
    # Избегаем дублирования записей в памяти
    
    # === ШАГ 3: Удаление мусора (повторы, ошибки формата) ===
    cleaned_history = []
    seen_hashes = set()
    
    for msg in compressed_history:
        content = msg.get('content', '')
        
        # Пропускаем ошибки формата (уже не актуальны)
        if any(keyword in content for keyword in [
            'ОШИБКА ФОРМАТА',
            'НЕ соответствует формату',
            'ТРЕБУЕМЫЙ ФОРМАТ:',
            'КРИТИЧЕСКАЯ ОШИБКА ФОРМАТА'
        ]):
            duplicates_removed += 1
            logger.debug("🧹 Удалена ошибка формата")
            continue
        
        # Пропускаем пустые Observation
        if content.strip() in ['Observation:', 'Observation: ']:
            duplicates_removed += 1
            logger.debug("🧹 Удалён пустой Observation")
            continue
        
        # Проверка на дубликаты (по первым 200 символам)
        content_hash = content[:200]
        if content_hash in seen_hashes:
            duplicates_removed += 1
            logger.debug("🧹 Удалён дубликат")
            continue
        
        seen_hashes.add(content_hash)
        cleaned_history.append(msg)
    
    logger.info(f"🧹 Удалено дубликатов и мусора: {duplicates_removed}")
    
    # === ФИНАЛ: Статистика ===
    final_count = len(cleaned_history)
    reduction = ((original_count - final_count) / original_count * 100) if original_count > 0 else 0
    
    logger.info(f"✅ Сжатие завершено: {original_count} → {final_count} сообщений ({reduction:.1f}% сокращение)")
    logger.info(f"📊 Итого: {observations_compressed} сжато, {facts_saved} фактов сохранено, {duplicates_removed} удалено")
    
    return cleaned_history


def _summarize_observation(observation_text: str, llm) -> str:
    """
    Сжимает длинный Observation через LLM до 2-3 предложений.
    
    Args:
        observation_text: Полный текст Observation
        llm: Экземпляр LLM
        
    Returns:
        Краткое резюме (2-3 предложения)
    """
    # Берём первые 3000 символов для экономии токенов
    truncated_text = observation_text[:3000]
    
    prompt = f"""Сожми результат до 2-3 предложений, сохранив ТОЛЬКО ключевые факты.

ПОЛНЫЙ РЕЗУЛЬТАТ:
{truncated_text}

КРАТКОЕ РЕЗЮМЕ (2-3 предложения):"""
    
    try:
        messages = [{"role": "user", "content": prompt}]
        output = llm.create_chat_completion(
            messages=messages,
            max_tokens=256,  # Короткое резюме
            temperature=0.2   # Низкая температура = точность
        )
        
        summary = output['choices'][0]['message']['content'].strip()
        logger.debug(f"📝 Резюме создано: {len(observation_text)} → {len(summary)} символов")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Ошибка суммаризации: {e}")
        # Fallback: механическая обрезка
        return observation_text[:500] + "... (обрезано)"


def _extract_key_facts(observation_text: str) -> str:
    """
    Извлекает ТОЛЬКО ключевые факты из Observation.
    
    Ключевые факты:
    - URL (начинаются с http:// или https://)
    - Названия файлов (содержат расширения .py, .txt, .md, и т.д.)
    - Числовые данные (версии, даты)
    - Упоминания технологий (Python, Node.js, и т.д.)
    
    Args:
        observation_text: Текст Observation
        
    Returns:
        Строка с извлечёнными фактами или пустая строка
    """
    facts = []
    
    # === 1. Извлекаем URL ===
    urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', observation_text)
    if urls:
        # Берём максимум 3 URL, удаляем дубликаты
        unique_urls = list(dict.fromkeys(urls[:3]))
        facts.append(f"URL: {', '.join(unique_urls)}")
    
    # === 2. Извлекаем упоминания файлов ===
    files = re.findall(
        r'\b[\w-]+\.(py|txt|md|json|yaml|yml|toml|cfg|ini|sh|bash|js|ts|html|css|sql)\b',
        observation_text,
        re.IGNORECASE
    )
    if files:
        # Максимум 3 файла, уникальные
        unique_files = list(dict.fromkeys(files[:3]))
        facts.append(f"Файлы: {', '.join(unique_files)}")
    
    # === 3. Извлекаем версии ===
    # Паттерн: Python 3.13, version 2.1.0, v3.0, и т.д.
    versions = re.findall(
        r'\b(?:Python|Node|v\.?|version|ver\.?)\s*(\d+\.\d+(?:\.\d+)?)\b',
        observation_text,
        re.IGNORECASE
    )
    if versions:
        unique_versions = list(dict.fromkeys(versions[:2]))
        facts.append(f"Версии: {', '.join(unique_versions)}")
    
    # === 4. Извлекаем упоминания технологий ===
    technologies = re.findall(
        r'\b(Python|JavaScript|TypeScript|Node\.js|React|Vue|Angular|Django|Flask|FastAPI|Docker|Kubernetes|PostgreSQL|MySQL|MongoDB|Redis)\b',
        observation_text,
        re.IGNORECASE
    )
    if technologies:
        unique_tech = list(dict.fromkeys([t.lower() for t in technologies[:3]]))
        facts.append(f"Технологии: {', '.join(unique_tech)}")
    
    # === 5. Извлекаем даты ===
    dates = re.findall(
        r'\b(\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4}|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})\b',
        observation_text,
        re.IGNORECASE
    )
    if dates:
        facts.append(f"Даты: {', '.join(dates[:2])}")
    
    # === 6. Если ничего не нашли - берём первые 150 символов ===
    if not facts:
        # Убираем "Observation: " если есть
        clean_text = observation_text.replace('Observation:', '').strip()
        return clean_text[:150].strip()
    
    # Объединяем факты
    result = " | ".join(facts)
    
    logger.debug(f"🔍 Извлечено фактов: {result[:100]}...")
    
    return result
