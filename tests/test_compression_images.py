"""
Тесты для системы сжатия контекста с поддержкой изображений.
"""
import sys
from pathlib import Path

# Добавляем родительскую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from compression import compress_block_on_overflow, _compress_images_in_message


class MockLLM:
    """Мок LLM для тестирования."""
    
    def create_chat_completion(self, messages, max_tokens=256, temperature=0.2):
        """Мок генерации резюме."""
        content = messages[0]['content']
        # Возвращаем короткое резюме
        summary = "Краткое резюме: " + content[:100] + "..."
        return {
            'choices': [{
                'message': {'content': summary}
            }]
        }


def test_compress_images_in_message():
    """Тест сжатия количества изображений в сообщении."""
    print("\n=== Тест сжатия изображений в сообщении ===")
    
    # Сообщение с 5 изображениями
    content = """
    Text before images
    [IMAGE_DATA:base64data1]
    [IMAGE_DATA:base64data2]
    [PAGE_3_IMAGE_DATA:base64data3]
    [IMAGE_DATA:base64data4]
    [IMAGE_DATA:base64data5]
    Text after images
    """
    
    # Сжимаем до 2 изображений
    compressed = _compress_images_in_message(content, max_images=2)
    
    # Проверяем количество изображений
    import re
    image_pattern = r'\[(?:PAGE_\d+_)?IMAGE_DATA:[^\]]+\]'
    images_after = re.findall(image_pattern, compressed)
    
    print(f"Изображений до сжатия: 5")
    print(f"Изображений после сжатия: {len(images_after)}")
    
    if len(images_after) == 2:
        print("✅ Изображения сжаты корректно до 2")
    else:
        print(f"❌ Ожидалось 2 изображения, получено {len(images_after)}")
    
    # Проверяем наличие уведомления об удалении
    if "Удалено изображений" in compressed:
        print("✅ Уведомление об удалении присутствует")
    else:
        print("❌ Уведомление об удалении отсутствует")


def test_compress_block_on_overflow():
    """Тест сжатия блока при переполнении."""
    print("\n=== Тест сжатия блока при переполнении ===")
    
    llm = MockLLM()
    
    # Создаем большой блок текста с изображениями
    large_text = "Very long observation text. " * 100  # ~2800 символов
    content = f"""
    Observation: {large_text}
    [IMAGE_DATA:verylongbase64string1]
    [IMAGE_DATA:verylongbase64string2]
    [IMAGE_DATA:verylongbase64string3]
    [IMAGE_DATA:verylongbase64string4]
    """
    
    print(f"Размер блока до сжатия: {len(content)} символов")
    
    # Сжимаем блок до 2048 токенов (~8192 символа)
    compressed = compress_block_on_overflow(
        block_content=content,
        llm=llm,
        max_tokens=2048,
        preserve_images=True
    )
    
    print(f"Размер блока после сжатия: {len(compressed)} символов")
    
    # Проверяем, что размер уменьшился
    if len(compressed) < len(content):
        reduction = ((len(content) - len(compressed)) / len(content)) * 100
        print(f"✅ Блок сжат: {reduction:.1f}% сокращение")
    else:
        print("❌ Блок не сжат")
    
    # Проверяем количество изображений
    import re
    image_pattern = r'\[(?:PAGE_\d+_)?IMAGE_DATA:[^\]]+\]'
    images_after = re.findall(image_pattern, compressed)
    
    print(f"Изображений после сжатия: {len(images_after)} (макс. 3)")
    
    if len(images_after) <= 3:
        print("✅ Изображения ограничены до 3")
    else:
        print(f"❌ Слишком много изображений: {len(images_after)}")


def test_compress_block_without_images():
    """Тест сжатия блока без изображений (только текст)."""
    print("\n=== Тест сжатия блока без изображений ===")
    
    llm = MockLLM()
    
    # Создаем большой блок текста БЕЗ изображений
    large_text = "Observation: This is a very long text. " * 200  # ~8000 символов
    
    print(f"Размер блока до сжатия: {len(large_text)} символов")
    
    # Сжимаем блок
    compressed = compress_block_on_overflow(
        block_content=large_text,
        llm=llm,
        max_tokens=1024,
        preserve_images=True
    )
    
    print(f"Размер блока после сжатия: {len(compressed)} символов")
    
    # Проверяем, что сжатие произошло через LLM
    if "Краткое резюме:" in compressed:
        print("✅ Текст сжат через LLM")
    else:
        print("⚠️ Текст не сжат через LLM (возможно, исходный размер подходящий)")
    
    # Проверяем отсутствие изображений
    import re
    image_pattern = r'\[(?:PAGE_\d+_)?IMAGE_DATA:[^\]]+\]'
    images = re.findall(image_pattern, compressed)
    
    if len(images) == 0:
        print("✅ Изображения отсутствуют (как ожидалось)")
    else:
        print(f"❌ Неожиданно найдены изображения: {len(images)}")


def test_compress_block_remove_all_images():
    """Тест полного удаления изображений при preserve_images=False."""
    print("\n=== Тест удаления всех изображений ===")
    
    llm = MockLLM()
    
    content = """
    Some text
    [IMAGE_DATA:data1]
    [IMAGE_DATA:data2]
    [PAGE_3_IMAGE_DATA:data3]
    More text
    """
    
    # Сжимаем с удалением изображений
    compressed = compress_block_on_overflow(
        block_content=content,
        llm=llm,
        max_tokens=1024,
        preserve_images=False  # Удаляем все изображения
    )
    
    # Проверяем отсутствие изображений
    import re
    image_pattern = r'\[(?:PAGE_\d+_)?IMAGE_DATA:[^\]]+\]'
    images = re.findall(image_pattern, compressed)
    
    print(f"Изображений после сжатия: {len(images)}")
    
    if len(images) == 0:
        print("✅ Все изображения удалены")
    else:
        print(f"❌ Изображения остались: {len(images)}")
    
    # Проверяем наличие уведомления
    if "Удалено изображений" in compressed:
        print("✅ Уведомление об удалении присутствует")


if __name__ == "__main__":
    print("🧪 Запуск тестов системы сжатия контекста\n")
    
    test_compress_images_in_message()
    test_compress_block_on_overflow()
    test_compress_block_without_images()
    test_compress_block_remove_all_images()
    
    print("\n✅ Все тесты сжатия завершены!")
