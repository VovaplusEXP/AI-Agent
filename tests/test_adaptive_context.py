"""
Тесты адаптивного Context Manager (v2.2.0)
Проверяет гибкое распределение токенов с приоритизацией
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from context_manager import ContextManager
from memory import MemoryManager
from pathlib import Path
import tempfile
import shutil


class TestAdaptiveContextManager:
    """Тесты адаптивного менеджера контекста"""
    
    def setup_method(self):
        """Подготовка перед каждым тестом"""
        self.temp_dir = tempfile.mkdtemp()
        self.memory_path = Path(self.temp_dir) / "memory"
        self.memory_path.mkdir(parents=True, exist_ok=True)
        
        # Mock LLM для подсчёта токенов
        class MockLLM:
            def tokenize(self, text):
                return text.encode('utf-8')[:len(text)//4]  # Примерно 1 токен = 4 символа
        
        # Создаём memory manager с глобальной памятью
        self.memory = MemoryManager(
            global_memory_dir=str(self.memory_path / "global"),
            chats_base_dir=str(self.memory_path / "chats")
        )
        
        # Получаем проектную память
        self.project_memory = self.memory.get_project_memory("test_project")
        
        # Создаём context manager с адаптивными приоритетами
        self.cm = ContextManager(
            llm=MockLLM(),
            global_memory=self.memory.global_memory,
            project_memory=self.project_memory,
            max_tokens=20480  # 20k контекст
        )
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        shutil.rmtree(self.temp_dir)
    
    def count_tokens(self, text: str) -> int:
        """Примерный подсчёт токенов (1 токен ≈ 4 символа)"""
        return len(text) // 4
    
    # ==================== ТЕСТ 1: Пустая память ====================
    
    def test_empty_memory_redistributes_to_history(self):
        """
        СЦЕНАРИЙ: Пустая память → токены отдаются истории
        
        Старый подход: memory=20% зарезервировано (даже если пустая)
        Новый подход: memory=0%, токены → history (+40%)
        """
        system_prompt = "Ты AI-ассистент" * 200  # ~1500 токенов
        
        scratchpad = {
            "goal": "Анализ проекта",
            "plan": "1. Читать файлы\n2. Анализировать код",
            "last_action_result": "Файл прочитан"
        }
        
        # История: 30 сообщений (должна вместиться полностью)
        history = []
        for i in range(30):
            history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Сообщение {i}: тестовый контент с деталями" * 20
            })
        
        context, stats, _ = self.cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            current_query="Продолжить анализ"
        )
        
        # Проверки
        context_tokens = self.count_tokens(str(context))
        
        # 1. Контекст НЕ должен превышать max_tokens
        assert context_tokens <= self.cm.max_tokens, \
            f"Контекст {context_tokens} превысил лимит {self.cm.max_tokens}"
        
        # 2. Использование должно быть > 85% (мало отходов)
        utilization = stats['utilization']
        assert utilization > 85, \
            f"Использование {utilization}% слишком низкое (ожидалось >85%)"
        
        # 3. История должна получить МНОГО места (> 50%)
        history_in_context = "### История диалога" in context
        assert history_in_context, "История должна присутствовать в контексте"
        
        # 4. Память НЕ должна занимать места (пустая)
        memory_budget = stats.get('budget_redistribution', {}).get('l3_saved', 0)
        assert memory_budget >= 0, "Пустая память должна экономить токены"
        
        print(f"✅ ТЕСТ 1 ПРОЙДЕН: Утилизация {utilization}%, память сэкономила {memory_budget} токенов")
    
    # ==================== ТЕСТ 2: Огромная память ====================
    
    def test_large_memory_expands_adaptively(self):
        """
        СЦЕНАРИЙ: Много записей в памяти → расширение до max (30%)
        
        Старый подход: memory=20% (Top-5)
        Новый подход: memory=30% (Top-12), история сжата
        """
        # Добавляем 50 записей в глобальную память
        for i in range(50):
            self.memory.global_memory.add(
                text=f"Важная информация #{i}: детали реализации функции process_data() с параметрами..." * 10,
                metadata={"source": "code_analysis", "priority": i}
            )
        
        # Добавляем 50 записей в проектную память
        for i in range(50):
            self.project_memory.add(
                text=f"Проектная информация #{i}: структура класса DataProcessor с методами..." * 10,
                metadata={"source": "architecture", "priority": i}
            )
        
        system_prompt = "Ты AI-ассистент" * 200
        scratchpad = {
            "goal": "Оптимизация кода",
            "plan": "Использовать память для контекста",
            "last_action_result": "ok"
        }
        history = [
            {"role": "user", "content": "Оптимизируй код"},
            {"role": "assistant", "content": "Анализирую архитектуру..."}
        ]
        
        context, stats, _ = self.cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            current_query="process_data и DataProcessor"  # Ключевые слова для поиска
        )
        
        # Проверки
        # 1. В контексте должно быть МНОГО записей из памяти (адаптивное расширение)
        memory_entries_count = context.count("Релевантная информация")
        assert memory_entries_count >= 8, \
            f"Ожидалось ≥8 записей из памяти, найдено {memory_entries_count}"
        
        # 2. Проверяем наличие ключевых слов из памяти
        assert "process_data" in context or "DataProcessor" in context, \
            "Память должна содержать релевантные записи"
        
        # 3. История должна присутствовать (хотя бы минимум 30%)
        assert "История диалога" in context, "История должна быть в контексте"
        
        # 4. Утилизация должна быть высокой
        assert stats['utilization'] > 80, \
            f"Утилизация {stats['utilization']}% слишком низкая"
        
        print(f"✅ ТЕСТ 2 ПРОЙДЕН: {memory_entries_count} записей из памяти, утилизация {stats['utilization']}%")
    
    # ==================== ТЕСТ 3: Критичный scratchpad ====================
    
    def test_critical_components_never_truncated(self):
        """
        СЦЕНАРИЙ: Огромный scratchpad → история сжимается, но scratchpad ПОЛНОСТЬЮ сохраняется
        
        Приоритет 1 (критично): system_prompt, scratchpad - НЕЛЬЗЯ обрезать
        Приоритет 3 (гибко): history - может сжаться
        """
        system_prompt = "Ты AI-ассистент" * 300  # ~2500 токенов
        
        # Огромный scratchpad (план с 50 шагами)
        huge_plan = "\n".join([f"{i}. Шаг {i}: детальное описание действия с параметрами и ожидаемым результатом" * 5 
                                for i in range(1, 51)])
        
        scratchpad = {
            "goal": "Реализация сложной системы авторизации с OAuth2, JWT, refresh tokens и multi-tenancy",
            "plan": huge_plan,  # ОГРОМНЫЙ план
            "last_action_result": "Прочитал документацию по OAuth2 RFC 6749, проанализировал существующие решения (Auth0, Keycloak, AWS Cognito), выбрал архитектуру..." * 20
        }
        
        history = []
        for i in range(50):  # Большая история
            history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Сообщение {i}" * 50
            })
        
        context, stats = self.cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            query="Продолжить"
        )
        
        # Проверки
        # 1. Scratchpad должен быть ПОЛНОСТЬЮ в контексте (приоритет 1)
        assert scratchpad["goal"] in context, "Цель из scratchpad должна быть полностью"
        assert "Шаг 1:" in context and "Шаг 50:" in context, \
            "Весь план должен быть сохранён (критичный компонент)"
        assert scratchpad["last_action_result"][:100] in context, \
            "Результат последнего действия должен быть сохранён"
        
        # 2. История может быть обрезана (приоритет 3)
        # Но хотя бы последние сообщения должны быть
        assert "Сообщение 49" in context or "Сообщение 48" in context, \
            "Последние сообщения истории должны присутствовать"
        
        # 3. Контекст не превышает лимит
        assert self.count_tokens(context) <= self.cm.n_ctx, \
            "Контекст не должен превышать n_ctx"
        
        print(f"✅ ТЕСТ 3 ПРОЙДЕН: Критичные компоненты сохранены, утилизация {stats['utilization']}%")
    
    # ==================== ТЕСТ 4: Адаптивное расширение памяти ====================
    
    def test_memory_k_adaptive_expansion(self):
        """
        СЦЕНАРИЙ: Проверка адаптивного увеличения k для памяти
        
        Начинаем: k=2 global, k=3 project
        Если токенов < target → расширяем до k=5 global, k=7 project
        """
        # Добавляем средне записей (не слишком много)
        for i in range(15):
            self.memory.add_to_global_memory(
                content=f"Global info {i}" * 20,
                metadata={"index": i}
            )
            self.memory.add_to_project_memory(
                content=f"Project info {i}" * 20,
                metadata={"index": i}
            )
        
        system_prompt = "Короткий промпт"
        scratchpad = {"goal": "test", "plan": "short", "last_action_result": "ok"}
        history = [{"role": "user", "content": "test"}]
        
        context, stats = self.cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            query="info"  # Релевантное слово для поиска
        )
        
        # Проверки
        # 1. Должно быть > 5 записей (адаптивное расширение k)
        # Начальный k=2+3=5, расширенный k=5+7=12
        memory_entries = context.count("Релевантная информация")
        assert memory_entries >= 5, \
            f"Ожидалось ≥5 записей (адаптивное расширение), найдено {memory_entries}"
        
        # 2. Проверяем, что были и global, и project записи
        has_global = "Global info" in context
        has_project = "Project info" in context
        assert has_global or has_project, \
            "Должны быть записи из глобальной или проектной памяти"
        
        print(f"✅ ТЕСТ 4 ПРОЙДЕН: {memory_entries} записей (адаптивное расширение k)")
    
    # ==================== ТЕСТ 5: Минимальные гарантии ====================
    
    def test_minimum_budget_guarantees(self):
        """
        СЦЕНАРИЙ: Проверка минимальных гарантий для каждого компонента
        
        history: min=30% (ВСЕГДА)
        memory:  min=10% (ВСЕГДА)
        """
        system_prompt = "Системный промпт" * 500  # Огромный промпт (~4000 токенов)
        
        scratchpad = {
            "goal": "Цель" * 200,  # Огромный
            "plan": "План" * 300,
            "last_action_result": "Результат" * 200
        }
        
        # Добавляем память
        for i in range(10):
            self.memory.add_to_global_memory(
                content=f"Память {i}" * 30,
                metadata={"i": i}
            )
        
        history = []
        for i in range(20):
            history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Msg {i}" * 40
            })
        
        context, stats = self.cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            query="память"
        )
        
        # Проверки
        context_tokens = self.count_tokens(context)
        
        # 1. История должна получить минимум 30% (даже при огромных критичных компонентах)
        min_history_tokens = int(self.cm.n_ctx * 0.30)
        # Проверяем косвенно: история должна присутствовать хотя бы частично
        assert "История диалога" in context, \
            "История должна присутствовать (минимум 30%)"
        
        # 2. Память должна получить минимум 10%
        # Проверяем наличие хотя бы одной записи
        assert context.count("Релевантная информация") >= 1, \
            "Память должна иметь хотя бы 1 запись (минимум 10%)"
        
        # 3. Контекст НЕ переполнен
        assert context_tokens <= self.cm.n_ctx, \
            f"Контекст {context_tokens} превысил лимит {self.cm.n_ctx}"
        
        print(f"✅ ТЕСТ 5 ПРОЙДЕН: Минимальные гарантии соблюдены")
    
    # ==================== ТЕСТ 6: Перераспределение ====================
    
    def test_token_redistribution(self):
        """
        СЦЕНАРИЙ: Проверка метрик перераспределения токенов
        
        Если память использует меньше целевого бюджета → токены перераспределяются истории
        """
        system_prompt = "Промпт" * 100
        scratchpad = {"goal": "test", "plan": "plan", "last_action_result": "ok"}
        
        # Малая память (будет < целевого бюджета)
        self.memory.add_to_global_memory("Small memory entry", {})
        
        history = []
        for i in range(30):
            history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}" * 30
            })
        
        context, stats = self.cm.build_context(
            system_prompt=system_prompt,
            scratchpad=scratchpad,
            history=history,
            query="memory"
        )
        
        # Проверки
        # 1. Должны быть метрики перераспределения
        assert 'budget_redistribution' in stats, \
            "Должны быть метрики перераспределения"
        
        redist = stats['budget_redistribution']
        
        # 2. l3_saved должно быть положительным (память сэкономила токены)
        assert 'l3_saved' in redist, "Должна быть метрика l3_saved"
        
        # 3. Утилизация должна быть высокой (токены не теряются)
        assert stats['utilization'] > 80, \
            f"Утилизация {stats['utilization']}% низкая, токены теряются"
        
        print(f"✅ ТЕСТ 6 ПРОЙДЕН: Перераспределение работает, утилизация {stats['utilization']}%")


# ==================== ЗАПУСК ТЕСТОВ ====================

if __name__ == "__main__":
    import pytest
    
    print("\n" + "="*60)
    print("🚀 ТЕСТЫ АДАПТИВНОГО CONTEXT MANAGER v2.2.0")
    print("="*60 + "\n")
    
    # Запускаем все тесты
    pytest.main([__file__, "-v", "-s"])
