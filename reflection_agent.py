# reflection_agent.py
"""
Reflection Agent: Evaluates task completion and extracts learnings.

The reflection agent:
1. Checks if the goal was truly achieved based on observations
2. Extracts strategic lessons from failures
3. Creates SOPs from successful trajectories
4. Identifies tool usage patterns
5. Provides feedback for memory compression
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ReflectionAgent:
    """
    Reflection agent that evaluates task completion and extracts learnings.
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def evaluate_task_completion(
        self,
        goal: str,
        final_result: str,
        trajectory: List[Dict]
    ) -> Tuple[bool, str, List[str]]:
        """
        Evaluate if the task goal was truly achieved.
        
        Args:
            goal: Original task goal
            final_result: Final result from the agent
            trajectory: List of steps taken (tool calls and results)
            
        Returns:
            Tuple of (success: bool, evaluation: str, learnings: List[str])
        """
        logger.info("🤔 Reflection Agent: Оценка завершения задачи...")
        
        # Build context from trajectory
        trajectory_summary = self._summarize_trajectory(trajectory)
        
        # Prompt for evaluation
        prompt = f"""Ты - агент рефлексии. Оцени, была ли задача выполнена УСПЕШНО.

ЗАДАЧА: {goal}

ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:
{final_result[:1000]}

ВЫПОЛНЕННЫЕ ШАГИ:
{trajectory_summary}

Проанализируй и ответь в СТРОГОМ ФОРМАТЕ:

<SUCCESS>yes или no</SUCCESS>
<REASON>Краткое объяснение (1-2 предложения)</REASON>
<LESSONS>
- Урок 1 (если есть)
- Урок 2 (если есть)
</LESSONS>

КРИТЕРИИ УСПЕХА:
- Задача выполнена полностью (не частично)
- Результат соответствует запросу
- Нет критических ошибок

Пример 1 (успех):
<SUCCESS>yes</SUCCESS>
<REASON>Информация о Python 3.13 найдена и сохранена в файл. Задача выполнена.</REASON>
<LESSONS>
- Использование web_search_in_page после web_fetch эффективно для извлечения данных
- Создание файла сразу после получения информации предотвращает потерю данных
</LESSONS>

Пример 2 (неудача):
<SUCCESS>no</SUCCESS>
<REASON>Задача требовала анализ кода, но агент только прочитал файл и не проанализировал его.</REASON>
<LESSONS>
- После read_file нужно использовать analyze_code для полного анализа
- Не завершать задачу без проверки выполнения всех требований
</LESSONS>"""

        try:
            messages = [{"role": "user", "content": prompt}]
            output = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=512,
                temperature=0.2  # Low temperature for consistent evaluation
            )
            
            response = output['choices'][0]['message']['content'].strip()
            
            # Parse response
            success = self._parse_success(response)
            reason = self._parse_reason(response)
            lessons = self._parse_lessons(response)
            
            logger.info(f"✅ Оценка: {'УСПЕХ' if success else 'НЕУДАЧА'} - {reason}")
            if lessons:
                logger.info(f"📚 Извлечено уроков: {len(lessons)}")
            
            return success, reason, lessons
            
        except Exception as e:
            logger.error(f"❌ Ошибка в reflection agent: {e}")
            # Fallback: simple heuristic
            success = "ошибка" not in final_result.lower() and len(final_result) > 50
            return success, f"Автоматическая оценка (ошибка LLM): {e}", []
    
    def _summarize_trajectory(self, trajectory: List[Dict]) -> str:
        """Summarize trajectory for reflection."""
        if not trajectory:
            return "Нет выполненных шагов"
        
        summary_lines = []
        for i, step in enumerate(trajectory[-10:], 1):  # Last 10 steps
            tool = step.get('tool_name', 'unknown')
            success = "✅" if step.get('success', False) else "❌"
            result_preview = step.get('result', '')[:60]
            summary_lines.append(f"{i}. {success} {tool}: {result_preview}...")
        
        return "\n".join(summary_lines)
    
    def _parse_success(self, response: str) -> bool:
        """Parse success from response."""
        match = re.search(r'<SUCCESS>\s*(yes|no)\s*</SUCCESS>', response, re.IGNORECASE)
        if match:
            return match.group(1).lower() == 'yes'
        
        # Fallback: check for keywords
        return 'успех' in response.lower() or 'yes' in response.lower()
    
    def _parse_reason(self, response: str) -> str:
        """Parse reason from response."""
        match = re.search(r'<REASON>\s*(.+?)\s*</REASON>', response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return "Причина не указана"
    
    def _parse_lessons(self, response: str) -> List[str]:
        """Parse lessons from response."""
        match = re.search(r'<LESSONS>\s*(.+?)\s*</LESSONS>', response, re.DOTALL | re.IGNORECASE)
        if not match:
            return []
        
        lessons_text = match.group(1).strip()
        
        # Parse bullet points
        lessons = []
        for line in lessons_text.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('•'):
                lesson = line[1:].strip()
                if lesson and len(lesson) > 10:
                    lessons.append(lesson)
        
        return lessons
    
    def extract_tool_patterns(self, trajectory: List[Dict]) -> Dict[str, List[str]]:
        """
        Extract tool usage patterns from trajectory.
        
        Args:
            trajectory: List of steps taken
            
        Returns:
            Dict mapping tool_name to list of usage hints
        """
        patterns = {}
        
        # Look for successful tool sequences
        for i in range(len(trajectory) - 1):
            current = trajectory[i]
            next_step = trajectory[i + 1]
            
            if current.get('success') and next_step.get('success'):
                tool1 = current.get('tool_name')
                tool2 = next_step.get('tool_name')
                
                # Record successful sequences
                hint = f"После {tool1} эффективно использовать {tool2}"
                
                if tool1 not in patterns:
                    patterns[tool1] = []
                
                if hint not in patterns[tool1]:
                    patterns[tool1].append(hint)
        
        # Look for parameter patterns
        tool_params = {}
        for step in trajectory:
            if step.get('success'):
                tool = step.get('tool_name')
                params = step.get('parameters', {})
                
                if tool not in tool_params:
                    tool_params[tool] = []
                
                tool_params[tool].append(params)
        
        # Analyze parameter patterns
        for tool, params_list in tool_params.items():
            if len(params_list) >= 2:
                # Find common parameters
                common_keys = set(params_list[0].keys())
                for params in params_list[1:]:
                    common_keys &= set(params.keys())
                
                if common_keys:
                    if tool not in patterns:
                        patterns[tool] = []
                    
                    hint = f"Часто используемые параметры: {', '.join(common_keys)}"
                    if hint not in patterns[tool]:
                        patterns[tool].append(hint)
        
        return patterns
    
    def identify_failure_causes(self, trajectory: List[Dict]) -> List[Dict]:
        """
        Identify causes of failures in trajectory.
        
        Args:
            trajectory: List of steps taken
            
        Returns:
            List of failure analysis dicts
        """
        failures = []
        
        for i, step in enumerate(trajectory):
            if not step.get('success', True):
                tool = step.get('tool_name')
                result = step.get('result', '')
                
                # Categorize error
                error_type = self._categorize_error(result)
                
                # Look for context (previous steps)
                context = []
                if i > 0:
                    context.append(trajectory[i-1].get('tool_name'))
                
                failure = {
                    'tool': tool,
                    'error_type': error_type,
                    'error_message': result[:200],
                    'context': context,
                    'step_number': i
                }
                
                failures.append(failure)
        
        return failures
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message."""
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower or 'timed out' in error_lower:
            return 'timeout'
        elif 'not found' in error_lower or '404' in error_lower:
            return 'not_found'
        elif 'permission' in error_lower or 'access denied' in error_lower:
            return 'permission'
        elif 'invalid' in error_lower or 'syntax' in error_lower:
            return 'invalid_input'
        elif 'connection' in error_lower or 'network' in error_lower:
            return 'network'
        else:
            return 'unknown'
    
    def should_compress_memory(self, memory_stats: Dict) -> Tuple[bool, str]:
        """
        Decide if memory should be compressed.
        
        Args:
            memory_stats: Statistics about current memory state
            
        Returns:
            Tuple of (should_compress: bool, reason: str)
        """
        # Compress if strategic memory has > 50 lessons
        if memory_stats.get('strategic', {}).get('lessons', 0) > 50:
            return True, "Стратегическая память содержит более 50 уроков"
        
        # Compress if procedural memory has > 100 SOPs
        if memory_stats.get('procedural', {}).get('sops', 0) > 100:
            return True, "Процедурная память содержит более 100 процедур"
        
        # Compress if tool memory has > 200 hints
        if memory_stats.get('tool_memory', {}).get('total_hints', 0) > 200:
            return True, "Инструментальная память содержит более 200 подсказок"
        
        # Compress if average quality is low
        if memory_stats.get('strategic', {}).get('avg_quality', 1.0) < 0.4:
            return True, "Средняя оценка качества стратегических уроков низкая"
        
        return False, "Сжатие не требуется"
