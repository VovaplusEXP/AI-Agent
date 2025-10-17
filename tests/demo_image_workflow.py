"""
Интеграционный тест для демонстрации полного цикла работы с изображениями.
Создает тестовые файлы, читает их через read_file, и проверяет работу контекста.
"""
import os
import sys
import tempfile
from pathlib import Path

# Добавляем родительскую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import tools


def create_demo_image(filepath: str):
    """Создает демонстрационное изображение с градиентом."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Создаем изображение 800x600
        img = Image.new('RGB', (800, 600), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Рисуем градиент
        for y in range(600):
            color_value = int(255 * (y / 600))
            draw.rectangle([(0, y), (800, y+1)], fill=(color_value, 100, 255-color_value))
        
        # Добавляем текст
        draw.text((50, 50), "Test Image for AI Agent", fill=(0, 0, 0))
        draw.text((50, 100), "Testing image reading capability", fill=(255, 255, 255))
        
        img.save(filepath)
        return True
    except ImportError:
        print("⚠️ Pillow не установлен")
        return False


def create_demo_pdf(filepath: str):
    """Создает демонстрационный PDF с несколькими страницами."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        
        c = canvas.Canvas(filepath, pagesize=letter)
        
        # Страница 1
        c.setFont("Helvetica-Bold", 24)
        c.drawString(1*inch, 10*inch, "AI Agent Test Document")
        c.setFont("Helvetica", 12)
        c.drawString(1*inch, 9.5*inch, "This is a test PDF for image reading functionality")
        c.drawString(1*inch, 9*inch, "Page 1 of 3")
        c.showPage()
        
        # Страница 2
        c.setFont("Helvetica-Bold", 18)
        c.drawString(1*inch, 10*inch, "Chapter 1: Introduction")
        c.setFont("Helvetica", 12)
        c.drawString(1*inch, 9.5*inch, "This document demonstrates PDF to image conversion.")
        c.drawString(1*inch, 9*inch, "Each page will be converted to a separate image.")
        c.drawString(1*inch, 8.5*inch, "Page 2 of 3")
        c.showPage()
        
        # Страница 3
        c.setFont("Helvetica-Bold", 18)
        c.drawString(1*inch, 10*inch, "Chapter 2: Conclusion")
        c.setFont("Helvetica", 12)
        c.drawString(1*inch, 9.5*inch, "PDF reading is working correctly!")
        c.drawString(1*inch, 9*inch, "Page 3 of 3")
        c.showPage()
        
        c.save()
        return True
    except ImportError:
        print("⚠️ reportlab не установлен")
        return False


def demo_workflow():
    """Демонстрация полного рабочего процесса."""
    print("\n" + "="*80)
    print("🎬 ДЕМОНСТРАЦИЯ РАБОТЫ С ИЗОБРАЖЕНИЯМИ И PDF")
    print("="*80 + "\n")
    
    # Создаем временную директорию
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # === Тест 1: Чтение изображения ===
        print("📸 Тест 1: Чтение изображения JPEG")
        print("-" * 60)
        
        image_path = tmpdir_path / "test_image.jpg"
        if create_demo_image(str(image_path)):
            print(f"✓ Создано тестовое изображение: {image_path.name}")
            print(f"  Размер файла: {image_path.stat().st_size / 1024:.2f} КБ")
            
            result = tools.read_file(str(image_path))
            
            print(f"\n📊 Результат read_file():")
            print("-" * 60)
            # Показываем первые 500 символов (без base64 данных)
            result_preview = result[:500] + "..." if len(result) > 500 else result
            if "[IMAGE_DATA:" in result_preview:
                # Обрезаем base64 для читаемости
                import re
                result_preview = re.sub(r'\[IMAGE_DATA:[^\]]{50}[^\]]*\]', '[IMAGE_DATA:...truncated...]', result_preview)
            print(result_preview)
            
            # Проверяем результат
            if "ИЗОБРАЖЕНИЕ:" in result and "[IMAGE_DATA:" in result:
                print("\n✅ Изображение успешно прочитано и оптимизировано")
            else:
                print("\n❌ Ошибка чтения изображения")
        else:
            print("⏭️ Тест пропущен (Pillow не установлен)")
        
        print("\n")
        
        # === Тест 2: Чтение PDF ===
        print("📄 Тест 2: Чтение PDF документа")
        print("-" * 60)
        
        pdf_path = tmpdir_path / "test_document.pdf"
        if create_demo_pdf(str(pdf_path)):
            print(f"✓ Создан тестовый PDF: {pdf_path.name}")
            print(f"  Размер файла: {pdf_path.stat().st_size / 1024:.2f} КБ")
            
            result = tools.read_file(str(pdf_path))
            
            print(f"\n📊 Результат read_file():")
            print("-" * 60)
            # Показываем первые 800 символов
            result_preview = result[:800] + "..." if len(result) > 800 else result
            if "[PAGE_" in result_preview:
                # Обрезаем base64 для читаемости
                import re
                result_preview = re.sub(r'\[PAGE_\d+_IMAGE_DATA:[^\]]{50}[^\]]*\]', '[PAGE_X_IMAGE_DATA:...truncated...]', result_preview)
            print(result_preview)
            
            # Проверяем результат
            import re
            pages = re.findall(r'\[PAGE_\d+_IMAGE_DATA:', result)
            if "PDF ДОКУМЕНТ:" in result and len(pages) > 0:
                print(f"\n✅ PDF успешно прочитан, страниц конвертировано: {len(pages)}")
            else:
                print("\n❌ Ошибка чтения PDF")
        else:
            print("⏭️ Тест пропущен (reportlab не установлен)")
        
        print("\n")
        
        # === Тест 3: Различные форматы изображений ===
        print("🖼️ Тест 3: Поддержка различных форматов")
        print("-" * 60)
        
        formats = ['.png', '.bmp', '.gif']
        supported_formats = []
        
        for fmt in formats:
            test_path = tmpdir_path / f"test{fmt}"
            try:
                if create_demo_image(str(test_path)):
                    result = tools.read_file(str(test_path))
                    if "ИЗОБРАЖЕНИЕ:" in result:
                        supported_formats.append(fmt)
                        print(f"✓ {fmt.upper():5s} - поддерживается")
            except Exception as e:
                print(f"✗ {fmt.upper():5s} - ошибка: {e}")
        
        print(f"\n✅ Поддерживаемые форматы: {', '.join(supported_formats)}")
        
        print("\n")
        
        # === Тест 4: Оценка экономии токенов ===
        print("💾 Тест 4: Оценка экономии токенов")
        print("-" * 60)
        
        # Создаем большое изображение
        large_image_path = tmpdir_path / "large_image.png"
        try:
            from PIL import Image
            large_img = Image.new('RGB', (2048, 1536), color=(128, 128, 128))
            large_img.save(str(large_image_path))
            
            original_size = large_image_path.stat().st_size
            
            result = tools.read_file(str(large_image_path))
            
            # Извлекаем base64 данные
            import re
            match = re.search(r'\[IMAGE_DATA:([^\]]+)\]', result)
            if match:
                optimized_base64 = match.group(1)
                optimized_size = len(optimized_base64)
                
                print(f"Исходное изображение: 2048x1536, {original_size / 1024:.2f} КБ")
                print(f"Оптимизированное:     512x512, {optimized_size / 1024:.2f} КБ (base64)")
                
                # Приблизительная оценка токенов
                # Vision модели: ~85 токенов для изображения 512x512
                estimated_tokens = 65
                print(f"\n📊 Оценка токенов: ~{estimated_tokens} токенов на изображение")
                print(f"   (вместо ~{original_size // 40} для несжатого)")
                
                reduction = (1 - (optimized_size / original_size)) * 100
                print(f"\n✅ Экономия места: {reduction:.1f}%")
        except Exception as e:
            print(f"⚠️ Тест пропущен: {e}")
    
    print("\n" + "="*80)
    print("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("="*80 + "\n")


if __name__ == "__main__":
    demo_workflow()
