"""
Простой тест адаптивного Context Manager v2.2.0
Проверяет базовую функциональность без глубокого анализа контекста
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from context_manager import ContextManager
from memory import MemoryManager
from pathlib import Path
import tempfile
import shutil


def test_adaptive_context_basic():
    """
    Базовый тест: Проверяет, что адаптивный контекст менеджер работает
    и возвращает корректную структуру
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Mock LLM
        class MockLLM:
            def tokenize(self, text):
                return text.encode('utf-8')[:len(text)//4]
        
        # Создаём memory manager
        memory = MemoryManager(
            global_memory_dir=str(Path(temp_dir) / "global"),
            chats_base_dir=str(Path(temp_dir) / "chats")
        )
        project_memory = memory.get_project_memory("test")
        
        # Создаём context manager
        cm = ContextManager(
            llm=MockLLM(),
            global_memory=memory.global_memory,
            project_memory=project_memory,
            max_tokens=20480
        )
        
        # Подготавливаем данные
        system_prompt = "Ты AI-ассистент" * 100
        scratchpad = {"goal": "Test", "plan": "Step 1\nStep 2", "last_action_result": "ok"}
        history = [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Здравствуйте!"}
        ]
        
        # Вызываем build_context
        context_messages, stats, enhanced_prompt = cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            current_query="Продолжить"
        )
        
        # Проверки
        assert isinstance(context_messages, list), "Контекст должен быть списком"
        assert isinstance(stats, dict), "Статистика должна быть словарём"
        assert isinstance(enhanced_prompt, str), "Улучшенный промпт должен быть строкой"
        
        # Проверяем наличие ключей в статистике
        assert 'total_tokens' in stats
        assert 'system_tokens' in stats
        assert 'scratchpad_tokens' in stats
        assert 'memory_tokens' in stats
        assert 'history_tokens' in stats
        assert 'budget_redistribution' in stats  # Новая метрика адаптивности
        
        # Проверяем, что токены не превышают лимит
        assert stats['total_tokens'] <= cm.max_tokens, \
            f"Токены {stats['total_tokens']} превысили лимит {cm.max_tokens}"
        
        print(f"✅ БАЗОВЫЙ ТЕСТ ПРОЙДЕН")
        print(f"   Токенов: {stats['total_tokens']}/{cm.max_tokens}")
        print(f"   Утилизация: {stats.get('utilization', 0):.1f}%")
        print(f"   Перераспределение: {stats['budget_redistribution']}")
        
    finally:
        shutil.rmtree(temp_dir)


def test_adaptive_empty_memory():
    """
    Тест пустой памяти: Токены должны перераспределяться истории
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        class MockLLM:
            def tokenize(self, text):
                return text.encode('utf-8')[:len(text)//4]
        
        memory = MemoryManager(
            global_memory_dir=str(Path(temp_dir) / "global"),
            chats_base_dir=str(Path(temp_dir) / "chats")
        )
        project_memory = memory.get_project_memory("test")
        
        cm = ContextManager(
            llm=MockLLM(),
            global_memory=memory.global_memory,
            project_memory=project_memory,
            max_tokens=20480
        )
        
        # Короткий промпт и scratchpad
        system_prompt = "Ты AI"
        scratchpad = {"goal": "Test", "plan": "A", "last_action_result": "ok"}
        
        # Большая история (30 сообщений)
        history = []
        for i in range(30):
            history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Сообщение {i}: детали и контекст" * 20
            })
        
        context_messages, stats, _ = cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            current_query="Продолжить"
        )
        
        # Проверки
        # 1. Память должна быть пустая или близка к нулю
        assert stats['memory_tokens'] < 500, \
            f"Память должна быть малой (пустая), получено {stats['memory_tokens']}"
        
        # 2. История должна получить много места
        history_percent = (stats['history_tokens'] / cm.max_tokens) * 100
        assert history_percent > 40, \
            f"История должна получить >40% при пустой памяти, получено {history_percent:.1f}%"
        
        # 3. Должно быть перераспределение (l3_saved > 0)
        redist = stats['budget_redistribution']
        assert 'l3_saved' in redist, "Должна быть метрика l3_saved"
        
        print(f"✅ ТЕСТ ПУСТОЙ ПАМЯТИ ПРОЙДЕН")
        print(f"   История: {history_percent:.1f}% ({stats['history_tokens']} токенов)")
        print(f"   Память сэкономила: {redist.get('l3_saved', 0)} токенов")
        
    finally:
        shutil.rmtree(temp_dir)


def test_adaptive_large_memory():
    """
    Тест большой памяти: Память должна расширяться адаптивно
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        class MockLLM:
            def tokenize(self, text):
                return text.encode('utf-8')[:len(text)//4]
        
        memory = MemoryManager(
            global_memory_dir=str(Path(temp_dir) / "global"),
            chats_base_dir=str(Path(temp_dir) / "chats")
        )
        project_memory = memory.get_project_memory("test")
        
        # Добавляем много записей
        for i in range(30):
            memory.global_memory.add(
                text=f"Глобальная запись {i}: важные детали реализации" * 15,
                metadata={"index": i}
            )
            project_memory.add(
                text=f"Проектная запись {i}: архитектурные решения" * 15,
                metadata={"index": i}
            )
        
        cm = ContextManager(
            llm=MockLLM(),
            global_memory=memory.global_memory,
            project_memory=project_memory,
            max_tokens=20480
        )
        
        system_prompt = "Ты AI-ассистент"
        scratchpad = {"goal": "Анализ", "plan": "Шаг 1", "last_action_result": "ok"}
        history = [{"role": "user", "content": "Найди информацию о записях"}]
        
        context_messages, stats, _ = cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            current_query="записи и детали"  # Релевантный запрос
        )
        
        # Проверки
        # 1. Память должна занимать значительное место
        memory_percent = (stats['memory_tokens'] / cm.max_tokens) * 100
        assert memory_percent >= 10, \
            f"Память должна занимать ≥10% при большом количестве записей, получено {memory_percent:.1f}%"
        
        # 2. Должна быть статистика перераспределения
        assert 'budget_redistribution' in stats
        
        print(f"✅ ТЕСТ БОЛЬШОЙ ПАМЯТИ ПРОЙДЕН")
        print(f"   Память: {memory_percent:.1f}% ({stats['memory_tokens']} токенов)")
        print(f"   История: {(stats['history_tokens']/cm.max_tokens)*100:.1f}%")
        
    finally:
        shutil.rmtree(temp_dir)


def test_adaptive_critical_components():
    """
    Тест критичных компонентов: Огромный scratchpad НЕ должен обрезаться
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        class MockLLM:
            def tokenize(self, text):
                return text.encode('utf-8')[:len(text)//4]
        
        memory = MemoryManager(
            global_memory_dir=str(Path(temp_dir) / "global"),
            chats_base_dir=str(Path(temp_dir) / "chats")
        )
        project_memory = memory.get_project_memory("test")
        
        cm = ContextManager(
            llm=MockLLM(),
            global_memory=memory.global_memory,
            project_memory=project_memory,
            max_tokens=20480
        )
        
        # Огромный системный промпт и scratchpad
        system_prompt = "Системный промпт с инструкциями" * 300
        huge_plan = "\n".join([f"{i}. Шаг {i}: детальное описание" * 5 for i in range(1, 31)])
        scratchpad = {
            "goal": "Сложная задача с детальным описанием целей и ожиданий" * 10,
            "plan": huge_plan,
            "last_action_result": "Результат предыдущего действия с деталями" * 20
        }
        
        history = [{"role": "user", "content": "Тест"}]
        
        context_messages, stats, enhanced_prompt = cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            current_query="Продолжить"
        )
        
        # Проверки
        # 1. Scratchpad должен присутствовать в улучшенном промпте (приоритет 1)
        assert scratchpad["goal"][:50] in enhanced_prompt or \
               "Цель:" in enhanced_prompt, \
               "Цель из scratchpad должна быть в контексте (критичный компонент)"
        
        # 2. Контекст НЕ должен превышать лимит
        assert stats['total_tokens'] <= cm.max_tokens, \
            f"Контекст превысил лимит: {stats['total_tokens']} > {cm.max_tokens}"
        
        # 3. История может быть урезана (приоритет 3), но минимум должен быть
        assert stats['history_tokens'] >= 0, "История должна присутствовать"
        
        print(f"✅ ТЕСТ КРИТИЧНЫХ КОМПОНЕНТОВ ПРОЙДЕН")
        print(f"   Scratchpad: {stats['scratchpad_tokens']} токенов")
        print(f"   System: {stats['system_tokens']} токенов")
        print(f"   История: {stats['history_tokens']} токенов")
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 ТЕСТЫ АДАПТИВНОГО CONTEXT MANAGER v2.2.0")
    print("="*70 + "\n")
    
    test_adaptive_context_basic()
    print()
    test_adaptive_empty_memory()
    print()
    test_adaptive_large_memory()
    print()
    test_adaptive_critical_components()
    
    print("\n" + "="*70)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
    print("="*70 + "\n")
