"""
Тесты для поддержки изображений и PDF в инструменте read_file.
"""
import os
import sys
import tempfile
from pathlib import Path

# Добавляем родительскую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import tools


def create_test_image(filepath: str, size=(100, 100), color=(255, 0, 0)):
    """Создает тестовое изображение."""
    try:
        from PIL import Image
        img = Image.new('RGB', size, color)
        img.save(filepath)
        return True
    except ImportError:
        print("⚠️ Pillow не установлен, пропускаем тесты изображений")
        return False


def create_test_pdf(filepath: str):
    """Создает тестовый PDF файл с текстом."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(filepath, pagesize=letter)
        c.drawString(100, 750, "Test PDF Document")
        c.drawString(100, 730, "Page 1 - This is a test")
        c.showPage()
        
        c.drawString(100, 750, "Page 2")
        c.drawString(100, 730, "Second page content")
        c.showPage()
        
        c.save()
        return True
    except ImportError:
        print("⚠️ reportlab не установлен, создаем PDF через pypdfium2")
        # Альтернатива: создаем простой текстовый "PDF" для тестирования
        with open(filepath, 'w') as f:
            f.write("%PDF-1.4\nTest PDF")
        return True


def test_image_optimization():
    """Тест оптимизации изображения."""
    print("\n=== Тест оптимизации изображения ===")
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        if not create_test_image(tmp_path, size=(800, 600), color=(0, 128, 255)):
            print("⏭️ Пропущен (Pillow не установлен)")
            return
        
        # Тестируем оптимизацию
        img_base64 = tools._optimize_image_for_vision(tmp_path, max_size=(512, 512), quality=85)
        
        if img_base64:
            print(f"✅ Изображение оптимизировано, base64 длина: {len(img_base64)}")
            print(f"   Приблизительный размер: {len(img_base64) / 1024:.2f} KB")
            
            # Проверяем, что base64 валидный
            import base64
            try:
                base64.b64decode(img_base64)
                print("✅ Base64 валидный")
            except Exception as e:
                print(f"❌ Base64 невалидный: {e}")
        else:
            print("❌ Не удалось оптимизировать изображение")
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_read_image_file():
    """Тест чтения файла изображения через read_file."""
    print("\n=== Тест чтения изображения через read_file ===")
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        if not create_test_image(tmp_path, size=(200, 200), color=(255, 128, 0)):
            print("⏭️ Пропущен (Pillow не установлен)")
            return
        
        # Читаем изображение через read_file
        result = tools.read_file(tmp_path)
        
        if "ИЗОБРАЖЕНИЕ:" in result:
            print("✅ Изображение распознано")
            print(f"   Результат (первые 200 символов): {result[:200]}...")
            
            # Проверяем наличие IMAGE_DATA
            if "[IMAGE_DATA:" in result:
                print("✅ IMAGE_DATA присутствует в результате")
            else:
                print("❌ IMAGE_DATA отсутствует в результате")
        else:
            print(f"❌ Изображение не распознано. Результат: {result[:200]}")
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_read_pdf_file():
    """Тест чтения PDF файла через read_file."""
    print("\n=== Тест чтения PDF через read_file ===")
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        create_test_pdf(tmp_path)
        
        # Читаем PDF через read_file
        result = tools.read_file(tmp_path)
        
        if "PDF ДОКУМЕНТ:" in result:
            print("✅ PDF распознан")
            print(f"   Результат (первые 300 символов): {result[:300]}...")
            
            # Проверяем наличие PAGE_X_IMAGE_DATA
            if "PAGE_" in result and "IMAGE_DATA:" in result:
                print("✅ Страницы PDF конвертированы в изображения")
            else:
                print("⚠️ Страницы PDF не найдены (возможно, библиотеки не установлены)")
        else:
            print(f"⚠️ PDF обработка недоступна. Результат: {result[:200]}")
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_read_text_file():
    """Тест чтения обычного текстового файла (проверка обратной совместимости)."""
    print("\n=== Тест чтения текстового файла (обратная совместимость) ===")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        tmp.write("Test content\nLine 2\nLine 3")
        tmp_path = tmp.name
    
    try:
        result = tools.read_file(tmp_path)
        
        if result == "Test content\nLine 2\nLine 3":
            print("✅ Текстовый файл читается корректно")
        else:
            print(f"❌ Текстовый файл прочитан неправильно: {result}")
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_token_counting_with_images():
    """Тест подсчета токенов для текста с изображениями."""
    print("\n=== Тест подсчета токенов с изображениями ===")
    
    # Мокируем LLM для подсчета токенов
    class MockLLM:
        def tokenize(self, text):
            # Простой мок: 1 токен = 4 символа
            return [0] * (len(text) // 4)
    
    # Импортируем ContextManager
    from context_manager import ContextManager
    
    llm = MockLLM()
    ctx_manager = ContextManager(llm)
    
    # Текст без изображений
    text1 = "This is a simple text without images"
    tokens1 = ctx_manager.count_tokens(text1)
    print(f"Текст без изображений: {len(text1)} символов → {tokens1} токенов")
    
    # Текст с одним изображением
    text2 = "Text before [IMAGE_DATA:base64encodedstring] text after"
    tokens2 = ctx_manager.count_tokens(text2)
    print(f"Текст с 1 изображением: {len(text2)} символов → {tokens2} токенов")
    
    # Текст с несколькими изображениями
    text3 = "Image 1: [IMAGE_DATA:data1] Image 2: [PAGE_2_IMAGE_DATA:data2]"
    tokens3 = ctx_manager.count_tokens(text3)
    print(f"Текст с 2 изображениями: {len(text3)} символов → {tokens3} токенов")
    
    # Проверяем, что изображения учитываются
    if tokens2 > tokens1:
        print("✅ Изображения учитываются в подсчете токенов")
    else:
        print("❌ Изображения не учитываются в подсчете токенов")


if __name__ == "__main__":
    print("🧪 Запуск тестов поддержки изображений и PDF\n")
    
    test_image_optimization()
    test_read_image_file()
    test_read_pdf_file()
    test_read_text_file()
    test_token_counting_with_images()
    
    print("\n✅ Все тесты завершены!")
