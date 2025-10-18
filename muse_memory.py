# muse_memory.py
"""
MUSE Memory System - Multi-level memory architecture for AI agents.

Implements three types of memory based on the MUSE (Plan-Execute-Reflect-Remember) approach:
1. Strategic Memory: Lessons from failures and workarounds
2. Procedural Memory: SOPs (Standard Operating Procedures) - step-by-step instructions
3. Tool Memory: Tool usage patterns and optimizations

All memories are stored in natural language for model-agnostic transfer.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class StrategicMemory:
    """
    Strategic Memory: Stores high-level lessons from failures and successful workarounds.
    
    Examples:
    - "When web_fetch fails with timeout, try web_get_structure first to check if URL is valid"
    - "Always check L3 memory before using internet_search to avoid duplicate searches"
    - "If file path is relative, use list_directory first to see available files"
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.lessons: List[Dict] = []
        self.load()
    
    def load(self):
        """Load strategic lessons from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.lessons = data.get('lessons', [])
                logger.info(f"Загружено стратегических уроков: {len(self.lessons)}")
            except Exception as e:
                logger.error(f"Ошибка загрузки стратегической памяти: {e}")
                self.lessons = []
        else:
            self.lessons = []
            logger.info("Создана новая стратегическая память")
    
    def save(self):
        """Save strategic lessons to disk."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'lessons': self.lessons,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            logger.debug("Стратегическая память сохранена")
        except Exception as e:
            logger.error(f"Ошибка сохранения стратегической памяти: {e}")
    
    def add_lesson(self, lesson: str, context: Dict = None):
        """
        Add a strategic lesson from experience.
        
        Args:
            lesson: The lesson learned (in natural language)
            context: Optional context (tool_name, error_type, etc.)
        """
        # УЛУЧШЕНО: Проверка на дубликаты и похожие записи
        lesson_lower = lesson.lower().strip()
        
        for existing in self.lessons:
            existing_lower = existing['lesson'].lower().strip()
            
            # Точное совпадение
            if existing_lower == lesson_lower:
                existing['usage_count'] = existing.get('usage_count', 1) + 1
                existing['last_seen'] = datetime.now().isoformat()
                self.save()
                logger.debug(f"Урок уже существует, обновлён счётчик использования")
                return
            
            # Проверка на очень похожие уроки (>80% совпадение слов)
            lesson_words = set(lesson_lower.split())
            existing_words = set(existing_lower.split())
            if len(lesson_words) > 3 and len(existing_words) > 3:  # Минимум 4 слова
                common_words = lesson_words & existing_words
                similarity = len(common_words) / max(len(lesson_words), len(existing_words))
                if similarity > 0.8:
                    existing['usage_count'] = existing.get('usage_count', 1) + 1
                    existing['last_seen'] = datetime.now().isoformat()
                    self.save()
                    logger.debug(f"Найден похожий урок (сходство {similarity:.0%}), обновлён счётчик")
                    return
        
        entry = {
            'lesson': lesson,
            'context': context or {},
            'created': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'usage_count': 1,
            'quality_score': 0.5  # Will be updated based on effectiveness
        }
        
        self.lessons.append(entry)
        self.save()
        logger.info(f"Добавлен стратегический урок: {lesson[:80]}...")
    
    def get_relevant_lessons(self, context: Dict, max_lessons: int = 3) -> List[str]:
        """
        Get relevant strategic lessons for current context.
        
        Args:
            context: Current context (tool_name, error_type, etc.)
            max_lessons: Maximum number of lessons to return
            
        Returns:
            List of relevant lesson texts
        """
        # Filter and sort by relevance
        relevant = []
        
        for entry in self.lessons:
            relevance = 0
            
            # Check context match
            if context.get('tool_name') and entry['context'].get('tool_name') == context.get('tool_name'):
                relevance += 2
            
            if context.get('error_type') and entry['context'].get('error_type') == context.get('error_type'):
                relevance += 2
            
            # Boost by quality score and usage count
            relevance += entry.get('quality_score', 0.5) * 2
            relevance += min(entry.get('usage_count', 1) * 0.1, 1.0)
            
            if relevance > 0:
                relevant.append((relevance, entry['lesson']))
        
        # Sort by relevance and return top max_lessons
        relevant.sort(reverse=True, key=lambda x: x[0])
        return [lesson for _, lesson in relevant[:max_lessons]]
    
    def compress(self, llm):
        """
        Compress strategic memory by merging similar lessons.
        
        Args:
            llm: LLM instance for semantic comparison
        """
        if len(self.lessons) < 10:
            return  # No need to compress yet
        
        logger.info(f"🗜️ Сжатие стратегической памяти ({len(self.lessons)} уроков)...")
        
        # Remove low-quality lessons (quality_score < 0.2, usage_count == 1)
        original_count = len(self.lessons)
        self.lessons = [
            l for l in self.lessons 
            if l.get('quality_score', 0.5) >= 0.2 or l.get('usage_count', 1) > 1
        ]
        
        removed = original_count - len(self.lessons)
        if removed > 0:
            logger.info(f"Удалено низкокачественных уроков: {removed}")
            self.save()


class ProceduralMemory:
    """
    Procedural Memory: Stores SOPs (Standard Operating Procedures).
    
    SOPs are step-by-step instructions for common subtasks.
    Examples:
    - "How to search and analyze web page: 1) internet_search 2) web_fetch 3) web_search_in_page 4) create_file"
    - "How to analyze code file: 1) read_file 2) analyze_code 3) save findings to memory"
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.sops: List[Dict] = []
        self.load()
    
    def load(self):
        """Load SOPs from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sops = data.get('sops', [])
                logger.info(f"Загружено процедур (SOPs): {len(self.sops)}")
            except Exception as e:
                logger.error(f"Ошибка загрузки процедурной памяти: {e}")
                self.sops = []
        else:
            self.sops = []
            logger.info("Создана новая процедурная память")
    
    def save(self):
        """Save SOPs to disk."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'sops': self.sops,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            logger.debug("Процедурная память сохранена")
        except Exception as e:
            logger.error(f"Ошибка сохранения процедурной памяти: {e}")
    
    def add_sop(self, task_description: str, steps: List[str], success: bool = True):
        """
        Add a new SOP from a successful task trajectory.
        
        Args:
            task_description: Description of the task
            steps: List of steps (tool calls) that led to success
            success: Whether the task was successful
        """
        if not success or len(steps) < 2:
            return  # Only store successful multi-step procedures
        
        # УЛУЧШЕНО: Проверка на похожие SOPs
        task_lower = task_description.lower().strip()
        
        for existing in self.sops:
            existing_lower = existing['task_description'].lower().strip()
            
            # Точное совпадение описания
            if existing_lower == task_lower:
                existing['usage_count'] = existing.get('usage_count', 1) + 1
                existing['last_used'] = datetime.now().isoformat()
                if success:
                    existing['success_count'] = existing.get('success_count', 0) + 1
                self.save()
                logger.debug(f"SOP уже существует, обновлён счётчик")
                return
            
            # Проверка на очень похожие задачи (>70% совпадение слов)
            task_words = set(task_lower.split())
            existing_words = set(existing_lower.split())
            if len(task_words) > 2 and len(existing_words) > 2:
                common_words = task_words & existing_words
                similarity = len(common_words) / max(len(task_words), len(existing_words))
                
                # Также проверяем похожесть шагов
                if similarity > 0.7 and len(steps) == len(existing['steps']):
                    # Если шаги совпадают на >80%, считаем это дубликатом
                    matching_steps = sum(1 for s1, s2 in zip(steps, existing['steps']) if s1 == s2)
                    step_similarity = matching_steps / len(steps)
                    
                    if step_similarity > 0.8:
                        existing['usage_count'] = existing.get('usage_count', 1) + 1
                        existing['last_used'] = datetime.now().isoformat()
                        if success:
                            existing['success_count'] = existing.get('success_count', 0) + 1
                        self.save()
                        logger.debug(f"Найдена похожая SOP (сходство задачи {similarity:.0%}, шагов {step_similarity:.0%})")
                        return
        
        entry = {
            'task_description': task_description,
            'steps': steps,
            'created': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat(),
            'usage_count': 1,
            'success_count': 1 if success else 0,
            'quality_score': 1.0 if success else 0.5
        }
        
        self.sops.append(entry)
        self.save()
        logger.info(f"Добавлена процедура (SOP): {task_description[:60]}... ({len(steps)} шагов)")
    
    def get_relevant_sop(self, task_description: str) -> Optional[Dict]:
        """
        Get relevant SOP for a task.
        
        Args:
            task_description: Description of current task
            
        Returns:
            SOP dictionary or None
        """
        # Simple keyword matching (can be improved with embeddings)
        task_lower = task_description.lower()
        
        best_match = None
        best_score = 0
        
        for sop in self.sops:
            sop_desc_lower = sop['task_description'].lower()
            
            # Count common words
            task_words = set(task_lower.split())
            sop_words = set(sop_desc_lower.split())
            common_words = task_words & sop_words
            
            if len(common_words) > 0:
                score = len(common_words) / max(len(task_words), len(sop_words))
                score *= sop.get('quality_score', 0.5)
                
                if score > best_score:
                    best_score = score
                    best_match = sop
        
        if best_score > 0.3:  # Threshold for relevance
            return best_match
        
        return None
    
    def list_sops(self) -> str:
        """Return formatted list of all SOPs."""
        if not self.sops:
            return "Процедурная память пуста."
        
        lines = ["📋 Процедуры (SOPs):"]
        for i, sop in enumerate(self.sops, 1):
            success_rate = (sop.get('success_count', 0) / max(sop.get('usage_count', 1), 1)) * 100
            lines.append(f"{i}. {sop['task_description'][:60]}... ({len(sop['steps'])} шагов, успех: {success_rate:.0f}%)")
        
        return "\n".join(lines)
    
    def compress(self):
        """Remove low-quality or rarely used SOPs."""
        if len(self.sops) < 20:
            return
        
        logger.info(f"🗜️ Сжатие процедурной памяти ({len(self.sops)} процедур)...")
        
        original_count = len(self.sops)
        
        # Remove SOPs with low success rate or single use
        self.sops = [
            sop for sop in self.sops
            if (sop.get('success_count', 0) / max(sop.get('usage_count', 1), 1)) > 0.5
            or sop.get('usage_count', 1) > 3
        ]
        
        removed = original_count - len(self.sops)
        if removed > 0:
            logger.info(f"Удалено низкокачественных процедур: {removed}")
            self.save()


class ToolMemory:
    """
    Tool Memory: Stores tool-specific optimizations and usage patterns.
    
    Examples:
    - "web_fetch: Always set timeout=30 for slow sites"
    - "read_file: Use absolute paths when possible"
    - "internet_search: Check L3 memory first to avoid duplicates"
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.tool_hints: Dict[str, List[Dict]] = {}
        self.load()
    
    def load(self):
        """Load tool memory from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tool_hints = data.get('tool_hints', {})
                total_hints = sum(len(hints) for hints in self.tool_hints.values())
                logger.info(f"Загружено подсказок для инструментов: {total_hints} (для {len(self.tool_hints)} инструментов)")
            except Exception as e:
                logger.error(f"Ошибка загрузки инструментальной памяти: {e}")
                self.tool_hints = {}
        else:
            self.tool_hints = {}
            logger.info("Создана новая инструментальная память")
    
    def save(self):
        """Save tool memory to disk."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'tool_hints': self.tool_hints,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            logger.debug("Инструментальная память сохранена")
        except Exception as e:
            logger.error(f"Ошибка сохранения инструментальной памяти: {e}")
    
    def add_hint(self, tool_name: str, hint: str, context: Dict = None):
        """
        Add a tool usage hint.
        
        Args:
            tool_name: Name of the tool
            hint: Usage hint or optimization
            context: Optional context (error avoided, performance improvement, etc.)
        """
        if tool_name not in self.tool_hints:
            self.tool_hints[tool_name] = []
        
        # УЛУЧШЕНО: Проверка на похожие подсказки
        hint_lower = hint.lower().strip()
        
        for existing in self.tool_hints[tool_name]:
            existing_lower = existing['hint'].lower().strip()
            
            # Точное совпадение
            if existing_lower == hint_lower:
                existing['usage_count'] = existing.get('usage_count', 1) + 1
                existing['last_seen'] = datetime.now().isoformat()
                self.save()
                logger.debug(f"Подсказка для '{tool_name}' уже существует, обновлён счётчик")
                return
            
            # Проверка на очень похожие подсказки (>75% совпадение слов)
            hint_words = set(hint_lower.split())
            existing_words = set(existing_lower.split())
            if len(hint_words) > 3 and len(existing_words) > 3:
                common_words = hint_words & existing_words
                similarity = len(common_words) / max(len(hint_words), len(existing_words))
                if similarity > 0.75:
                    existing['usage_count'] = existing.get('usage_count', 1) + 1
                    existing['last_seen'] = datetime.now().isoformat()
                    self.save()
                    logger.debug(f"Найдена похожая подсказка для '{tool_name}' (сходство {similarity:.0%})")
                    return
        
        entry = {
            'hint': hint,
            'context': context or {},
            'created': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'usage_count': 1,
            'effectiveness': 0.5  # Will be updated based on results
        }
        
        self.tool_hints[tool_name].append(entry)
        self.save()
        logger.info(f"Добавлена подсказка для '{tool_name}': {hint[:60]}...")
    
    def get_hints(self, tool_name: str, max_hints: int = 3) -> List[str]:
        """
        Get usage hints for a tool.
        
        Args:
            tool_name: Name of the tool
            max_hints: Maximum number of hints to return
            
        Returns:
            List of hint texts
        """
        if tool_name not in self.tool_hints:
            return []
        
        hints = self.tool_hints[tool_name]
        
        # Sort by effectiveness and usage count
        sorted_hints = sorted(
            hints,
            key=lambda h: h.get('effectiveness', 0.5) * 2 + min(h.get('usage_count', 1) * 0.1, 1.0),
            reverse=True
        )
        
        return [h['hint'] for h in sorted_hints[:max_hints]]
    
    def list_tools(self) -> str:
        """Return formatted list of tools with hints."""
        if not self.tool_hints:
            return "Инструментальная память пуста."
        
        lines = ["🔧 Инструменты с подсказками:"]
        for tool_name, hints in self.tool_hints.items():
            lines.append(f"  {tool_name}: {len(hints)} подсказок")
        
        return "\n".join(lines)
    
    def compress(self):
        """Remove low-quality hints."""
        logger.info("🗜️ Сжатие инструментальной памяти...")
        
        original_total = sum(len(hints) for hints in self.tool_hints.values())
        
        for tool_name in list(self.tool_hints.keys()):
            hints = self.tool_hints[tool_name]
            
            # Keep only effective hints or frequently used ones
            filtered = [
                h for h in hints
                if h.get('effectiveness', 0.5) > 0.3 or h.get('usage_count', 1) > 2
            ]
            
            if filtered:
                self.tool_hints[tool_name] = filtered
            else:
                del self.tool_hints[tool_name]
        
        final_total = sum(len(hints) for hints in self.tool_hints.values())
        removed = original_total - final_total
        
        if removed > 0:
            logger.info(f"Удалено низкоэффективных подсказок: {removed}")
            self.save()


class MUSEMemoryManager:
    """
    MUSE Memory Manager: Orchestrates all three types of memory.
    
    Responsibilities:
    - Load/save all memory types
    - Provide unified interface for memory access
    - Coordinate memory compression
    - Track task completion for reflection
    """
    
    def __init__(self, memory_dir: str):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize three memory types
        self.strategic = StrategicMemory(str(self.memory_dir / "strategic.json"))
        self.procedural = ProceduralMemory(str(self.memory_dir / "procedural.json"))
        self.tool_memory = ToolMemory(str(self.memory_dir / "tool_memory.json"))
        
        # Task tracking for reflection
        self.current_task: Optional[Dict] = None
        self.task_trajectory: List[Dict] = []
        
        logger.info("MUSE Memory Manager инициализирован")
    
    def start_task(self, task_description: str):
        """Mark the beginning of a task for reflection."""
        self.current_task = {
            'description': task_description,
            'started': datetime.now().isoformat(),
            'steps': []
        }
        self.task_trajectory = []
        logger.info(f"Начата задача: {task_description}")
    
    def record_step(self, tool_name: str, parameters: Dict, result: str, success: bool):
        """Record a step in the current task trajectory."""
        if self.current_task is None:
            return
        
        step = {
            'tool_name': tool_name,
            'parameters': parameters,
            'result': result[:200],  # Truncate long results
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        self.current_task['steps'].append(step)
        self.task_trajectory.append(step)
    
    def finish_task(self, success: bool, final_result: str = ""):
        """
        Mark task as finished and extract learnings.
        
        Args:
            success: Whether the task was completed successfully
            final_result: Final result or error message
        """
        if self.current_task is None:
            return
        
        self.current_task['finished'] = datetime.now().isoformat()
        self.current_task['success'] = success
        self.current_task['final_result'] = final_result[:500]
        
        logger.info(f"Задача завершена: {self.current_task['description'][:60]}... (успех: {success})")
        
        # Extract learnings from trajectory
        if success and len(self.task_trajectory) >= 2:
            # Create SOP from successful trajectory
            steps = [f"{s['tool_name']}({', '.join(f'{k}={v}' for k, v in s['parameters'].items())})" 
                     for s in self.task_trajectory if s['success']]
            
            self.procedural.add_sop(
                task_description=self.current_task['description'],
                steps=steps,
                success=True
            )
        
        # Reset for next task
        self.current_task = None
        self.task_trajectory = []
    
    def get_context_for_task(self, task_description: str, current_tool: str = None) -> str:
        """
        Get relevant memory context for current task.
        
        Args:
            task_description: Description of current task
            current_tool: Tool about to be used (optional)
            
        Returns:
            Formatted memory context string
        """
        context_parts = []
        
        # Get relevant SOP
        sop = self.procedural.get_relevant_sop(task_description)
        if sop:
            steps_str = "\n  ".join([f"{i+1}. {step}" for i, step in enumerate(sop['steps'])])
            context_parts.append(f"📋 ПРОЦЕДУРА (SOP):\n  Задача: {sop['task_description']}\n  Шаги:\n  {steps_str}")
        
        # Get strategic lessons
        lessons = self.strategic.get_relevant_lessons({'task': task_description}, max_lessons=2)
        if lessons:
            lessons_str = "\n  ".join([f"• {lesson}" for lesson in lessons])
            context_parts.append(f"💡 СТРАТЕГИЧЕСКИЕ УРОКИ:\n  {lessons_str}")
        
        # Get tool hints if tool specified
        if current_tool:
            hints = self.tool_memory.get_hints(current_tool, max_hints=2)
            if hints:
                hints_str = "\n  ".join([f"• {hint}" for hint in hints])
                context_parts.append(f"🔧 ПОДСКАЗКИ ДЛЯ '{current_tool}':\n  {hints_str}")
        
        if context_parts:
            return "🧠 ПАМЯТЬ MUSE:\n\n" + "\n\n".join(context_parts)
        
        return ""
    
    def compress_all(self, llm):
        """Compress all memory types."""
        logger.info("🗜️ Начало полного сжатия памяти MUSE...")
        
        self.strategic.compress(llm)
        self.procedural.compress()
        self.tool_memory.compress()
        
        logger.info("✅ Сжатие памяти MUSE завершено")
    
    def save_all(self):
        """Save all memory types."""
        self.strategic.save()
        self.procedural.save()
        self.tool_memory.save()
    
    def get_stats(self) -> Dict:
        """Get statistics for all memory types."""
        return {
            'strategic': {
                'lessons': len(self.strategic.lessons),
                'avg_quality': sum(l.get('quality_score', 0.5) for l in self.strategic.lessons) / max(len(self.strategic.lessons), 1)
            },
            'procedural': {
                'sops': len(self.procedural.sops),
                'avg_success_rate': sum((s.get('success_count', 0) / max(s.get('usage_count', 1), 1)) for s in self.procedural.sops) / max(len(self.procedural.sops), 1)
            },
            'tool_memory': {
                'tools_tracked': len(self.tool_memory.tool_hints),
                'total_hints': sum(len(hints) for hints in self.tool_memory.tool_hints.values())
            }
        }
