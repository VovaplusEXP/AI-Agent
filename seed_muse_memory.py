# seed_muse_memory.py
"""
Seed MUSE memory with initial strategic lessons and tool hints.

This script pre-populates MUSE memory with common best practices
to help the agent avoid common mistakes from the start.
"""

import json
from pathlib import Path
from datetime import datetime


def seed_strategic_memory(memory_path: Path):
    """Seed strategic memory with common lessons."""
    
    lessons = [
        {
            "lesson": "Всегда проверяй L3 память перед использованием internet_search - возможно информация уже есть",
            "context": {"tool_name": "internet_search"},
            "created": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "usage_count": 1,
            "quality_score": 0.8
        },
        {
            "lesson": "После web_fetch ОБЯЗАТЕЛЬНО используй web_search_in_page для извлечения данных - web_fetch возвращает только HTML",
            "context": {"tool_name": "web_fetch"},
            "created": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "usage_count": 1,
            "quality_score": 0.9
        },
        {
            "lesson": "Не повторяй web_fetch на том же URL - информация уже загружена, используй web_search_in_page",
            "context": {"tool_name": "web_fetch"},
            "created": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "usage_count": 1,
            "quality_score": 0.9
        },
        {
            "lesson": "При ошибке 'file not found' сначала используй list_directory чтобы увидеть доступные файлы",
            "context": {"tool_name": "read_file", "error_type": "not_found"},
            "created": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "usage_count": 1,
            "quality_score": 0.8
        },
        {
            "lesson": "Используй абсолютные пути для файлов когда это возможно - это предотвращает ошибки",
            "context": {"tool_name": "read_file"},
            "created": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "usage_count": 1,
            "quality_score": 0.7
        },
        {
            "lesson": "После получения важной информации СРАЗУ сохрани её в файл - не откладывай на потом",
            "context": {"tool_name": "create_file"},
            "created": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "usage_count": 1,
            "quality_score": 0.8
        },
        {
            "lesson": "Если задача требует анализа кода, используй analyze_code после read_file - не пропускай этот шаг",
            "context": {"tool_name": "analyze_code"},
            "created": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "usage_count": 1,
            "quality_score": 0.7
        },
        {
            "lesson": "При timeout ошибке попробуй повторить запрос или используй альтернативный источник",
            "context": {"error_type": "timeout"},
            "created": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "usage_count": 1,
            "quality_score": 0.6
        }
    ]
    
    data = {
        "lessons": lessons,
        "last_updated": datetime.now().isoformat()
    }
    
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    with open(memory_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Seeded {len(lessons)} strategic lessons to {memory_path}")


def seed_procedural_memory(memory_path: Path):
    """Seed procedural memory with common SOPs."""
    
    sops = [
        {
            "task_description": "Поиск информации в интернете и сохранение в файл",
            "steps": [
                "internet_search(query='запрос')",
                "web_fetch(url='найденный_url')",
                "web_search_in_page(url='тот_же_url', query='что_ищем')",
                "create_file(file_path='result.txt', content='найденная_информация')",
                "finish(final_answer='информация сохранена')"
            ],
            "created": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "usage_count": 1,
            "success_count": 1,
            "quality_score": 0.9
        },
        {
            "task_description": "Анализ кода файла и сохранение результатов",
            "steps": [
                "list_directory(directory_path='.')",
                "read_file(file_path='файл.py')",
                "analyze_code(code='прочитанный_код', language='python')",
                "create_file(file_path='analysis.txt', content='результаты_анализа')",
                "finish(final_answer='анализ завершен')"
            ],
            "created": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "usage_count": 1,
            "success_count": 1,
            "quality_score": 0.8
        },
        {
            "task_description": "Чтение и редактирование файла",
            "steps": [
                "read_file(file_path='файл.txt')",
                "replace_in_file(file_path='файл.txt', old_text='старый_текст', new_text='новый_текст')",
                "read_file(file_path='файл.txt')",
                "finish(final_answer='файл успешно изменен')"
            ],
            "created": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "usage_count": 1,
            "success_count": 1,
            "quality_score": 0.8
        }
    ]
    
    data = {
        "sops": sops,
        "last_updated": datetime.now().isoformat()
    }
    
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    with open(memory_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Seeded {len(sops)} procedural SOPs to {memory_path}")


def seed_tool_memory(memory_path: Path):
    """Seed tool memory with common hints."""
    
    tool_hints = {
        "internet_search": [
            {
                "hint": "Проверь L3 память перед поиском - информация может быть уже там",
                "context": {},
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "usage_count": 1,
                "effectiveness": 0.8
            },
            {
                "hint": "Формулируй запрос конкретно - избегай общих слов",
                "context": {},
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "usage_count": 1,
                "effectiveness": 0.7
            }
        ],
        "web_fetch": [
            {
                "hint": "После web_fetch ВСЕГДА используй web_search_in_page для извлечения данных",
                "context": {},
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "usage_count": 1,
                "effectiveness": 0.9
            },
            {
                "hint": "Не повторяй web_fetch на том же URL - информация уже есть в контексте",
                "context": {},
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "usage_count": 1,
                "effectiveness": 0.9
            }
        ],
        "web_search_in_page": [
            {
                "hint": "Используй конкретные ключевые слова для поиска в HTML",
                "context": {},
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "usage_count": 1,
                "effectiveness": 0.7
            }
        ],
        "read_file": [
            {
                "hint": "При ошибке 'not found' используй list_directory чтобы увидеть доступные файлы",
                "context": {},
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "usage_count": 1,
                "effectiveness": 0.8
            },
            {
                "hint": "Предпочитай абсолютные пути относительным",
                "context": {},
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "usage_count": 1,
                "effectiveness": 0.6
            }
        ],
        "create_file": [
            {
                "hint": "Сохраняй важную информацию сразу - не откладывай на потом",
                "context": {},
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "usage_count": 1,
                "effectiveness": 0.8
            }
        ],
        "analyze_code": [
            {
                "hint": "Обязательно используй этот инструмент если задача требует анализа кода",
                "context": {},
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "usage_count": 1,
                "effectiveness": 0.7
            }
        ]
    }
    
    data = {
        "tool_hints": tool_hints,
        "last_updated": datetime.now().isoformat()
    }
    
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    with open(memory_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    total_hints = sum(len(hints) for hints in tool_hints.values())
    print(f"✅ Seeded {total_hints} tool hints for {len(tool_hints)} tools to {memory_path}")


def main():
    """Seed all MUSE memory components."""
    
    base_path = Path(__file__).parent / "memory" / "muse"
    
    print("🌱 Seeding MUSE memory with initial knowledge...")
    
    seed_strategic_memory(base_path / "strategic.json")
    seed_procedural_memory(base_path / "procedural.json")
    seed_tool_memory(base_path / "tool_memory.json")
    
    print("\n✅ MUSE memory seeding complete!")
    print(f"📁 Memory location: {base_path}")
    print("\n💡 The agent will now start with these pre-seeded learnings.")


if __name__ == "__main__":
    main()
