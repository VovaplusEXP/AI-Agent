# Сравнение CLI: Оригинальный vs Enhanced

## Визуальное Сравнение

### Оригинальный CLI (cli.py)

```
Начинаем интерактивный чат.
Нажмите Ctrl+O для переключения в режим оболочки.
Введите /help для списка команд или 'exit' для выхода.
─────────────────────────────────────────────────────

[default] Вы: создай файл test.py с приветствием

Мысль: Создам простой файл с функцией приветствия
──────────────────────────────────────────────────────────────
Действие: write_file(file_path='test.py')

Выполнить это действие? ([Y]es/[N]o/[A]lways) y
```

### Enhanced CLI (enhanced_cli.py)

```
╔═══════════════════════════════════════════╗
║                                           ║
║         🤖  AI Agent Enhanced CLI         ║
║                                           ║
║         Powered by Gemma-3n-E4B          ║
║                                           ║
╚═══════════════════════════════════════════╝

╭────────────── Status ──────────────╮
│ Chat:      default                 │
│ Context:   75% free                │
│            (6,000/24,576 tokens)   │
│ Memory:    145.3 MB                │
╰────────────────────────────────────╯

╭────────────── Quick Start ──────────────╮
│  📝 Commands:     /help - show commands │
│  🔄 Switch mode:  Ctrl+O - toggle mode  │
│  📊 Statistics:   /memory - show stats  │
│  🚪 Exit:         exit or quit          │
╰─────────────────────────────────────────╯

[default] You: создай файл test.py с приветствием

╭────────── 💭 Agent Thinking ──────────╮
│ Создам простой файл с функцией        │
│ приветствия                            │
╰────────────────────────────────────────╯

🔧 Action: write_file(file_path='test.py')

─────────── Code Preview ───────────────
File: test.py
Lines: 5

╭──────────── test.py ────────────╮
│  1 def greet(name):              │
│  2     print(f"Hello, {name}!")  │
│  3                               │
│  4 if __name__ == "__main__":    │
│  5     greet("World")            │
╰──────────────────────────────────╯

Write this file? ([Y]es/[N]o/[E]dit path) y

✓ File written successfully
```

## Основные Улучшения

### 1. Визуальный Дизайн

| Элемент | Оригинал | Enhanced |
|---------|----------|----------|
| Приветствие | Простой текст | ASCII Art + панель |
| Границы | Простые линии (─) | Закругленные box (╭╮╰╯) |
| Цвета | Базовые | Богатая палитра |
| Иконки | Нет | Эмодзи для контекста (💭🔧✓✗) |
| Панели | Нет | Rich Panels везде |

### 2. Функциональность

#### Оригинальный CLI
- ✓ Базовые команды чата
- ✓ Shell режим (Ctrl+O)
- ✓ История команд
- ✗ Статус-панель
- ✗ Мониторинг контекста
- ✗ Мониторинг памяти
- ✗ Предпросмотр кода

#### Enhanced CLI
- ✓ Все функции оригинала
- ✓ **Статус-панель в реальном времени**
- ✓ **Мониторинг контекста (% свободно)**
- ✓ **Мониторинг памяти RAM**
- ✓ **Предпросмотр кода с подсветкой**
- ✓ **Команда /status**
- ✓ **Улучшенный рендеринг Markdown**
- ✓ **Цветовые индикаторы состояния**

### 3. Информативность

#### Контекст-трекер

**Оригинал:** Нет видимой информации о контексте

**Enhanced:**
```
Context:   75% free  (6,000/24,576 tokens)
           🟢 Зеленый: >50% свободно
           🟡 Желтый: 20-50% свободно  
           🔴 Красный: <20% свободно
```

#### Мониторинг Памяти

**Оригинал:** Нет

**Enhanced:**
```
Memory:    145.3 MB
           🟢 Зеленый: <1 GB
           🟡 Желтый: 1-2 GB
           🔴 Красный: >2 GB
```

### 4. Предпросмотр Кода

**Оригинал:** Файл записывается сразу после подтверждения

**Enhanced:** Показывает:
- Путь к файлу
- Количество строк
- Код с подсветкой синтаксиса
- Опции: Yes/No/Edit path

```python
╭──────────── test.py ────────────╮
│  1 def greet(name):              │  # С подсветкой!
│  2     print(f"Hello, {name}!")  │
│  3                               │
│  4 if __name__ == "__main__":    │
│  5     greet("World")            │
╰──────────────────────────────────╯

Write this file? ([Y]es/[N]o/[E]dit path)
```

### 5. Команды

#### Новые команды в Enhanced:

```
/status  - Показать детальный статус с панелью
           (контекст, память, текущий чат)
```

Все остальные команды идентичны:
- `/new`, `/switch`, `/list`
- `/save`, `/load`, `/saved`, `/delete`
- `/memory`, `/help`

### 6. Markdown Рендеринг

**Оригинал:**
```python
from rich.markdown import Markdown
self.console.print(Markdown(final_answer))
```

**Enhanced:**
```python
# То же + обрамление в панель
self.console.print(Panel(
    Markdown(final_answer),
    title="[bold green]✓ Final Answer[/bold green]",
    border_style="green",
    box=box.ROUNDED
))
```

### 7. Цветовая Схема

#### Оригинал
- `yellow` - Системные сообщения
- `cyan` - Команды
- `red` - Ошибки
- `green` - Режим shell

#### Enhanced
- `cyan` - Заголовки и акценты
- `green` - Успех и здоровые показатели
- `yellow` - Предупреждения и средние показатели
- `red` - Ошибки и критические показатели
- `magenta` - Действия агента
- `blue` - Режим чата

### 8. Производительность

| Метрика | Оригинал | Enhanced | Разница |
|---------|----------|----------|---------|
| Импорт модулей | ~0.2s | ~0.3s | +0.1s |
| Инициализация | ~1.0s | ~1.2s | +0.2s |
| Рендеринг ответа | ~0.01s | ~0.02s | +0.01s |
| Память (overhead) | 0 MB | ~5 MB | +5 MB (psutil) |

**Вывод:** Незначительное увеличение накладных расходов, приемлемо для улучшенной UX.

## Код: Ключевые Различия

### Статус-панель (новое в Enhanced)

```python
class EnhancedStatusBar:
    def __init__(self, agent: Agent):
        self.agent = agent
        self.process = psutil.Process(os.getpid())
    
    def get_context_usage(self) -> tuple[int, int, float]:
        """Возвращает: current_tokens, max_tokens, free_percent"""
        current_tokens = self.agent.last_context_stats.get('total_tokens', 0)
        max_tokens = self.agent.context_manager.max_tokens
        free_percent = ((max_tokens - current_tokens) / max_tokens * 100)
        return current_tokens, max_tokens, free_percent
    
    def get_memory_usage(self) -> tuple[float, str]:
        """Возвращает: mem_mb, formatted_string"""
        mem_mb = self.process.memory_info().rss / 1024 / 1024
        mem_str = f"{mem_mb:.1f} MB" if mem_mb < 1024 else f"{mem_mb/1024:.2f} GB"
        return mem_mb, mem_str
```

### Предпросмотр кода (новое в Enhanced)

```python
class CodePreviewDialog:
    def show(self, file_path: str, content: str, language: str = "python"):
        # Показываем код с подсветкой
        syntax = Syntax(content, language, theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax, title=f"[bold cyan]{file_path}[/bold cyan]"))
        
        # Запрашиваем подтверждение
        response = self.session.prompt("Write this file? ([Y]es/[N]o/[E]dit path) ")
        
        if response in ['e', 'edit']:
            new_path = self.session.prompt("Enter new file path: ")
            return new_path  # Можно изменить путь!
        return response in ['y', 'yes']
```

### Интеграция в цикл агента (Enhanced)

```python
# В оригинале:
if tool_name in ["write_file", "create_file"]:
    # Обычное подтверждение
    should_proceed = prompt_user()

# В Enhanced:
if tool_name in ["write_file", "create_file"]:
    # Показываем предпросмотр с подсветкой
    result = self.code_preview.show(file_path, content, language)
    
    if isinstance(result, str):  # Пользователь изменил путь
        parameters["file_path"] = result
        should_proceed = True
    else:
        should_proceed = result
```

## Обратная Совместимость

Enhanced CLI **полностью совместим** с оригиналом:
- Все команды работают идентично
- Те же сочетания клавиш (Ctrl+O)
- Та же структура истории и памяти
- Можно запускать параллельно (разные файлы)

## Рекомендации по Использованию

### Когда использовать Enhanced CLI:
- ✓ Интерактивная работа с агентом
- ✓ Нужен контроль над контекстом и памятью
- ✓ Частые операции с файлами
- ✓ Обучение/демонстрация возможностей

### Когда использовать оригинальный CLI:
- ✓ Автоматизация (скрипты)
- ✓ Минимальные зависимости
- ✓ Старые терминалы (без Unicode)
- ✓ Удаленный SSH без цветов

## Выводы

**Enhanced CLI** - это **superset** оригинального CLI, который:

1. ✓ **Не ломает** существующий функционал
2. ✓ **Добавляет** полезные фичи из gemini-cli
3. ✓ **Улучшает** user experience
4. ✓ **Минимально** влияет на производительность

**Рекомендация:** Использовать Enhanced CLI для интерактивной работы, оригинальный - для автоматизации.
