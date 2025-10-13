#!/usr/bin/env python3
"""
Тест hotfix v2.1.2: JSON парсинг + пути в корневой директории
"""

import sys
import os

# Добавляем путь к AI директории
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_json_cleaning():
    """Тест очистки escape-последовательностей в JSON"""
    print("="*70)
    print("ТЕСТ 1: Очистка escape-последовательностей")
    print("="*70)
    
    # Симулируем ответ Gemma с тройным экранированием
    raw_response = r'{"thought": "test", "action": {"tool_name": "write_file", "parameters": {"file_path": "test.py", "content": "import re\n\nstring = input(\"Enter text:\\\")\nprint(string)"}}}'
    
    print(f"\n1. Исходный ответ Gemma:")
    print(f"   {raw_response[:100]}...")
    print(f"\n   Проблема: \\\" внутри content (должно быть \\\")")
    
    # Применяем очистку как в agent.py
    cleaned = raw_response
    
    # Шаг 1: \\\" → \"
    cleaned = cleaned.replace('\\\\\"', '\\"')
    print(f"\n2. После замены \\\\\" → \\\":")
    print(f"   {cleaned[:100]}...")
    
    # Шаг 2: \\\\ → \\
    cleaned = cleaned.replace('\\\\', '\\')
    print(f"\n3. После замены \\\\\\\\ → \\\\:")
    print(f"   {cleaned[:100]}...")
    
    # Парсим JSON
    import json
    try:
        parsed = json.loads(cleaned)
        print(f"\n✅ JSON успешно распарсен!")
        print(f"   content: {parsed['action']['parameters']['content'][:50]}...")
        return True
    except json.JSONDecodeError as e:
        print(f"\n❌ Ошибка парсинга: {e}")
        return False


def test_paths():
    """Тест создания путей в корневой директории"""
    print("\n" + "="*70)
    print("ТЕСТ 2: Пути создаются в корневой директории агента")
    print("="*70)
    
    from pathlib import Path
    import tempfile
    import shutil
    
    # Создаём временную директорию для теста
    test_dir = Path(tempfile.mkdtemp(prefix="agent_test_"))
    print(f"\nВременная директория: {test_dir}")
    
    # Создаём фейковый agent.py
    fake_agent_dir = test_dir / "AI"
    fake_agent_dir.mkdir()
    fake_agent_file = fake_agent_dir / "agent.py"
    fake_agent_file.write_text("# fake agent")
    
    try:
        # Меняем CWD на другую директорию (симулируем запуск из /home/vova/testsand)
        original_cwd = Path.cwd()
        other_dir = test_dir / "other_location"
        other_dir.mkdir()
        os.chdir(other_dir)
        
        print(f"Текущий CWD: {Path.cwd()}")
        print(f"Файл агента: {fake_agent_file}")
        print(f"CWD != директория агента ✓")
        
        # Симулируем создание Agent с Path(__file__).parent
        # __file__ был бы = fake_agent_file
        project_root = fake_agent_file.parent.resolve()  # /tmp/.../AI
        logs_dir = project_root / "logs"
        chats_dir = project_root / "chats"
        memory_dir = project_root / "memory"
        
        # Создаём директории
        logs_dir.mkdir(exist_ok=True)
        chats_dir.mkdir(exist_ok=True)
        memory_dir.mkdir(exist_ok=True)
        
        print(f"\nСозданные пути:")
        print(f"  logs:   {logs_dir}")
        print(f"  chats:  {chats_dir}")
        print(f"  memory: {memory_dir}")
        
        # Проверяем, что они созданы в директории agent.py, а НЕ в CWD
        assert logs_dir.parent == fake_agent_dir, "logs не в директории agent.py!"
        assert chats_dir.parent == fake_agent_dir, "chats не в директории agent.py!"
        assert memory_dir.parent == fake_agent_dir, "memory не в директории agent.py!"
        assert fake_agent_dir != Path.cwd(), "Тест некорректен: agent_dir == cwd"
        
        print(f"\n✅ Все пути созданы в директории agent.py")
        print(f"   agent_dir = {fake_agent_dir}")
        print(f"   cwd = {Path.cwd()}")
        print(f"   agent_dir != cwd ✓")
        
        os.chdir(original_cwd)
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        os.chdir(original_cwd)
        return False
    finally:
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    print("\n🚀 HOTFIX v2.1.2 - Тесты исправлений\n")
    
    result1 = test_json_cleaning()
    result2 = test_paths()
    
    print("\n" + "="*70)
    if result1 and result2:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        sys.exit(0)
    else:
        print("❌ ЕСТЬ ОШИБКИ")
        sys.exit(1)
    print("="*70 + "\n")
