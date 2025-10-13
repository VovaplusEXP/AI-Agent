# context_manager.py
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Менеджер Контекста (Context Manager).
    Отвечает за сборку финального промпта для LLM, управляя тем, какая
    информация из разных уровней памяти (L1, L2, L3) попадет в
    ограниченное контекстное окно модели.
    
    Уровни памяти:
    - L1 (Рабочая память): Текущий scratchpad (план, цель, последнее действие)
    - L2 (Эпизодическая память): История диалога текущей сессии
    - L3 (Долгосрочная память): Векторная память (глобальная + проектная)
    """
    
    def __init__(self, llm, global_memory=None, project_memory=None, max_tokens=24576):
        self.llm = llm
        self.global_memory = global_memory  # Глобальная память (shared)
        self.project_memory = project_memory  # Проектная память (per-chat)
        self.max_tokens = max_tokens  # v3.3.1: Увеличено с 20480 до 24576 (RTX 4060: 61% → ~72% VRAM)
        
        # НОВЫЙ ПОДХОД: Приоритеты вместо жёстких лимитов
        # Приоритет 1 (критично, нельзя обрезать): system_prompt, scratchpad
        # Приоритет 2 (важно): векторная память
        # Приоритет 3 (можно обрезать): история
        
        self.token_priorities = {
            'system_prompt': {'priority': 1, 'min': 0.10, 'max': 0.20},  # 10-20%
            'l1_scratchpad': {'priority': 1, 'min': 0.05, 'max': 0.15},  # 5-15%
            'l3_memory':     {'priority': 2, 'min': 0.10, 'max': 0.30},  # 10-30%
            'l2_history':    {'priority': 3, 'min': 0.30, 'max': 0.70},  # 30-70%
            'reserve':       {'priority': 4, 'min': 0.05, 'max': 0.10}   # 5-10%
        }
        
        # Старые бюджеты для обратной совместимости (используются как целевые значения)
        self.token_budget = {
            'system_prompt': 0.15,
            'l1_scratchpad': 0.10,
            'l3_memory': 0.20,
            'l2_history': 0.50,
            'reserve': 0.05
        }
    
    def count_tokens(self, text: str) -> int:
        """Подсчитывает количество токенов в тексте."""
        if not text:
            return 0
        try:
            return len(self.llm.tokenize(text.encode('utf-8')))
        except Exception as e:
            logger.warning(f"Ошибка подсчета токенов: {e}, используем приблизительную оценку")
            return int(len(text.split()) * 1.3)  # Примерная оценка
    
    def build_context(
        self,
        system_prompt: str,
        scratchpad: Dict,
        history: List[Dict],
        current_query: str
    ) -> Tuple[List[Dict], Dict, str]:
        """
        Собирает оптимизированный контекст для LLM с АДАПТИВНЫМ распределением токенов.
        
        Новая логика:
        1. Приоритет 1 (критично): system_prompt, scratchpad - НЕ обрезаются
        2. Приоритет 2 (важно): L3 память - адаптивно расширяется если есть место
        3. Приоритет 3 (гибко): L2 история - получает ВСЁ оставшееся место
        4. Перераспределение: свободные токены отдаются по приоритетам
        
        Args:
            system_prompt: Системный промпт
            scratchpad: Рабочая память (план, цель, последнее действие)
            history: История диалога
            current_query: Текущий запрос пользователя
            
        Returns:
            Tuple[оптимизированная история, статистика, улучшенный системный промпт]
        """
        stats = {
            'total_tokens': 0,
            'system_tokens': 0,
            'scratchpad_tokens': 0,
            'memory_tokens': 0,
            'history_tokens': 0,
            'trimmed_messages': 0,
            'budget_redistribution': {}  # Новая метрика
        }
        
        # === ШАГ 1: Подсчёт КРИТИЧНЫХ компонентов (Приоритет 1) ===
        
        # 1.1 Системный промпт (НЕЛЬЗЯ обрезать)
        system_tokens = self.count_tokens(system_prompt)
        stats['system_tokens'] = system_tokens
        
        # 1.2 Scratchpad (НЕЛЬЗЯ обрезать - текущая задача)
        scratchpad_context = self._build_scratchpad_context(scratchpad)
        scratchpad_tokens = self.count_tokens(scratchpad_context)
        stats['scratchpad_tokens'] = scratchpad_tokens
        
        # === ШАГ 2: Расчёт доступного пространства ===
        
        critical_tokens = system_tokens + scratchpad_tokens
        reserve_tokens = int(self.max_tokens * self.token_priorities['reserve']['min'])
        available_tokens = self.max_tokens - critical_tokens - reserve_tokens
        
        logger.debug(f"Критичных токенов: {critical_tokens}, доступно: {available_tokens}/{self.max_tokens}")
        
        # Проверка переполнения критичных компонентов
        if critical_tokens > self.max_tokens * 0.5:
            logger.warning(f"⚠️ Критичные компоненты занимают {critical_tokens} токенов (>{self.max_tokens*0.5})")
        
        # === ШАГ 3: АДАПТИВНОЕ распределение памяти (Приоритет 2) ===
        
        # Целевой бюджет для L3 (20% от total)
        target_memory_budget = int(self.max_tokens * self.token_budget['l3_memory'])
        
        # Получаем память с АДАПТИВНЫМ лимитом
        memory_context, actual_memory_tokens = self._build_memory_context_adaptive(
            query=current_query,
            scratchpad=scratchpad,
            target_budget=target_memory_budget,
            max_budget=int(self.max_tokens * self.token_priorities['l3_memory']['max'])
        )
        
        stats['memory_tokens'] = actual_memory_tokens
        stats['budget_redistribution']['l3_saved'] = target_memory_budget - actual_memory_tokens
        
        # === ШАГ 4: ГИБКОЕ распределение истории (Приоритет 3) ===
        
        # История получает ВСЁ оставшееся место
        used_tokens = critical_tokens + actual_memory_tokens
        history_budget = available_tokens - actual_memory_tokens
        
        # Но не меньше минимума (30% от total)
        min_history_budget = int(self.max_tokens * self.token_priorities['l2_history']['min'])
        if history_budget < min_history_budget:
            logger.warning(f"⚠️ История получила {history_budget} токенов < минимума {min_history_budget}")
            # Урезаем память в пользу истории
            memory_reduction = min_history_budget - history_budget
            history_budget = min_history_budget
            logger.info(f"🔄 Перераспределение: -{memory_reduction} из L3 → +{memory_reduction} в L2")
            stats['budget_redistribution']['l3_to_l2'] = memory_reduction
        
        logger.debug(f"📊 Бюджет истории: {history_budget} токенов ({history_budget/self.max_tokens*100:.1f}%)")
        
        # Обрезаем историю под бюджет
        trimmed_history = self._trim_history(history, history_budget)
        history_tokens = sum(self.count_tokens(msg.get('content', '')) for msg in trimmed_history)
        stats['history_tokens'] = history_tokens
        stats['trimmed_messages'] = len(history) - len(trimmed_history)
        
        # Свободные токены (если история не заполнила весь бюджет)
        free_tokens = history_budget - history_tokens
        if free_tokens > 100:
            stats['budget_redistribution']['unused'] = free_tokens
            logger.debug(f"💡 Свободно {free_tokens} токенов ({free_tokens/self.max_tokens*100:.1f}%)")
        
        # === ШАГ 5: Формируем финальный контекст ===
        
        context_parts = []
        
        if memory_context:
            context_parts.append(f"ДОЛГОСРОЧНАЯ ПАМЯТЬ:\n{memory_context}\n")
        
        if scratchpad_context:
            context_parts.append(f"{scratchpad_context}\n")
        
        full_context = "---\n\n" + "\n".join(context_parts) if context_parts else ""
        enhanced_system_prompt = system_prompt + "\n" + full_context
        
        # Создаем оптимизированную историю
        optimized_history = []
        for msg in trimmed_history:
            optimized_history.append(msg)
        
        stats['total_tokens'] = used_tokens + history_tokens
        stats['utilization'] = (stats['total_tokens'] / self.max_tokens) * 100
        
        logger.debug(f"✅ Контекст собран: {stats['total_tokens']}/{self.max_tokens} токенов ({stats['utilization']:.1f}% использовано)")
        
        return optimized_history, stats, enhanced_system_prompt
    
    def _build_scratchpad_context(self, scratchpad: Dict) -> str:
        """Формирует текст из рабочей памяти (scratchpad)."""
        parts = []
        
        if scratchpad.get('main_goal'):
            parts.append(f"ТЕКУЩАЯ ЗАДАЧА: {scratchpad['main_goal']}")
        
        if scratchpad.get('plan'):
            parts.append(f"ТЕКУЩИЙ ПЛАН:\n{scratchpad['plan']}")
        
        if scratchpad.get('last_action_result'):
            parts.append(f"ПОСЛЕДНЕЕ ДЕЙСТВИЕ: {scratchpad['last_action_result'][:200]}...")
        
        return "\n\n".join(parts) if parts else ""
    
    def _build_memory_context(self, query: str, scratchpad: Dict) -> str:
        """УСТАРЕВШИЙ метод для обратной совместимости. Использует _build_memory_context_adaptive."""
        context, _ = self._build_memory_context_adaptive(
            query=query,
            scratchpad=scratchpad,
            target_budget=int(self.max_tokens * 0.20),
            max_budget=int(self.max_tokens * 0.30)
        )
        return context
    
    def _build_memory_context_adaptive(
        self, 
        query: str, 
        scratchpad: Dict, 
        target_budget: int,
        max_budget: int
    ) -> Tuple[str, int]:
        """
        АДАПТИВНО получает контекст из долгосрочной памяти.
        
        Логика:
        1. Начинаем с минимального k (Top-2 global, Top-3 project)
        2. Если токенов < target_budget И память не пустая → увеличиваем k
        3. Если токенов > max_budget → уменьшаем записи
        4. Возвращаем (контекст, реальное количество токенов)
        """
        parts = []
        
        # Формируем поисковый запрос
        search_query = query
        if scratchpad.get('main_goal'):
            search_query = f"{scratchpad['main_goal']} {query}"
        
        # === АДАПТИВНЫЙ поиск в глобальной памяти ===
        global_results = []
        if self.global_memory:
            # Начинаем с k=2, можем расширить до k=5
            k_global = 2
            global_results = self.global_memory.search(search_query, k=k_global)
            
            # Если есть результаты и токенов мало - расширяем
            current_tokens = self.count_tokens("\n".join(global_results))
            if global_results and current_tokens < target_budget * 0.4:  # 40% от target для global
                k_global = min(5, len(global_results) + 3)
                global_results = self.global_memory.search(search_query, k=k_global)
                logger.debug(f"🔄 Расширили global memory: k={k_global}")
        
        if global_results:
            parts.append("📚 Общие знания:")
            for i, result in enumerate(global_results, 1):
                # Адаптивная длина: если места мало - короче
                max_len = 150 if len(global_results) <= 3 else 100
                parts.append(f"  {i}. {result[:max_len]}...")
        
        # === АДАПТИВНЫЙ поиск в проектной памяти ===
        project_results = []
        if self.project_memory:
            k_project = 3
            project_results = self.project_memory.search(search_query, k=k_project)
            
            # Если есть результаты и токенов мало - расширяем
            current_tokens = self.count_tokens("\n".join(parts))
            if project_results and current_tokens < target_budget * 0.6:  # 60% от target для project
                k_project = min(7, len(project_results) + 4)
                project_results = self.project_memory.search(search_query, k=k_project)
                logger.debug(f"🔄 Расширили project memory: k={k_project}")
        
        if project_results:
            parts.append("\n🔬 Контекст проекта:")
            for i, result in enumerate(project_results, 1):
                max_len = 150 if len(project_results) <= 4 else 100
                parts.append(f"  {i}. {result[:max_len]}...")
        
        # Формируем финальный контекст
        context = "\n".join(parts) if parts else ""
        actual_tokens = self.count_tokens(context)
        
        # === ОБРЕЗКА если превышен max_budget ===
        if actual_tokens > max_budget:
            logger.warning(f"⚠️ Память превысила max_budget: {actual_tokens} > {max_budget}")
            # Обрезаем последние записи (они менее релевантны)
            while actual_tokens > max_budget and len(parts) > 5:
                parts.pop()  # Удаляем последнюю запись
                context = "\n".join(parts)
                actual_tokens = self.count_tokens(context)
                logger.debug(f"🔄 Обрезали память до {actual_tokens} токенов")
        
        logger.debug(f"💾 L3 память: {actual_tokens}/{target_budget} токенов (target), {len(global_results)+len(project_results)} записей")
        
        return context, actual_tokens
    
    def _trim_history(self, history: List[Dict], token_budget: int) -> List[Dict]:
        """
        Умная обрезка истории с сохранением важного контекста.
        
        Стратегия:
        1. Всегда сохраняем последние N сообщений (свежий контекст)
        2. Из старых сообщений сохраняем те, что содержат важные действия
        """
        if not history:
            return []
        
        # Подсчитываем токены с конца
        trimmed = []
        current_tokens = 0
        
        # Сначала берем последние сообщения (самые важные)
        for msg in reversed(history):
            msg_tokens = self.count_tokens(msg.get('content', ''))
            if current_tokens + msg_tokens <= token_budget:
                trimmed.insert(0, msg)
                current_tokens += msg_tokens
            else:
                # Пытаемся сократить сообщение, если оно очень длинное
                if msg_tokens > token_budget * 0.3:  # Если больше 30% бюджета
                    shortened_content = msg.get('content', '')[:500] + "..."
                    shortened_msg = msg.copy()
                    shortened_msg['content'] = shortened_content
                    trimmed.insert(0, shortened_msg)
                break
        
        return trimmed
    
    def get_context_stats(self, history: List[Dict], system_prompt: str = "") -> Dict:
        """Возвращает статистику текущего контекста."""
        total_tokens = sum(self.count_tokens(msg.get('content', '')) for msg in history)
        if system_prompt:
            total_tokens += self.count_tokens(system_prompt)
        
        return {
            'total_tokens': total_tokens,
            'max_tokens': self.max_tokens,
            'usage_percent': (total_tokens / self.max_tokens) * 100,
            'messages_count': len(history),
            'available_tokens': self.max_tokens - total_tokens
        }
