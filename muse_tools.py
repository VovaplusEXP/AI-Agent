# muse_tools.py
"""
Tools for managing MUSE memory system.

These tools allow the agent to:
- View strategic lessons
- View procedural SOPs
- View tool hints
- Manually add learnings
"""

def view_strategic_lessons(muse_memory) -> str:
    """
    View all strategic lessons in MUSE memory.
    
    Args:
        muse_memory: MUSEMemoryManager instance
        
    Returns:
        Formatted list of strategic lessons
    """
    if not muse_memory.strategic.lessons:
        return "Стратегическая память пуста. Еще нет извлеченных уроков."
    
    lines = ["📚 Стратегические уроки:"]
    
    # Sort by usage count and quality
    sorted_lessons = sorted(
        muse_memory.strategic.lessons,
        key=lambda l: l.get('usage_count', 1) * l.get('quality_score', 0.5),
        reverse=True
    )
    
    for i, entry in enumerate(sorted_lessons[:20], 1):  # Top 20
        lesson = entry['lesson']
        usage = entry.get('usage_count', 1)
        quality = entry.get('quality_score', 0.5)
        context = entry.get('context', {})
        
        lines.append(f"\n{i}. {lesson}")
        lines.append(f"   Использован: {usage} раз, Оценка: {quality:.2f}")
        
        if context.get('tool_name'):
            lines.append(f"   Инструмент: {context['tool_name']}")
    
    return "\n".join(lines)


def view_procedural_sops(muse_memory) -> str:
    """
    View all Standard Operating Procedures (SOPs) in MUSE memory.
    
    Args:
        muse_memory: MUSEMemoryManager instance
        
    Returns:
        Formatted list of SOPs
    """
    if not muse_memory.procedural.sops:
        return "Процедурная память пуста. Еще нет созданных процедур (SOPs)."
    
    lines = ["📋 Процедуры (SOPs):"]
    
    # Sort by usage and success rate
    sorted_sops = sorted(
        muse_memory.procedural.sops,
        key=lambda s: s.get('usage_count', 1) * (s.get('success_count', 0) / max(s.get('usage_count', 1), 1)),
        reverse=True
    )
    
    for i, sop in enumerate(sorted_sops[:15], 1):  # Top 15
        desc = sop['task_description']
        steps = sop['steps']
        usage = sop.get('usage_count', 1)
        success = sop.get('success_count', 0)
        success_rate = (success / max(usage, 1)) * 100
        
        lines.append(f"\n{i}. {desc[:70]}...")
        lines.append(f"   Использована: {usage} раз, Успешность: {success_rate:.0f}%")
        lines.append(f"   Шаги ({len(steps)}):")
        
        for j, step in enumerate(steps[:5], 1):  # First 5 steps
            lines.append(f"     {j}. {step}")
        
        if len(steps) > 5:
            lines.append(f"     ... и еще {len(steps) - 5} шагов")
    
    return "\n".join(lines)


def view_tool_hints(muse_memory, tool_name: str = None) -> str:
    """
    View tool usage hints from MUSE memory.
    
    Args:
        muse_memory: MUSEMemoryManager instance
        tool_name: Optional tool name to filter by
        
    Returns:
        Formatted list of tool hints
    """
    if not muse_memory.tool_memory.tool_hints:
        return "Инструментальная память пуста. Еще нет подсказок для инструментов."
    
    lines = ["🔧 Подсказки для инструментов:"]
    
    if tool_name:
        # Show hints for specific tool
        if tool_name not in muse_memory.tool_memory.tool_hints:
            return f"Нет подсказок для инструмента '{tool_name}'."
        
        hints = muse_memory.tool_memory.tool_hints[tool_name]
        lines.append(f"\nИнструмент: {tool_name}")
        
        for i, hint_entry in enumerate(hints, 1):
            hint = hint_entry['hint']
            usage = hint_entry.get('usage_count', 1)
            effectiveness = hint_entry.get('effectiveness', 0.5)
            
            lines.append(f"  {i}. {hint}")
            lines.append(f"     Использована: {usage} раз, Эффективность: {effectiveness:.2f}")
    else:
        # Show all tools with hint counts
        for tool, hints in sorted(muse_memory.tool_memory.tool_hints.items()):
            lines.append(f"\n  {tool}: {len(hints)} подсказок")
            
            # Show top 2 hints
            sorted_hints = sorted(
                hints,
                key=lambda h: h.get('effectiveness', 0.5) * 2 + h.get('usage_count', 1) * 0.1,
                reverse=True
            )
            
            for hint_entry in sorted_hints[:2]:
                lines.append(f"    • {hint_entry['hint']}")
    
    return "\n".join(lines)


def add_strategic_lesson(muse_memory, lesson: str, tool_name: str = None) -> str:
    """
    Manually add a strategic lesson to MUSE memory.
    
    Args:
        muse_memory: MUSEMemoryManager instance
        lesson: Lesson to add
        tool_name: Optional tool name for context
        
    Returns:
        Success message
    """
    context = {}
    if tool_name:
        context['tool_name'] = tool_name
    
    muse_memory.strategic.add_lesson(lesson=lesson, context=context)
    muse_memory.strategic.save()
    
    return f"✅ Стратегический урок добавлен: {lesson[:60]}..."


def add_tool_hint(muse_memory, tool_name: str, hint: str) -> str:
    """
    Manually add a tool usage hint to MUSE memory.
    
    Args:
        muse_memory: MUSEMemoryManager instance
        tool_name: Name of the tool
        hint: Usage hint
        
    Returns:
        Success message
    """
    muse_memory.tool_memory.add_hint(tool_name=tool_name, hint=hint)
    muse_memory.tool_memory.save()
    
    return f"✅ Подсказка для '{tool_name}' добавлена: {hint[:60]}..."


def compress_muse_memory(muse_memory, llm) -> str:
    """
    Manually trigger MUSE memory compression.
    
    Args:
        muse_memory: MUSEMemoryManager instance
        llm: LLM instance
        
    Returns:
        Compression report
    """
    stats_before = muse_memory.get_stats()
    
    muse_memory.compress_all(llm)
    
    stats_after = muse_memory.get_stats()
    
    lines = ["🗜️ Сжатие MUSE памяти завершено:"]
    
    lessons_before = stats_before['strategic']['lessons']
    lessons_after = stats_after['strategic']['lessons']
    lines.append(f"\n  Стратегические уроки: {lessons_before} → {lessons_after} ({lessons_before - lessons_after} удалено)")
    
    sops_before = stats_before['procedural']['sops']
    sops_after = stats_after['procedural']['sops']
    lines.append(f"  Процедуры (SOPs): {sops_before} → {sops_after} ({sops_before - sops_after} удалено)")
    
    hints_before = stats_before['tool_memory']['total_hints']
    hints_after = stats_after['tool_memory']['total_hints']
    lines.append(f"  Подсказки инструментов: {hints_before} → {hints_after} ({hints_before - hints_after} удалено)")
    
    return "\n".join(lines)
